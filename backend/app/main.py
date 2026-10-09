"""Saans backend — FastAPI app.

All endpoints are prefixed /api. JSON everywhere, CORS allow-all (hackathon demo).
Bad lat/lon → 422 (FastAPI validation). Upstream Open-Meteo unreachable → 503.
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

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


# ---------------------------------------------------------------- models

class SchoolIn(BaseModel):
    name: str = Field(..., min_length=1)
    city: str = Field(..., min_length=1)
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)
    contact: str | None = None


class ChatIn(BaseModel):
    message: str = Field(..., min_length=1)
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)
    history: list[dict] = Field(default_factory=list)


def _latlon(lat: float = Query(..., ge=-90, le=90),
            lon: float = Query(..., ge=-180, le=180)):
    return lat, lon


# ---------------------------------------------------------------- health

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
                 lon: float = Query(..., ge=-180, le=180)):
    adv = advisory.school_advisory(lat, lon)
    return {
        "call": {"level": adv["level"], "headline": adv["headline"],
                 "detail": adv["detail"]},
        "aqi_now": adv["aqi_now"],
        "peak_6h": adv["peak_6h"],
        "best_windows": adv["best_windows"],
        "generated_at": adv["generated_at"],
    }


@app.get("/api/alerts")
def get_alerts(lat: float = Query(..., ge=-90, le=90),
               lon: float = Query(..., ge=-180, le=180)):
    adv = advisory.school_advisory(lat, lon)
    return {"alerts": adv["alerts"]}


# ---------------------------------------------------------------- schools

@app.post("/api/schools", status_code=201)
def create_school(body: SchoolIn):
    return stores.create(body.name, body.city, body.lat, body.lon, body.contact)


@app.get("/api/schools")
def list_schools():
    return {"schools": stores.list_all()}


@app.delete("/api/schools/{school_id}")
def delete_school(school_id: str):
    if not stores.delete(school_id):
        raise HTTPException(404, "School not found")
    return {"deleted": True}


@app.get("/api/schools/{school_id}/bulletin")
def school_bulletin(school_id: str):
    school = stores.get(school_id)
    if not school:
        raise HTTPException(404, "School not found")
    adv = advisory.school_advisory(school["lat"], school["lon"])
    from datetime import datetime
    return {
        "school": {"id": school["id"], "name": school["name"], "city": school["city"]},
        "date": datetime.now(IST).date().isoformat(),
        "call": {"level": adv["level"], "headline": adv["headline"],
                 "detail": adv["detail"]},
        "aqi_now": adv["aqi_now"],
        "category": adv["category"],
        "peak_today": adv["peak_today"],
        "best_windows": adv["best_windows"],
        "checklist": adv["checklist"],
        "generated_at": adv["generated_at"],
    }


# ---------------------------------------------------------------- agent

@app.post("/api/agent/chat")
def agent_chat(body: ChatIn):
    reply, mode, sources = agent.chat(body.message, body.lat, body.lon, body.history)
    return {"reply": reply, "agent": mode, "sources": sources}
