"""Weather + solar context fetchers with provider fallback and caching."""

from __future__ import annotations
import json
import os
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Optional
import httpx
from sqlmodel import Session, select

from db.sqlite import (
    OutdoorWeatherCurrent,
    OutdoorWeatherHistory,
    WeatherCache,
    engine,
    mysql_engine,
)

DEFAULT_LAT = float(os.getenv("DEFAULT_LAT", 13.8476))
DEFAULT_LON = float(os.getenv("DEFAULT_LON", 100.5696))
WEATHER_CACHE_TTL_SECONDS = int(os.getenv("WEATHER_CACHE_TTL", 3600))
DEFAULT_TIMEZONE = os.getenv("WEATHER_TIMEZONE", "Asia/Bangkok")

def _now_utc() -> datetime:
    return datetime.now(timezone.utc)

def _cache_get(session: Session, key: str) -> Optional[dict]:
    row = session.get(WeatherCache, key)
    if not row: return None
    try:
        payload = json.loads(row.payload)
        if _now_utc() - row.ts.replace(tzinfo=timezone.utc) > timedelta(seconds=WEATHER_CACHE_TTL_SECONDS):
            return None
        return payload
    except: return None

def _cache_set(session: Session, key: str, payload: dict) -> dict:
    data = json.dumps(payload)
    row = WeatherCache(key=key, payload=data, ts=_now_utc())
    session.merge(row)
    session.commit()
    return payload

def _parse_iso_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        normalized = value.replace("Z", "+00:00")
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None

def _sync_current_weather_to_mysql(payload: dict) -> bool:
    fetched_at = _parse_iso_datetime(payload.get("fetched_at"))
    if fetched_at is None:
        return False

    try:
        with Session(mysql_engine) as session:
            row = OutdoorWeatherCurrent(
                lat=payload.get("lat"),
                lon=payload.get("lon"),
                source=payload.get("source") or "",
                temp_c=payload.get("temp_c"),
                humidity=payload.get("humidity"),
                wind_speed_mps=payload.get("wind_speed_mps"),
                apparent_temp_c=payload.get("apparent_temp_c"),
                sunrise_utc=_parse_iso_datetime(payload.get("sunrise_utc")),
                sunset_utc=_parse_iso_datetime(payload.get("sunset_utc")),
                fetched_at=fetched_at,
            )
            session.add(row)
            session.commit()
            return True
    except Exception as exc:
        print(f"[MySQL] Failed to sync current weather: {exc}")
        return False

def _sync_weather_history_to_mysql(payload: dict) -> int:
    lat = payload.get("lat")
    lon = payload.get("lon")
    source = payload.get("source") or ""
    stored = 0

    try:
        with Session(mysql_engine) as session:
            for point in payload.get("points", []):
                ts = _parse_iso_datetime(point.get("ts"))
                if ts is None:
                    continue

                existing = session.exec(
                    select(OutdoorWeatherHistory).where(
                        OutdoorWeatherHistory.lat == lat,
                        OutdoorWeatherHistory.lon == lon,
                        OutdoorWeatherHistory.ts == ts,
                    )
                ).first()

                if existing:
                    existing.source = source
                    existing.temp_c = point.get("temp")
                    existing.humidity = point.get("humidity")
                else:
                    session.add(
                        OutdoorWeatherHistory(
                            lat=lat,
                            lon=lon,
                            source=source,
                            ts=ts,
                            temp_c=point.get("temp"),
                            humidity=point.get("humidity"),
                        )
                    )
                stored += 1

            session.commit()
    except Exception as exc:
        print(f"[MySQL] Failed to sync weather history: {exc}")
        return 0

    return stored

# --- API Fetching Logic ---

def fetch_open_meteo(lat: float, lon: float) -> dict:
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat, "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,apparent_temperature,wind_speed_10m",
        "daily": "sunrise,sunset", "timezone": DEFAULT_TIMEZONE,
    }
    with httpx.Client(timeout=10) as client:
        resp = client.get(url, params=params)
        resp.raise_for_status()
        raw = resp.json()
        current = raw.get("current", {})
        daily = raw.get("daily", {})
        sunrise = next((value for value in daily.get("sunrise", []) if value), None)
        sunset = next((value for value in daily.get("sunset", []) if value), None)
        return {
            "source": "open-meteo", "lat": lat, "lon": lon,
            "temp_c": current.get("temperature_2m"),
            "humidity": current.get("relative_humidity_2m"),
            "apparent_temp_c": current.get("apparent_temperature"),
            "wind_speed_mps": current.get("wind_speed_10m"),
            "sunrise_utc": sunrise,
            "sunset_utc": sunset,
            "timezone": DEFAULT_TIMEZONE,
            "fetched_at": _now_utc().isoformat(),
        }

def fetch_open_meteo_history(lat: float, lon: float, past_days: int = 7) -> dict:
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat, "longitude": lon,
        "hourly": "temperature_2m,relative_humidity_2m",
        "past_days": max(1, min(past_days, 14)), "forecast_days": 1, "timezone": "UTC",
    }
    with httpx.Client(timeout=15) as client:
        resp = client.get(url, params=params)
        resp.raise_for_status()
        raw = resp.json()
    
    hourly = raw.get("hourly", {})
    points = [{"ts": ts, "temp": t, "humidity": h} 
              for ts, t, h in zip(hourly.get("time", []), hourly.get("temperature_2m", []), hourly.get("relative_humidity_2m", []))]
    return {"source": "open-meteo", "lat": lat, "lon": lon, "points": points, "fetched_at": _now_utc().isoformat()}


def get_weather_bundle(session: Session, lat: Optional[float] = None, lon: Optional[float] = None) -> dict:
    lat, lon = lat or DEFAULT_LAT, lon or DEFAULT_LON
    key = f"weather:v3:{DEFAULT_TIMEZONE}:{lat:.3f}:{lon:.3f}"
    
    cached = _cache_get(session, key)
    if cached:
        _sync_current_weather_to_mysql(cached)
        return cached
    
    data = fetch_open_meteo(lat, lon)
    _sync_current_weather_to_mysql(data)
    
    return _cache_set(session, key, data)

def get_outdoor_history(session: Session, lat: Optional[float] = None, lon: Optional[float] = None, past_days: int = 7) -> dict:
    lat, lon = lat or DEFAULT_LAT, lon or DEFAULT_LON
    key = f"outdoor-history:{lat:.3f}:{lon:.3f}:{past_days}"
    
    cached = _cache_get(session, key)
    if cached:
        _sync_weather_history_to_mysql(cached)
        return cached
    
    data = fetch_open_meteo_history(lat, lon, past_days=past_days)
    _sync_weather_history_to_mysql(data)
    return _cache_set(session, key, data)

def get_outdoor_daily_avg(session: Session, lat: Optional[float], lon: Optional[float], past_days: int = 7) -> dict:
    history = get_outdoor_history(session, lat, lon, past_days=past_days)
    grouped = defaultdict(lambda: {"temp_sum": 0.0, "humidity_sum": 0.0, "count": 0.0})
    
    for pt in history.get("points", []):
        date_key = str(pt.get("ts"))[:10]
        bucket = grouped[date_key]
        bucket["temp_sum"] += pt.get("temp", 0)
        bucket["humidity_sum"] += pt.get("humidity", 0)
        bucket["count"] += 1
        
    points = [{"date": k, "avg_temp": v["temp_sum"]/v["count"], "avg_humidity": v["humidity_sum"]/v["count"]} 
              for k, v in sorted(grouped.items()) if v["count"] > 0]
    return {"points": points, "source": "open-meteo"}

def backfill_weather_cache_to_mysql():
    migrated = {"current": 0, "history": 0}

    try:
        with Session(engine) as session:
            rows = session.exec(select(WeatherCache)).all()
            for row in rows:
                try:
                    payload = json.loads(row.payload)
                except json.JSONDecodeError:
                    continue

                if row.key.startswith("weather:"):
                    migrated["current"] += int(_sync_current_weather_to_mysql(payload))
                elif row.key.startswith("outdoor-history:"):
                    migrated["history"] += _sync_weather_history_to_mysql(payload)
    except Exception as exc:
        print(f"[MySQL] Weather backfill failed: {exc}")

    return migrated
