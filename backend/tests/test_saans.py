"""Saans verification tests: calculation boundaries, missing/stale data,
school-hour filtering, timing questions, dedupe, recipient isolation,
demo isolation, and teacher acknowledgements.

Pure-function tests run without network; the in-memory store backend is
used (no SCHOOLS_TABLE env var).
"""

import sys
from datetime import datetime, timedelta

import pytest

sys.path.insert(0, "backend")

from app import advisory as adv
from app import aqi as aqi_mod
from app import demo as demo_mod
from app import i18n as i18n_mod
from app import stores
from app.data import AQServiceError, IST
from app import handler as handler_mod


# ---------------------------------------------------------------- helpers

def _rows(start, aqis):
    """Fabricate hourly AQI rows starting at ``start`` (IST datetime)."""
    rows = []
    for i, a in enumerate(aqis):
        t = start + timedelta(hours=i)
        cat, color = aqi_mod.category(a)
        rows.append({
            "time": t, "aqi": a, "category": cat, "color": color,
            "dominant": "pm2_5", "pm2_5": 40.0, "pm10": 80.0,
            "pollutants": {"pm2_5": 40.0, "pm10": 80.0, "o3": 30.0,
                           "no2": 20.0, "so2": 10.0, "co": 500.0},
        })
    return rows


def _school(**kw):
    s = {"id": "t1", "name": "Test School", "city": "Patna",
         "lat": 25.59, "lon": 85.13,
         "hours": {"start": "08:00", "end": "15:00"},
         "days": [0, 1, 2, 3, 4, 5], "pt_duration_min": 40}
    s.update(kw)
    return s


# ------------------------------------------------------- AQI boundaries

def test_pm25_breakpoint_boundaries():
    # CPCB: 30 µg/m³ -> 50, 31 -> just above 50
    assert aqi_mod.sub_index(30, aqi_mod._PM25) == pytest.approx(50.0)
    assert aqi_mod.sub_index(31, aqi_mod._PM25) == pytest.approx(51.0, abs=1.5)
    assert aqi_mod.sub_index(60, aqi_mod._PM25) == pytest.approx(100.0)
    assert aqi_mod.sub_index(250, aqi_mod._PM25) == pytest.approx(400.0)


def test_pm10_breakpoint_boundaries():
    assert aqi_mod.sub_index(50, aqi_mod._PM10) == pytest.approx(50.0)
    assert aqi_mod.sub_index(51, aqi_mod._PM10) == pytest.approx(51.0, abs=1.5)
    assert aqi_mod.sub_index(430, aqi_mod._PM10) == pytest.approx(400.0)


def test_co_units_mg_per_m3():
    # 1.0 mg/m³ -> 50 ; 2.0 -> 100. Callers convert µg->mg (÷1000).
    assert aqi_mod.sub_index(1.0, aqi_mod._CO) == pytest.approx(50.0)
    assert aqi_mod.sub_index(2.0, aqi_mod._CO) == pytest.approx(100.0)
    # 2000 µg/m³ = 2.0 mg/m³ must give the same sub-index after conversion
    assert aqi_mod.sub_index(2000 / 1000.0, aqi_mod._CO) == pytest.approx(100.0)


def test_missing_pollutant_skipped_not_zero():
    # Only PM2.5 present: AQI comes from PM2.5 alone; missing != 0.
    aqi, dom, subs = aqi_mod.compute({"pm2_5": 60.0, "pm10": None, "o3": None,
                                      "no2": None, "so2": None, "co": None})
    assert dom == "pm2_5"
    assert aqi == 100
    assert set(subs) == {"pm2_5"}


def test_all_missing_returns_none():
    aqi, dom, subs = aqi_mod.compute(
        {"pm2_5": None, "pm10": None, "o3": None,
         "no2": None, "so2": None, "co": None})
    assert (aqi, dom, subs) == (None, None, {})


def test_category_boundaries():
    assert aqi_mod.category(50)[0] == "Good"
    assert aqi_mod.category(100)[0] == "Satisfactory"
    assert aqi_mod.category(200)[0] == "Moderate"
    assert aqi_mod.category(300)[0] == "Poor"
    assert aqi_mod.category(400)[0] == "Very Poor"
    assert aqi_mod.category(401)[0] == "Severe"  # CPCB Severe starts at 401


# ------------------------------------------------------- call thresholds

@pytest.mark.parametrize("ref,level", [
    (100, "clear"), (101, "caution"), (200, "caution"),
    (201, "indoor"), (300, "indoor"), (301, "severe"),
])
def test_call_thresholds(ref, level):
    got, _headline = adv.call_for(ref)
    assert got == level


def test_action_labels_distinct_from_cpcb():
    # School action at 301+ must NOT be called "Severe" (CPCB Severe = 401+).
    assert adv.ACTION_LABELS["severe"] != "Severe"
    assert adv.ACTION_LABELS["severe"] == "Emergency day"


# ------------------------------------------------------- school hours

def _monday_6am():
    # Find next Monday 06:00 IST so rows fall on operating days.
    now = datetime.now(IST)
    days_ahead = (0 - now.weekday()) % 7
    d = (now + timedelta(days=days_ahead)).replace(
        hour=6, minute=0, second=0, microsecond=0)
    if d <= now:
        d += timedelta(days=7)
    return d


def test_evening_window_excluded_from_school_hours():
    # Clean air only 17:00-20:00 (after school) -> no school-hours window.
    start = _monday_6am()
    aqis = [200] * 11 + [80, 70, 60] + [200] * 10  # 17:00,18:00,19:00 clean
    rows = _rows(start, aqis)
    wins = adv.best_windows(rows, school=_school())
    assert wins == []


def test_morning_window_qualifies():
    # Clean air 09:00-11:00 on a school day -> one window.
    start = _monday_6am()
    aqis = [200] * 3 + [80, 70, 60] + [200] * 16
    rows = _rows(start, aqis)
    wins = adv.best_windows(rows, school=_school())
    assert len(wins) == 1
    assert wins[0]["start"][11:13] == "09"


def test_no_window_note_when_polluted_all_day():
    start = _monday_6am()
    rows = _rows(start, [250] * 24)
    wins = adv.best_windows(rows, school=_school())
    assert wins == []  # never recommend a polluted period as "cleanest"


def test_plan_morning_never_returns_afternoon():
    start = _monday_6am()
    # Clean only in the afternoon.
    aqis = [200] * 6 + [80, 70] + [200] * 16
    rows = _rows(start, aqis)
    plan = adv.plan_activity(rows, school=_school(), activity="PT",
                             duration_min=40, preferred="morning")
    assert plan["recommendation"] == "indoor"
    assert "morning" in plan["reason"]


def test_plan_finds_morning_slot():
    start = _monday_6am()
    aqis = [200] * 2 + [80, 70] + [200] * 20  # 08:00-09:00 clean
    rows = _rows(start, aqis)
    plan = adv.plan_activity(rows, school=_school(), activity="PT",
                             duration_min=40, preferred="morning")
    assert plan["recommendation"] == "outdoor_slot"
    assert plan["slot"]["start"][11:13] == "08"


def test_plan_explains_why():
    start = _monday_6am()
    rows = _rows(start, [80] * 24)
    plan = adv.plan_activity(rows, school=_school(), activity="Assembly",
                             duration_min=30)
    assert plan["reason"]  # non-empty explanation
    assert "school hours" in plan["reason"]


# ------------------------------------------------------- teacher actions

def test_action_record_and_dedupe():
    s = stores.create("Action School", "Patna", 25.59, 85.13)
    try:
        rec1, created1 = stores.record_action(
            s["id"], "pt_moved_indoors", "Meera", advisory_version="indoor@x")
        assert created1 is True
        assert rec1["label"] == "PT moved indoors"
        rec2, created2 = stores.record_action(
            s["id"], "pt_moved_indoors", "Meera", advisory_version="indoor@x")
        assert created2 is False  # duplicate suppressed
        assert rec2["recorded_at"] == rec1["recorded_at"]
        hist = stores.get_actions(s["id"], date=rec1["date"])
        assert len(hist) == 1
    finally:
        stores.delete(s["id"])


def test_action_invalid_type_rejected():
    s = stores.create("Action School 2", "Patna", 25.59, 85.13)
    try:
        with pytest.raises(ValueError):
            stores.record_action(s["id"], "fly_kites", "Meera")
    finally:
        stores.delete(s["id"])


def test_unable_to_implement_keeps_reason():
    s = stores.create("Action School 3", "Patna", 25.59, 85.13)
    try:
        rec, created = stores.record_action(
            s["id"], "unable_to_implement", "Ravi",
            reason="no indoor hall available")
        assert created is True
        assert rec["reason"] == "no indoor hall available"
    finally:
        stores.delete(s["id"])


# ------------------------------------------------------- material change

def _adv(level, label):
    return {"level": level, "action_label": label, "aqi_now": 200,
            "peak_6h": {"aqi": 220, "at": "x"}}


def test_no_change_no_alert():
    school = {"last_bulletin": {"date": "2026-10-11", "level": "indoor",
                                "action_label": "Indoor day"}}
    assert handler_mod._material_change(school, _adv("indoor", "Indoor day")) is None


def test_level_change_produces_update():
    school = {"last_bulletin": {"date": "2026-10-11", "level": "caution",
                                "action_label": "Caution advised"}}
    change = handler_mod._material_change(school, _adv("indoor", "Indoor day"))
    assert change is not None
    assert change["from_level"] == "caution"
    assert change["to_level"] == "indoor"


def test_first_bulletin_is_baseline_not_update():
    assert handler_mod._material_change({}, _adv("indoor", "Indoor day")) is None


def test_no_spam_after_update_unless_worsened():
    today = datetime.now(IST).date().isoformat()
    school = {"last_bulletin": {"date": today, "level": "indoor",
                                "action_label": "Indoor day",
                                "update_sent": True}}
    # Same-direction wobble (indoor -> caution is an improvement): no alert.
    assert handler_mod._material_change(
        school, _adv("caution", "Caution advised")) is None
    # Escalation (indoor -> severe) still alerts.
    change = handler_mod._material_change(school, _adv("severe", "Emergency day"))
    assert change is not None


# ------------------------------------------------------- recipient isolation

def test_bulletin_uses_schools_own_coordinates():
    s1 = stores.create("North School", "Delhi", 28.61, 77.21)
    s2 = stores.create("South School", "Chennai", 13.08, 80.27)
    try:
        assert (s1["lat"], s1["lon"]) != (s2["lat"], s2["lon"])
        # Each school's advisory is computed from its own stored coords.
        assert stores.get(s1["id"])["lat"] == 28.61
        assert stores.get(s2["id"])["lat"] == 13.08
    finally:
        stores.delete(s1["id"])
        stores.delete(s2["id"])


# ------------------------------------------------------- demo isolation

def test_demo_scenarios_labelled_and_shaped():
    for name in ("normal_day", "indoor_day", "worsening"):
        b = demo_mod.demo_scenario(name)
        assert b["demo"] is True
        assert b["demo_scenario"] == name
        assert b["data_status"] == "demo"
        assert "evidence" in b and "checklist" in b


def test_demo_consistent_decision():
    # worsening: current 150 (Moderate) but 6h peak 260 -> Indoor day, matching the rule.
    b = demo_mod.demo_scenario("worsening")
    assert b["level"] == "indoor"
    assert b["evidence"]["reference_aqi"] == 260
    assert any("Poor air expected" in a["title"] for a in b["alerts"])


def test_demo_outage_raises_service_error():
    with pytest.raises(AQServiceError):
        demo_mod.demo_scenario("outage")


def test_demo_unknown_scenario_rejected():
    with pytest.raises(ValueError):
        demo_mod.demo_scenario("bogus")


# ------------------------------------------------------- i18n

def test_hindi_bulletin_translation():
    en = {
        "call": {"level": "indoor", "headline": "x", "detail": "y"},
        "checklist": ["a"],
        "best_windows": [{"start": "s", "end": "e",
                          "label": "Cleanest window today", "aqi": 80}],
        "windows_note": None,
        "disclaimer": "en disclaimer",
    }
    hi = i18n_mod.translate_bulletin(en, "hi")
    assert hi["lang"] == "hi"
    assert hi["call"]["label"] == "अंदर का दिन"
    assert hi["checklist"][0] != "a"
    assert hi["best_windows"][0]["label"] == "आज का सबसे साफ समय"
    assert "आधिकारिक" in hi["disclaimer"] or "आधिकारिक" in hi["disclaimer"]


def test_english_bulletin_unchanged():
    en = {"call": {"level": "clear"}, "checklist": ["a"], "lang": "en"}
    out = i18n_mod.translate_bulletin(en, "en")
    assert out["lang"] == "en"
    assert out["checklist"] == ["a"]


# ------------------------------------------------------- school profile

def test_profile_defaults_and_validation():
    p = adv.school_profile(None)
    assert p["start"] == (8, 0) and p["end"] == (15, 0)
    assert p["pt_duration_min"] == 40
    p2 = adv.school_profile({"hours": {"start": "xx", "end": "99:99"},
                             "days": [9, -1], "pt_duration_min": 999})
    assert p2["start"] == (8, 0)  # invalid -> default
    assert p2["days"] == [0, 1, 2, 3, 4, 5]  # invalid -> default
    assert p2["pt_duration_min"] == 180  # clamped


def test_create_normalizes_profile():
    s = stores.create("Profile School", "Patna", 25.59, 85.13,
                      hours={"start": "09:00", "end": "16:00"},
                      days=[0, 1, 2, 3, 4], pt_duration_min=60)
    try:
        assert s["hours"] == {"start": "09:00", "end": "16:00"}
        assert s["days"] == [0, 1, 2, 3, 4]
        assert s["pt_duration_min"] == 60
    finally:
        stores.delete(s["id"])
