# from datetime import datetime
# from fastapi import APIRouter
# from models import HistoryResponse

# router = APIRouter()

# @router.get("/", response_model=HistoryResponse)
# def get_history():
#     # Mock empty history until schema/data is aligned
#     return HistoryResponse(points=[])


from datetime import datetime, timedelta
from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from models import HistoryResponse, HistoryPoint
from db.sqlite import get_session, SensorReading

router = APIRouter()

@router.get("/", response_model=HistoryResponse)
def get_history(session: Session = Depends(get_session)):
    now = datetime.utcnow()
    rows = session.exec(select(SensorReading).order_by(SensorReading.ts.desc()).limit(168)).all()

    use_mock = not rows
    if rows:
        newest = rows[0].ts
        if (now - newest) > timedelta(hours=24):
            use_mock = True

    if use_mock:
        pts = []
    else:
        pts = [
            HistoryPoint(
                ts=r.ts,
                soil=r.soil,
                temp=r.temp,
                humidity=r.humidity,
                light=r.light,
                stage=r.stage,
                stage_name=r.stage_name,
                spectrum=r.spectrum,
                pump_on=r.pump_on,
                pump_status=r.pump_status,
                light_hrs_today=r.light_hrs_today,
                harvest_eta_days=r.harvest_eta_days,
                health_score=r.health_score,
            )
            for r in reversed(rows)
        ]

    return HistoryResponse(points=pts)