"""Guided identification keys as JSON decision trees in data/keys/."""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from api.ai.labels import ROOT

KEYS_DIR = ROOT / "data" / "keys"


@lru_cache
def load_key(key_id: str) -> dict[str, Any]:
    return json.loads((KEYS_DIR / f"{key_id}.json").read_text(encoding="utf-8"))


def run_key(key_id: str, answers: dict[str, str]) -> str | None:
    """Walk the tree with the citizen's answers. Returns a result id, or None if unanswered or unsure."""
    key = load_key(key_id)
    node_id = key["start"]
    for _ in range(len(key["nodes"]) + 1):
        node = key["nodes"][node_id]
        answer = answers.get(node_id)
        if answer is None:
            if node.get("optional") and len(node["options"]) and _same_result(node):
                return next(iter(node["options"].values()))["result"]
            return None
        option = node["options"].get(answer)
        if option is None:
            return None
        if "result" in option:
            return option["result"]
        node_id = option["next"]
    raise ValueError(f"Key {key_id} has a cycle")


def _same_result(node: dict[str, Any]) -> bool:
    results = {opt.get("result") for opt in node["options"].values()}
    return len(results) == 1 and None not in results


def compare(key_result: str | None, vision_label: str | None) -> str:
    """agree, disagree or incomplete. Disagreement means the UI shows both and asks the citizen."""
    if not key_result or not vision_label or "not_sure" in (key_result, vision_label):
        return "incomplete"
    return "agree" if key_result == vision_label else "disagree"
