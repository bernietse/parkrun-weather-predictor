"""Fetch weather from Open-Meteo (free, no API key).

Location is currently fixed below; change LOCATION_LAT/LON to point this at
a different parkrun course.
"""
import urllib.request
import json
from datetime import datetime, date

LOCATION_LAT = 50.7236
LOCATION_LON = -3.5275
PARKRUN_HOUR = 9  # parkrun always starts at 9am


def get_forecast_at_9am(target_date: date | None = None) -> dict:
    """Return weather at 9am on target_date (default: today) for LOCATION_LAT/LON.

    Open-Meteo serves both forecast (future/today) and historical archive
    (past dates) from the same shape of hourly response, so callers don't
    need to know which endpoint was used.
    """
    if target_date is None:
        target_date = date.today()

    is_past = target_date < date.today()
    base = (
        "https://archive-api.open-meteo.com/v1/archive"
        if is_past
        else "https://api.open-meteo.com/v1/forecast"
    )
    params = (
        f"latitude={LOCATION_LAT}&longitude={LOCATION_LON}"
        "&hourly=temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,wind_direction_10m"
        "&timezone=Europe%2FLondon"
    )
    if is_past:
        d = target_date.isoformat()
        params += f"&start_date={d}&end_date={d}"
    else:
        params += "&forecast_days=7"

    url = f"{base}?{params}"
    with urllib.request.urlopen(url, timeout=10) as resp:
        data = json.load(resp)

    times = data["hourly"]["time"]
    target_prefix = f"{target_date.isoformat()}T{PARKRUN_HOUR:02d}:00"
    idx = next((i for i, t in enumerate(times) if t == target_prefix), None)
    if idx is None:
        raise ValueError(f"No weather data available for {target_prefix}")

    h = data["hourly"]
    return {
        "date": target_date.isoformat(),
        "temperature_c": h["temperature_2m"][idx],
        "humidity_pct": h["relative_humidity_2m"][idx],
        "precipitation_mm": h["precipitation"][idx],
        "wind_speed_kmh": h["wind_speed_10m"][idx],
        "wind_direction_deg": h["wind_direction_10m"][idx],
    }
