# from datetime import datetime
# from fastapi import APIRouter

# from models import PumpStatusResponse, ErrorResponse

# router = APIRouter()


# @router.get(
#     "/",
#     response_model=PumpStatusResponse,
#     summary="Pump vibration status",
#     description="Returns last vibration reading from the pump (mocked until hardware is connected).",
#     responses={
#         422: {"model": ErrorResponse, "description": "Validation error"},
#         500: {
#             "model": ErrorResponse,
#             "description": "Internal server error",
#             "content": {"application/json": {"example": {"detail": "Database unavailable"}}},
#         },
#     },
# )
# def get_pump_status():
#     return PumpStatusResponse(ok=True, vibration=0.12, last_checked=datetime.utcnow())


from datetime import datetime
from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from models import PumpStatusResponse, ErrorResponse
from db.sqlite import get_session, PlantInstance, SensorReading

router = APIRouter()

@router.get("/", response_model=PumpStatusResponse)
def get_pump_status(session: Session = Depends(get_session)):
    active = session.exec(
        select(PlantInstance)
        .where(PlantInstance.is_active == True)  # noqa: E712
        .order_by(PlantInstance.started_at.desc())
        .limit(1)
    ).first()
    if not active:
        return PumpStatusResponse(ok=False, vibration=0.0, last_checked=datetime.utcnow())

    reading = session.exec(
        select(SensorReading)
        .where(SensorReading.plant_instance_id == active.id)
        .order_by(SensorReading.ts.desc())
        .limit(1)
    ).first()
    if not reading:
        return PumpStatusResponse(ok=False, vibration=0.0, last_checked=datetime.utcnow())

    return PumpStatusResponse(
        ok=bool(reading.pump_on),
        vibration=float(reading.vibration or 0.0),
        last_checked=reading.ts,
    )
