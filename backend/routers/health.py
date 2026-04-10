from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from models import HealthResponse
from services.health_score import compute_health
from db.sqlite import get_session, PlantInstance, PlantTypeTarget, SensorReading
from services.health_score import TargetRange

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
    target_row = session.exec(
        select(PlantTypeTarget).where(PlantTypeTarget.plant_type_id == active.plant_type_id)
    ).first()
    target = None
    if target_row:
        target = TargetRange(
            temp_min_c=target_row.temp_min_c,
            temp_max_c=target_row.temp_max_c,
            humidity_min=target_row.humidity_min,
            humidity_max=target_row.humidity_max,
            light_min_lux=target_row.light_min_lux,
            light_max_lux=target_row.light_max_lux,
        )

    score, components = compute_health(reading, targets=target)
    return HealthResponse(score=score, components=components)
