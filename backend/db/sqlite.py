import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from sqlalchemy import Column, JSON
from sqlmodel import Field, Session, SQLModel, create_engine, select

from datetime import datetime, timezone, timedelta

ICT = timezone(timedelta(hours=7))

# Make DB path stable no matter the working directory (defaults to backend/autogrow.db)
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")
DB_PATH = Path(os.getenv("SQLITE_PATH", BASE_DIR / "autogrow.db"))
engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})


class Observation(SQLModel, table=True):
    """Manual observation log (entered by user)."""

    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    height_cm: float
    leaf_count: int
    root_visible: bool
    canopy_score: int


class SensorReading(SQLModel, table=True):
    """Time-series of sensor data; can be downsampled later."""

    id: Optional[int] = Field(default=None, primary_key=True)
    plant_instance_id: Optional[int] = Field(default=None, foreign_key="plantinstance.id", index=True)
    ts: datetime = Field(default_factory=lambda: datetime.now(ICT), index=True)
    soil: float
    temp: float
    humidity: float
    light: float
    vibration: float = Field(default=0.0)
    # ── field ใหม่จาก ESP32 ──
    stage: int = Field(default=0)
    stage_name: str = Field(default="")
    spectrum: str = Field(default="")
    pump_on: bool = Field(default=False)
    pump_status: str = Field(default="")
    light_hrs_today: float = Field(default=0.0)
    harvest_eta_days: int = Field(default=0)
    health_score: int = Field(default=0)



class GrowthStage(SQLModel, table=True):
    """Tracks current stage and confirmation flag."""

    id: Optional[int] = Field(default=None, primary_key=True)
    stage_index: int
    stage_name: str
    started_at: datetime = Field(default_factory=datetime.utcnow)
    confirmed: bool = False


class WeatherCache(SQLModel, table=True):
    """Cache for external API payloads to avoid rate limits."""

    key: str = Field(primary_key=True)
    ts: datetime = Field(default_factory=datetime.utcnow, index=True)
    payload: str  # store raw JSON string


class PlantType(SQLModel, table=True):
    """Type of plant being grown."""

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    stage_durations_days: list[int] = Field(sa_column=Column(JSON))
    stage_colors: list[str] = Field(sa_column=Column(JSON)) # hex strings


class PlantInstance(SQLModel, table=True):
    """Instance of a plant type, e.g. 'Cucumber 1'."""

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
    """Ideal environmental ranges for a plant type (for scoring/alerts)."""

    id: Optional[int] = Field(default=None, primary_key=True)
    plant_type_id: int = Field(foreign_key="planttype.id", index=True)
    temp_min_c: float
    temp_max_c: float
    humidity_min: float
    humidity_max: float
    light_min_lux: float
    light_max_lux: float


def init_db() -> None:
    """Create DB file/directories and ensure all tables exist."""

    # Make sure directory exists if DB_PATH points to a nested folder
    db_file = Path(DB_PATH)
    if db_file.parent and not db_file.parent.exists():
        db_file.parent.mkdir(parents=True, exist_ok=True)

    SQLModel.metadata.create_all(engine)
    _run_migrations(db_file)


def _column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    cursor = conn.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cursor.fetchall())


def _run_migrations(db_file: Path) -> None:
    """Best-effort SQLite schema migrations for existing local DBs."""
    conn = sqlite3.connect(db_file)
    try:
        if not _column_exists(conn, "plantinstance", "session_code"):
            conn.execute("ALTER TABLE plantinstance ADD COLUMN session_code TEXT DEFAULT ''")
        if not _column_exists(conn, "plantinstance", "started_at"):
            conn.execute("ALTER TABLE plantinstance ADD COLUMN started_at TIMESTAMP")
        if not _column_exists(conn, "plantinstance", "harvested_at"):
            conn.execute("ALTER TABLE plantinstance ADD COLUMN harvested_at TIMESTAMP")
        if not _column_exists(conn, "plantinstance", "is_active"):
            conn.execute("ALTER TABLE plantinstance ADD COLUMN is_active INTEGER DEFAULT 1")

        if not _column_exists(conn, "sensorreading", "plant_instance_id"):
            conn.execute("ALTER TABLE sensorreading ADD COLUMN plant_instance_id INTEGER")
        if not _column_exists(conn, "sensorreading", "vibration"):
            conn.execute("ALTER TABLE sensorreading ADD COLUMN vibration REAL DEFAULT 0")

        conn.execute(
            "UPDATE plantinstance SET started_at = COALESCE(started_at, stage_started_at, CURRENT_TIMESTAMP)"
        )
        conn.execute("UPDATE plantinstance SET is_active = COALESCE(is_active, 0)")

        # Legacy rows created before session tracking have blank session codes.
        # Treat them as historical (inactive) so dashboard starts empty until a new plant is started.
        conn.execute(
            """
            UPDATE plantinstance
            SET is_active = 0,
                harvested_at = COALESCE(harvested_at, CURRENT_TIMESTAMP)
            WHERE COALESCE(session_code, '') = ''
            """
        )
        conn.commit()
    finally:
        conn.close()


def get_session():
    """FastAPI dependency yielding a SQLModel session."""

    with Session(engine) as session:
        yield session


def record_sensor(field: str, value: float) -> None:
    """Store a sensor reading, carrying forward last known values for other fields.

    This lets us persist single-sensor MQTT updates into the wide SensorReading table
    without needing all metrics at once.
    """

    with Session(engine) as session:
        last = session.exec(select(SensorReading).order_by(SensorReading.ts.desc()).limit(1)).first()

        # Carry forward previous values so history/health stay smooth
        base = {
            "soil": last.soil if last else value,
            "temp": last.temp if last else value,
            "humidity": last.humidity if last else value,
            "light": last.light if last else value,
        }
        if field in base:
            base[field] = value

        row = SensorReading(**base)
        session.add(row)
        session.commit()


def record_sensor_combined(
    soil: float,
    temp: float,
    humidity: float,
    light: float,
    vibration: float = 0.0,
    stage: int = 0,
    stage_name: str = "",
    spectrum: str = "",
    pump_on: bool = False,
    pump_status: str = "",
    light_hrs_today: float = 0.0,
    harvest_eta_days: int = 0,
    health_score: int = 0,
) -> None:
    """Store a complete sensor reading from combined ESP32 payload."""
    with Session(engine) as session:
        active = session.exec(
            select(PlantInstance)
            .where(PlantInstance.is_active == True)  # noqa: E712
            .order_by(PlantInstance.started_at.desc())
            .limit(1)
        ).first()
        if not active:
            return

        row = SensorReading(
            plant_instance_id=active.id,
            soil=soil,
            temp=temp,
            humidity=humidity,
            light=light,
            vibration=vibration,
            stage=stage,
            stage_name=stage_name,
            spectrum=spectrum,
            pump_on=pump_on,
            pump_status=pump_status,
            light_hrs_today=light_hrs_today,
            harvest_eta_days=harvest_eta_days,
            health_score=health_score,
        )
        session.add(row)
        session.commit()
