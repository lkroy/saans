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

### GET /api/advisory?lat={f}&lon={f}
School-day advisory for the location.
→
```json
{
  "call": {"level": "caution|indoor|severe|clear", "headline": "…", "detail": "…"},
  "aqi_now": 187,
  "peak_6h": {"aqi": 214, "at": "2026-10-10T08:00:00+05:30"},
  "best_windows": [{"start": "…", "end": "…", "label": "Cleanest window today", "aqi": 96}],
  "generated_at": "…"
}
```
Call logic (max of current AQI and 6h forecast peak):
- ≤100 → `clear`: "All clear — normal outdoor schedule."
- 101–200 → `caution`: "Caution — shorten strenuous outdoor activity; sensitive children stay in."
- 201–300 → `indoor`: "Indoor day — move PT and sports indoors; keep windows closed."
- 301+ → `severe`: "Severe — indoor day, masks for commute; consider remote classes."
`best_windows`: up to 2 contiguous low-AQI windows (≥2h) in the next 24h.

### GET /api/alerts?lat={f}&lon={f}
Active threshold alerts derived from current + 24h forecast.
→ `{"alerts": [{"severity": "warn|critical", "title": "…", "detail": "…", "at": "…"}]}`

### Schools (in-memory store for demo; DynamoDB in SAM deploy)

### POST /api/schools
Body: `{"name": "…", "city": "Patna", "lat": 25.59, "lon": 85.13, "contact": "optional"}`
→ `{"id": "…", "name": "…", "city": "…", "lat": …, "lon": …, "created_at": "…"}`

### GET /api/schools
→ `{"schools": [ …same shape… ]}`

### DELETE /api/schools/{id}
→ `{"deleted": true}`

### GET /api/schools/{id}/bulletin
Morning bulletin for a registered school.
→
```json
{
  "school": {"id": "…", "name": "…", "city": "…"},
  "date": "2026-10-10",
  "call": {"level": "…", "headline": "…", "detail": "…"},
  "aqi_now": 187, "category": "Moderate",
  "peak_today": {"aqi": 231, "at": "…"},
  "best_windows": […],
  "checklist": ["Keep classroom windows closed 8–11 AM", "Move morning PT indoors", "…"],
  "generated_at": "…"
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
