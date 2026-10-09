# Saans — Architecture

```
Browser (Vite + React + TS)
   │  REST /api/*
   ▼
FastAPI (:8000)
   ├── app/data.py      Open-Meteo client (air quality + geocoding), 10-min TTL cache
   ├── app/aqi.py       CPCB breakpoint tables → AQI, category, color, dominant pollutant
   ├── app/advisory.py  call levels (clear/caution/indoor/severe), best windows,
   │                     alerts, school checklists — pure functions, no I/O
   ├── app/agent.py     Strands Agent (GeminiModel, tools → advisory engine)
   │                     + transparent rule-based fallback (no key → fallback)
   ├── app/stores.py    schools store (in-memory; DynamoDB in AWS deploy)
   └── app/handler.py   Mangum adapter for Lambda
```

**Data flow (dashboard):** `GET /api/advisory?lat&lon` → fetch (cached) →
hourly AQI series → call = f(max(current, 6h peak)) → best ≥2h low-AQI windows
in next 24h → checklist per level.

**Agent flow:** user message + lat/lon → Strands agent with three tools
(`get_current_aqi`, `get_forecast_summary`, `get_school_advisory`) → grounded
reply + sources. No key → fallback answers from the same engine and labels
itself `fallback` (see `/api/health`).

**AWS deploy (`infra/template.yaml`):** API Gateway → Lambda (Mangum);
EventBridge Scheduler (cron 05:30 Asia/Kolkata) → bulletin Lambda;
DynamoDB `saans-schools`; SNS `saans-alerts`. Frontend → Amplify Hosting.

**Honesty invariants** (enforced in code, not just docs):
- No mock data paths. Upstream failure → HTTP 503 with a clear message.
- Hourly AQI is labelled `data_status: "indicative"` (CPCB uses 24h averages).
- Agent labels its mode (`strands` | `fallback`) on every reply and in `/api/health`.
