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


def create(name, city, lat, lon, contact=None):
    school = {
        "id": uuid.uuid4().hex[:12],
        "name": name,
        "city": city,
        "lat": float(lat),
        "lon": float(lon),
        "contact": contact,
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
