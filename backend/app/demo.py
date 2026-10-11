"""Clearly labelled demo scenarios for the hackathon demo video.

Each scenario returns a fully scripted advisory bundle shaped like
``advisory.school_advisory`` output, WITHOUT calling upstream APIs and
WITHOUT touching the school store or notification delivery. The bundle
carries ``"demo": True`` and ``"demo_scenario": <name>`` so the UI can
badge it.

Scenarios:
  normal_day  — AQI ~65 (Satisfactory), All clear, outdoor window available
  indoor_day  — AQI ~240 (Poor), Indoor day, no suitable school-hours window
  worsening   — AQI ~150 now (Moderate) but 6h peak ~260 → Indoor day + alert
  outage      — raises AQServiceError (tests the 503 / retry UI path)
"""

from datetime import datetime, timedelta

from . import advisory as adv_mod
from .data import AQServiceError, IST

SCENARIOS = ("normal_day", "indoor_day", "worsening", "outage")


def _base(level, ref_aqi, cur_aqi, category, color, dominant, peak6_aqi,
          peak6_in_h, windows, alerts):
    now = datetime.now(IST).replace(minute=0, second=0, microsecond=0)
    peak6_at = (now + timedelta(hours=peak6_in_h)).isoformat()
    return {
        "demo": True,
        "level": level,
        "action_label": adv_mod.ACTION_LABELS[level],
        "headline": adv_mod.call_for(ref_aqi)[1],
        "detail": adv_mod._DETAILS[level],
        "aqi_now": cur_aqi,
        "category": category,
        "color": color,
        "dominant": dominant,
        "peak_6h": {"aqi": peak6_aqi, "at": peak6_at},
        "peak_today": {"aqi": peak6_aqi, "at": peak6_at},
        "best_windows": windows,
        "windows_note": (None if windows
                         else "No suitable outdoor window during school hours (08:00–15:00 IST)"),
        "checklist": adv_mod.checklist(level),
        "disclaimer": adv_mod.GUIDANCE_DISCLAIMER,
        "alerts": alerts,
        "evidence": {
            "rule": ("Take max(current AQI, 6-hour forecast peak) as the reference; "
                     "map ≤100 → All clear, 101–200 → Caution advised, "
                     "201–300 → Indoor day, 301+ → Emergency day."),
            "reference_aqi": ref_aqi,
            "current_aqi": cur_aqi,
            "current_category": category,
            "forecast_peak_6h": {"aqi": peak6_aqi, "at": peak6_at},
            "dominant_pollutant": dominant,
            "pollutant_concentrations": {"pm2_5": 38.0, "pm10": 92.0},
            "period": "current hour + next 6 hours",
            "source": "demo scenario (scripted, not live data)",
            "data_status": "demo",
            "data_age_min": 0,
            "stale": False,
            "limitations": ["Scripted demonstration data — not real measurements."],
        },
        "wind": {
            "direction": "NW", "direction_label": "northwest", "degrees": 315,
            "speed_kmh": 12,
            "headline": "Winds from the northwest — moderate dispersion.",
            "detail": ("Demo wind data: moderate ventilation. Wind alone cannot "
                       "identify pollution sources."),
        },
        "generated_at": now.isoformat(),
        "source": "demo scenario (scripted, not live data)",
        "data_status": "demo",
    }


def demo_scenario(name):
    """Return the scripted advisory bundle for ``name`` (no I/O at all)."""
    now = datetime.now(IST).replace(minute=0, second=0, microsecond=0)

    if name == "normal_day":
        w0 = now.replace(hour=10)
        bundle = _base(
            level="clear", ref_aqi=70, cur_aqi=65, category="Satisfactory",
            color="#7ac143", dominant="pm10", peak6_aqi=88, peak6_in_h=4,
            windows=[{"start": w0.isoformat(),
                      "end": (w0 + timedelta(hours=2)).isoformat(),
                      "label": "Cleanest window today", "aqi": 62}],
            alerts=[],
        )
        bundle["demo_scenario"] = name
        return bundle
    if name == "indoor_day":
        bundle = _base(
            level="indoor", ref_aqi=245, cur_aqi=240, category="Poor",
            color="#ff7f0e", dominant="pm2_5", peak6_aqi=262, peak6_in_h=3,
            windows=[],
            alerts=[{"severity": "warn",
                     "title": "Poor air right now (AQI 240)",
                     "detail": ("Poor air quality at the moment. Move outdoor "
                                "activity indoors and keep windows closed."),
                     "at": now.isoformat()}],
        )
        bundle["demo_scenario"] = name
        return bundle
    if name == "worsening":
        peak_at = now + timedelta(hours=5)
        bundle = _base(
            level="indoor", ref_aqi=260, cur_aqi=150, category="Moderate",
            color="#ffbf00", dominant="pm2_5", peak6_aqi=260, peak6_in_h=5,
            windows=[],
            alerts=[{"severity": "warn",
                     "title": "Moderate air right now (AQI 150)",
                     "detail": ("Moderate air quality. Sensitive children should "
                                "avoid strenuous outdoor activity."),
                     "at": now.isoformat()},
                    {"severity": "warn",
                     "title": "Poor air expected (AQI 260)",
                     "detail": (f"Forecast crosses into Poor around "
                                f"{peak_at.strftime('%-I %p, %a')}. Plan indoor activities."),
                     "at": peak_at.isoformat()}],
        )
        bundle["demo_scenario"] = name
        return bundle
    if name == "outage":
        raise AQServiceError("Demo scenario: upstream data source unavailable")

    raise ValueError(f"Unknown demo scenario: {name!r}. Choose from {SCENARIOS}")
