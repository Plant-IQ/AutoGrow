"""Weather + solar context fetchers with provider fallback and caching."""

from __future__ import annotations

import json
import os
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Optional

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


def fetch_open_meteo_history(lat: float, lon: float, past_days: int = 7) -> dict:
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "temperature_2m,relative_humidity_2m",
        "past_days": max(1, min(past_days, 14)),
        "forecast_days": 1,
        "timezone": "UTC",
    }
    with httpx.Client(timeout=10) as client:
        resp = client.get(url, params=params)
        resp.raise_for_status()
        raw = resp.json()

    hourly = raw.get("hourly", {})
    times = hourly.get("time", [])
    temps = hourly.get("temperature_2m", [])
    humidities = hourly.get("relative_humidity_2m", [])
    points = []

    for ts, temp, humidity in zip(times, temps, humidities):
        points.append(
            {
                "ts": ts,
                "temp": temp,
                "humidity": humidity,
            }
        )

    return {
        "source": "open-meteo",
        "lat": lat,
        "lon": lon,
        "points": points,
        "fetched_at": _now_utc().isoformat(),
    }


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


def get_outdoor_history(session: Session, lat: Optional[float], lon: Optional[float], past_days: int = 7) -> dict:
    lat = lat if lat is not None else DEFAULT_LAT
    lon = lon if lon is not None else DEFAULT_LON
    if lat == 0 and lon == 0:
        raise RuntimeError("Latitude/longitude required; set DEFAULT_LAT/DEFAULT_LON or pass lat/lon params")

    key = f"outdoor-history:{lat:.3f}:{lon:.3f}:{past_days}"
    cached = _cache_get(session, key)
    if cached:
        return cached

    data = fetch_open_meteo_history(lat, lon, past_days=past_days)
    return _cache_set(session, key, data)


def get_outdoor_daily_avg(session: Session, lat: Optional[float], lon: Optional[float], past_days: int = 7) -> dict:
    history = get_outdoor_history(session, lat, lon, past_days=past_days)

    grouped: dict[str, dict[str, float]] = defaultdict(lambda: {"temp_sum": 0.0, "humidity_sum": 0.0, "count": 0.0})
    for point in history.get("points", []):
        ts = point.get("ts")
        if not ts:
            continue
        date_key = str(ts)[:10]
        bucket = grouped[date_key]
        temp = point.get("temp")
        humidity = point.get("humidity")
        if isinstance(temp, (int, float)):
            bucket["temp_sum"] += float(temp)
        if isinstance(humidity, (int, float)):
            bucket["humidity_sum"] += float(humidity)
        bucket["count"] += 1.0

    points = []
    for date_key in sorted(grouped.keys()):
        bucket = grouped[date_key]
        if bucket["count"] <= 0:
          continue
        points.append(
            {
                "date": date_key,
                "avg_temp": bucket["temp_sum"] / bucket["count"],
                "avg_humidity": bucket["humidity_sum"] / bucket["count"],
            }
        )

    return {
        "source": history.get("source", "open-meteo"),
        "lat": history.get("lat"),
        "lon": history.get("lon"),
        "points": points,
        "fetched_at": history.get("fetched_at"),
    }
