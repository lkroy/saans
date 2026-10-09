"""CPCB (India) AQI computation from pollutant concentrations.

HONESTY NOTE: the CPCB officially computes the AQI from 24-hour average
concentrations. Open-Meteo only gives us *hourly modelled* concentrations,
so we apply the official CPCB breakpoint tables to hourly values and label
every result ``data_status: "indicative"``. These numbers must never be
presented as official CPCB AQI values.

Breakpoint tables: CPCB National Air Quality Index (2014). Concentrations in
µg/m³ for PM2.5/PM10/NO2/O3(8h)/SO2; CO is in mg/m³ (8h average), so callers
must convert CO from µg/m³ → mg/m³ (÷1000) before calling :func:`compute`.
"""

# (conc_lo, conc_hi, index_lo, index_hi)
_PM25 = [(0, 30, 0, 50), (30, 60, 50, 100), (60, 90, 100, 200),
         (90, 120, 200, 300), (120, 250, 300, 400), (250, 10_000, 400, 500)]
_PM10 = [(0, 50, 0, 50), (50, 100, 50, 100), (100, 250, 100, 200),
         (250, 350, 200, 300), (350, 430, 300, 400), (430, 10_000, 400, 500)]
_NO2 = [(0, 40, 0, 50), (40, 80, 50, 100), (80, 180, 100, 200),
        (180, 280, 200, 300), (280, 400, 300, 400), (400, 10_000, 400, 500)]
_O3 = [(0, 50, 0, 50), (50, 100, 50, 100), (100, 168, 100, 200),
       (168, 208, 200, 300), (208, 748, 300, 400), (748, 10_000, 400, 500)]
_SO2 = [(0, 40, 0, 50), (40, 80, 50, 100), (80, 380, 100, 200),
        (380, 800, 200, 300), (800, 1600, 300, 400), (1600, 10_000, 400, 500)]
_CO = [(0, 1.0, 0, 50), (1.0, 2.0, 50, 100), (2.0, 10, 100, 200),
       (10, 17, 200, 300), (17, 34, 300, 400), (34, 10_000, 400, 500)]

_BREAKPOINTS = {
    "pm2_5": _PM25,
    "pm10": _PM10,
    "no2": _NO2,
    "o3": _O3,
    "so2": _SO2,
    "co": _CO,
}

_CATEGORY_COLORS = [
    (50, "Good", "#2ca02c"),
    (100, "Satisfactory", "#7ac143"),
    (200, "Moderate", "#ffbf00"),
    (300, "Poor", "#ff7f0e"),
    (400, "Very Poor", "#d62728"),
    (500, "Severe", "#8b0000"),
]


def sub_index(conc, breakpoints):
    """Linear-interpolated sub-index for one pollutant; None if no data."""
    if conc is None:
        return None
    c = max(0.0, float(conc))
    for clo, chi, ilo, ihi in breakpoints:
        if c <= chi:
            if chi == clo:
                return float(ihi)
            return (ihi - ilo) / (chi - clo) * (c - clo) + ilo
    return 500.0


def category(aqi):
    """Return (category_name, color_hex) for an AQI value."""
    for limit, name, color in _CATEGORY_COLORS:
        if aqi <= limit:
            return name, color
    return "Severe", "#8b0000"


def compute(concentrations):
    """Compute overall AQI = max of pollutant sub-indices.

    ``concentrations``: dict with keys pm2_5, pm10, o3, no2, so2 (µg/m³)
    and co (**mg/m³** — convert before calling).

    Returns ``(aqi:int, dominant:str, sub_indices:dict)`` or
    ``(None, None, {})`` when no pollutant data is available.
    """
    subs = {}
    for pollutant, bps in _BREAKPOINTS.items():
        idx = sub_index(concentrations.get(pollutant), bps)
        if idx is not None:
            subs[pollutant] = idx
    if not subs:
        return None, None, {}
    dominant = max(subs, key=subs.get)
    aqi = int(round(subs[dominant]))
    return aqi, dominant, {k: int(round(v)) for k, v in subs.items()}
