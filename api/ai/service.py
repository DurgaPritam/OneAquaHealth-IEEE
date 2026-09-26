"""Orchestrates one suggestion: provider, gate, guided key and GBIF plausibility."""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Any

from api.ai import gbif
from api.ai.base import ProviderError, VisionProvider
from api.ai.gate import apply_gate
from api.ai.keys import compare
from api.ai.labels import VISION_TYPES, allowed, label_info
from api.ai.mock import MockProvider


class NeverAnalysed(ValueError):
    """Raised for finding types that must never reach a vision model (dead birds)."""


@lru_cache
def get_provider() -> VisionProvider:
    choice = os.environ.get("AI_PROVIDER", "mock").lower()
    if choice == "anthropic":
        from api.ai.anthropic_provider import AnthropicProvider

        return AnthropicProvider()
    if choice == "gemini":
        from api.ai.gemini_provider import GeminiProvider

        return GeminiProvider()
    return MockProvider()


def status() -> dict[str, Any]:
    try:
        p = get_provider()
        return {"provider": p.name, "model": p.model, "mock": p.name == "mock", "available": True}
    except (ProviderError, ImportError) as exc:
        return {"provider": os.environ.get("AI_PROVIDER", "mock"), "model": None, "mock": False, "available": False, "error": str(exc)}


def suggest(image: bytes, finding_type: str, lat: float | None = None, lon: float | None = None,
            key_result: str | None = None, provider: VisionProvider | None = None, gbif_fetch: Any = None) -> dict[str, Any]:
    if finding_type == "dead_bird":
        raise NeverAnalysed("Dead birds are never analysed by AI. Report location, count and time only.")
    if finding_type not in VISION_TYPES:
        raise ValueError(f"Unknown finding type {finding_type}")
    try:
        p = provider or get_provider()
        raw = p.suggest(image, finding_type, allowed(finding_type))
    except (ProviderError, ImportError) as exc:
        return {"available": False, "error": str(exc), "suggestions": [], "dropped": []}

    gated = apply_gate(finding_type, raw.suggestions)
    suggestions = []
    for s in gated.kept:
        info = label_info(finding_type, s.label) or {}
        item: dict[str, Any] = {**s.to_dict(), "text": info.get("text", s.label)}
        if finding_type == "predator" and info.get("gbif") and lat is not None and lon is not None:
            kwargs = {"fetch": gbif_fetch} if gbif_fetch else {}
            item["plausibility"] = gbif.plausibility(info["gbif"], lat, lon, **kwargs)
        suggestions.append(item)

    top = suggestions[0]["label"] if suggestions else None
    return {
        "available": True,
        "provider": raw.provider,
        "model": raw.model,
        "mock": raw.provider == "mock",
        "latency_ms": round(raw.latency_ms, 1),
        "suggestions": suggestions,
        "dropped": gated.dropped,
        "key_result": key_result,
        "key_vs_vision": compare(key_result, top) if finding_type == "adult_mosquito" else None,
    }
