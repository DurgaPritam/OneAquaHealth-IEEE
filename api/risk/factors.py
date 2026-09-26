"""Pure factor functions. Each returns a Factor with its value, inputs and a plain-language explanation.

A factor with no data returns value None: it is excluded from the total and
shown as "no data", never silently treated as zero.
"""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

APE_SCORE = {"absent": 0.0, "present": 0.5, "extensive": 1.0}
AMPHIBIAN_SCORE = {"none": 0.0, "heard": 0.7, "seen": 1.0}


@dataclass
class Factor:
    name: str
    label: str
    value: float | None
    explanation: str
    inputs: dict[str, Any] = field(default_factory=dict)
    data_age_days: float | None = None
    weight: float = 0.0
    contribution: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@lru_cache
def question_labels() -> dict[str, str]:
    doc = json.loads((Path(__file__).resolve().parents[2] / "data" / "questions.json").read_text(encoding="utf-8"))
    return {q["id"]: q["label"] for sec in doc["sections"] for q in sec["questions"]}


def _clip(x: float) -> float:
    return max(0.0, min(1.0, x))


def _r(x: float) -> float:
    return round(x, 4)


# ------------------------------------------------------------------ weather


def temperature(days: list[dict[str, Any]], cfg: dict[str, Any]) -> Factor:
    """Degree-days above the WNV zero-development point, reduced above the thermal optimum."""
    c = cfg["temperature"]
    temps = [d["tmean"] for d in days if d.get("tmean") is not None]
    if not temps:
        return Factor("temperature", "Temperature suitability", None, "No weather data for this window.")
    dd = sum(max(0.0, t - c["base_c"]) for t in temps)
    mean = sum(temps) / len(temps)
    heat = 1.0
    if mean > c["upper_optimum_c"]:
        heat = _clip((c["upper_limit_c"] - mean) / (c["upper_limit_c"] - c["upper_optimum_c"]))
    value = _clip(dd / c["degree_days_target"]) * heat
    text = (f"{dd:.0f} degree-days above {c['base_c']} °C in {len(temps)} days "
            f"(about {c['degree_days_target']} are needed for the virus to develop in Culex mosquitoes); mean {mean:.1f} °C.")
    if heat < 1:
        text += f" Above {c['upper_optimum_c']} °C transmission declines, so the factor is reduced."
    return Factor("temperature", "Temperature suitability", _r(value), text,
                  {"degree_days": _r(dd), "mean_c": _r(mean), "days": days, "base_c": c["base_c"]})


def dry_spell(days: list[dict[str, Any]], cfg: dict[str, Any]) -> Factor:
    """Consecutive dry days up to the last day: a proxy for stagnant pools in the channel."""
    c = cfg["dry_spell"]
    precip = [d for d in days if d.get("precip") is not None]
    if not precip:
        return Factor("dry_spell", "Dry spell and stagnation", None, "No rainfall data for this window.")
    run = 0
    for d in reversed(precip):
        if d["precip"] >= c["dry_day_max_mm"]:
            break
        run += 1
    total_mm = sum(d["precip"] for d in precip)
    value = _clip(run / c["days_to_saturate"])
    text = f"{run} dry days in a row (under {c['dry_day_max_mm']} mm); {total_mm:.0f} mm of rain in the window. Dry spells leave still pools behind weirs and in the channel."
    return Factor("dry_spell", "Dry spell and stagnation", _r(value), text, {"dry_days": run, "rain_mm": _r(total_mm)})


# ------------------------------------------------------------------ citizen observations


def habitat(posteriors: dict[str, dict[str, Any]], cfg: dict[str, Any]) -> Factor:
    """Weighted mean of reliability-weighted stream-check answers (expected A/P/E score)."""
    weights = cfg["habitat"]["questions"]
    used = {q: v for q, v in posteriors.items() if q in weights}
    if not used:
        return Factor("habitat", "Larval habitat (stream check)", None, "No stream-check answers in this window.")
    total_w = sum(weights[q] for q in used)
    value = sum(weights[q] * used[q]["expected"] for q in used) / total_w
    worst = max(used, key=lambda q: used[q]["expected"])
    text = (f"From {sum(v['n_reports'] for v in used.values())} answers to {len(used)} questions, weighted by observer reliability. "
            f"Strongest signal: {question_labels().get(worst, worst).lower()} (expected score {used[worst]['expected']:.2f} of 1).")
    return Factor("habitat", "Larval habitat (stream check)", _r(value), text, {"questions": used})


def vector_presence(larval: list[dict[str, Any]], cfg: dict[str, Any]) -> Factor:
    """Reliability-weighted mean larvae per dip, on a saturating curve."""
    if not larval:
        return Factor("vector_presence", "Mosquito larvae found", None, "No larval dips in this window.")
    wsum = sum(r["weight"] for r in larval)
    mean = sum(r["per_dip"] * r["weight"] for r in larval) / wsum
    value = 1 - math.exp(-mean / cfg["vector_presence"]["scale_per_dip"])
    text = f"{len(larval)} larval dip sessions; reliability-weighted mean {mean:.1f} larvae per dip."
    return Factor("vector_presence", "Mosquito larvae found", _r(value), text, {"mean_per_dip": _r(mean), "reports": larval})


def predator_deficit(reports: list[dict[str, Any]], cfg: dict[str, Any]) -> Factor:
    """1 minus the reliability-weighted presence of frogs, insect-eating birds and bats."""
    if not reports:
        return Factor("predator_deficit", "Missing mosquito predators", None, "No predator observations in this window.")
    c = cfg["predator_deficit"]
    parts = c["parts"]
    num = 0.0
    wsum = 0.0
    for r in reports:
        pieces = {}
        if r.get("amphibians") in AMPHIBIAN_SCORE:
            pieces["amphibians"] = AMPHIBIAN_SCORE[r["amphibians"]]
        if r.get("birds") is not None:
            pieces["birds"] = _clip(r["birds"] / c["birds_to_saturate"])
        if r.get("bats") in ("none", "seen"):
            pieces["bats"] = 1.0 if r["bats"] == "seen" else 0.0
        if not pieces:
            continue
        presence = sum(parts[k] * v for k, v in pieces.items()) / sum(parts[k] for k in pieces)
        num += presence * r["weight"]
        wsum += r["weight"]
    if wsum == 0:
        return Factor("predator_deficit", "Missing mosquito predators", None, "No usable predator observations in this window.")
    presence = num / wsum
    text = f"Predator presence {presence:.2f} of 1 from {len(reports)} observations. Fewer frogs, insect-eating birds and bats means less natural mosquito control."
    return Factor("predator_deficit", "Missing mosquito predators", _r(1 - presence), text, {"presence": _r(presence), "reports": reports})


def host_signal(dead_birds: list[dict[str, Any]] | None, cfg: dict[str, Any]) -> Factor:
    """Dead-bird reports. Always reported as a routing signal, never as a diagnosis.

    ``None`` means nobody visited in the window, so absence of reports is not evidence.
    """
    if dead_birds is None:
        return Factor("host_signal", "Dead bird reports", None, "No visits in this window, so no dead-bird information.")
    n = sum(r["count"] for r in dead_birds)
    value = _clip(n / cfg["host_signal"]["reports_to_saturate"])
    if n == 0:
        text = "No dead birds reported in this window."
    else:
        text = f"{n} dead bird(s) reported. Reports go to the veterinary team; this is not a diagnosis of any bird or place."
    return Factor("host_signal", "Dead bird reports", _r(value), text, {"count": n, "reports": dead_birds})
