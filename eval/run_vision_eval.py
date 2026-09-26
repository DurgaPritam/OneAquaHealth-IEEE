"""Score a vision provider against human labels.

Usage:
  .venv/bin/python -m eval.run_vision_eval --folder eval/photos [--provider mock|anthropic|gemini]

The folder needs labels.csv with columns: file, finding_type, human_label, licence, source.
Human labels come from people, never from an AI. Writes eval/reports/vision_<provider>.md.
Without --folder it builds a set of generated test cards (labelled synthetic), which is
only useful to exercise the pipeline: the mock provider does not look at pixels.
"""

from __future__ import annotations

import argparse
import csv
import io
import statistics
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from PIL import Image, ImageDraw

from api.ai import service
from api.ai.labels import NOT_SURE, allowed

REPORTS = Path(__file__).parent / "reports"
PRICES_PER_MTOK = {"claude-opus-5": (5.0, 25.0), "claude-sonnet-5": (2.0, 10.0), "claude-haiku-4-5": (1.0, 5.0)}


@dataclass
class Item:
    file: str
    finding_type: str
    human_label: str
    image: bytes


def load_folder(folder: Path) -> list[Item]:
    with (folder / "labels.csv").open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    return [Item(r["file"], r["finding_type"], r["human_label"], (folder / r["file"]).read_bytes()) for r in rows]


def synthetic_cards() -> list[Item]:
    """Plain test cards with the intended label written on them. Synthetic."""
    items = []
    for ftype in ("larvae", "adult_mosquito", "predator", "habitat"):
        for i, label in enumerate(label for label in allowed(ftype) if label != NOT_SURE):
            img = Image.new("RGB", (320, 200), (30 + 40 * i % 200, 90, 120))
            ImageDraw.Draw(img).text((10, 90), f"synthetic card: {label}", fill=(255, 255, 255))
            buf = io.BytesIO()
            img.save(buf, format="JPEG")
            items.append(Item(f"card_{ftype}_{i}.jpg", ftype, label, buf.getvalue()))
    return items


def evaluate(items: list[Item]) -> dict[str, object]:
    rows = []
    for it in items:
        out = service.suggest(it.image, it.finding_type)
        top = out["suggestions"][0] if out.get("suggestions") else None
        rows.append({
            "item": it, "available": out["available"], "label": top["label"] if top else None,
            "confidence": top["confidence"] if top else None, "dropped": len(out.get("dropped", [])),
            "latency": out.get("latency_ms", 0.0), "model": out.get("model"), "provider": out.get("provider"),
        })
    answered = [r for r in rows if r["available"]]
    decided = [r for r in answered if r["label"] and r["label"] != NOT_SURE]
    right = [r for r in decided if r["label"] == r["item"].human_label]
    wrong = [r for r in decided if r["label"] != r["item"].human_label]
    latencies = sorted(r["latency"] for r in answered) or [0.0]
    return {
        "n": len(rows),
        "available_rate": len(answered) / len(rows) if rows else 0,
        "agreement": len(right) / len(decided) if decided else 0,
        "not_sure_rate": sum(1 for r in answered if r["label"] in (None, NOT_SURE)) / len(answered) if answered else 0,
        "drop_rate": sum(r["dropped"] for r in answered) / len(answered) if answered else 0,
        "confidence_right": statistics.mean(r["confidence"] for r in right) if right else None,
        "confidence_wrong": statistics.mean(r["confidence"] for r in wrong) if wrong else None,
        "latency_p50_ms": latencies[len(latencies) // 2],
        "latency_p95_ms": latencies[min(len(latencies) - 1, int(len(latencies) * 0.95))],
        "provider": answered[0]["provider"] if answered else None,
        "model": answered[0]["model"] if answered else None,
        "rows": rows,
    }


def cost_per_1000(model: str | None, in_tok: int = 1600, out_tok: int = 60) -> str:
    if model not in PRICES_PER_MTOK:
        return "n/a (mock or unknown model)"
    p_in, p_out = PRICES_PER_MTOK[model]
    return f"about ${1000 * (in_tok * p_in + out_tok * p_out) / 1e6:.2f} per 1000 photos (assumes {in_tok} input and {out_tok} output tokens)"


def fmt(x: object) -> str:
    return f"{x:.2f}" if isinstance(x, float) else str(x)


def write_report(result: dict[str, object], synthetic: bool) -> Path:
    REPORTS.mkdir(parents=True, exist_ok=True)
    path = REPORTS / f"vision_{result['provider']}.md"
    lines = [
        f"# Vision eval: {result['provider']} ({result['model']})",
        "",
        f"Run {date.today().isoformat()} with `python -m eval.run_vision_eval`.",
        "",
        "## Limits first",
        "",
    ]
    if synthetic:
        lines += ["- **Synthetic inputs.** These are generated test cards, not photos. `\"synthetic\": true`.",]
    if result["provider"] == "mock":
        lines += ["- **Mock provider.** It picks a label by hashing the image bytes and never looks at pixels. Agreement here measures nothing about AI accuracy; it only proves the pipeline, the validation gate and the metrics work end to end."]
    lines += [
        "- Human labels are the reference. No AI output is ever used as a reference label.",
        "",
        "## Results",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Items | {result['n']} |",
        f"| Provider available | {fmt(result['available_rate'])} |",
        f"| Agreement with human label (excluding not sure) | {fmt(result['agreement'])} |",
        f"| Not-sure rate | {fmt(result['not_sure_rate'])} |",
        f"| Dropped labels per photo (validation gate) | {fmt(result['drop_rate'])} |",
        f"| Mean confidence when right | {fmt(result['confidence_right'])} |",
        f"| Mean confidence when wrong | {fmt(result['confidence_wrong'])} |",
        f"| Latency p50 / p95 (ms) | {fmt(result['latency_p50_ms'])} / {fmt(result['latency_p95_ms'])} |",
        f"| Cost | {cost_per_1000(result['model'])} |",
        "",
        "## How to run on real photos",
        "",
        "Put licensed photos in a folder with `labels.csv` (file, finding_type, human_label, licence, source), then:",
        "",
        "```",
        "AI_PROVIDER=anthropic ANTHROPIC_API_KEY=... .venv/bin/python -m eval.run_vision_eval --folder path/to/photos",
        "```",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--folder", type=Path)
    args = parser.parse_args(argv)
    items = load_folder(args.folder) if args.folder else synthetic_cards()
    result = evaluate(items)
    path = write_report(result, synthetic=args.folder is None)
    print(f"wrote {path}")


if __name__ == "__main__":
    sys.exit(main())
