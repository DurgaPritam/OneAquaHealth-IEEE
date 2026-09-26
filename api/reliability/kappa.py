"""Cohen's kappa of one observer against the reference answers, and plain-language bias feedback."""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass

TIER_CALIBRATED = 0.4  # "moderate" agreement or better (Landis and Koch 1977)
TIER_TRUSTED = 0.7  # "substantial" agreement or better


def cohen_kappa(reference: Sequence[str], answers: Sequence[str]) -> float:
    """Unweighted Cohen's kappa. Returns 1.0 for perfect agreement even when only one class occurs."""
    if len(reference) != len(answers) or not reference:
        raise ValueError("Need two equal, non-empty sequences")
    n = len(reference)
    po = sum(r == a for r, a in zip(reference, answers)) / n
    ref_c, ans_c = Counter(reference), Counter(answers)
    pe = sum(ref_c[c] * ans_c[c] for c in set(ref_c) | set(ans_c)) / (n * n)
    if pe >= 1.0:
        return 1.0 if po == 1.0 else 0.0
    return (po - pe) / (1 - pe)


def tier_for(kappa: float | None) -> str:
    if kappa is None:
        return "new"
    if kappa >= TIER_TRUSTED:
        return "trusted"
    if kappa >= TIER_CALIBRATED:
        return "calibrated"
    return "new"


@dataclass(frozen=True)
class Confusion:
    question: str
    reference: str
    answered: str
    count: int


def confusions(items: Sequence[tuple[str, str, str]]) -> list[Confusion]:
    """(question, reference, answer) triples to a sorted list of disagreements."""
    c = Counter((q, r, a) for q, r, a in items if r != a)
    return [Confusion(q, r, a, n) for (q, r, a), n in c.most_common()]
