# from datetime import datetime
# from fastapi import APIRouter
# from models import HistoryResponse

# router = APIRouter()

# @router.get("/", response_model=HistoryResponse)
# def get_history():
#     # Mock empty history until schema/data is aligned
#     return HistoryResponse(points=[])


from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, SQLModel, Field, select, create_engine
from sqlalchemy.engine import URL
from models import HistoryResponse, HistoryPoint

router = APIRouter()

MYSQL_URL = URL.create(
    drivername="mysql+pymysql",
    username="b6710545652",
    password="natcha.limsu@ku.th",
    host="iot.cpe.ku.ac.th",
    port=3306,
    database="b6710545652",
)
mysql_engine = create_engine(
    MYSQL_URL,
    pool_pre_ping=True,
    pool_recycle=1800,
)

def get_mysql_session():
    with Session(mysql_engine) as session:
        yield session

class AutogrowReading(SQLModel, table=True):
    __tablename__ = "Autogrow"
    id: Optional[int] = Field(default=None, primary_key=True)
    ts: datetime = Field(default_factory=datetime.utcnow)
    stage: int = 0
    stage_name: str = ""
    spectrum: str = ""
    temp1: float = 0.0
    temp2: float = 0.0
    humidity: float = 0.0
    soil_pct: float = 0.0
    light_lux: float = 0.0
    vibration: float = 0.0
    pump_on: int = 0
    pump_status: str = ""
    light_hrs_today: float = 0.0
    harvest_eta_days: int = 0
    health_score: int = 0

@router.get("/", response_model=HistoryResponse)
def get_history(
    until_stage: str | None = Query(
        None,
        description="If provided, trims off any newer rows after the most recent row with this stage name.",
    ),
    session: Session = Depends(get_mysql_session),
):
    rows = session.exec(
        select(AutogrowReading)
        .order_by(AutogrowReading.ts.desc())
        .limit(168)
    ).all()

    if not rows:
        return HistoryResponse(points=[])

    if until_stage:
        normalized_stage = until_stage.strip().lower()
        cutoff_row = next((row for row in rows if (row.stage_name or "").strip().lower() == normalized_stage), None)
        if cutoff_row is not None:
            rows = [row for row in rows if row.ts <= cutoff_row.ts]

    pts = [
        HistoryPoint(
            ts=r.ts,
            soil=r.soil_pct,
            temp=r.temp1,
            humidity=r.humidity,
            light=r.light_lux,
            stage=r.stage,
            stage_name=r.stage_name,
            spectrum=r.spectrum,
            pump_on=bool(r.pump_on),
            pump_status=r.pump_status,
            light_hrs_today=r.light_hrs_today,
            harvest_eta_days=r.harvest_eta_days,
            health_score=r.health_score,
        )
        for r in reversed(rows)
    ]
    return HistoryResponse(points=pts)
