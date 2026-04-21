import os
import sqlite3
import urllib.parse
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, List

from dotenv import load_dotenv
from sqlalchemy import Column, JSON, UniqueConstraint, text
from sqlalchemy.engine import URL
from sqlmodel import Field, Session, SQLModel, create_engine, select

ICT = timezone(timedelta(hours=7))

# --- Setup Paths ---
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")
DB_PATH = Path(os.getenv("SQLITE_PATH", BASE_DIR / "autogrow.db"))


import os
from sqlmodel import create_engine, SQLModel, Session

sqlite_file_name = "autogrow.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

mysql_user = "b6710545652"
mysql_pass = "natcha.limsu@ku.th" 
mysql_host = "iot.cpe.ku.ac.th"
mysql_port = "3306"
mysql_db   = "b6710545652"

encoded_pass = urllib.parse.quote_plus(mysql_pass)

mysql_url = f"mysql+pymysql://{mysql_user}:{encoded_pass}@{mysql_host}:{mysql_port}/{mysql_db}"

engine = create_engine(sqlite_url, connect_args={"check_same_thread": False})

mysql_engine = create_engine(
    mysql_url,
    pool_size=1,
    max_overflow=0,
    pool_recycle=60, 
    pool_pre_ping=True,    
)

# --- Models (SQLite & MySQL) ---

class Observation(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    height_cm: float
    leaf_count: int
    root_visible: bool
    canopy_score: int

class SensorReading(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    plant_instance_id: Optional[int] = Field(default=None, foreign_key="plantinstance.id", index=True)
    ts: datetime = Field(default_factory=lambda: datetime.now(ICT), index=True)
    soil: float
    temp: float
    humidity: float
    light: float
    vibration: float = Field(default=0.0)
    stage: int = Field(default=0)
    stage_name: str = Field(default="")
    spectrum: str = Field(default="")
    pump_on: bool = Field(default=False)
    pump_status: str = Field(default="")
    light_hrs_today: float = Field(default=0.0)
    harvest_eta_days: int = Field(default=0)
    health_score: int = Field(default=0)

class GrowthStage(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    stage_index: int
    stage_name: str
    started_at: datetime = Field(default_factory=datetime.utcnow)
    confirmed: bool = False

class WeatherCache(SQLModel, table=True):
    key: str = Field(primary_key=True)
    ts: datetime = Field(default_factory=datetime.utcnow, index=True)
    payload: str 

class OutdoorWeatherCurrent(SQLModel, table=True):
    __tablename__ = "outdoor_weather_current"
    id: Optional[int] = Field(default=None, primary_key=True)
    lat: float = Field(index=True); lon: float = Field(index=True)
    source: str = Field(default="")
    temp_c: Optional[float] = Field(default=None)
    humidity: Optional[float] = Field(default=None)
    wind_speed_mps: Optional[float] = Field(default=None)
    apparent_temp_c: Optional[float] = Field(default=None)
    sunrise_utc: Optional[datetime] = Field(default=None)
    sunset_utc: Optional[datetime] = Field(default=None)
    fetched_at: datetime = Field(index=True)
    stored_at: datetime = Field(default_factory=datetime.utcnow, index=True)

class OutdoorWeatherHistory(SQLModel, table=True):
    __tablename__ = "outdoor_weather_history"
    __table_args__ = (UniqueConstraint("lat", "lon", "ts", name="uq_outdoor_weather_history_lat_lon_ts"),)
    id: Optional[int] = Field(default=None, primary_key=True)
    lat: float = Field(index=True); lon: float = Field(index=True)
    source: str = Field(default="")
    ts: datetime = Field(index=True)
    temp_c: Optional[float] = Field(default=None)
    humidity: Optional[float] = Field(default=None)

class PlantType(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    stage_durations_days: List[int] = Field(sa_column=Column(JSON))
    stage_colors: List[str] = Field(sa_column=Column(JSON))

class PlantInstance(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    session_code: str = Field(default="")
    label: str
    plant_type_id: int = Field(foreign_key="planttype.id")
    started_at: datetime = Field(default_factory=datetime.utcnow)
    harvested_at: Optional[datetime] = None
    is_active: bool = Field(default=True, index=True)
    current_stage_index: int = 0
    stage_started_at: datetime = Field(default_factory=datetime.utcnow)
    pending_confirm: bool = False 

class PlantTypeTarget(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    plant_type_id: int = Field(foreign_key="planttype.id", index=True)
    temp_min_c: float
    temp_max_c: float
    humidity_min: float
    humidity_max: float
    light_min_lux: float
    light_max_lux: float

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

# --- Functions ---

def init_db() -> None:
    db_file = Path(DB_PATH)
    if db_file.parent and not db_file.parent.exists():
        db_file.parent.mkdir(parents=True, exist_ok=True)
    SQLModel.metadata.create_all(engine)
    _run_migrations(db_file)

def _column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    cursor = conn.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cursor.fetchall())

def _run_migrations(db_file: Path) -> None:
    conn = sqlite3.connect(db_file)
    try:
        for col in ["session_code", "started_at", "harvested_at", "is_active"]:
            if not _column_exists(conn, "plantinstance", col):
                conn.execute(f"ALTER TABLE plantinstance ADD COLUMN {col} TEXT DEFAULT ''")
        for col in ["plant_instance_id", "vibration"]:
            if not _column_exists(conn, "sensorreading", col):
                conn.execute(f"ALTER TABLE sensorreading ADD COLUMN {col} REAL DEFAULT 0")
        conn.commit()
    finally:
        conn.close()

def get_session():
    with Session(engine) as session:
        yield session

def get_mysql_session():
    with Session(mysql_engine) as session:
        yield session

def init_mysql_tables() -> None:
    try:
        OutdoorWeatherCurrent.__table__.create(mysql_engine, checkfirst=True)
        OutdoorWeatherHistory.__table__.create(mysql_engine, checkfirst=True)
    except Exception as exc:
        print(f"[MySQL] Skipping table init: {exc}")

def record_sensor(field: str, value: float) -> None:
    with Session(engine) as session:
        last = session.exec(select(SensorReading).order_by(SensorReading.ts.desc()).limit(1)).first()
        base = {"soil": last.soil if last else 0.0, "temp": last.temp if last else 0.0, 
                "humidity": last.humidity if last else 0.0, "light": last.light if last else 0.0}
        if field in base: base[field] = value
        row = SensorReading(**base)
        session.add(row)
        session.commit()

def record_sensor_combined(soil, temp, humidity, light, vibration=0.0, **kwargs) -> None:
    with Session(engine) as session:
        active = session.exec(select(PlantInstance).where(PlantInstance.is_active == True).limit(1)).first()
        if not active: return
        row = SensorReading(plant_instance_id=active.id, soil=soil, temp=temp, humidity=humidity, light=light, vibration=vibration, **kwargs)
        session.add(row)
        session.commit()