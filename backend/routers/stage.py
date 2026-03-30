from fastapi import APIRouter, Depends
from sqlmodel import Session

from models import StageResponse
from db.sqlite import get_session
from services.stage_engine import get_current_stage

router = APIRouter()


@router.get(
    "/",
    response_model=StageResponse,
    summary="Current growth stage",
    description="Returns current stage index/name and days elapsed in stage.",
)
def get_stage(session: Session = Depends(get_session)):
    idx, name, days = get_current_stage(session)
    return StageResponse(stage=idx, label=name, days_in_stage=days)
