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
    (10**9, "severe", "Emergency day — indoor day, masks for commute; consider remote classes."),
]

# School-action display names, deliberately distinct from CPCB pollution
# categories (CPCB "Severe" starts at AQI 401; our top school action starts
# at 301, so it must not be called "Severe").
ACTION_LABELS = {
    "clear": "All clear",
    "caution": "Caution advised",
    "indoor": "Indoor day",
    "severe": "Emergency day",
}

_DETAILS = {
    "clear": ("Air is Good/Satisfactory right now and the 6-hour outlook stays at or "
              "below AQI 100. Normal outdoor schedule."),
    "caution": ("Air is Moderate. Consider shortening strenuous outdoor activity and "
                "keeping sensitive children (asthma, allergies) indoors; watch the 6-hour peak."),
    "indoor": ("Air is Poor or Very Poor. Plan to move PT and sports indoors and keep "
               "classroom windows closed during the worst hours, subject to your school's "
               "ventilation and heat policy."),
    "severe": ("Air is Very Poor or worse. Treat as an emergency indoor day: N95 masks for "
               "the commute and consider remote classes per your school board's policy."),
}

_CHECKLISTS = {
    "clear": [
        "Normal outdoor schedule",
        "Keep the school AQI display board updated",
        "Remind students of the no-idling rule near the school gate",
    ],
    "caution": [
        "Consider limiting continuous strenuous outdoor activity",
        "Sensitive children (asthma/allergies) may stay indoors — follow their health plans",
        "Use the cleanest window below for longer sports practice, if available",
        "Watch the 6-hour forecast peak before finalising outdoor plans",
    ],
    "indoor": [
        "Plan morning PT and sports indoors",
        "Limit window-opening during peak pollution hours, balanced with classroom ventilation needs",
        "Run air purifiers in classrooms if available",
        "Suggest masks for the outdoor commute; avoid strenuous exertion outdoors",
    ],
    "severe": [
        "Keep all outdoor activities suspended; consider remote classes per school board policy",
        "Recommend N95 masks for everyone commuting",
        "Limit window-opening, balanced with ventilation and heat requirements",
        "Watch for breathing complaints; keep inhalers accessible per student health plans",
    ],
}

# Shown with every checklist: Saans is planning guidance, not an official order.
GUIDANCE_DISCLAIMER = (
    "Saans provides planning guidance based on modelled air-quality data. "
    "It is not an official school-closure order and not medical advice. "
    "Follow your school board and local authorities for closures, and students' "
    "doctors for health decisions."
)


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



def checklist(level):
    """3-5 concrete school actions for a call level."""
    return list(_CHECKLISTS.get(level, _CHECKLISTS["caution"]))


# ---------------------------------------------------------- school hours

DEFAULT_SCHOOL_PROFILE = {
    "hours": {"start": "08:00", "end": "15:00"},  # IST, school on campus
    "days": [0, 1, 2, 3, 4, 5],                  # Mon-Sat (0=Monday)
    "pt_duration_min": 40,
}


def _parse_hhmm(s, fallback):
    try:
        h, m = s.split(":")
        h, m = int(h), int(m)
        if 0 <= h <= 23 and 0 <= m <= 59:
            return h, m
    except (ValueError, AttributeError):
        pass
    return fallback


def school_profile(school):
    """Normalized school operating profile with safe defaults."""
    school = school or {}
    hours = school.get("hours") or {}
    start = _parse_hhmm(hours.get("start"), (8, 0))
    end = _parse_hhmm(hours.get("end"), (15, 0))
    days = school.get("days")
    if not isinstance(days, list) or not days:
        days = DEFAULT_SCHOOL_PROFILE["days"]
    days = sorted({d for d in days if isinstance(d, int) and 0 <= d <= 6}) or \
        DEFAULT_SCHOOL_PROFILE["days"]
    try:
        duration = int(school.get("pt_duration_min")
                       or DEFAULT_SCHOOL_PROFILE["pt_duration_min"])
    except (TypeError, ValueError):
        duration = DEFAULT_SCHOOL_PROFILE["pt_duration_min"]
    duration = max(15, min(duration, 180))
    return {"start": start, "end": end, "days": days,
            "pt_duration_min": duration}


def _slot_in_school_hours(slot_start, profile):
    """True if an hourly slot falls inside school operating hours/days."""
    if slot_start.weekday() not in profile["days"]:
        return False
    sh, sm = profile["start"]
    eh, em = profile["end"]
    t = (slot_start.hour, slot_start.minute)
    return (sh, sm) <= t < (eh, em)


def best_windows(rows, school=None, limit=2):
    """School-aware low-AQI windows.

    Only *future* slots inside the school's operating hours/days qualify, and
    a window must be long enough for the school's typical activity duration.
    Never recommends a polluted period just because it is the day's cleanest:
    returns [] when nothing at or below AQI 100 fits — callers then show
    "No suitable outdoor window during school hours".
    """
    profile = school_profile(school)
    need_hours = max(1, -(-profile["pt_duration_min"] // 60))  # ceil div
    now = datetime.now(IST).replace(minute=0, second=0, microsecond=0)

    eligible = [r for r in rows
                if r["time"] >= now
                and r["aqi"] <= LOW_AQI
                and _slot_in_school_hours(r["time"], profile)]

    runs, cur = [], []
    for r in eligible:
        if cur and (r["time"] - cur[-1]["time"]).total_seconds() > 5400:
            runs.append(cur)
            cur = []
        cur.append(r)
    if cur:
        runs.append(cur)

    runs = [run for run in runs if len(run) >= need_hours]
    if profile["pt_duration_min"] > 60:
        runs = [run for run in runs if len(run) >= 2]

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


def plan_activity(rows, school=None, activity="PT", duration_min=None,
                  preferred=None):
    """Recommend a practical outdoor slot for an activity, or an indoor alternative.

    preferred: "morning" (before 12:00) or "afternoon" (12:00+), else any.
    Returns dict with recommendation "outdoor_slot" | "indoor" and a reason.
    """
    profile = school_profile(school)
    duration_min = duration_min or profile["pt_duration_min"]
    need_hours = max(1, -(-int(duration_min) // 60))
    now = datetime.now(IST).replace(minute=0, second=0, microsecond=0)

    def ok_time(t):
        if preferred == "morning" and t.hour >= 12:
            return False
        if preferred == "afternoon" and t.hour < 12:
            return False
        return True

    eligible = [r for r in rows
                if r["time"] >= now and r["aqi"] <= LOW_AQI
                and _slot_in_school_hours(r["time"], profile)
                and ok_time(r["time"])]

    runs, cur = [], []
    for r in eligible:
        if cur and (r["time"] - cur[-1]["time"]).total_seconds() > 5400:
            runs.append(cur)
            cur = []
        cur.append(r)
    if cur:
        runs.append(cur)
    runs = [run for run in runs if len(run) >= need_hours]
    runs.sort(key=lambda run: (min(x["aqi"] for x in run), run[0]["time"]))

    when = f"{duration_min}-minute {activity}"
    period = f" ({preferred})" if preferred else ""
    if runs:
        run = runs[0]
        s, e = run[0]["time"], run[-1]["time"]
        return {
            "recommendation": "outdoor_slot",
            "activity": activity,
            "slot": {"start": s.isoformat(), "end": e.isoformat(),
                     "aqi": min(x["aqi"] for x in run)},
            "reason": (f"{when}{period} fits inside school hours with AQI at or "
                       f"below 100 from {s.strftime('%-I %p')} to {e.strftime('%-I %p')} "
                       f"(cleanest AQI {min(x['aqi'] for x in run)})."),
        }
    return {
        "recommendation": "indoor",
        "activity": activity,
        "slot": None,
        "reason": (f"No {when}{period} fits inside school hours with AQI at or "
                   f"below 100 in the forecast. Hold {activity} indoors."),
    }


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


def school_advisory(lat, lon, school=None):
    """Full advisory bundle for a location. Raises AQServiceError upstream.

    ``school`` (optional dict) supplies operating hours/days/activity
    duration so outdoor windows are school-aware.
    """
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

    future_rows = rows[aq_data["current_idx"]:]
    windows = best_windows(future_rows, school=school)
    profile = school_profile(school)
    sh, sm = profile["start"]
    eh, em = profile["end"]
    windows_note = (f"No suitable outdoor window during school hours "
                    f"({sh:02d}:{sm:02d}–{eh:02d}:{em:02d} IST)") if not windows else None

    # Freshness: how old is the newest hourly model slot?
    latest_slot = max(r["time"] for r in rows)
    data_age_min = max(0, int((datetime.now(IST) - latest_slot).total_seconds() // 60))
    stale = data_age_min > 180

    evidence = {
        "rule": ("Take max(current AQI, 6-hour forecast peak) as the reference; "
                 "map ≤100 → All clear, 101–200 → Caution advised, "
                 "201–300 → Indoor day, 301+ → Emergency day."),
        "reference_aqi": ref,
        "current_aqi": cur["aqi"],
        "current_category": cur["category"],
        "forecast_peak_6h": {"aqi": peak6["aqi"], "at": peak6["time"].isoformat()},
        "dominant_pollutant": cur["dominant"],
        "pollutant_concentrations": {  # µg/m³ as modelled for the current hour
            k: v for k, v in cur["pollutants"].items() if v is not None},
        "period": "current hour + next 6 hours",
        "source": SOURCE,
        "data_status": DATA_STATUS,
        "data_age_min": data_age_min,
        "stale": stale,
        "limitations": [
            "Hourly modelled concentrations (Open-Meteo/CAMS), not CPCB 24-hour averages.",
            "Sub-index computed per pollutant with CPCB breakpoints; missing pollutants are skipped, never treated as zero.",
            "NH3 is not modelled by the upstream source and cannot contribute.",
            "Local sources (traffic jams, construction, nearby fires) may not be fully captured.",
        ],
    }

    return {
        "level": level,
        "action_label": ACTION_LABELS[level],
        "headline": headline,
        "detail": _DETAILS[level],
        "aqi_now": cur["aqi"],
        "category": cur["category"],
        "color": cur["color"],
        "dominant": cur["dominant"],
        "current": cur,
        "peak_6h": {"aqi": peak6["aqi"], "at": peak6["time"].isoformat()},
        "peak_today": {"aqi": peak_day["aqi"], "at": peak_day["time"].isoformat()},
        "best_windows": windows,
        "windows_note": windows_note,
        "checklist": checklist(level),
        "disclaimer": GUIDANCE_DISCLAIMER,
        "alerts": build_alerts(cur, rows24),
        "evidence": evidence,
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
    """Plain-language wind context: dispersion/transport conditions only.

    Describes what the wind is doing (direction, speed, ventilation) without
    attributing pollution to specific sources — wind and season alone cannot
    identify whether pollution comes from stubble burning, traffic, or
    cooking fires. Returns dict, or None if wind data is unavailable.
    Never raises.
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

    if avg_speed < 8:
        headline = "Light winds — poor dispersion conditions."
        detail = (f"Winds are only {avg_speed} km/h from the "
                  f"{_COMPASS_FULL[prevailing]}. With so little movement, "
                  "pollutants tend to accumulate near the ground instead of "
                  "dispersing, so local air quality can worsen through the day.")
    elif avg_speed >= 20:
        headline = "Strong winds — good ventilation."
        detail = (f"Winds from the {_COMPASS_FULL[prevailing]} at {avg_speed} km/h "
                  "are ventilating the area well, which usually keeps pollution "
                  "from building up. Persistently high AQI under these conditions "
                  "points to strong nearby or regional sources.")
    else:
        headline = f"Winds from the {_COMPASS_FULL[prevailing]} — moderate dispersion."
        detail = (f"Winds at {avg_speed} km/h are moving air through the area at a "
                  "moderate rate. Air quality reflects a mix of local emissions and "
                  "whatever is transported in from upwind; wind alone cannot tell "
                  "which sources dominate.")

    return {
        "direction": prevailing,
        "direction_label": _COMPASS_FULL[prevailing],
        "degrees": deg,
        "speed_kmh": avg_speed,
        "headline": headline,
        "detail": detail,
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
