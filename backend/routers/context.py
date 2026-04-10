from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from db.sqlite import get_session
from services.external_weather import get_weather_bundle

router = APIRouter()


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

