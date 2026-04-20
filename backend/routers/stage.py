from datetime import datetime
from fastapi import APIRouter, BackgroundTasks, Depends
from sqlmodel import Session, select
from pydantic import BaseModel

from models import StageResponse, StageUpdate
from db.sqlite import get_session, PlantInstance, PlantType
from services.stage_engine import upsert_stage, schedule_stage_transitions
from mqtt.publisher import publish_stage_update

router = APIRouter()


class StartGrowRequest(BaseModel):
    name: str = "New plant"
    plant_id: int = 1
    seed_days: int = 7
    veg_days: int = 21
    bloom_days: int = 0


@router.get("/", response_model=StageResponse)
def get_stage(session: Session = Depends(get_session)):
    active = session.exec(
        select(PlantInstance)
        .where(PlantInstance.is_active == True)
        .order_by(PlantInstance.started_at.desc())
        .limit(1)
    ).first()
    if not active:
        return StageResponse(stage=-1, label="Harvested", days_in_stage=0)

    plant_type = session.get(PlantType, active.plant_type_id)
    if not plant_type:
        return StageResponse(stage=active.current_stage_index, label="Seed", days_in_stage=1)

    idx = min(active.current_stage_index, 2)
    label = ["Seed", "Veg", "Bloom"][idx]
    days = max(1, (datetime.utcnow() - active.started_at).days + 1)
    return StageResponse(stage=idx, label=label, days_in_stage=days)

@router.post(
    "/set",
    response_model=StageResponse,
    summary="Set current growth stage",
    description="Manually set the current stage index and label; resets days_in_stage to 1.",
)
def set_stage(payload: StageUpdate, session: Session = Depends(get_session)):
    upsert_stage(session, payload.stage, payload.label)
    return StageResponse(stage=payload.stage, label=payload.label, days_in_stage=1)


@router.post("/reset")
async def reset_stage(
    req: StartGrowRequest,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
):
    upsert_stage(session, 0, "Seed")
    publish_stage_update(req.plant_id, 0)

    plant = session.get(PlantInstance, req.plant_id)
    started_at = plant.started_at if plant else datetime.utcnow()

    background_tasks.add_task(
        schedule_stage_transitions,
        req.plant_id,
        started_at,
        req.seed_days,
        req.veg_days,
        req.bloom_days,
    )

    return StageResponse(stage=0, label="Seed", days_in_stage=1)