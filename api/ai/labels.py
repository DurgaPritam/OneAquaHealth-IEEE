"""Allowed labels, loaded from data/labels.json (the single source of truth)."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
LABELS_FILE = ROOT / "data" / "labels.json"
NOT_SURE = "not_sure"
VISION_TYPES = ("larvae", "adult_mosquito", "predator", "habitat")


@lru_cache
def load_labels() -> dict[str, Any]:
    return json.loads(LABELS_FILE.read_text(encoding="utf-8"))


def allowed(finding_type: str) -> list[str]:
    spec = load_labels()["types"].get(finding_type)
    return [label["id"] for label in spec["labels"]] if spec else []


def label_info(finding_type: str, label: str) -> dict[str, Any] | None:
    spec = load_labels()["types"].get(finding_type, {"labels": []})
    return next((x for x in spec["labels"] if x["id"] == label), None)
