"""Saans backend — FastAPI app.

All endpoints are prefixed /api. JSON everywhere, CORS allow-all (hackathon demo).
Bad lat/lon → 422 (FastAPI validation). Upstream Open-Meteo unreachable → 503.
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

import os

from . import advisory, agent, data, stores
from .data import AQServiceError, IST

VERSION = "1.0.0"

app = FastAPI(title="Saans — school air-safety API", version=VERSION)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)


@app.exception_handler(AQServiceError)
async def _aq_service_error(_request, exc):
    return JSONResponse(status_code=503, content={"detail": str(exc)})


@app.exception_handler(ValueError)
async def _value_error(_request, exc):
    return JSONResponse(status_code=422, content={"detail": str(exc)})


# ---------------------------------------------------------------- models

class SchoolIn(BaseModel):
    name: str = Field(..., min_length=1)
    city: str = Field(..., min_length=1)
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)
    contact: str | None = None
    hours: dict | None = None  # {"start": "08:00", "end": "15:00"} IST
    days: list[int] | None = None  # 0=Mon..6=Sun, default Mon–Sat
    pt_duration_min: int | None = Field(default=None, ge=15, le=180)


class ActionIn(BaseModel):
    action: str = Field(..., min_length=1)
    recorded_by: str = Field(..., min_length=1, max_length=80)
    reason: str | None = Field(default=None, max_length=280)
    date: str | None = None  # YYYY-MM-DD, defaults to today IST


class PlanIn(BaseModel):
    activity: str = Field(default="PT", max_length=40)
    duration_min: int | None = Field(default=None, ge=15, le=180)
    preferred: str | None = Field(default=None, pattern="^(morning|afternoon)$")


class ChatIn(BaseModel):
    message: str = Field(..., min_length=1)
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)
    history: list[dict] = Field(default_factory=list)


def _latlon(lat: float = Query(..., ge=-90, le=90),
            lon: float = Query(..., ge=-180, le=180)):
    return lat, lon


# ---------------------------------------------------------------- health

def _public_school(school, include_private=False):
    """Mask contact details in list views (privacy); full record on get."""
    s = dict(school)
    if not include_private:
        s.pop("contact", None)
        masked = []
        for sub in s.get("subscriptions", []):
            sub = dict(sub)
            t = sub.get("target", "")
            sub["target"] = (t[:3] + "…" + t[-2:]) if len(t) > 5 else "…"
            masked.append(sub)
        s["subscriptions"] = masked
    return s


@app.get("/api/health")
def health():
    return {"status": "ok", "agent": agent.agent_mode(), "version": VERSION}


# ---------------------------------------------------------------- search

@app.get("/api/search")
def search(q: str = Query(..., min_length=1), limit: int = Query(8, ge=1, le=20)):
    return {"results": data.search_places(q, limit)}


# ---------------------------------------------------------------- AQI

@app.get("/api/aqi/current")
def aqi_current(lat: float = Query(..., ge=-90, le=90),
                lon: float = Query(..., ge=-180, le=180)):
    adv = advisory.school_advisory(lat, lon)
    cur = adv["current"]
    return {
        "aqi": cur["aqi"],
        "category": cur["category"],
        "color": cur["color"],
        "dominant": cur["dominant"],
        "pollutants": cur["pollutants"],  # µg/m³ (CO raw µg/m³, per contract)
        "updated_at": cur["time"].isoformat(),
        "source": adv["source"],
        "data_status": adv["data_status"],
    }


@app.get("/api/aqi/forecast")
def aqi_forecast(lat: float = Query(..., ge=-90, le=90),
                 lon: float = Query(..., ge=-180, le=180),
                 hours: int = Query(48, ge=1, le=72)):
    aq_data = data.fetch_air_quality(lat, lon)
    rows = advisory.hourly_series(aq_data)
    start = aq_data["current_idx"]
    sel = rows[start:start + hours]
    return {
        "hours": [{
            "time": r["time"].isoformat(),
            "aqi": r["aqi"],
            "category": r["category"],
            "pm2_5": r["pm2_5"],
            "pm10": r["pm10"],
        } for r in sel],
        "source": advisory.SOURCE,
        "data_status": advisory.DATA_STATUS,
    }


# ---------------------------------------------------------------- advisory & alerts

@app.get("/api/advisory")
def get_advisory(lat: float = Query(..., ge=-90, le=90),
                 lon: float = Query(..., ge=-180, le=180),
                 demo: str | None = Query(default=None)):
    """School-day advisory. ``demo=<scenario>`` returns scripted demo data
    (normal_day | indoor_day | worsening | outage) — no upstream calls, no
    writes, clearly labelled."""
    if demo:
        from . import demo as demo_mod
        adv = demo_mod.demo_scenario(demo)  # ValueError -> 422, AQServiceError -> 503
        return {
            "call": {"level": adv["level"], "label": adv["action_label"],
                     "headline": adv["headline"], "detail": adv["detail"]},
            "aqi_now": adv["aqi_now"],
            "category": adv["category"],
            "color": adv["color"],
            "dominant": adv["dominant"],
            "peak_6h": adv["peak_6h"],
            "best_windows": adv["best_windows"],
            "windows_note": adv["windows_note"],
            "evidence": adv["evidence"],
            "wind": adv["wind"],
            "generated_at": adv["generated_at"],
            "demo": True,
            "demo_scenario": demo,
            "alerts": adv["alerts"],
        }
    adv = advisory.school_advisory(lat, lon)
    return {
        "call": {"level": adv["level"], "label": adv["action_label"],
                 "headline": adv["headline"], "detail": adv["detail"]},
        "aqi_now": adv["aqi_now"],
        "category": adv["category"],
        "peak_6h": adv["peak_6h"],
        "best_windows": adv["best_windows"],
        "windows_note": adv["windows_note"],
        "evidence": adv["evidence"],
        "wind": adv["wind"],
        "generated_at": adv["generated_at"],
        "source": adv["source"],
        "data_status": adv["data_status"],
    }


@app.get("/api/alerts")
def get_alerts(lat: float = Query(..., ge=-90, le=90),
               lon: float = Query(..., ge=-180, le=180)):
    adv = advisory.school_advisory(lat, lon)
    return {"alerts": adv["alerts"]}


# ---------------------------------------------------------------- schools

@app.post("/api/schools", status_code=201)
def create_school(body: SchoolIn):
    return _public_school(stores.create(
        body.name, body.city, body.lat, body.lon, body.contact,
        hours=body.hours, days=body.days,
        pt_duration_min=body.pt_duration_min), include_private=True)


@app.get("/api/schools")
def list_schools():
    return {"schools": [_public_school(s) for s in stores.list_all()]}


@app.get("/api/schools/{school_id}")
def get_school(school_id: str):
    school = stores.get(school_id)
    if not school:
        raise HTTPException(404, "School not found")
    return _public_school(school, include_private=True)


class SubscriptionIn(BaseModel):
    channel: str = Field(..., pattern="^(sms|email)$")
    target: str = Field(..., min_length=3)


def _normalize_sms(target: str) -> str:
    """Normalize an Indian phone number to E.164 (+91XXXXXXXXXX)."""
    import re
    digits = re.sub(r"\D", "", target)
    if target.strip().startswith("+"):
        e164 = "+" + digits
    elif len(digits) == 10:
        e164 = "+91" + digits
    elif len(digits) == 12 and digits.startswith("91"):
        e164 = "+" + digits
    else:
        raise HTTPException(422, "Enter a valid 10-digit mobile number")
    return e164


@app.post("/api/schools/{school_id}/subscriptions", status_code=201)
def subscribe_school(school_id: str, body: SubscriptionIn):
    """Subscribe a phone (SMS) or email to this school's bulletin alerts.

    Uses the SNS alerts topic when configured (AWS deploy). The subscriber
    gets a confirmation text/email to opt in — required before delivery.
    """
    school = stores.get(school_id)
    if not school:
        raise HTTPException(404, "School not found")

    target = body.target.strip()
    if body.channel == "sms":
        target = _normalize_sms(target)  # 422 on bad numbers, before any AWS call
        protocol = "SMS"
    else:
        if "@" not in target:
            raise HTTPException(422, "Enter a valid email address")
        protocol = "email"

    topic = os.environ.get("ALERTS_TOPIC_ARN")
    if not topic:
        raise HTTPException(
            503, "Alert subscriptions need the AWS deploy (SNS topic not configured)")

    import boto3
    sns = boto3.client("sns")
    try:
        resp = sns.subscribe(TopicArn=topic, Protocol=protocol,
                             Endpoint=target, ReturnSubscriptionArn=True)
    except Exception as exc:
        raise HTTPException(502, f"SNS subscription failed: {exc}")

    sub = {
        "channel": body.channel,
        "target": target,
        "arn": resp.get("SubscriptionArn", "pending"),
        "status": "pending_confirmation",
    }
    subs = school.setdefault("subscriptions", [])
    subs[:] = [s for s in subs
               if not (s.get("channel") == sub["channel"]
                       and s.get("target") == sub["target"])]
    subs.append(sub)
    stores.upsert(school)
    return {
        "subscription": sub,
        "note": ("Confirm via the text/email just sent to start receiving "
                 "the 5:30 AM bulletin."),
    }


@app.delete("/api/schools/{school_id}")
def delete_school(school_id: str):
    if not stores.delete(school_id):
        raise HTTPException(404, "School not found")
    return {"deleted": True}


@app.get("/api/schools/{school_id}/bulletin")
def school_bulletin(school_id: str, lang: str = Query(default="en")):
    from . import i18n as i18n_mod
    school = stores.get(school_id)
    if not school:
        raise HTTPException(404, "School not found")
    # School-aware advisory: windows respect this school's hours/days.
    adv = advisory.school_advisory(school["lat"], school["lon"], school=school)
    from datetime import datetime
    aq_data = data.fetch_air_quality(school["lat"], school["lon"])
    rows = advisory.hourly_series(aq_data)
    plan = advisory.plan_activity(
        rows[aq_data["current_idx"]:], school=school, activity="PT")
    bulletin = {
        "school": {"id": school["id"], "name": school["name"],
                   "city": school["city"]},
        "date": datetime.now(IST).date().isoformat(),
        "call": {"level": adv["level"], "label": adv["action_label"],
                 "headline": adv["headline"], "detail": adv["detail"]},
        "aqi_now": adv["aqi_now"],
        "category": adv["category"],
        "color": adv["color"],
        "dominant": adv["dominant"],
        "peak_today": adv["peak_today"],
        "best_windows": adv["best_windows"],
        "windows_note": adv["windows_note"],
        "activity_plan": plan,
        "checklist": adv["checklist"],
        "disclaimer": adv["disclaimer"],
        "evidence": adv["evidence"],
        "generated_at": adv["generated_at"],
        "source": adv["source"],
        "data_status": adv["data_status"],
        "lang": "en",
    }
    return i18n_mod.translate_bulletin(bulletin, lang)


@app.post("/api/schools/{school_id}/actions", status_code=201)
def record_teacher_action(school_id: str, body: ActionIn):
    """Record a teacher acknowledgement for today's guidance.

    Idempotent per (date, action): repeats return the existing record.
    """
    from datetime import datetime
    date = body.date or datetime.now(IST).date().isoformat()
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(422, "date must be YYYY-MM-DD")
    school = stores.get(school_id)
    if not school:
        raise HTTPException(404, "School not found")
    adv_version = None
    try:
        adv = advisory.school_advisory(school["lat"], school["lon"], school=school)
        adv_version = f"{adv['level']}@{adv['generated_at']}"
    except AQServiceError:
        adv_version = None  # outage: still record the acknowledgement
    try:
        record, created = stores.record_action(
            school_id, body.action, body.recorded_by, reason=body.reason,
            date=date, advisory_version=adv_version)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    return {"action": record, "created": created,
            "action_types": stores.ACTION_LABELS}


@app.get("/api/schools/{school_id}/actions")
def teacher_action_history(school_id: str,
                           date: str | None = Query(default=None)):
    school = stores.get(school_id)
    if not school:
        raise HTTPException(404, "School not found")
    history = stores.get_actions(school_id, date=date)
    return {"school_id": school_id, "date": date, "actions": history,
            "action_types": stores.ACTION_LABELS}


@app.post("/api/schools/{school_id}/plan")
def plan_school_activity(school_id: str, body: PlanIn):
    """Recommend a practical outdoor slot for an activity, or an indoor
    alternative — respecting school hours, days, and activity duration."""
    school = stores.get(school_id)
    if not school:
        raise HTTPException(404, "School not found")
    aq_data = data.fetch_air_quality(school["lat"], school["lon"])
    rows = advisory.hourly_series(aq_data)
    plan = advisory.plan_activity(
        rows[aq_data["current_idx"]:], school=school,
        activity=body.activity, duration_min=body.duration_min,
        preferred=body.preferred)
    return dict(plan, generated_at=advisory.datetime.now(advisory.IST).isoformat(),
                data_status=advisory.DATA_STATUS)


# ---------------------------------------------------------------- agent

@app.post("/api/agent/chat")
def agent_chat(body: ChatIn):
    reply, mode, sources = agent.chat(body.message, body.lat, body.lon, body.history)
    return {"reply": reply, "agent": mode, "sources": sources}
