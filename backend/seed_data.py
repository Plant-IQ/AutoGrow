import csv
from datetime import datetime, timedelta
from pathlib import Path

from sqlmodel import Session, select

from db.sqlite import engine, SensorReading, PlantType, PlantTypeTarget, init_db

BASE_DIR = Path(__file__).resolve().parent.parent
PLANT_TARGETS_CSV = BASE_DIR / "data" / "plant_targets.csv"
DEFAULT_STAGE_COLORS = ["#4DA6FF", "#FFFFFF", "#FF6FA3"]

def seed_sensor_data():
    
    with Session(engine) as session:
        now = datetime.utcnow()
        
        for i in range(168):
            ts = now - timedelta(minutes=10 * (167 - i))
            
            reading = SensorReading(
                ts=ts,
                soil=50 + (i % 20) * 0.5,           # 50-60%
                temp=25 + (i % 15) * 0.3,           # 25-29°C
                humidity=60 + (i % 20) * 0.4,       # 60-68%
                light=300 + (i % 50) * 3,           # 300-450 lux
                stage=2,                             # bloom stage
                stage_name="Bloom",
                spectrum="bloom",
                pump_on=i % 3 == 0,
                pump_status="healthy",
                light_hrs_today=12.5,
                harvest_eta_days=15,
                health_score=85 + (i % 10)
            )
            session.add(reading)
        
        session.commit()
        print("created 168 records")


def seed_default_targets():
    """Ensure at least one plant type and its target ranges exist."""
    default_name = "Default 3-stage"
    default_durations = [10, 25, 40]
    default_colors = ["#4DA6FF", "#FFFFFF", "#FF6FA3"]
    with Session(engine) as session:
        plant_type = session.exec(select(PlantType).where(PlantType.name == default_name)).first()
        if not plant_type:
            plant_type = PlantType(name=default_name, stage_durations_days=default_durations, stage_colors=default_colors)
            session.add(plant_type)
            session.commit()
            session.refresh(plant_type)
            print(f"✅ Created plant type '{default_name}'")

        target = session.exec(select(PlantTypeTarget).where(PlantTypeTarget.plant_type_id == plant_type.id)).first()
        if not target:
            target = PlantTypeTarget(
                plant_type_id=plant_type.id,
                temp_min_c=22,
                temp_max_c=26,
                humidity_min=55,
                humidity_max=70,
                light_min_lux=250,
                light_max_lux=450,
            )
            session.add(target)
            session.commit()
            print(f"✅ Added default targets for '{default_name}'")
        else:
            print("ℹ️ Default targets already present")


def seed_plant_catalog_from_csv(csv_path: Path = PLANT_TARGETS_CSV) -> int:
    """Sync plant catalog + target ranges from the CSV master list."""
    if not csv_path.exists():
        print(f"⚠️ Plant target catalog not found: {csv_path}")
        return 0

    synced = 0
    with csv_path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    with Session(engine) as session:
        existing_types = session.exec(select(PlantType)).all()
        by_name = {}
        for plant_type in sorted(existing_types, key=lambda row: row.id or 0):
            key = plant_type.name.strip().lower()
            if key not in by_name:
                by_name[key] = plant_type

        for raw in rows:
            name = (raw.get("name") or "").strip()
            if not name:
                continue

            durations = [
                int(raw["stage_seed_days"]),
                int(raw["stage_veg_days"]),
                int(raw["stage_bloom_days"]),
            ]
            key = name.lower()
            plant_type = by_name.get(key)

            if plant_type is None:
                plant_type = PlantType(
                    name=name,
                    stage_durations_days=durations,
                    stage_colors=list(DEFAULT_STAGE_COLORS),
                )
                session.add(plant_type)
                session.commit()
                session.refresh(plant_type)
                by_name[key] = plant_type
            else:
                plant_type.name = name
                plant_type.stage_durations_days = durations
                if not plant_type.stage_colors or len(plant_type.stage_colors) != 3:
                    plant_type.stage_colors = list(DEFAULT_STAGE_COLORS)
                session.add(plant_type)
                session.commit()

            target = session.exec(
                select(PlantTypeTarget).where(PlantTypeTarget.plant_type_id == plant_type.id)
            ).first()
            if target is None:
                target = PlantTypeTarget(plant_type_id=plant_type.id)

            target.temp_min_c = float(raw["temp_min_c"])
            target.temp_max_c = float(raw["temp_max_c"])
            target.humidity_min = float(raw["humidity_min"])
            target.humidity_max = float(raw["humidity_max"])
            target.light_min_lux = float(raw["light_min_lux"])
            target.light_max_lux = float(raw["light_max_lux"])
            session.add(target)
            session.commit()
            synced += 1

    print(f"✅ Synced {synced} plant catalog entries from {csv_path.name}")
    return synced


if __name__ == "__main__":
    init_db()
    seed_sensor_data()
    seed_default_targets()
    seed_plant_catalog_from_csv()
