"""Score a calibration round against the reference set and explain disagreements.

Feedback is rule-based: the direction of each confusion (under, over, swap)
selects a plain-language message. No language model rates or explains here.
"""

from __future__ import annotations

import json
from collections import defaultdict
from functools import lru_cache
from pathlib import Path
from typing import Any

from api.reliability.kappa import cohen_kappa, tier_for

ROOT = Path(__file__).resolve().parents[2]
REFERENCE = ROOT / "data" / "reference_set" / "items.json"
ORDINAL = {"ape": ["absent", "present", "extensive"], "cover5": ["1", "2", "3", "4", "5"]}


@lru_cache
def reference_items() -> list[dict[str, Any]]:
    return json.loads(REFERENCE.read_text(encoding="utf-8"))["items"]


def public_items() -> list[dict[str, Any]]:
    """Items without answers or rationales, for the practice round."""
    return [{k: v for k, v in it.items() if k not in ("answer", "rationale")} for it in reference_items()]


def direction(scale: str, reference: str, answered: str) -> str:
    order = ORDINAL.get(scale)
    if order and reference in order and answered in order:
        return "under" if order.index(answered) < order.index(reference) else "over"
    return "swap"


def score(answers: dict[str, str]) -> dict[str, Any]:
    items = [it for it in reference_items() if it["id"] in answers]
    if not items:
        raise ValueError("No reference items answered")
    by_q: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for it in items:
        by_q[it["question_id"]].append(it)

    per_question = {}
    for q, its in by_q.items():
        ref = [it["answer"] for it in its]
        ans = [answers[it["id"]] for it in its]
        per_question[q] = {
            "kappa": round(cohen_kappa(ref, ans), 3),
            "agreement": round(sum(r == a for r, a in zip(ref, ans)) / len(its), 3),
            "n": len(its),
        }
    total = sum(v["n"] for v in per_question.values())
    overall = round(sum(v["kappa"] * v["n"] for v in per_question.values()) / total, 3)

    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for it in items:
        given = answers[it["id"]]
        if given != it["answer"]:
            grouped[(it["question_id"], direction(it["scale"], it["answer"], given))].append(
                {"item": it["id"], "reference": it["answer"], "answered": given, "rationale": it["rationale"]}
            )
    feedback = [
        {"question": q, "direction": d, "key": f"calib.fb.{q}.{d}", "count": len(v), "examples": v}
        for (q, d), v in sorted(grouped.items(), key=lambda kv: -len(kv[1]))
    ]
    return {"per_question": per_question, "overall_kappa": overall, "tier": tier_for(overall), "n": total, "feedback": feedback}
