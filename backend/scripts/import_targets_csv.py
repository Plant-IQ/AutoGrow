"""Import plant target ranges from a CSV (e.g., Kaggle dataset export).

Expected CSV columns (case-insensitive):
name,temp_min_c,temp_max_c,humidity_min,humidity_max,light_min_lux,light_max_lux
Optional columns:
- stage_seed_days, stage_veg_days, stage_bloom_days (ints)
- color_seed, color_veg, color_bloom (hex strings)

Usage:
    PYTHONPATH=. python3 backend/scripts/import_targets_csv.py /path/to/targets.csv

Notes:
- Matches PlantType by case-insensitive name. Creates the PlantType if missing,
  with default stage durations/colors.
- Updates existing PlantTypeTarget rows if present; otherwise inserts.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlmodel import Session, select

BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR / ".env")

from db.sqlite import engine, PlantType, PlantTypeTarget  # noqa: E402

DEFAULT_DURATIONS = [10, 25, 40]
DEFAULT_COLORS = ["#4DA6FF", "#FFFFFF", "#FF6FA3"]


def import_csv(path: Path) -> None:
    with Session(engine) as session:
        with path.open() as f:
            reader = csv.DictReader(f)
            count = 0
            for row in reader:
                name = (row.get("name") or "").strip()
                if not name:
                    continue

                def _num(key: str, default: float = 0.0) -> float:
                    try:
                        return float(row.get(key, "") or default)
                    except ValueError:
                        return default

                pt = session.exec(
                    select(PlantType).where(PlantType.name.ilike(name))
                ).first()
                seed_d = row.get("stage_seed_days")
                veg_d = row.get("stage_veg_days")
                bloom_d = row.get("stage_bloom_days")
                colors = [
                    row.get("color_seed"),
                    row.get("color_veg"),
                    row.get("color_bloom"),
                ]
                durations_raw = [
                    int(seed_d) if seed_d and seed_d.strip().isdigit() else None,
                    int(veg_d) if veg_d and veg_d.strip().isdigit() else None,
                    int(bloom_d) if bloom_d and bloom_d.strip().isdigit() else None,
                ]

                if not pt:
                    pt = PlantType(
                        name=name,
                        stage_durations_days=[
                            durations_raw[i] if durations_raw[i] is not None else DEFAULT_DURATIONS[i]
                            for i in range(3)
                        ],
                        stage_colors=[
                            (colors[i] or DEFAULT_COLORS[i]).upper()
                            for i in range(3)
                        ],
                    )
                    session.add(pt)
                    session.commit()
                    session.refresh(pt)
                else:
                    if any(d is not None for d in durations_raw):
                        merged = [
                            durations_raw[i] if durations_raw[i] is not None else pt.stage_durations_days[i]
                            for i in range(3)
                        ]
                        pt.stage_durations_days = merged
                    if any(colors):
                        merged_colors = [
                            colors[i] if colors[i] else pt.stage_colors[i] if i < len(pt.stage_colors) else DEFAULT_COLORS[i]
                            for i in range(3)
                        ]
                        pt.stage_colors = [c.upper() for c in merged_colors]
                    session.add(pt)

                target = session.exec(
                    select(PlantTypeTarget).where(PlantTypeTarget.plant_type_id == pt.id)
                ).first()
                data = dict(
                    plant_type_id=pt.id,
                    temp_min_c=_num("temp_min_c"),
                    temp_max_c=_num("temp_max_c"),
                    humidity_min=_num("humidity_min"),
                    humidity_max=_num("humidity_max"),
                    light_min_lux=_num("light_min_lux"),
                    light_max_lux=_num("light_max_lux"),
                )
                if target:
                    for k, v in data.items():
                        setattr(target, k, v)
                    session.add(target)
                else:
                    session.add(PlantTypeTarget(**data))
                count += 1
            session.commit()
            print(f"Imported/updated targets for {count} entries")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    csv_path = Path(sys.argv[1]).expanduser()
    if not csv_path.exists():
        print(f"CSV not found: {csv_path}")
        sys.exit(1)
    import_csv(csv_path)
