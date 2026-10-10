"""School-day advisory engine — pure functions.

Call levels are decided from ``ref = max(current AQI, 6h forecast peak)``:

  ref ≤ 100        → clear    "All clear — normal outdoor schedule."
  101–200          → caution  "Caution — shorten strenuous outdoor activity; sensitive children stay in."
  201–300          → indoor   "Indoor day — move PT and sports indoors; keep windows closed."
  301+             → severe   "Severe — indoor day, masks for commute; consider remote classes."

All AQI inputs here are *indicative hourly* values (see app/aqi.py honesty
note); CPCB officially uses 24h averages, so responses always carry
``data_status: "indicative"``.
"""

from datetime import datetime

from . import aqi as aqi_mod
from . import data as data_mod
from .data import IST

SOURCE = "open-meteo (modelled)"
DATA_STATUS = "indicative"  # hourly modelled values, not official 24h CPCB averages
LOW_AQI = 100               # "low" window threshold (Good/Satisfactory)
WINDOW_MIN_HOURS = 2        # a low-AQI window must be at least 2h contiguous

_LEVELS = [
    (100, "clear", "All clear — normal outdoor schedule."),
    (200, "caution", "Caution — shorten strenuous outdoor activity; sensitive children stay in."),
    (300, "indoor", "Indoor day — move PT and sports indoors; keep windows closed."),
    (10**9, "severe", "Severe — indoor day, masks for commute; consider remote classes."),
]

_DETAILS = {
    "clear": ("Air is Good/Satisfactory right now and the 6-hour outlook stays at or "
              "below AQI 100. Normal outdoor schedule."),
    "caution": ("Air is Moderate. Shorten strenuous outdoor activity, keep sensitive "
                "children (asthma, allergies) indoors, and keep an eye on the 6-hour peak."),
    "indoor": ("Air is Poor/Very Poor. Move PT and sports indoors, keep classroom "
               "windows closed, and run air purifiers if available."),
    "severe": ("Air is Severe. Indoor day: N95 masks for the commute, consider remote "
               "classes, and avoid all outdoor exertion."),
}

_CHECKLISTS = {
    "clear": [
        "Normal outdoor schedule",
        "Keep the school AQI display board updated",
        "Remind students of the no-idling rule near the school gate",
    ],
    "caution": [
        "Shorten strenuous outdoor activity (limit to 20–30 minutes)",
        "Sensitive children (asthma/allergies) stay indoors",
        "Keep classroom windows closed during peak traffic hours",
        "Reschedule long sports practice to the cleanest window below",
    ],
    "indoor": [
        "Move morning PT and sports indoors",
        "Keep classroom windows closed 8–11 AM",
        "Run air purifiers in classrooms if available",
        "Masks for the outdoor commute; avoid exertion",
    ],
    "severe": [
        "Shift to indoor or remote classes if possible",
        "N95 masks for everyone commuting",
        "Keep all windows and doors closed; seal gaps",
        "Cancel all outdoor activities",
        "Watch for breathing complaints; keep inhalers accessible",
    ],
}


def call_for(ref_aqi):
    """Return (level, headline) for the reference AQI."""
    for limit, level, headline in _LEVELS:
        if ref_aqi <= limit:
            return level, headline
    return "severe", _LEVELS[-1][2]


def hourly_series(aq_data):
    """Compute per-hour AQI rows from normalized Open-Meteo data.

    Returns list of dicts: time (datetime IST), aqi, category, color,
    dominant, pm2_5, pm10 (+ full pollutant detail for 'current').
    """
    rows = []
    pols = aq_data["pollutants"]
    for i, t in enumerate(aq_data["times"]):
        concs = {p: (vals[i] if i < len(vals) else None)
                 for p, vals in pols.items()}
        concs_aqi = dict(concs)
        if concs_aqi.get("co") is not None:
            concs_aqi["co"] = concs_aqi["co"] / 1000.0  # µg/m³ → mg/m³
        val, dominant, _subs = aqi_mod.compute(concs_aqi)
        if val is None:
            continue
        cat, color = aqi_mod.category(val)
        rows.append({
            "time": t,
            "aqi": val,
            "category": cat,
            "color": color,
            "dominant": dominant,
            "pm2_5": concs.get("pm2_5"),
            "pm10": concs.get("pm10"),
            "pollutants": {  # full detail (µg/m³, incl. raw CO) for 'current'
                "pm2_5": concs.get("pm2_5"), "pm10": concs.get("pm10"),
                "o3": concs.get("o3"), "no2": concs.get("no2"),
                "so2": concs.get("so2"), "co": concs.get("co"),
            },
        })
    return rows


def best_windows(rows, horizon_hours=24, limit=2):
    """Up to ``limit`` contiguous low-AQI windows (≥2h) in the next N hours.

    A window is "low" when every hour is ≤100 (Good/Satisfactory).
    Windows are ranked by cleanest minimum AQI, then earliest start.
    """
    horizon = rows[:horizon_hours]
    runs, cur = [], []
    for r in horizon:
        if r["aqi"] <= LOW_AQI:
            cur.append(r)
        else:
            if len(cur) >= WINDOW_MIN_HOURS:
                runs.append(cur)
            cur = []
    if len(cur) >= WINDOW_MIN_HOURS:
        runs.append(cur)

    def key(run):
        return (min(x["aqi"] for x in run), run[0]["time"])

    picked = sorted(runs, key=key)[:limit]
    picked.sort(key=lambda run: run[0]["time"])
    out = []
    for i, run in enumerate(picked):
        best = min(x["aqi"] for x in run)
        out.append({
            "start": run[0]["time"].isoformat(),
            "end": run[-1]["time"].isoformat(),
            "label": "Cleanest window today" if i == 0 else "Another low-AQI spell",
            "aqi": best,
        })
    return out


def checklist(level):
    """3–5 concrete school actions for a call level."""
    return list(_CHECKLISTS.get(level, _CHECKLISTS["caution"]))


def build_alerts(current, rows_24h):
    """Threshold alerts from current conditions + 24h forecast."""
    alerts = []
    now_iso = current["time"].isoformat()
    cur_aqi, cur_cat = current["aqi"], current["category"]

    if cur_aqi >= 301:
        alerts.append({"severity": "critical",
                       "title": f"Severe air right now (AQI {cur_aqi})",
                       "detail": "Severe conditions at the moment. Keep everyone indoors and use N95 masks for any commute.",
                       "at": now_iso})
    elif cur_aqi >= 201:
        alerts.append({"severity": "warn",
                       "title": f"Poor air right now (AQI {cur_aqi})",
                       "detail": "Poor air quality at the moment. Move outdoor activity indoors and keep windows closed.",
                       "at": now_iso})
    elif cur_aqi >= 101:
        alerts.append({"severity": "warn",
                       "title": f"Moderate air right now (AQI {cur_aqi})",
                       "detail": "Moderate air quality. Sensitive children should avoid strenuous outdoor activity.",
                       "at": now_iso})

    # First forecast crossing of Poor (200) and Severe (300) within 24h.
    for threshold, severity, label in ((200, "warn", "Poor"), (300, "critical", "Severe")):
        for r in rows_24h:
            if r["aqi"] >= threshold and cur_aqi < threshold:
                alerts.append({
                    "severity": severity,
                    "title": f"{label} air expected (AQI {r['aqi']})",
                    "detail": f"Forecast crosses into {label} around {r['time'].strftime('%I %p, %a')}. Plan indoor activities.",
                    "at": r["time"].isoformat(),
                })
                break
    return alerts


def school_advisory(lat, lon):
    """Full advisory bundle for a location. Raises AQServiceError upstream."""
    aq_data = data_mod.fetch_air_quality(lat, lon)
    rows = hourly_series(aq_data)
    if not rows:
        raise data_mod.AQServiceError("Upstream data source returned no usable AQI data")

    cur = rows[aq_data["current_idx"]] if aq_data["current_idx"] < len(rows) else rows[0]
    next6 = rows[aq_data["current_idx"]:aq_data["current_idx"] + 6]
    peak6 = max(next6, key=lambda r: r["aqi"]) if next6 else cur
    ref = max(cur["aqi"], peak6["aqi"])

    level, headline = call_for(ref)
    rows24 = rows[aq_data["current_idx"]:aq_data["current_idx"] + 24]
    peak_day = max(rows24, key=lambda r: r["aqi"]) if rows24 else cur

    try:
        wind = wind_story(lat, lon)
    except Exception:
        wind = None  # wind is enrichment; never break the advisory

    return {
        "level": level,
        "headline": headline,
        "detail": _DETAILS[level],
        "aqi_now": cur["aqi"],
        "category": cur["category"],
        "color": cur["color"],
        "dominant": cur["dominant"],
        "current": cur,
        "peak_6h": {"aqi": peak6["aqi"], "at": peak6["time"].isoformat()},
        "peak_today": {"aqi": peak_day["aqi"], "at": peak_day["time"].isoformat()},
        "best_windows": best_windows(rows[aq_data["current_idx"]:], horizon_hours=24),
        "checklist": checklist(level),
        "alerts": build_alerts(cur, rows24),
        "wind": wind,
        "generated_at": datetime.now(IST).isoformat(),
        "source": SOURCE,
        "data_status": DATA_STATUS,
    }


_COMPASS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
_COMPASS_FULL = {
    "N": "north", "NE": "northeast", "E": "east", "SE": "southeast",
    "S": "south", "SW": "southwest", "W": "west", "NW": "northwest",
}


def _compass(degrees):
    """Degrees (direction wind comes FROM) -> 8-point compass label."""
    return _COMPASS[int(((float(degrees) + 22.5) % 360) // 45)]


def wind_story(lat, lon):
    """Plain-language 'why is the air like this' from wind data.

    Returns dict with direction label/degrees, speed, headline and detail,
    or None if wind data is unavailable. Never raises.
    """
    try:
        w = data_mod.fetch_wind(lat, lon)
    except Exception:
        return None
    i = w["current_idx"]
    dirs = [d for d in w["direction"][i:i + 12] if d is not None]
    speeds = [s for s in w["speed"][i:i + 12] if s is not None]
    if not dirs or not speeds:
        return None

    # Prevailing direction = most common compass sector over next 12h.
    sectors = [_compass(d) for d in dirs]
    prevailing = max(set(sectors), key=sectors.count)
    deg = round(sum(d for d, s in zip(dirs, sectors) if s == prevailing)
                / max(1, sectors.count(prevailing)))
    avg_speed = round(sum(speeds) / len(speeds))

    from datetime import datetime
    month = datetime.now(IST).month
    stubble_season = month in (10, 11)

    if avg_speed < 8:
        headline = "Light winds are letting pollution sit still."
        detail = (f"Winds are only {avg_speed} km/h from the "
                  f"{_COMPASS_FULL[prevailing]}. With so little movement, "
                  "emissions from traffic and cooking fires accumulate near "
                  "the ground instead of dispersing.")
    elif prevailing in ("NW", "W", "N") and stubble_season:
        headline = "Northwesterlies are carrying stubble smoke across the plains."
        detail = (f"Winds from the {_COMPASS_FULL[prevailing]} at {avg_speed} km/h "
                  "are blowing across the farm belt upwind. In October–November this "
                  "pattern typically carries smoke from post-harvest field fires, "
                  "which is why the AQI climbs even on otherwise clear days.")
    elif avg_speed >= 20:
        headline = "Strong winds are sweeping pollution away."
        detail = (f"Winds from the {_COMPASS_FULL[prevailing]} at {avg_speed} km/h "
                  "are ventilating the area well. If the AQI is still high, local "
                  "sources (traffic, dust, waste burning nearby) are likely the cause.")
    else:
        headline = f"Winds from the {_COMPASS_FULL[prevailing]} at {avg_speed} km/h."
        detail = ("Moderate winds are moving air through the area. Pollution levels "
                  "reflect a mix of local emissions and whatever is drifting in "
                  "from upwind.")

    return {
        "direction": prevailing,
        "direction_label": _COMPASS_FULL[prevailing],
        "degrees": deg,
        "speed_kmh": avg_speed,
        "headline": headline,
        "detail": detail,
    }
