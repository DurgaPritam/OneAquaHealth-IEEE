"""Load config/risk.yaml and fingerprint it so every score records which formula made it."""

from __future__ import annotations

import hashlib
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
CONFIG_FILE = ROOT / "config" / "risk.yaml"


@lru_cache
def load_config(path: Path = CONFIG_FILE) -> dict[str, Any]:
    raw = path.read_bytes()
    cfg = yaml.safe_load(raw)
    cfg["fingerprint"] = f"{cfg['version']}+{hashlib.sha256(raw).hexdigest()[:8]}"
    return cfg


def band_for(total: float, cfg: dict[str, Any]) -> str:
    for band in cfg["bands"]:
        if total < band["below"]:
            return band["name"]
    return cfg["bands"][-1]["name"]
