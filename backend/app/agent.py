"""Saans conversational agent.

Primary mode: Strands Agents SDK (AWS open-source) with Gemini
(``gemini-2.5-flash``), tools grounded in our own advisory engine.

Fallback mode: when ``GEMINI_API_KEY`` is absent (or the model call fails),
a transparent rule-based fallback answers from the same engine and says so.
The endpoint never crashes for lack of a key.
"""

import os

from strands import Agent, tool

from . import advisory
from . import data as data_mod

MODEL_ID = "gemini-2.5-flash"

SYSTEM_PROMPT = (
    "You are Saans, a plain-language air-safety advisor for Indian parents and teachers. "
    "You help decide whether children should play or exercise outdoors, go to school, "
    "or wear masks, based on air-quality data.\n"
    "Rules:\n"
    "- Ground EVERY claim about air quality in the output of your tools. Never invent AQI numbers.\n"
    "- Use the get_school_advisory tool for school-day decisions; it already combines current AQI, "
    "the 6-hour forecast peak, and the school checklist.\n"
    "- Timing questions ('morning PT', 'afternoon sports', 'tomorrow') must be answered from the "
    "best_windows the tool returns, filtered to the requested part of day and the school's "
    "operating hours. Never recommend an evening window for a morning question.\n"
    "- Answer in plain, short English. If the user writes in Hindi or Hinglish, reply in the same style.\n"
    "- Keep answers short and actionable. Write times like '10 AM', never raw ISO timestamps.\n"
    "- On medical questions (asthma, breathing trouble, inhalers, allergies), add exactly one line: "
    "\"I'm not a doctor — please check with your child's paediatrician for medical advice.\"\n"
    "- AQI numbers here are indicative hourly model values (Open-Meteo), not official CPCB 24-hour averages; "
    "say 'indicative' if the user asks how reliable the numbers are."
)

MEDICAL_WORDS = ("asthma", "inhaler", "breath", "doctor", "paediatric",
                 "pediatric", "allerg", "medical", "cough", "wheez")


def agent_mode():
    """'strands' when a Gemini key is configured, else 'fallback'."""
    if os.environ.get("GEMINI_API_KEY"):
        return "strands"
    return "fallback"


def _gemini_model():
    """GeminiModel wired through our egress-hardened HTTP client."""
    from strands.models.gemini import GeminiModel
    from google import genai
    # genai builds both sync and async httpx clients; harden both against
    # this sandbox's broken no_proxy parsing.
    http_client = data_mod.egress_httpx_client(timeout=60.0)
    async_client = data_mod.egress_async_httpx_client(timeout=60.0)
    client = genai.Client(
        api_key=os.environ["GEMINI_API_KEY"],
        http_options={"httpx_client": http_client,
                      "httpx_async_client": async_client},
    )
    return GeminiModel(model_id=MODEL_ID, client=client)


# ---------------------------------------------------------------- tools

@tool
def get_current_aqi(lat: float, lon: float) -> dict:
    """Get the current indicative AQI for a location.

    Args:
        lat: latitude in degrees (-90 to 90)
        lon: longitude in degrees (-180 to 180)
    """
    adv = advisory.school_advisory(lat, lon)
    cur = adv["current"]
    return {
        "aqi": cur["aqi"], "category": cur["category"],
        "dominant_pollutant": cur["dominant"],
        "pollutants_ug_m3": cur["pollutants"],
        "as_of": cur["time"].isoformat(),
        "source": adv["source"], "data_status": adv["data_status"],
    }


@tool
def get_forecast_summary(lat: float, lon: float, hours: int = 24) -> dict:
    """Summarise the AQI forecast for a location.

    Args:
        lat: latitude in degrees (-90 to 90)
        lon: longitude in degrees (-180 to 180)
        hours: how many hours ahead to summarise (1-72)
    """
    hours = max(1, min(int(hours or 24), 72))
    adv = advisory.school_advisory(lat, lon)
    aq_data = data_mod.fetch_air_quality(lat, lon)
    rows = advisory.hourly_series(aq_data)
    start = aq_data["current_idx"]
    sel = rows[start:start + hours]
    peak = max(sel, key=lambda r: r["aqi"])
    cleanest = min(sel, key=lambda r: r["aqi"])
    return {
        "hours_covered": len(sel),
        "peak": {"aqi": peak["aqi"], "category": peak["category"],
                 "at": peak["time"].isoformat()},
        "cleanest": {"aqi": cleanest["aqi"], "category": cleanest["category"],
                     "at": cleanest["time"].isoformat()},
        "source": adv["source"], "data_status": adv["data_status"],
    }


@tool
def get_school_advisory(lat: float, lon: float) -> dict:
    """Get the school-day advisory: call level, 6h peak, best low-AQI windows, checklist.

    Args:
        lat: latitude in degrees (-90 to 90)
        lon: longitude in degrees (-180 to 180)
    """
    adv = advisory.school_advisory(lat, lon)
    return {
        "call_level": adv["level"], "headline": adv["headline"],
        "detail": adv["detail"], "aqi_now": adv["aqi_now"],
        "category": adv["category"], "peak_6h": adv["peak_6h"],
        "best_windows": adv["best_windows"], "checklist": adv["checklist"],
        "source": adv["source"], "data_status": adv["data_status"],
    }


# ---------------------------------------------------------------- chat

def _extract_text(result):
    """Pull plain text out of a Strands AgentResult, defensively."""
    msg = getattr(result, "message", None)
    if isinstance(msg, dict):
        parts = [b["text"] for b in msg.get("content", [])
                 if isinstance(b, dict) and b.get("text")]
        if parts:
            return "\n".join(parts).strip()
    text = str(result).strip()
    return text


def _fmt_time(iso):
    """'2026-10-11T10:00:00+05:30' -> '10 AM'."""
    try:
        from datetime import datetime
        return datetime.fromisoformat(iso).strftime("%-I %p")
    except (ValueError, TypeError):
        return iso


_TIMING_WORDS = {
    "morning": ("morning", ("morning", "subah", "am ", "a.m.", "pt ", "assembly")),
    "afternoon": ("afternoon", ("afternoon", "dopahar", "pm ", "p.m.", "sports", "games")),
}


def _detect_preferred(message):
    msg_l = (message or "").lower()
    for preferred, words in _TIMING_WORDS.values():
        if any(w in msg_l for w in words):
            return preferred
    return None


def _detect_duration(message):
    import re
    m = re.search(r"(\d{2,3})\s*(min|minute)", (message or "").lower())
    if m:
        return max(15, min(int(m.group(1)), 180))
    return None


def _fallback_reply(message, lat, lon, note=None):
    """Rule-based answer built from the advisory engine. Always transparent.

    Grounded in the same deterministic decision object as the dashboard and
    bulletin — never invents readings or overrides thresholds.
    """
    adv = advisory.school_advisory(lat, lon)
    lines = []
    if note:
        lines.append(note)
    lines.append(f"**{adv['action_label']}** — {adv['headline']}")
    lines.append(f"Indicative AQI {adv['aqi_now']} ({adv['category']}), "
                 f"dominant pollutant {adv['dominant']}. "
                 f"6-hour peak: AQI {adv['peak_6h']['aqi']} around "
                 f"{_fmt_time(adv['peak_6h']['at'])}.")

    msg_l = (message or "").lower()
    timing_q = any(w in msg_l for w in
                   ("when", "best time", "what time", "morning", "afternoon",
                    "evening", "pt", "sports", "assembly", "outdoor", "play"))
    if timing_q:
        preferred = _detect_preferred(message)
        duration = _detect_duration(message)
        aq_data = data_mod.fetch_air_quality(lat, lon)
        rows = advisory.hourly_series(aq_data)
        plan = advisory.plan_activity(
            rows[aq_data["current_idx"]:], school=None,
            activity="outdoor activity", duration_min=duration,
            preferred=preferred)
        if plan["recommendation"] == "outdoor_slot":
            s = plan["slot"]
            lines.append(f"Best time: {_fmt_time(s['start'])}–{_fmt_time(s['end'])} "
                         f"(AQI ~{s['aqi']}). {plan['reason']}")
        else:
            lines.append(plan["reason"])
    elif adv["best_windows"]:
        w = adv["best_windows"][0]
        lines.append(f"Cleanest window in school hours: {_fmt_time(w['start'])}–"
                     f"{_fmt_time(w['end'])} (AQI ~{w['aqi']}).")
    elif adv["windows_note"]:
        lines.append(adv["windows_note"] + ".")

    lines.append("Checklist: " + "; ".join(adv["checklist"][:3]) + ".")
    if any(w in msg_l for w in MEDICAL_WORDS):
        lines.append("I'm not a doctor — please check with your child's "
                     "paediatrician for medical advice.")
    lines.append("(Indicative hourly model data from Open-Meteo, not an official CPCB value.)")
    return "\n".join(lines)


def chat(message, lat, lon, history=None):
    """Return (reply, mode, sources). Never raises on missing key."""
    mode = agent_mode()
    sources = ["open-meteo (modelled) air quality via the Saans advisory engine"]

    if mode == "strands":
        try:
            model = _gemini_model()
            agent = Agent(
                model=model,
                tools=[get_current_aqi, get_forecast_summary, get_school_advisory],
                system_prompt=SYSTEM_PROMPT,
            )
            convo = []
            for turn in history or []:
                role = turn.get("role")
                if role in ("user", "assistant"):
                    convo.append(f"{role}: {turn.get('content', '')}")
            prompt = ""
            if convo:
                prompt += "Conversation so far:\n" + "\n".join(convo) + "\n\n"
            prompt += (f"The user is asking about location lat={lat}, lon={lon}. "
                       f"Use your tools with these coordinates.\nUser: {message}")
            result = agent(prompt)
            return _extract_text(result), "strands", sources
        except Exception as exc:  # transparent degradation, never a 500
            note = ("Note: the AI agent was unavailable just now, so this is a "
                    "rule-based answer from the advisory engine.")
            try:
                return _fallback_reply(message, lat, lon, note=note), "fallback", sources
            except data_mod.AQServiceError:
                raise

    return _fallback_reply(message, lat, lon), "fallback", sources
