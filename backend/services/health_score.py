"""Simple health score calculator.

Given the latest sensor reading (or None), return a 0–100 score and the
component weights that contributed to it. This is intentionally lightweight
until we have a trained model.
"""

from typing import Optional, Tuple, Dict

from db.sqlite import SensorReading


class TargetRange:
    def __init__(self, temp_min_c: float, temp_max_c: float, humidity_min: float, humidity_max: float, light_min_lux: float, light_max_lux: float):
        self.temp_min_c = temp_min_c
        self.temp_max_c = temp_max_c
        self.humidity_min = humidity_min
        self.humidity_max = humidity_max
        self.light_min_lux = light_min_lux
        self.light_max_lux = light_max_lux


def _clamp(value: float, min_v: float, max_v: float) -> float:
    return max(min_v, min(value, max_v))


def _score_range(value: float, ideal_min: float, ideal_max: float, hard_min: float, hard_max: float) -> float:
    """Return 0–1 score based on how close a value is to the ideal band."""
    if value < hard_min or value > hard_max:
        return 0.0
    if ideal_min <= value <= ideal_max:
        return 1.0
    # linearly decay toward hard limits
    if value < ideal_min:
        return (value - hard_min) / (ideal_min - hard_min)
    return (hard_max - value) / (hard_max - ideal_max)


def compute_health(reading: Optional[SensorReading], targets: Optional[TargetRange] = None) -> Tuple[float, Dict[str, float]]:
    """Return (score, components) where score is 0–100.

    If no reading is provided, fall back to mid-range defaults.
    If targets are provided, use them as the ideal band with a 20% buffer for hard limits.
    """

    if reading is None:
        components = {"soil": 0.8, "temp": 0.9, "humidity": 0.85, "light": 0.75}
    else:
        if targets:
            temp_hard_min, temp_hard_max = _expand(targets.temp_min_c, targets.temp_max_c)
            humid_hard_min, humid_hard_max = _expand(targets.humidity_min, targets.humidity_max)
            light_hard_min, light_hard_max = _expand(targets.light_min_lux, targets.light_max_lux)
            ideal_temp = (targets.temp_min_c, targets.temp_max_c)
            ideal_humid = (targets.humidity_min, targets.humidity_max)
            ideal_light = (targets.light_min_lux, targets.light_max_lux)
        else:
            temp_hard_min, temp_hard_max = 15, 32
            humid_hard_min, humid_hard_max = 30, 90
            light_hard_min, light_hard_max = 100, 700
            ideal_temp = (22, 26)
            ideal_humid = (55, 70)
            ideal_light = (250, 450)

        components = {
            "soil": _score_range(reading.soil, ideal_min=35, ideal_max=55, hard_min=20, hard_max=70),
            "temp": _score_range(reading.temp, ideal_min=ideal_temp[0], ideal_max=ideal_temp[1], hard_min=temp_hard_min, hard_max=temp_hard_max),
            "humidity": _score_range(reading.humidity, ideal_min=ideal_humid[0], ideal_max=ideal_humid[1], hard_min=humid_hard_min, hard_max=humid_hard_max),
            "light": _score_range(reading.light, ideal_min=ideal_light[0], ideal_max=ideal_light[1], hard_min=light_hard_min, hard_max=light_hard_max),
        }

    score = sum(components.values()) / len(components) * 100
    score = round(_clamp(score, 0, 100), 1)

    return score, components


def _expand(min_v: float, max_v: float, margin: float = 0.2) -> tuple[float, float]:
    span = max_v - min_v
    pad = span * margin if span > 0 else margin
    return min_v - pad, max_v + pad
