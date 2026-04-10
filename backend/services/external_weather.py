"""Weather + solar context fetchers with provider fallback and caching."""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import httpx
from sqlmodel import Session

from db.sqlite import WeatherCache


DEFAULT_LAT = float(os.getenv("DEFAULT_LAT", 0) or 0)
DEFAULT_LON = float(os.getenv("DEFAULT_LON", 0) or 0)
WEATHER_CACHE_TTL_SECONDS = int(os.getenv("WEATHER_CACHE_TTL", 1800))  # 30 minutes
OWM_API_KEY = os.getenv("OWM_API_KEY", "")


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _cache_get(session: Session, key: str) -> Optional[dict]:
    row = session.get(WeatherCache, key)
    if not row:
        return None
    try:
        payload = json.loads(row.payload)
    except json.JSONDecodeError:
        return None
    if _now_utc() - row.ts.replace(tzinfo=timezone.utc) > timedelta(seconds=WEATHER_CACHE_TTL_SECONDS):
        return None
    return payload


def _cache_set(session: Session, key: str, payload: dict) -> dict:
    data = json.dumps(payload)
    row = WeatherCache(key=key, payload=data, ts=_now_utc())
    session.merge(row)
    session.commit()
    return payload


def _normalize_from_open_meteo(raw: dict, lat: float, lon: float) -> dict:
    current = raw.get("current", {})
    sunrise_list = raw.get("daily", {}).get("sunrise", [])
    sunset_list = raw.get("daily", {}).get("sunset", [])
    return {
        "source": "open-meteo",
        "lat": lat,
        "lon": lon,
        "temp_c": current.get("temperature_2m"),
        "humidity": current.get("relative_humidity_2m"),
        "wind_speed_mps": current.get("wind_speed_10m"),
        "apparent_temp_c": current.get("apparent_temperature"),
        "sunrise_utc": sunrise_list[0] if sunrise_list else None,
        "sunset_utc": sunset_list[0] if sunset_list else None,
        "fetched_at": _now_utc().isoformat(),
    }


def _normalize_from_openweather(raw: dict, lat: float, lon: float) -> dict:
    return {
        "source": "openweathermap",
        "lat": lat,
        "lon": lon,
        "temp_c": raw.get("main", {}).get("temp"),
        "humidity": raw.get("main", {}).get("humidity"),
        "wind_speed_mps": raw.get("wind", {}).get("speed"),
        "apparent_temp_c": raw.get("main", {}).get("feels_like"),
        "sunrise_utc": _unix_to_iso(raw.get("sys", {}).get("sunrise")),
        "sunset_utc": _unix_to_iso(raw.get("sys", {}).get("sunset")),
        "fetched_at": _now_utc().isoformat(),
    }


def _normalize_from_sunrise(raw: dict) -> dict:
    results = raw.get("results", {})
    return {
        "sunrise_utc": results.get("sunrise"),
        "sunset_utc": results.get("sunset"),
    }


def _unix_to_iso(ts: Optional[int]) -> Optional[str]:
    if ts is None:
        return None
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


def fetch_open_meteo(lat: float, lon: float) -> dict:
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,apparent_temperature,wind_speed_10m",
        "daily": "sunrise,sunset",
        "timezone": "UTC",
    }
    with httpx.Client(timeout=10) as client:
        resp = client.get(url, params=params)
        resp.raise_for_status()
        return _normalize_from_open_meteo(resp.json(), lat, lon)


def fetch_openweather(lat: float, lon: float) -> dict:
    if not OWM_API_KEY:
        raise RuntimeError("OWM_API_KEY is not configured")
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "lat": lat,
        "lon": lon,
        "appid": OWM_API_KEY,
        "units": "metric",
    }
    with httpx.Client(timeout=10) as client:
        resp = client.get(url, params=params)
        resp.raise_for_status()
        return _normalize_from_openweather(resp.json(), lat, lon)


def fetch_sunrise_sunset(lat: float, lon: float) -> dict:
    url = "https://api.sunrise-sunset.org/json"
    params = {"lat": lat, "lng": lon, "formatted": 0}
    with httpx.Client(timeout=10) as client:
        resp = client.get(url, params=params)
        resp.raise_for_status()
        return _normalize_from_sunrise(resp.json())


def get_weather_bundle(session: Session, lat: Optional[float], lon: Optional[float]) -> dict:
    lat = lat if lat is not None else DEFAULT_LAT
    lon = lon if lon is not None else DEFAULT_LON
    if lat == 0 and lon == 0:
        raise RuntimeError("Latitude/longitude required; set DEFAULT_LAT/DEFAULT_LON or pass lat/lon params")
    key = f"weather:{lat:.3f}:{lon:.3f}"

    cached = _cache_get(session, key)
    if cached:
        return cached

    last_error: Optional[str] = None
    try:
        data = fetch_open_meteo(lat, lon)
        return _cache_set(session, key, data)
    except Exception as exc:  # noqa: BLE001
        last_error = f"open-meteo: {exc}"

    try:
        data = fetch_openweather(lat, lon)
        # If openweather lacks sunrise/sunset, supplement from sunrise-sunset
        if data.get("sunrise_utc") is None or data.get("sunset_utc") is None:
            try:
                sun = fetch_sunrise_sunset(lat, lon)
                data.update({k: v for k, v in sun.items() if v})
            except Exception:
                pass
        return _cache_set(session, key, data)
    except Exception as exc:  # noqa: BLE001
        last_error = f"openweather: {exc}" if last_error is None else f"{last_error}; openweather: {exc}"

    if cached := _cache_get(session, key):
        return cached

    raise RuntimeError(last_error or "No weather providers reachable")
