import asyncio

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select

from db.sqlite import PlantInstance, PlantType, engine, init_db, init_mysql_tables
from mqtt.subscriber import start_subscriber
from routers import context, harvest, health, history, light, observations, pump, stage, targets
from routers import plants
from seed_data import seed_plant_catalog_from_csv
from services.external_weather import backfill_weather_cache_to_mysql
from services.stage_engine import schedule_stage_transitions

app = FastAPI(title="AutoGrow API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(stage.router, prefix="/stage", tags=["stage"])
app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(light.router, prefix="/light", tags=["light"])
app.include_router(harvest.router, prefix="/harvest-eta", tags=["harvest"])
app.include_router(history.router, prefix="/history", tags=["history"])
app.include_router(pump.router, prefix="/pump-status", tags=["pump"])
app.include_router(observations.router, prefix="/observations", tags=["observations"])
app.include_router(context.router, prefix="/context", tags=["context"])
app.include_router(context.outdoor_router, prefix="/outdoor", tags=["outdoor"])
app.include_router(targets.router, prefix="/targets", tags=["targets"])
app.include_router(plants.router, prefix="/plants", tags=["plants"])
app.include_router(plants.alias_router, tags=["plants"])


async def resume_stage_tasks() -> None:
    """Recreate stage transition tasks for all active plants on restart."""
    with Session(engine) as session:
        actives = session.exec(
            select(PlantInstance).where(PlantInstance.is_active == True)
        ).all()

        for plant in actives:
            plant_type = session.get(PlantType, plant.plant_type_id)
            if not plant_type:
                continue

            durations = plant_type.stage_durations_days or []
            seed_days  = durations[0] if len(durations) > 0 else 0
            veg_days   = durations[1] if len(durations) > 1 else 0
            bloom_days = durations[2] if len(durations) > 2 else 0

            asyncio.create_task(schedule_stage_transitions(
                plant_id=plant.id,
                started_at=plant.started_at,
                seed_days=seed_days,
                veg_days=veg_days,
                bloom_days=bloom_days,
            ))
            print(f"[Startup] Resumed stage task for plant_id={plant.id} "
                  f"(seed={seed_days}d, veg={veg_days}d, bloom={bloom_days}d)")


@app.on_event("startup")
async def startup() -> None:
    init_db()
    seed_plant_catalog_from_csv()
    init_mysql_tables()
    migrated = backfill_weather_cache_to_mysql()
    print(
        f"[MySQL] Weather backfill complete: current={migrated['current']}, history={migrated['history']}"
    )
    start_subscriber()
    plants.sync_plants_now()
    plants.start_pending_refresher()
    await resume_stage_tasks()
