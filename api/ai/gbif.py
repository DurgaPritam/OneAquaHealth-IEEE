"""GBIF plausibility check for bird and amphibian suggestions.

A suggestion is flagged for expert review when GBIF has no occurrence of the
species within the search box around the site. GBIF never confirms a record.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx

GBIF_URL = "https://api.gbif.org/v1/occurrence/search"
CACHE_FILE = Path("var/gbif_cache.json")
DEFAULT_RADIUS_DEG = 0.5  # about 55 km north-south


def _fetch(params: dict[str, Any]) -> dict[str, Any]:
    res = httpx.get(GBIF_URL, params=params, timeout=10)
    res.raise_for_status()
    return res.json()


def occurrence_count(species: str, lat: float, lon: float, radius_deg: float = DEFAULT_RADIUS_DEG,
                     fetch: Callable[[dict[str, Any]], dict[str, Any]] = _fetch) -> int | None:
    """Occurrences within a box around the point, or None if GBIF could not be reached."""
    key = f"{species}|{round(lat, 1)}|{round(lon, 1)}|{radius_deg}"
    cache = _read_cache()
    if key in cache:
        return cache[key]
    params = {
        "scientificName": species,
        "decimalLatitude": f"{lat - radius_deg},{lat + radius_deg}",
        "decimalLongitude": f"{lon - radius_deg},{lon + radius_deg}",
        "limit": 0,
    }
    try:
        count = int(fetch(params)["count"])
    except (httpx.HTTPError, KeyError, ValueError):
        return None
    cache[key] = count
    _write_cache(cache)
    return count


def plausibility(species: str | None, lat: float, lon: float, fetch: Callable[[dict[str, Any]], dict[str, Any]] = _fetch) -> dict[str, Any]:
    if not species:
        return {"status": "not_applicable"}
    count = occurrence_count(species, lat, lon, fetch=fetch)
    if count is None:
        return {"status": "unchecked", "species": species, "note": "GBIF could not be reached"}
    status = "plausible" if count > 0 else "implausible"
    return {"status": status, "species": species, "gbif_occurrences": count, "radius_deg": DEFAULT_RADIUS_DEG, "source": GBIF_URL}


def _read_cache() -> dict[str, int]:
    try:
        return json.loads(CACHE_FILE.read_text())
    except (OSError, ValueError):
        return {}


def _write_cache(cache: dict[str, int]) -> None:
    try:
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        CACHE_FILE.write_text(json.dumps(cache))
    except OSError:
        pass
