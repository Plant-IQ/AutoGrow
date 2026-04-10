"""Stage lookup helper."""

import asyncio
from datetime import datetime
from typing import Tuple

from sqlmodel import Session, select

from db.sqlite import GrowthStage
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


# MQTT stage scheduler
async def schedule_stage_transitions(
    plant_id: int,
    seed_days: int,
    veg_days: int,
    bloom_days: int,
) -> None:
    """
    state 0 → ส่งทันทีตอน start (เรียกจาก router)
    state 1 → หลังครบ seed_days  (เข้า Veg)
    state 2 → หลังครบ veg_days   (เข้า Bloom)
    """
    await asyncio.sleep(seed_days * 86400)
    publish_stage_update(plant_id, 1)

    if bloom_days > 0:
        await asyncio.sleep(veg_days * 86400)
        publish_stage_update(plant_id, 2)