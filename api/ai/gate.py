"""Validation gate: only labels in data/labels.json survive."""

from __future__ import annotations

from dataclasses import dataclass, field

from api.ai.base import Suggestion
from api.ai.labels import allowed


@dataclass
class GateResult:
    kept: list[Suggestion] = field(default_factory=list)
    dropped: list[dict[str, object]] = field(default_factory=list)


def apply_gate(finding_type: str, suggestions: list[Suggestion]) -> GateResult:
    """Keep allowed labels with a valid confidence and a reason; record every drop and why."""
    permitted = set(allowed(finding_type))
    result = GateResult()
    for s in suggestions:
        if s.label not in permitted:
            result.dropped.append({"label": s.label, "why": "not in the allowed label list"})
        elif not 0 <= s.confidence <= 1:
            result.dropped.append({"label": s.label, "why": "confidence outside 0 to 1"})
        elif not s.reason.strip():
            result.dropped.append({"label": s.label, "why": "no reason given"})
        else:
            result.kept.append(s)
    return result
