from fastapi import APIRouter, BackgroundTasks, Depends
from sqlmodel import Session
from pydantic import BaseModel

from models import StageResponse, StageUpdate
from db.sqlite import get_session
from services.stage_engine import get_current_stage, upsert_stage, schedule_stage_transitions
from mqtt.publisher import publish_stage_update

router = APIRouter()


class StartGrowRequest(BaseModel):
    name: str = "New plant"
    plant_id: int = 1
    seed_days: int = 7
    veg_days: int = 21
    bloom_days: int = 0


@router.get(
    "/",
    response_model=StageResponse,
    summary="Current growth stage",
    description="Returns current stage index/name and days elapsed in stage.",
)
def get_stage(session: Session = Depends(get_session)):
    idx, name, days = get_current_stage(session)
    return StageResponse(stage=idx, label=name, days_in_stage=days)


@router.post(
    "/set",
    response_model=StageResponse,
    summary="Set current growth stage",
    description="Manually set the current stage index and label; resets days_in_stage to 1.",
)
def set_stage(payload: StageUpdate, session: Session = Depends(get_session)):
    upsert_stage(session, payload.stage, payload.label)
    idx, name, days = get_current_stage(session)
    return StageResponse(stage=idx, label=name, days_in_stage=days)


@router.post(
    "/reset",
    summary="Reset to seed stage and start new grow cycle",
    description="Resets to stage 0 (Seed), publishes state=0 via MQTT, and schedules state=1/2 after seed/veg days.",
)
async def reset_stage(
    req: StartGrowRequest,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
):
    upsert_stage(session, 0, "Seed")

    publish_stage_update(req.plant_id, 0)

    background_tasks.add_task(
        schedule_stage_transitions,
        req.plant_id,
        req.seed_days,
        req.veg_days,
        req.bloom_days,
    )

    idx, name, days = get_current_stage(session)
    return StageResponse(stage=idx, label=name, days_in_stage=days)