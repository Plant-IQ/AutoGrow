from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from db.sqlite import PlantType, PlantTypeTarget, get_session
from models import PlantTypeTargetIn, PlantTypeTargetOut

router = APIRouter()


@router.get("/plant-types/{plant_type_id}/targets", response_model=PlantTypeTargetOut | None)
def get_targets(plant_type_id: int, session: Session = Depends(get_session)):
    return session.exec(select(PlantTypeTarget).where(PlantTypeTarget.plant_type_id == plant_type_id)).first()


@router.put("/plant-types/{plant_type_id}/targets", response_model=PlantTypeTargetOut)
def upsert_targets(plant_type_id: int, payload: PlantTypeTargetIn, session: Session = Depends(get_session)):
    if not session.get(PlantType, plant_type_id):
        raise HTTPException(status_code=404, detail="Plant type not found")

    row = session.exec(select(PlantTypeTarget).where(PlantTypeTarget.plant_type_id == plant_type_id)).first()
    data = payload.model_dump()
    if row:
        for k, v in data.items():
            setattr(row, k, v)
    else:
        row = PlantTypeTarget(plant_type_id=plant_type_id, **data)

    session.add(row)
    session.commit()
    session.refresh(row)
    return row

