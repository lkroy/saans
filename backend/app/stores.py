"""School store.

Two backends, same CRUD shape (keyed by school id):
- Local/demo: in-memory dict.
- AWS deploy: DynamoDB table named by the ``SCHOOLS_TABLE`` env var
  (see infra/template.yaml). Floats are stored as DynamoDB Decimals and
  converted back on read so the API shape never changes.
"""

import os
import uuid
from datetime import datetime
from decimal import Decimal

from .data import IST

_TABLE_NAME = os.environ.get("SCHOOLS_TABLE")
_ddb_table = None
_schools: dict = {}


def _table():
    global _ddb_table
    if _ddb_table is None and _TABLE_NAME:
        import boto3

        _ddb_table = boto3.resource("dynamodb").Table(_TABLE_NAME)
    return _ddb_table


def _to_ddb(school: dict) -> dict:
    item = dict(school)
    item["lat"] = Decimal(str(school["lat"]))
    item["lon"] = Decimal(str(school["lon"]))
    return item


def _from_ddb(item: dict) -> dict:
    school = dict(item)
    for key in ("lat", "lon"):
        if isinstance(school.get(key), Decimal):
            school[key] = float(school[key])
    return school


def create(name, city, lat, lon, contact=None, hours=None, days=None,
           pt_duration_min=None):
    from .advisory import school_profile
    profile = school_profile({"hours": hours, "days": days,
                              "pt_duration_min": pt_duration_min})
    sh, sm = profile["start"]
    eh, em = profile["end"]
    school = {
        "id": uuid.uuid4().hex[:12],
        "name": name,
        "city": city,
        "lat": float(lat),
        "lon": float(lon),
        "contact": contact,
        "hours": {"start": f"{sh:02d}:{sm:02d}", "end": f"{eh:02d}:{em:02d}"},
        "days": profile["days"],
        "pt_duration_min": profile["pt_duration_min"],
        "actions": [],
        "last_bulletin": None,
        "created_at": datetime.now(IST).isoformat(),
    }
    table = _table()
    if table is not None:
        table.put_item(Item=_to_ddb(school))
    else:
        _schools[school["id"]] = school
    return school


def list_all():
    table = _table()
    if table is not None:
        return [_from_ddb(i) for i in table.scan().get("Items", [])]
    return list(_schools.values())


def get(school_id):
    table = _table()
    if table is not None:
        item = table.get_item(Key={"id": school_id}).get("Item")
        return _from_ddb(item) if item else None
    return _schools.get(school_id)


def delete(school_id):
    table = _table()
    if table is not None:
        resp = table.delete_item(Key={"id": school_id}, ReturnValues="ALL_OLD")
        return "Attributes" in resp
    return _schools.pop(school_id, None) is not None


def upsert(school):
    """Write a full school record (used after mutating subscriptions)."""
    table = _table()
    if table is not None:
        table.put_item(Item=_to_ddb(school))
    else:
        _schools[school["id"]] = school
    return school


# ------------------------------------------------------- teacher actions

ACTION_TYPES = (
    "guidance_reviewed",      # staff reviewed today's guidance
    "pt_moved_indoors",       # PT / sports moved indoors
    "assembly_rescheduled",   # morning assembly rescheduled/cancelled
    "outdoor_rescheduled",    # outdoor activity moved to a cleaner window
    "unable_to_implement",    # could not implement (reason optional)
)

ACTION_LABELS = {
    "guidance_reviewed": "Guidance reviewed",
    "pt_moved_indoors": "PT moved indoors",
    "assembly_rescheduled": "Assembly rescheduled",
    "outdoor_rescheduled": "Outdoor activity rescheduled",
    "unable_to_implement": "Unable to implement",
}


def record_action(school_id, action, recorded_by, reason=None, date=None,
                  advisory_version=None):
    """Record a teacher acknowledgement. Idempotent per (date, action).

    Returns (record, created). Duplicate (date, action) entries are not
    created — the existing record is returned with created=False.
    """
    if action not in ACTION_TYPES:
        raise ValueError(f"Unknown action: {action!r}")
    school = get(school_id)
    if not school:
        return None, False
    date = date or datetime.now(IST).date().isoformat()
    actions = school.setdefault("actions", [])
    for existing in actions:
        if existing.get("date") == date and existing.get("action") == action:
            return existing, False
    record = {
        "date": date,
        "action": action,
        "label": ACTION_LABELS[action],
        "recorded_by": (recorded_by or "").strip()[:80] or "staff",
        "reason": (reason or "").strip()[:280] or None,
        "advisory_version": advisory_version,
        "recorded_at": datetime.now(IST).isoformat(),
    }
    actions.append(record)
    # Bound the embedded log: keep the most recent 200 entries.
    school["actions"] = actions[-200:]
    upsert(school)
    return record, True


def get_actions(school_id, date=None):
    """Daily (or all) action history for a school, newest first."""
    school = get(school_id)
    if not school:
        return None
    actions = school.get("actions", [])
    if date:
        actions = [a for a in actions if a.get("date") == date]
    return sorted(actions, key=lambda a: a.get("recorded_at", ""), reverse=True)


def set_last_bulletin(school_id, state):
    """Persist bulletin/notification state for material-change detection."""
    school = get(school_id)
    if not school:
        return False
    school["last_bulletin"] = state
    upsert(school)
    return True
