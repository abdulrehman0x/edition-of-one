from __future__ import annotations

import json
import time
import urllib.request
from pathlib import Path
from typing import Dict, Optional

from ..core.config import get_settings

WEATHER_TTL = 3600

CITY_COORDS = {
    "islamabad": (33.68, 73.05),
    "rawalpindi": (33.60, 73.04),
    "karachi": (24.86, 67.01),
    "lahore": (31.55, 74.34),
    "peshawar": (34.01, 71.58),
    "quetta": (30.18, 66.99),
}


def _condition(code) -> str:
    try:
        c = int(code)
    except (TypeError, ValueError):
        return "unavailable"
    if c == 0:
        return "Clear"
    if c in (1, 2):
        return "Partly cloudy"
    if c == 3:
        return "Overcast"
    if c in (45, 48):
        return "Fog"
    if 51 <= c <= 67 or 80 <= c <= 82:
        return "Rain"
    if 71 <= c <= 77 or c in (85, 86):
        return "Snow"
    if c >= 95:
        return "Thunderstorm"
    return "Mixed"


def _cache_path(city: str) -> Path:
    s = get_settings()
    safe = "".join(ch if ch.isalnum() else "_" for ch in city.lower())
    return Path(s.cache_dir) / f"weather_{safe}.json"


def get_weather(city: str, lat: float, lon: float) -> Dict[str, Optional[object]]:
    # Blocking (urllib). Call from async code via asyncio.to_thread.
    cache = _cache_path(city)
    cache.parent.mkdir(parents=True, exist_ok=True)
    if cache.exists() and time.time() - cache.stat().st_mtime < WEATHER_TTL:
        try:
            return json.loads(cache.read_text(encoding="utf-8"))
        except Exception:
            pass

    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        "&current=temperature_2m,weather_code"
        "&daily=temperature_2m_max,temperature_2m_min"
        "&timezone=auto"
    )
    try:
        with urllib.request.urlopen(url, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        out = {
            "city": city,
            "temp_c": data.get("current", {}).get("temperature_2m"),
            "high_c": (data.get("daily", {}).get("temperature_2m_max") or [None])[0],
            "low_c": (data.get("daily", {}).get("temperature_2m_min") or [None])[0],
            "condition": _condition(data.get("current", {}).get("weather_code")),
        }
        cache.write_text(json.dumps(out), encoding="utf-8")
        return out
    except Exception:
        return {
            "city": city,
            "temp_c": None,
            "high_c": None,
            "low_c": None,
            "condition": "unavailable",
        }


def weather_for(city: str) -> Dict[str, Optional[object]]:
    # Weather for the reader's own city; unknown cities use the demo coords.
    s = get_settings()
    city = city or s.demo_city
    lat, lon = CITY_COORDS.get(city.strip().lower(), (s.demo_lat, s.demo_lon))
    return get_weather(city, lat, lon)
