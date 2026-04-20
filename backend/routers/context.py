from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from db.sqlite import get_session
from services.external_weather import get_outdoor_daily_avg, get_outdoor_history, get_weather_bundle

router = APIRouter()
outdoor_router = APIRouter()


@router.get(
    "/weather",
    summary="Outdoor weather + solar context",
    description="Returns temperature, humidity, wind, and sunrise/sunset from Open-Meteo or OpenWeatherMap with caching.",
)
def weather_context(
    lat: float | None = Query(None, description="Latitude; defaults to env DEFAULT_LAT"),
    lon: float | None = Query(None, description="Longitude; defaults to env DEFAULT_LON"),
    session: Session = Depends(get_session),
):
    try:
        return get_weather_bundle(session, lat, lon)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=str(exc))


@outdoor_router.get(
    "/history",
    summary="Outdoor hourly history",
    description="Returns hourly outdoor temperature and humidity history from Open-Meteo.",
)
def outdoor_history(
    lat: float | None = Query(None, description="Latitude; defaults to env DEFAULT_LAT"),
    lon: float | None = Query(None, description="Longitude; defaults to env DEFAULT_LON"),
    past_days: int = Query(7, ge=1, le=14, description="How many recent days to include"),
    session: Session = Depends(get_session),
):
    try:
        return get_outdoor_history(session, lat, lon, past_days=past_days)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=str(exc))


@outdoor_router.get(
    "/daily-avg",
    summary="Outdoor daily averages",
    description="Returns daily average outdoor temperature and humidity from Open-Meteo.",
)
def outdoor_daily_avg(
    lat: float | None = Query(None, description="Latitude; defaults to env DEFAULT_LAT"),
    lon: float | None = Query(None, description="Longitude; defaults to env DEFAULT_LON"),
    past_days: int = Query(7, ge=1, le=14, description="How many recent days to include"),
    session: Session = Depends(get_session),
):
    try:
        return get_outdoor_daily_avg(session, lat, lon, past_days=past_days)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=str(exc))
