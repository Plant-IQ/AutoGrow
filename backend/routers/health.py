from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from models import HealthResponse
from services.health_score import compute_health
from db.sqlite import get_session, PlantInstance, SensorReading

router = APIRouter()


@router.get(
    "/",
    response_model=HealthResponse,
    summary="Plant Health Score",
    description="Aggregated 0–100 score combining soil moisture, temperature, humidity, and light compliance.",
)
def get_health(session: Session = Depends(get_session)):
    active = session.exec(
        select(PlantInstance)
        .where(PlantInstance.is_active == True)  # noqa: E712
        .order_by(PlantInstance.started_at.desc())
        .limit(1)
    ).first()
    if not active:
        return HealthResponse(score=0, components={})

    reading = session.exec(
        select(SensorReading)
        .where(SensorReading.plant_instance_id == active.id)
        .order_by(SensorReading.ts.desc())
        .limit(1)
    ).first()
    if not reading:
        return HealthResponse(score=0, components={})

    score, components = compute_health(reading)
    return HealthResponse(score=score, components=components)
