# Saans — API Contract (v1)

Base URL: `http://localhost:8000` — all endpoints prefixed `/api`. JSON everywhere.
CORS: allow all origins (hackathon demo).

## Conventions

- AQI uses **CPCB (India) breakpoints**, computed from pollutant concentrations.
- `category` is one of: `Good`, `Satisfactory`, `Moderate`, `Poor`, `Very Poor`, `Severe`.
- Colors: Good `#2ca02c`, Satisfactory `#7ac143`, Moderate `#ffbf00`, Poor `#ff7f0e`, Very Poor `#d62728`, Severe `#8b0000`.
- Times are ISO 8601 with offset, timezone `Asia/Kolkata` unless otherwise requested.
- Data sources: Open-Meteo Air Quality API (no key, free) for current + forecast;
  Open-Meteo Geocoding API for search. Label honesty: `source: "open-meteo (modelled)"`.
  Hourly concentrations are indicative; CPCB officially uses 24h averages — the UI
  must show "indicative hourly AQI" wording. Backend exposes `data_status`.

## Endpoints

### GET /api/health
→ `{"status": "ok", "agent": "strands|fallback", "version": "1.0.0"}`
`agent` reports whether the Strands agent has a live model key (`strands`) or is
running the rule-based fallback (`fallback`).

### GET /api/search?q={text}&limit=8
Geocode a place name (bias to India).
→ `{"results": [{"name": "Patna", "admin1": "Bihar", "country": "India", "lat": 25.5941, "lon": 85.1376}]}`

### GET /api/aqi/current?lat={f}&lon={f}
→
```json
{
  "aqi": 187, "category": "Moderate", "color": "#ffbf00",
  "dominant": "pm2_5",
  "pollutants": {"pm2_5": 102.4, "pm10": 145.1, "o3": 38.2, "no2": 21.5, "so2": 6.1, "co": 512.0},
  "updated_at": "2026-10-09T22:00:00+05:30",
  "source": "open-meteo (modelled)", "data_status": "indicative"
}
```
CO in µg/m³.

### GET /api/aqi/forecast?lat={f}&lon={f}&hours=48
→ `{"hours": [{"time": "…", "aqi": 187, "category": "Moderate", "pm2_5": 102.4, "pm10": 145.1}], "source": "open-meteo (modelled)", "data_status": "indicative"}`

### GET /api/advisory?lat={f}&lon={f}&demo={scenario}
School-day advisory for the location. `demo` is optional: `normal_day |
indoor_day | worsening | outage` returns scripted, clearly labelled demo data
(`"demo": true`) with no upstream calls and no writes; `outage` raises the
503 path. Unknown scenarios → 422.
→
```json
{
  "call": {"level": "caution|indoor|severe|clear", "label": "Caution advised", "headline": "…", "detail": "…"},
  "aqi_now": 187,
  "category": "Moderate",
  "peak_6h": {"aqi": 214, "at": "2026-10-10T08:00:00+05:30"},
  "best_windows": [{"start": "…", "end": "…", "label": "Cleanest window today", "aqi": 96}],
  "windows_note": null,
  "evidence": {
    "rule": "Take max(current AQI, 6-hour forecast peak)…",
    "reference_aqi": 214, "current_aqi": 187, "current_category": "Moderate",
    "forecast_peak_6h": {"aqi": 214, "at": "…"},
    "dominant_pollutant": "pm2_5",
    "pollutant_concentrations": {"pm2_5": 88.2, "pm10": 120.5},
    "period": "current hour + next 6 hours",
    "source": "open-meteo (modelled)", "data_status": "indicative",
    "data_age_min": 42, "stale": false,
    "limitations": ["Hourly modelled concentrations…, not CPCB 24-hour averages.", "…"]
  },
  "wind": {
    "direction": "NW", "direction_label": "northwest", "degrees": 315,
    "speed_kmh": 14,
    "headline": "Winds from the northwest — moderate dispersion.",
    "detail": "…"
  },
  "generated_at": "…"
}
```
`wind` is null when wind data is unavailable. Direction is the compass sector the
wind blows FROM. Wind copy describes dispersion/transport conditions only — it
never attributes pollution to specific sources.
Call logic (max of current AQI and 6h forecast peak). School-action labels are
deliberately distinct from CPCB pollution categories (CPCB "Severe" starts at 401):
- ≤100 → `clear` ("All clear")
- 101–200 → `caution` ("Caution advised")
- 201–300 → `indoor` ("Indoor day")
- 301+ → `severe` ("Emergency day")
`best_windows`: school-aware — only future slots inside the school's operating
hours/days (default 08:00–15:00 IST, Mon–Sat, 40-min activity) with AQI ≤ 100.
Never recommends a polluted period; `windows_note` explains when nothing fits.

### GET /api/alerts?lat={f}&lon={f}
Active threshold alerts derived from current + 24h forecast.
→ `{"alerts": [{"severity": "warn|critical", "title": "…", "detail": "…", "at": "…"}]}`

### Schools (persistent store: in-memory locally, DynamoDB on AWS deploy)

### POST /api/schools
Body: `{"name": "…", "city": "Patna", "lat": 25.59, "lon": 85.13, "contact": "optional", "hours": {"start": "08:00", "end": "15:00"}, "days": [0,1,2,3,4,5], "pt_duration_min": 40}`
Hours are IST; days are 0=Mon..6=Sun (default Mon–Sat). Invalid values fall back to defaults.
→ `{"id": "…", "name": "…", "city": "…", "lat": …, "lon": …, "hours": {…}, "days": […], "pt_duration_min": 40, "created_at": "…"}`

### GET /api/schools
→ `{"schools": [ …same shape… ]}` — contact details and subscription targets are masked in list views.

### GET /api/schools/{id}
→ single school, including `subscriptions: [{channel, target, arn, status}]`

### POST /api/schools/{id}/subscriptions
Body: `{"channel": "sms|email", "target": "+919876543210 or name@example.com"}`
Subscribes the target to the school's bulletin via the SNS alerts topic (AWS
deploy only — 503 locally). Phone numbers are normalized to E.164 (+91…).
SNS sends a confirmation text/email that must be accepted before delivery.
→ `{"subscription": {"channel": "sms", "target": "+919876543210", "arn": "…", "status": "pending_confirmation"}, "note": "…"}`
422 on bad phone/email, 404 on unknown school.

### POST /api/schools/{id}/actions
Record a teacher acknowledgement. Idempotent per (date, action) — repeats return
the existing record with `created: false`.
Body: `{"action": "guidance_reviewed|pt_moved_indoors|assembly_rescheduled|outdoor_rescheduled|unable_to_implement", "recorded_by": "Meera Sharma", "reason": "optional", "date": "YYYY-MM-DD (optional)"}`
→ `{"action": {"date": "…", "action": "…", "label": "…", "recorded_by": "…", "reason": "…", "advisory_version": "indoor@…", "recorded_at": "…"}, "created": true, "action_types": {…}}`
422 on unknown action or bad date, 404 on unknown school.

### GET /api/schools/{id}/actions?date=YYYY-MM-DD
Daily (or all) action history, newest first. → `{"school_id": "…", "date": "…", "actions": […], "action_types": {…}}`

### POST /api/schools/{id}/plan
Recommend a practical outdoor slot for an activity, or an indoor alternative.
Body: `{"activity": "PT", "duration_min": 40, "preferred": "morning|afternoon"}`
→ `{"recommendation": "outdoor_slot|indoor", "activity": "PT", "slot": {"start": "…", "end": "…", "aqi": 82} | null, "reason": "…", "generated_at": "…", "data_status": "indicative"}`

### DELETE /api/schools/{id}
→ `{"deleted": true}`

### GET /api/schools/{id}/bulletin?lang=en|hi
Morning bulletin for a registered school. `lang=hi` returns Hindi user-facing
strings (call, checklist, labels, disclaimer); evidence stays in English.
→
```json
{
  "school": {"id": "…", "name": "…", "city": "…"},
  "date": "2026-10-10",
  "call": {"level": "…", "label": "Caution advised", "headline": "…", "detail": "…"},
  "aqi_now": 187, "category": "Moderate",
  "peak_today": {"aqi": 231, "at": "…"},
  "best_windows": […],
  "windows_note": null,
  "activity_plan": {"recommendation": "indoor", "activity": "PT", "slot": null, "reason": "…"},
  "checklist": ["Consider limiting continuous strenuous outdoor activity", "…"],
  "disclaimer": "Saans provides planning guidance… not an official school-closure order…",
  "evidence": {…same shape as /api/advisory…},
  "generated_at": "…", "source": "open-meteo (modelled)",
  "data_status": "indicative", "lang": "en"
}
```
`checklist`: 3–5 concrete actions derived from the call level.

### POST /api/agent/chat
Body: `{"message": "Should my asthmatic son play football tomorrow?", "lat": 25.59, "lon": 85.13, "history": [{"role":"user|assistant","content":"…"}] (optional)}`
→ `{"reply": "…", "agent": "strands|fallback", "sources": ["open-meteo …"]}`
The Strands agent (AWS open-source SDK) has tools: `get_current_aqi`, `get_forecast`,
`get_school_advisory`. It answers in plain language (English; Hindi/Hinglish if asked),
grounds every claim in tool output, and adds a one-line health disclaimer for medical
questions. If no model key is configured, a transparent rule-based fallback answers
from the same advisory engine and says so.

## Errors
`{"detail": "…"}` with appropriate HTTP status. Never 500 on bad input — validate and 422.
