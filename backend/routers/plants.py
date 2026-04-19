import asyncio
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlmodel import Session, select
from db.sqlite import PlantType, PlantInstance, get_session, engine
from models import (
    PlantTypeIn,
    PlantTypeOut,
    PlantInstanceIn,
    PlantInstanceOut,
    PlantInstanceUpdate,
    PlantLightResponse,
    StartPlantRequest,
)
from mqtt.publisher import publish_light_color
from services.actuators import set_humidifier, set_light, set_pump

router = APIRouter()
# Separate router to expose top-level /plant-types without inheriting the /plants prefix
alias_router = APIRouter()

@router.get("/types", response_model=list[PlantTypeOut])
def list_types(session: Session = Depends(get_session)):
    return session.exec(select(PlantType)).all()


@router.post("/types", response_model=PlantTypeOut)
def create_type(payload: PlantTypeIn, session: Session = Depends(get_session)):
    row = PlantType(**payload.model_dump())
    session.add(row); session.commit(); session.refresh(row)
    return row


@router.patch("/types/{type_id}", response_model=PlantTypeOut)
def update_type(type_id: int, payload: PlantTypeIn, session: Session = Depends(get_session)):
    row = session.get(PlantType, type_id)
    if not row:
        raise HTTPException(status_code=404, detail="Plant type not found")
    for k, v in payload.model_dump().items():
        setattr(row, k, v)
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


@router.delete("/types/{type_id}", status_code=204)
def delete_type(type_id: int, session: Session = Depends(get_session)):
    row = session.get(PlantType, type_id)
    if not row:
        raise HTTPException(status_code=404, detail="Plant type not found")
    in_use = session.exec(select(PlantInstance).where(PlantInstance.plant_type_id == type_id)).first()
    if in_use:
        raise HTTPException(status_code=400, detail="Cannot delete type; plants are using it.")
    session.delete(row)
    session.commit()
    return


@alias_router.get("/plant-types", response_model=list[PlantTypeOut])
def list_types_alias(session: Session = Depends(get_session)):
    return list_types(session)


@alias_router.post("/plant-types", response_model=PlantTypeOut)
def create_type_alias(payload: PlantTypeIn, session: Session = Depends(get_session)):
    return create_type(payload, session)


@router.get("/", response_model=list[PlantInstanceOut])
def list_plants(session: Session = Depends(get_session)):
    plants = session.exec(select(PlantInstance)).all()
    updated = False
    for p in plants:
        pt = session.get(PlantType, p.plant_type_id)
        if pt:
            updated |= _refresh_pending(p, pt, session)
    if updated:
        session.commit()
        # reload to reflect any pending flag changes
        plants = session.exec(select(PlantInstance)).all()
    return plants


@router.get("/active", response_model=PlantInstanceOut | None)
def get_active_plant(session: Session = Depends(get_session)):
    plant = session.exec(
        select(PlantInstance)
        .where(PlantInstance.is_active == True)  # noqa: E712
        .order_by(PlantInstance.started_at.desc())
        .limit(1)
    ).first()
    if not plant:
        return None

    pt = session.get(PlantType, plant.plant_type_id)
    if pt:
        changed = _refresh_pending(plant, pt, session)
        if changed:
            session.commit()
            session.refresh(plant)
    return plant


@router.patch("/{plant_id}", response_model=PlantInstanceOut)
def update_plant(plant_id: int, payload: PlantInstanceUpdate, session: Session = Depends(get_session)):
    plant = session.get(PlantInstance, plant_id)
    if not plant:
        raise HTTPException(status_code=404, detail="Plant not found")

    data = payload.model_dump(exclude_unset=True)
    if "plant_type_id" in data and not session.get(PlantType, data["plant_type_id"]):
        raise HTTPException(status_code=400, detail="Unknown plant_type_id")

    for k, v in data.items():
        setattr(plant, k, v)

    session.add(plant)
    session.commit()
    session.refresh(plant)
    return plant


@router.delete("/{plant_id}", status_code=204)
def delete_plant(plant_id: int, session: Session = Depends(get_session)):
    plant = session.get(PlantInstance, plant_id)
    if not plant:
        raise HTTPException(status_code=404, detail="Plant not found")
    session.delete(plant)
    session.commit()
    return


@router.post("/", response_model=PlantInstanceOut)
def create_plant(payload: PlantInstanceIn, session: Session = Depends(get_session)):
    if not session.get(PlantType, payload.plant_type_id):
        raise HTTPException(status_code=400, detail="Unknown plant_type_id")
    _deactivate_current(session)
    data = payload.model_dump()
    if data["stage_started_at"] is None:
        data["stage_started_at"] = datetime.utcnow()
    data["started_at"] = datetime.utcnow()
    data["is_active"] = True
    data["harvested_at"] = None
    data["session_code"] = _next_session_code(session)
    row = PlantInstance(**data)
    session.add(row); session.commit(); session.refresh(row)
    return row


@router.post("/start", response_model=PlantInstanceOut)
def start_plant(payload: StartPlantRequest, session: Session = Depends(get_session)):
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Plant name is required")

    plant_type = session.exec(select(PlantType).where(func.lower(PlantType.name) == name.lower())).first()
    if not plant_type:
        raise HTTPException(status_code=404, detail=f"Plant type '{name}' not found")

    _deactivate_current(session)
    now = datetime.utcnow()
    row = PlantInstance(
        session_code=_next_session_code(session),
        label=name,
        plant_type_id=plant_type.id,
        current_stage_index=0,
        stage_started_at=now,
        started_at=now,
        harvested_at=None,
        is_active=True,
        pending_confirm=False,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


@router.post("/harvest-active")
def harvest_active(session: Session = Depends(get_session)):
    active = session.exec(
        select(PlantInstance)
        .where(PlantInstance.is_active == True)  # noqa: E712
        .order_by(PlantInstance.started_at.desc())
        .limit(1)
    ).first()
    if not active:
        return {"ok": True, "message": "No active plant"}

    active.is_active = False  
    active.harvested_at = datetime.utcnow()
    active.pending_confirm = False
    active.current_stage_index = -1

    session.add(active)
    session.commit()

    # Best effort: stop all hardware output when plant is harvested.
    set_pump(False)
    set_light(False, "off")
    set_humidifier(False)

    try:
        publish_light_color(active.id, "off")
    except Exception as e:
        print(f"[MQTT] publish error after harvest: {e}")

    return {"ok": True, "harvested_session": active.session_code, "stage": -1}


def _get_color_for_stage(plant: PlantInstance, plant_type: PlantType) -> str:
    if plant.current_stage_index == -1:
        return "off"
        
    idx = max(0, min(plant.current_stage_index, len(plant_type.stage_colors) - 1))
    return plant_type.stage_colors[idx]


def _refresh_pending(plant: PlantInstance, plant_type: PlantType, session: Session) -> bool:
    """Update pending_confirm based on elapsed time in current stage.

    Returns True if the object was mutated.
    """
    if plant.current_stage_index == -1:
        if plant.pending_confirm:
            plant.pending_confirm = False
            session.add(plant)
            return True
        return False

    durations = plant_type.stage_durations_days
    if not durations:
        return False

    idx = min(plant.current_stage_index, len(durations) - 1)

    # If already at or beyond the final stage, clear pending if it was set.
    if idx >= len(durations) - 1:
        if plant.pending_confirm:
            plant.pending_confirm = False
            session.add(plant)
            return True
        return False

    target_days = durations[idx]
    elapsed = datetime.utcnow() - plant.stage_started_at
    should_pending = elapsed >= timedelta(days=target_days)

    if plant.pending_confirm != should_pending:
        plant.pending_confirm = should_pending
        session.add(plant)
        return True

    return False


def _next_session_code(session: Session) -> str:
    rows = session.exec(select(PlantInstance.session_code)).all()
    max_id = 0
    for code in rows:
        if not code:
            continue
        try:
            max_id = max(max_id, int(code))
        except ValueError:
            continue
    return f"{max_id + 1:05d}"


def _deactivate_current(session: Session) -> None:
    active = session.exec(
        select(PlantInstance).where(PlantInstance.is_active == True)  # noqa: E712
    ).all()
    now = datetime.utcnow()
    for plant in active:
        plant.is_active = False
        plant.harvested_at = now
        plant.pending_confirm = False
        session.add(plant)


@router.get("/{plant_id}/light", response_model=PlantLightResponse)
def get_plant_light(plant_id: int, session: Session = Depends(get_session)):
    plant = session.get(PlantInstance, plant_id)
    if not plant:
        raise HTTPException(status_code=404, detail="Plant not found")
    plant_type = session.get(PlantType, plant.plant_type_id)
    if not plant_type:
        raise HTTPException(status_code=400, detail="Plant type missing for this plant")

    _refresh_pending(plant, plant_type, session)
    session.commit()
    session.refresh(plant)

    color = _get_color_for_stage(plant, plant_type)
    return PlantLightResponse(
        plant_id=plant.id,
        stage=plant.current_stage_index,
        color=color,
        pending_confirm=plant.pending_confirm,
    )


@router.post("/{plant_id}/confirm-transition", response_model=PlantInstanceOut)
def confirm_transition(plant_id: int, session: Session = Depends(get_session)):
    plant = session.get(PlantInstance, plant_id)
    if not plant:
        raise HTTPException(status_code=404, detail="Plant not found")

    plant_type = session.get(PlantType, plant.plant_type_id)
    if not plant_type:
        raise HTTPException(status_code=400, detail="Plant type missing for this plant")

    if plant.current_stage_index == -1:
        return plant

    max_stage = max(0, len(plant_type.stage_durations_days) - 1)
    if plant.current_stage_index < max_stage:
        plant.current_stage_index += 1
    plant.stage_started_at = datetime.utcnow()
    plant.pending_confirm = False

    session.add(plant)
    session.commit()
    session.refresh(plant)

    # Publish new light color to MQTT (best effort)
    try:
        publish_light_color(plant.id, _get_color_for_stage(plant, plant_type))
    except Exception as e:
        print(f"[MQTT] publish error after confirm: {e}")

    return plant


def _refresh_all_pending():
    with Session(engine) as session:
        plants = session.exec(select(PlantInstance)).all()
        changed = False
        for p in plants:
            pt = session.get(PlantType, p.plant_type_id)
            if pt:
                changed |= _refresh_pending(p, pt, session)
        if changed:
            session.commit()
        # Publish current color for all non-pending plants
        for p in plants:
            pt = session.get(PlantType, p.plant_type_id)
            if pt and not p.pending_confirm:
                try:
                    publish_light_color(p.id, _get_color_for_stage(p, pt))
                except Exception as e:
                    print(f"[MQTT] publish error during refresh: {e}")


async def _pending_refresher_loop(interval_seconds: int = 600):
    while True:
        try:
            _refresh_all_pending()
        except Exception as e:
            print(f"[Plants] pending refresh error: {e}")
        await asyncio.sleep(interval_seconds)


def start_pending_refresher():
    try:
        loop = asyncio.get_event_loop()
        loop.create_task(_pending_refresher_loop())
        print("[Plants] Pending refresher started (10 min cadence).")
    except RuntimeError:
        print("[Plants] Could not start pending refresher (no event loop).")


def sync_plants_now():
    """One-shot refresh + publish, useful at startup."""
    try:
        _refresh_all_pending()
    except Exception as e:
        print(f"[Plants] sync_plants_now error: {e}")