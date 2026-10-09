"""School store.

In-memory dict for the hackathon demo. In the SAM deploy this is replaced by
the ``saans-schools`` DynamoDB table (see infra/template.yaml) — same CRUD
shape, keyed by school id.
"""

import uuid
from datetime import datetime

from .data import IST

_schools: dict = {}


def create(name, city, lat, lon, contact=None):
    school_id = uuid.uuid4().hex[:12]
    school = {
        "id": school_id,
        "name": name,
        "city": city,
        "lat": float(lat),
        "lon": float(lon),
        "contact": contact,
        "created_at": datetime.now(IST).isoformat(),
    }
    _schools[school_id] = school
    return school


def list_all():
    return list(_schools.values())


def get(school_id):
    return _schools.get(school_id)


def delete(school_id):
    return _schools.pop(school_id, None) is not None
