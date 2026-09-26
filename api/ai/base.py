"""Provider interface and the suggestion shape every provider must return."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Protocol


@dataclass(frozen=True)
class Suggestion:
    label: str
    confidence: float
    reason: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class ProviderResult:
    """Raw provider output before the validation gate."""

    suggestions: list[Suggestion]
    provider: str
    model: str
    latency_ms: float
    input_tokens: int = 0
    output_tokens: int = 0


class ProviderError(RuntimeError):
    """The provider could not answer; the UI falls back to manual answers."""


class VisionProvider(Protocol):
    name: str
    model: str

    def suggest(self, image: bytes, finding_type: str, allowed: list[str]) -> ProviderResult: ...


def build_prompt(finding_type: str, allowed: list[str], descriptions: dict[str, str]) -> str:
    """Instructions shared by the real providers."""
    options = "\n".join(f"- {label}: {descriptions.get(label, '')}" for label in allowed)
    return (
        "You help volunteers record what is visible in a photo taken at an urban stream. "
        "You suggest; the volunteer decides. Never diagnose disease or infection. "
        f"The photo is for a '{finding_type}' record. Choose the single best label from this list only:\n{options}\n"
        "If the photo does not clearly show one of these, answer not_sure. "
        "confidence is your probability (0 to 1) that the label is right. "
        "reason is one short sentence that points at something visible in the photo."
    )
