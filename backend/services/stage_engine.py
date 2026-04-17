"""Stage lookup helper."""

import asyncio
from datetime import datetime, timedelta
from typing import Tuple

from sqlmodel import Session, select

from db.sqlite import GrowthStage, PlantInstance, engine
from mqtt.publisher import publish_stage_update

DEFAULT_STAGE = (2, "Vegetative")


def get_current_stage(session: Session) -> Tuple[int, str, int]:
    """Return (index, name, days_in_stage)."""
    result = session.exec(select(GrowthStage).order_by(GrowthStage.started_at.desc()).limit(1)).first()

    if result is None:
        stage_index, stage_name = DEFAULT_STAGE
        started_at = datetime.utcnow()
    else:
        stage_index, stage_name, started_at = result.stage_index, result.stage_name, result.started_at

    days_in_stage = max(1, (datetime.utcnow() - started_at).days + 1)
    return stage_index, stage_name, days_in_stage


def upsert_stage(session: Session, stage_index: int, stage_name: str):
    existing = session.exec(select(GrowthStage).order_by(GrowthStage.started_at.desc()).limit(1)).first()
    now = datetime.utcnow()
    if existing:
        existing.stage_index = stage_index
        existing.stage_name = stage_name
        existing.started_at = now
        session.add(existing)
    else:
        session.add(GrowthStage(stage_index=stage_index, stage_name=stage_name, started_at=now))
    session.commit()


def _update_plant_stage(plant_id: int, stage: int, stage_started_at: datetime) -> None:
    with Session(engine) as session:
        plant = session.get(PlantInstance, plant_id)
        if plant:
            plant.current_stage_index = stage
            plant.stage_started_at = stage_started_at
            session.add(plant)
            session.commit()


async def schedule_stage_transitions(
    plant_id: int,
    started_at: datetime,
    seed_days: int,
    veg_days: int,
    bloom_days: int,
) -> None:
    now = datetime.utcnow()

    veg_start = started_at + timedelta(days=seed_days)
    bloom_start = started_at + timedelta(days=seed_days + veg_days)

    wait_veg = (veg_start - now).total_seconds()
    if wait_veg > 0:
        await asyncio.sleep(wait_veg)
    _update_plant_stage(plant_id, 1, veg_start)
    publish_stage_update(plant_id, 1)
    print(f"[Stage] plant_id={plant_id} → stage 1 (Veg)")

    if bloom_days > 0:
        wait_bloom = (bloom_start - now).total_seconds()
        remaining = wait_bloom - max(0, wait_veg)
        if remaining > 0:
            await asyncio.sleep(remaining)
        _update_plant_stage(plant_id, 2, bloom_start)
        publish_stage_update(plant_id, 2)
        print(f"[Stage] plant_id={plant_id} → stage 2 (Bloom)")