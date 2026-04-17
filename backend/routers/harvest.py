from datetime import datetime, timedelta
from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from db.sqlite import get_session, PlantInstance, PlantType
from models import HarvestETAResponse, ErrorResponse

router = APIRouter()

@router.get("/", response_model=HarvestETAResponse)
def get_harvest_eta(session: Session = Depends(get_session)):
    plant = session.exec(
        select(PlantInstance)
        .where(PlantInstance.is_active == True)  # noqa: E712
        .order_by(PlantInstance.started_at.desc())
        .limit(1)
    ).first()

    if not plant:
        return HarvestETAResponse(days_to_harvest=0, projected_date=datetime.utcnow())

    plant_type = session.get(PlantType, plant.plant_type_id)
    if not plant_type:
        return HarvestETAResponse(days_to_harvest=0, projected_date=datetime.utcnow())

    # stage_durations_days = [seed_days, veg_days, bloom_days]
    total_days = sum(plant_type.stage_durations_days)
    elapsed = (datetime.utcnow() - plant.started_at).days
    days_remaining = max(0, total_days - elapsed)

    return HarvestETAResponse(
        days_to_harvest=days_remaining,
        projected_date=datetime.utcnow() + timedelta(days=days_remaining),
    )