
from datetime import datetime, timedelta
from db.sqlite import engine, SensorReading, PlantType, PlantTypeTarget, init_db
from sqlmodel import Session, select

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


if __name__ == "__main__":
    init_db()
    seed_sensor_data()
    seed_default_targets()
