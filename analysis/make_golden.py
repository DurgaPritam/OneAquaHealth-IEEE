"""Golden fixtures: Python results that the TypeScript ports must reproduce exactly.

Usage: .venv/bin/python -m analysis.make_golden
"""

from __future__ import annotations

import json
import random
from pathlib import Path

from api.reliability.calibration import reference_items, score

OUT = Path(__file__).resolve().parent.parent / "data" / "fixtures"


def calibration_cases() -> list[dict]:
    items = reference_items()
    rng = random.Random(11)
    options = {"ape": ["absent", "present", "extensive"], "cover5": ["1", "2", "3", "4", "5"], "posture": ["angled", "flat"]}
    cases = [{it["id"]: it["answer"] for it in items}]
    for _ in range(6):
        cases.append({it["id"]: (it["answer"] if rng.random() < 0.6 else rng.choice(options[it["scale"]])) for it in items})
    return [{"answers": a, "result": score(a)} for a in cases]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "calibration_golden.json").write_text(json.dumps(calibration_cases(), indent=1) + "\n", encoding="utf-8")
    print("wrote calibration_golden.json")


if __name__ == "__main__":
    main()
