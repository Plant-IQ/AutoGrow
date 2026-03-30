from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from models import HealthResponse
from db.sqlite import get_session, SensorReading
from services.health_score import compute_health

router = APIRouter()


@router.get(
    "/",
    response_model=HealthResponse,
    summary="Plant Health Score",
    description="Aggregated 0–100 score combining soil moisture, temperature, humidity, and light compliance.",
)
def get_health(session: Session = Depends(get_session)):
    latest = session.exec(select(SensorReading).order_by(SensorReading.ts.desc()).limit(1)).first()
    score, components = compute_health(latest)
    return HealthResponse(score=score, components=components)
