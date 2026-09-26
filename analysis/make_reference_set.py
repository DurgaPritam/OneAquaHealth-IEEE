"""Generate the calibration reference set: illustrated stream scenes drawn from their answers.

Each scene is rendered from a specification, so the correct answer is fixed by
construction rather than judged by anyone (and never by an AI). Items are marked
``synthetic: true`` and ``review_status: pending`` until the team panel reviews them.

Usage: .venv/bin/python -m analysis.make_reference_set
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "data" / "reference_set"
W, H = 400, 260
TOP, BOTTOM = 92, 168  # water band


@dataclass
class Scene:
    bank: str = "earth"  # earth | concrete | concrete_moss | gabion | mixed
    flow: str = "run"  # run | riffle | still | mixed_still | dry_puddles
    trees: int = 1  # riparian cover class 1..5
    foam: str = "absent"  # absent | present | extensive
    seed: int = 0
    extras: list[str] = field(default_factory=list)


def _rng(scene: Scene) -> random.Random:
    return random.Random(scene.seed)


def _bank(y: int, h: int, kind: str, rng: random.Random, left_share: float = 1.0) -> str:
    parts = []
    if kind in ("earth", "mixed"):
        parts.append(f'<rect x="0" y="{y}" width="{W}" height="{h}" fill="#8b6b43"/>')
        for _ in range(26):
            x = rng.uniform(0, W)
            parts.append(f'<path d="M{x:.0f} {y + h} l3 -9 l3 9" stroke="#3f6212" stroke-width="2" fill="none"/>')
    if kind in ("concrete", "concrete_moss", "mixed"):
        x0 = 0 if kind != "mixed" else W * 0.55
        parts.append(f'<rect x="{x0:.0f}" y="{y}" width="{W - x0:.0f}" height="{h}" fill="#9ca3af"/>')
        for x in range(int(x0), W, 40):
            parts.append(f'<path d="M{x} {y} v{h}" stroke="#6b7280" stroke-width="2"/>')
        parts.append(f'<path d="M{x0:.0f} {y + h / 2:.0f} H{W}" stroke="#6b7280" stroke-width="1.5"/>')
        if kind == "concrete_moss":
            for _ in range(14):
                cx, cy = rng.uniform(0, W), rng.uniform(y, y + h)
                parts.append(f'<ellipse cx="{cx:.0f}" cy="{cy:.0f}" rx="{rng.uniform(8, 20):.0f}" ry="4" fill="#4d7c0f" opacity="0.75"/>')
    if kind == "gabion":
        parts.append(f'<rect x="0" y="{y}" width="{W}" height="{h}" fill="#a8a29e"/>')
        for _ in range(60):
            parts.append(f'<circle cx="{rng.uniform(0, W):.0f}" cy="{rng.uniform(y, y + h):.0f}" r="{rng.uniform(2, 5):.1f}" fill="#78716c"/>')
        for x in range(0, W, 14):
            parts.append(f'<path d="M{x} {y} l7 {h}" stroke="#44403c" stroke-width="0.8"/><path d="M{x + 7} {y} l-7 {h}" stroke="#44403c" stroke-width="0.8"/>')
    return "".join(parts)


def _water(scene: Scene, rng: random.Random) -> str:
    if scene.flow == "dry_puddles":
        parts = [f'<rect x="0" y="{TOP}" width="{W}" height="{BOTTOM - TOP}" fill="#d6c7a1"/>']
        for cx in (80, 210, 320):
            parts.append(f'<ellipse cx="{cx}" cy="{(TOP + BOTTOM) / 2 + rng.uniform(-10, 10):.0f}" rx="{rng.uniform(22, 34):.0f}" ry="12" fill="#1e3a5f" opacity="0.85"/>')
        return "".join(parts)
    still = scene.flow in ("still", "mixed_still")
    colour = "#1e3a5f" if still else "#38bdf8"
    parts = [f'<rect x="0" y="{TOP}" width="{W}" height="{BOTTOM - TOP}" fill="{colour}"/>']
    if scene.flow == "mixed_still":
        parts[0] = f'<rect x="0" y="{TOP}" width="{W}" height="{BOTTOM - TOP}" fill="#38bdf8"/>'
        parts.append(f'<rect x="0" y="{TOP}" width="120" height="{BOTTOM - TOP}" fill="#1e3a5f"/>')
    if scene.flow in ("run", "mixed_still"):
        x_start = 130 if scene.flow == "mixed_still" else 10
        for y in range(TOP + 14, BOTTOM - 6, 18):
            parts.append(f'<path d="M{x_start} {y} H{W - 10}" stroke="#e0f2fe" stroke-width="2" stroke-dasharray="40 18"/>')
    if scene.flow == "riffle":
        for y in range(TOP + 12, BOTTOM - 4, 16):
            for x in range(10, W, 30):
                parts.append(f'<path d="M{x} {y} q7 -8 14 0 q7 8 14 0" stroke="#ffffff" stroke-width="2.2" fill="none"/>')
    if still:
        x_max = 120 if scene.flow == "mixed_still" else W
        for _ in range(10 if scene.flow == "still" else 4):
            cx, cy = rng.uniform(8, x_max - 8), rng.uniform(TOP + 8, BOTTOM - 8)
            parts.append(f'<ellipse cx="{cx:.0f}" cy="{cy:.0f}" rx="5" ry="2.5" fill="#a16207"/>')  # floating leaves
        parts.append(f'<ellipse cx="{min(60, x_max / 2):.0f}" cy="{(TOP + BOTTOM) / 2:.0f}" rx="30" ry="10" fill="#0f172a" opacity="0.35"/>')  # reflection
    if scene.foam != "absent":
        n = 3 if scene.foam == "present" else 16
        for _ in range(n):
            cx, cy = rng.uniform(20, W - 20), rng.uniform(TOP + 10, BOTTOM - 10)
            r = rng.uniform(8, 14) if scene.foam == "present" else rng.uniform(14, 26)
            parts.append(f'<circle cx="{cx:.0f}" cy="{cy:.0f}" r="{r:.0f}" fill="#f8fafc" opacity="0.92"/>')
            parts.append(f'<circle cx="{cx + r * 0.6:.0f}" cy="{cy - r * 0.3:.0f}" r="{r * 0.6:.0f}" fill="#f8fafc" opacity="0.92"/>')
    return "".join(parts)


def _trees(scene: Scene, rng: random.Random) -> str:
    # cover classes 1..5 map to roughly 10, 30, 50, 70, 90 % of the bank length under canopy
    share = [0.1, 0.3, 0.5, 0.7, 0.9][scene.trees - 1]
    parts = []
    for y_row in (40, 222):
        covered = 0.0
        x = rng.uniform(0, 20)
        while covered < share * W and x < W:
            r = 26
            parts.append(f'<circle cx="{x + r:.0f}" cy="{y_row + rng.uniform(-6, 6):.0f}" r="{r}" fill="#166534" stroke="#14532d" stroke-width="2"/>')
            covered += 2 * r
            gap = (W - share * W) / max(1, share * W / (2 * r))
            x += 2 * r + gap * rng.uniform(0.6, 1.1)
    return "".join(parts)


def render(scene: Scene) -> str:
    rng = _rng(scene)
    body = [
        f'<rect width="{W}" height="{H}" fill="#bbf7d0"/>',
        _trees(scene, rng),
        _bank(TOP - 16, 16, scene.bank, rng),
        _bank(BOTTOM, 16, scene.bank, rng),
        _water(scene, rng),
    ]
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" role="img">'
        "<title>Top-down drawing of a stream section (synthetic reference illustration)</title>"
        + "".join(body)
        + "</svg>"
    )


def render_posture(angled: bool, seed: int) -> str:
    rng = random.Random(seed)
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" role="img">',
             "<title>Side view of a white cup with larvae (synthetic reference illustration)</title>",
             f'<rect width="{W}" height="{H}" fill="#f1f5f9"/>',
             '<path d="M60 40 H340 L320 240 H80 Z" fill="#ffffff" stroke="#334155" stroke-width="3"/>',
             '<rect x="63" y="70" width="274" height="168" fill="#e0f2fe"/>',
             '<path d="M63 70 H337" stroke="#0369a1" stroke-width="3"/>']
    for i in range(5):
        x = 90 + i * 50 + rng.uniform(-8, 8)
        if angled:
            parts.append(f'<g stroke="#334155" fill="#64748b"><path d="M{x + 10:.0f} 70 l6 16" stroke-width="3"/>'
                         f'<ellipse cx="{x:.0f}" cy="104" rx="6" ry="18" transform="rotate(-28 {x:.0f} 104)"/><circle cx="{x - 12:.0f}" cy="124" r="6"/></g>')
        else:
            parts.append(f'<g stroke="#334155" fill="#64748b"><ellipse cx="{x:.0f}" cy="76" rx="20" ry="4.5"/><circle cx="{x - 22:.0f}" cy="76" r="5"/></g>')
    parts.append("</svg>")
    return "".join(parts)


# id, question, scale, scene or posture, answer, rationale
ITEMS: list[tuple[str, str, str, object, str, str]] = [
    ("rs01", "bank_CC", "ape", Scene(bank="concrete", seed=1), "extensive", "Both banks are grey blocks with straight joints along their whole length."),
    ("rs02", "bank_CC", "ape", Scene(bank="concrete_moss", trees=3, seed=2), "extensive", "Moss grows on it, but the straight block joints show the banks are concrete."),
    ("rs03", "bank_CC", "ape", Scene(bank="earth", trees=4, seed=3), "absent", "Brown soil with grass; no blocks or joints."),
    ("rs04", "bank_CC", "ape", Scene(bank="mixed", trees=2, seed=4), "present", "Concrete covers only part of the bank; the rest is soil."),
    ("rs05", "bank_CC", "ape", Scene(bank="gabion", trees=2, seed=5), "absent", "Stones held in a wire mesh are gabions, not concrete."),
    ("rs06", "flow_NP", "ape", Scene(flow="still", bank="concrete", seed=6), "extensive", "Dark, flat water with floating leaves and a reflection: no flow anywhere."),
    ("rs07", "flow_NP", "ape", Scene(flow="riffle", trees=3, seed=7), "absent", "White standing waves across the channel: the water is moving."),
    ("rs08", "flow_NP", "ape", Scene(flow="mixed_still", trees=3, seed=8), "present", "A still, leafy patch at the left edge; the rest flows."),
    ("rs09", "flow_NP", "ape", Scene(flow="dry_puddles", bank="concrete", seed=9), "present", "The channel is mostly dry, with a few standing puddles."),
    ("rs10", "rip_trees", "cover5", Scene(trees=1, seed=10), "1", "Only a few trees: well under a fifth of the banks are under canopy."),
    ("rs11", "rip_trees", "cover5", Scene(trees=3, seed=11), "3", "About half of the banks are under tree canopy."),
    ("rs12", "rip_trees", "cover5", Scene(trees=5, seed=12), "5", "Trees almost all the way along both banks."),
    ("rs13", "water_foam", "ape", Scene(foam="absent", trees=3, seed=13), "absent", "Clear water surface with no white patches."),
    ("rs14", "water_foam", "ape", Scene(foam="present", trees=2, seed=14), "present", "A few small white foam patches."),
    ("rs15", "water_foam", "ape", Scene(foam="extensive", bank="concrete", seed=15), "extensive", "Foam covers a large part of the surface."),
    ("rs16", "larval_posture", "posture", True, "angled", "Bodies hang down at an angle from a short tube at the surface."),
    ("rs17", "larval_posture", "posture", False, "flat", "Bodies lie flat, parallel to the surface."),
    ("rs18", "larval_posture", "posture", True, "angled", "Hanging at an angle: Culex-type or Aedes-type."),
    ("rs19", "larval_posture", "posture", False, "flat", "Lying flat just under the surface: Anopheles-type."),
]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = []
    for item_id, question, scale, spec, answer, rationale in ITEMS:
        svg = render_posture(bool(spec), int(item_id[2:])) if scale == "posture" else render(spec)  # type: ignore[arg-type]
        (OUT / f"{item_id}.svg").write_text(svg, encoding="utf-8")
        manifest.append({
            "id": item_id, "question_id": question, "scale": scale, "image": f"{item_id}.svg", "answer": answer,
            "rationale": rationale, "labelled_by": "construction", "review_status": "pending team panel review",
            "synthetic": True,
        })
    doc = {
        "description": "Calibration reference set. Each illustration is generated from its answer (analysis/make_reference_set.py), so the answer is fixed by construction. No AI labelled any item. Items stay review_status pending until the team panel has looked at every drawing.",
        "synthetic": True,
        "items": manifest,
    }
    (OUT / "items.json").write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(manifest)} items to {OUT}")


if __name__ == "__main__":
    main()
