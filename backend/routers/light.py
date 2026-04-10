# from fastapi import APIRouter

# from models import LightResponse, ErrorResponse

# router = APIRouter()


# @router.get(
#     "/",
#     response_model=LightResponse,
#     summary="Light spectrum recommendation",
#     description="Returns the recommended spectrum/preset and light hours accumulated today (mock data).",
#     responses={
#         422: {"model": ErrorResponse, "description": "Validation error"},
#         500: {
#             "model": ErrorResponse,
#             "description": "Internal server error",
#             "content": {"application/json": {"example": {"detail": "Database unavailable"}}},
#         },
#     },
# )
# def get_light():
#     return LightResponse(spectrum="veg", hours_today=12.0)


from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from models import LightResponse, ErrorResponse
from db.sqlite import get_session, PlantInstance, SensorReading

router = APIRouter()

@router.get("/", response_model=LightResponse)
def get_light(session: Session = Depends(get_session)):
    active = session.exec(
        select(PlantInstance)
        .where(PlantInstance.is_active == True)  # noqa: E712
        .order_by(PlantInstance.started_at.desc())
        .limit(1)
    ).first()
    if not active:
        return LightResponse(spectrum="", hours_today=0.0)

    reading = session.exec(
        select(SensorReading)
        .where(SensorReading.plant_instance_id == active.id)
        .order_by(SensorReading.ts.desc())
        .limit(1)
    ).first()
    if not reading:
        return LightResponse(spectrum="", hours_today=0.0)
    return LightResponse(spectrum=reading.spectrum or "", hours_today=reading.light_hrs_today or 0.0)
