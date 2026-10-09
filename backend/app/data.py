"""Open-Meteo data layer: air quality + geocoding.

- Air Quality API: https://air-quality-api.open-meteo.com/v1/air-quality
  (free, no key). Hourly PM2.5/PM10/O3/NO2/SO2/CO, 3-day forecast.
- Geocoding API: https://geocoding-api.open-meteo.com/v1/search.

Results are cached in memory for 10 minutes per (lat, lon) rounded to 2dp
so we don't hammer the free API.

No fake/mock data: if Open-Meteo is unreachable, :class:`AQServiceError`
is raised and the API layer turns it into HTTP 503.
"""

import os
import time
from datetime import datetime
from zoneinfo import ZoneInfo

import httpx

IST = ZoneInfo("Asia/Kolkata")

AIR_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
GEO_URL = "https://geocoding-api.open-meteo.com/v1/search"
HOURLY_VARS = "pm2_5,pm10,ozone,nitrogen_dioxide,sulphur_dioxide,carbon_monoxide"
TTL_SECONDS = 600  # 10-minute cache

# Open-Meteo variable name -> our short key
_VAR_MAP = {
    "pm2_5": "pm2_5",
    "pm10": "pm10",
    "ozone": "o3",
    "nitrogen_dioxide": "no2",
    "sulphur_dioxide": "so2",
    "carbon_monoxide": "co",
}

# (cache_key) -> (expires_epoch, normalized_payload)
_cache: dict = {}


class AQServiceError(RuntimeError):
    """Raised when the upstream Open-Meteo API cannot be reached."""


_client = None


def egress_httpx_client(**kwargs):
    """httpx.Client hardened for this sandbox: explicit egress proxy + CA bundle.

    ``trust_env=False``: this sandbox's ``no_proxy`` contains bracketed IPv6
    literals (``[::1]``) that httpx's env-proxy parsing chokes on, so we read
    the egress proxy ourselves instead of letting httpx parse the environment.
    """
    proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
    # trust_env=False also disables SSL_CERT_FILE honoring, so pass it explicitly.
    verify = os.environ.get("SSL_CERT_FILE") or True
    return httpx.Client(timeout=kwargs.pop("timeout", 15.0), trust_env=False,
                        proxy=proxy or None, verify=verify, **kwargs)


def egress_async_httpx_client(**kwargs):
    """Async variant of :func:`egress_httpx_client`."""
    proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
    verify = os.environ.get("SSL_CERT_FILE") or True
    return httpx.AsyncClient(timeout=kwargs.pop("timeout", 15.0), trust_env=False,
                             proxy=proxy or None, verify=verify, **kwargs)


def _http_client():
    """Shared client for Open-Meteo calls."""
    global _client
    if _client is None:
        _client = egress_httpx_client()
    return _client


def _http_get(url, params):
    try:
        resp = _http_client().get(url, params=params)
        resp.raise_for_status()
        return resp.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise AQServiceError(f"Upstream data source unreachable: {exc}") from exc


def _localize(iso_str, tz_name):
    """Parse an Open-Meteo local ISO timestamp and return it in Asia/Kolkata."""
    dt = datetime.fromisoformat(iso_str)
    if dt.tzinfo is None:  # timezone=auto returns naive local times
        dt = dt.replace(tzinfo=ZoneInfo(tz_name))
    return dt.astimezone(IST)


def _current_index(times_local, tz_name):
    """Index of the most recent hourly slot at or before 'now'."""
    now = datetime.now(ZoneInfo(tz_name)).replace(minute=0, second=0, microsecond=0)
    idx = 0
    for i, iso in enumerate(times_local):
        slot = datetime.fromisoformat(iso)
        if slot.tzinfo is None:
            slot = slot.replace(tzinfo=ZoneInfo(tz_name))
        if slot <= now:
            idx = i
        else:
            break
    return idx


def fetch_air_quality(lat, lon):
    """Return normalized hourly data for a location (cached 10 min).

    Returns dict with:
      times: [datetime (Asia/Kolkata)] per hourly slot
      pollutants: {pm2_5|pm10|o3|no2|so2|co: [float|None]} (µg/m³)
      current_idx: int — slot matching the current hour
      timezone: str — location timezone reported by Open-Meteo
    """
    key = (round(float(lat), 2), round(float(lon), 2))
    now = time.time()
    cached = _cache.get(key)
    if cached and cached[0] > now:
        return cached[1]

    payload = _http_get(AIR_URL, {
        "latitude": key[0],
        "longitude": key[1],
        "hourly": HOURLY_VARS,
        "timezone": "auto",
        "forecast_days": 3,
    })
    hourly = payload.get("hourly") or {}
    tz_name = payload.get("timezone", "Asia/Kolkata")
    raw_times = hourly.get("time") or []
    if not raw_times:
        raise AQServiceError("Upstream data source returned no hourly data")

    times = [_localize(t, tz_name) for t in raw_times]
    pollutants = {}
    n = len(raw_times)
    for var, short in _VAR_MAP.items():
        vals = hourly.get(var) or [None] * n
        pollutants[short] = [None if v is None else float(v) for v in vals[:n]]

    data = {
        "times": times,
        "pollutants": pollutants,
        "current_idx": _current_index(raw_times, tz_name),
        "timezone": tz_name,
    }
    _cache[key] = (now + TTL_SECONDS, data)
    return data


def search_places(query, limit=8):
    """Geocode a place name; Indian results are ranked first."""
    payload = _http_get(GEO_URL, {
        "name": query,
        "count": max(1, min(int(limit), 20)),
        "language": "en",
        "format": "json",
    })
    results = payload.get("results") or []
    # Bias to India: exact/India matches first, then by population.
    results.sort(key=lambda r: (
        0 if (r.get("country") or "") == "India" else 1,
        -(r.get("population") or 0),
    ))
    return [{
        "name": r.get("name"),
        "admin1": r.get("admin1"),
        "country": r.get("country"),
        "lat": r.get("latitude"),
        "lon": r.get("longitude"),
    } for r in results]
