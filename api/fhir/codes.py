"""Systems, profile URLs and code maps shared by the FHIR exporter.

Everything here mirrors fhir/input/fsh. The canonical uses the reserved
example.org domain because the project has no registered domain (fhir/README.md).
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]

CANONICAL = "http://example.org/fhir/aquasentinel"
OAH = "http://hl7.eu/fhir/ig/oah/CodeSystem/temporarySystem-oah-eu"
OAH_SD = "http://hl7.eu/fhir/ig/oah/StructureDefinition"
AS = f"{CANONICAL}/CodeSystem/aquasentinel"
AS_QUESTIONS = f"{CANONICAL}/CodeSystem/aquasentinel-stream-check"
UCUM = "http://unitsofmeasure.org"
DATA_ABSENT = "http://terminology.hl7.org/CodeSystem/data-absent-reason"
PROVENANCE_TYPE = "http://terminology.hl7.org/CodeSystem/provenance-participant-type"

SID_OBSERVER = f"{CANONICAL}/sid/observer-code"
SID_SITE = f"{CANONICAL}/sid/enora-site-code"
SID_CITY = f"{CANONICAL}/sid/enora-city-id"
SID_FINDING = f"{CANONICAL}/sid/finding-id"
SID_CHECKIN = f"{CANONICAL}/sid/checkin-uuid"
SID_ACTION = f"{CANONICAL}/sid/action-id"
SID_MESSAGE = f"{CANONICAL}/sid/message-id"
SID_RISK = f"{CANONICAL}/sid/risk-score-id"

MEASURE_URL = f"{CANONICAL}/Measure/aquasentinel-vector-habitat-risk-week"
EXT_RELIABILITY = f"{CANONICAL}/StructureDefinition/observer-reliability"


def profile(pid: str) -> str:
    return f"{CANONICAL}/StructureDefinition/{pid}"


P_OBSERVER = profile("aquasentinel-observer")
P_SITE = profile("aquasentinel-site")
P_CITIZEN = profile("aquasentinel-citizen-finding")
P_INDICATOR = profile("aquasentinel-indicator-finding")
P_VEGETATION = profile("aquasentinel-vegetation-finding")
P_DEAD_BIRD = profile("aquasentinel-dead-bird-report")
P_RISK = profile("aquasentinel-vector-habitat-risk-index")
P_PROVENANCE = profile("aquasentinel-observer-provenance")
P_ACTION = profile("aquasentinel-action-request")
P_MESSAGE = profile("aquasentinel-volunteer-message")
P_CITY_WEEK = profile("aquasentinel-city-week-report")

SYNTHETIC_TAG = {"system": AS, "code": "synthetic", "display": "Synthetic record"}

# Codes defined in AquaSentinelCodes that a citizen answer or AI label may carry.
ANSWER_CODES = frozenset({
    "angled", "flat", "culex_type", "anopheles_type", "larvae_present", "larvae_absent",
    "striped_aedes_type", "plain_culex_type", "not_a_mosquito", "standing_water", "flowing_water",
    "dry_channel", "bird_unidentified", "amphibian_unidentified", "heard", "seen", "none", "not_sure",
})
DECISIONS = frozenset({"confirmed", "corrected", "rejected", "manual", "expert_review"})
RISK_FACTORS = ("temperature", "dry_spell", "habitat", "vector_presence", "predator_deficit", "host_signal")
RISK_BANDS = frozenset({"low", "moderate", "high", "very_high"})
TIERS = frozenset({"new", "calibrated", "trusted"})

# Stream-check answers that map to OAH vegetation component codes (sections 4a and 4b).
VEGETATION_COMPONENT = {
    "mac_liveworts": "liveworts",
    "mac_broad_leaved_herbs": "broad-leaved-herbs",
    "mac_floating_leaved": "floating-leaved",
    "mac_free_floating": "free-floating",
    "mac_amphibious": "amphibious",
    "mac_submerged_broad": "submerged-broad-leaved",
    "mac_submerged_linear": "submerged-linear-leaved",
    "mac_filamentous_algae": "filamentous-algae",
    "rip_trees": "trees",
    "rip_bushes": "bushes",
    "rip_herbaceous": "herbaceous",
}

OAH_DISPLAY = {
    "diptera": "Diptera", "birds": "Birds", "amphibians": "Amphibians", "hydrology": "Hydrology of the stream",
    "morophology": "Morphology of the streams", "foam": "Foam/colour/smell", "macrophytes": "Macrophytes",
    "riparianVegetation": "Riparian vegetation",
}


def coding(system: str, code: str, display: str | None = None) -> dict[str, Any]:
    out = {"system": system, "code": code}
    if display:
        out["display"] = display
    return out


@lru_cache
def questions() -> dict[str, Any]:
    return json.loads((ROOT / "data" / "questions.json").read_text(encoding="utf-8"))


@lru_cache
def answer_key_index() -> dict[str, dict[str, Any]]:
    """Answer key -> {section, question, scale, indicator}. Per-margin keys are expanded (bank_left_CC)."""
    doc = questions()
    out: dict[str, dict[str, Any]] = {}
    for sec in doc["sections"]:
        for margin in sec.get("per_margin") or [None]:
            for q in sec["questions"]:
                prefix, _, rest = q["id"].partition("_")
                key = q["id"] if margin is None else f"{prefix}_{margin}_{rest}"
                out[key] = {"section": sec, "question": q, "scale": doc["scales"][q["scale"]], "indicator": sec["fhir_indicator"]}
    return out


@lru_cache
def label_groups() -> dict[str, str]:
    """Predator label id -> bird or amphibian, from data/labels.json."""
    doc = json.loads((ROOT / "data" / "labels.json").read_text(encoding="utf-8"))
    return {lab["id"]: lab["group"] for lab in doc["types"]["predator"]["labels"] if "group" in lab}
