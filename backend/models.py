from datetime import datetime
from typing import List

from pydantic import BaseModel, model_validator

ALLOWED_STAGE_COLORS = ["#4DA6FF", "#FFFFFF", "#FF6FA3"]  # blue, white, pink/red


class StageResponse(BaseModel):
    stage: int
    label: str
    days_in_stage: int


class StageUpdate(BaseModel):
    stage: int
    label: str


class HealthResponse(BaseModel):
    score: float
    components: dict


class LightResponse(BaseModel):
    spectrum: str
    hours_today: float


class HarvestETAResponse(BaseModel):
    days_to_harvest: int
    projected_date: datetime


class HistoryPoint(BaseModel):
    ts: datetime
    soil: float
    temp: float
    humidity: float
    light: float
    stage: int = 0
    stage_name: str = ""
    spectrum: str = ""
    pump_on: bool = False
    pump_status: str = ""
    light_hrs_today: float = 0.0
    harvest_eta_days: int = 0
    health_score: int = 0


class HistoryResponse(BaseModel):
    points: List[HistoryPoint]


class PumpStatusResponse(BaseModel):
    ok: bool
    vibration: float
    last_checked: datetime


class ErrorResponse(BaseModel):
    detail: str


class ObservationCreate(BaseModel):
    height_cm: float
    leaf_count: int
    root_visible: bool
    canopy_score: int


class PlantTypeIn(BaseModel):
    name: str
    stage_durations_days: List[int]
    stage_colors: List[str]

    @model_validator(mode="after")
    def enforce_three_stage_palette(self):
        if len(self.stage_durations_days) != 3:
            raise ValueError("stage_durations_days must have exactly 3 entries (seed, veg, bloom).")
        if any(d < 0 for d in self.stage_durations_days): 
            raise ValueError("stage_durations_days values must be non-negative integers.")

        colors = [c.upper() for c in self.stage_colors]
        if len(colors) != 3:
            raise ValueError("stage_colors must have exactly 3 entries (blue, white, pink/red).")
        if any(c not in ALLOWED_STAGE_COLORS for c in colors):
            raise ValueError(f"stage_colors must be one of {ALLOWED_STAGE_COLORS}.")

        self.stage_colors = colors
        return self


class PlantTypeOut(PlantTypeIn):
    id: int


class PlantInstanceIn(BaseModel):
    label: str
    plant_type_id: int
    current_stage_index: int = 0
    stage_started_at: datetime | None = None


class PlantInstanceOut(PlantInstanceIn):
    id: int
    session_code: str
    started_at: datetime
    harvested_at: datetime | None = None
    is_active: bool
    pending_confirm: bool


class StartPlantRequest(BaseModel):
    name: str


class PlantInstanceUpdate(BaseModel):
    label: str | None = None
    plant_type_id: int | None = None
    current_stage_index: int | None = None
    stage_started_at: datetime | None = None
    pending_confirm: bool | None = None


class PlantLightResponse(BaseModel):
    plant_id: int
    stage: int
    color: str
    pending_confirm: bool