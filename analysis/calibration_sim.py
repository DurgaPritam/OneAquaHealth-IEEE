"""SIMULATION: does Dawid-Skene recover the true class better than majority vote?

Observers are simulated with known accuracy and systematic biases (for example
rating hard banks as natural). For each number of observers per site-week we
draw many observer panels and compare the share of items whose true class is
recovered by (a) majority vote, (b) Dawid-Skene EM, (c) Dawid-Skene seeded with
each observer's calibration accuracy. Everything here is simulated.

Usage: .venv/bin/python -m analysis.calibration_sim
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from api.reliability.dawid_skene import dawid_skene, majority_vote  # noqa: E402

CLASSES = ("absent", "present", "extensive")
METHODS = {
    "majority": ("Majority vote", "#94a3b8", "o"),
    "ds_ml": ("Dawid-Skene, maximum likelihood (no prior)", "#f59e0b", "x"),
    "dawid_skene": ("Dawid-Skene with default prior (used in AquaSentinel)", "#0b7a66", "s"),
    "ds_calibrated": ("Dawid-Skene with calibration prior", "#7c3aed", "^"),
}
REPORTS = Path(__file__).resolve().parent.parent / "eval" / "reports"


@dataclass(frozen=True)
class SimObserver:
    name: str
    accuracy: float
    bias: dict[str, str]
    bias_rate: float = 0.8


def observer_pool(n: int, rng: random.Random) -> list[SimObserver]:
    """Mixed pool: 30% careful, 40% average, 30% biased (hard banks rated as natural)."""
    pool = []
    for i in range(n):
        r = rng.random()
        if r < 0.3:
            pool.append(SimObserver(f"o{i}", rng.uniform(0.85, 0.95), {}))
        elif r < 0.7:
            pool.append(SimObserver(f"o{i}", rng.uniform(0.6, 0.8), {}))
        else:
            pool.append(SimObserver(f"o{i}", rng.uniform(0.7, 0.85), {"extensive": "absent", "present": "absent"}))
    return pool


def report(obs: SimObserver, true: str, rng: random.Random) -> str:
    if true in obs.bias and rng.random() < obs.bias_rate:
        return obs.bias[true]
    if rng.random() < obs.accuracy:
        return true
    return rng.choice([c for c in CLASSES if c != true])


def calibration_accuracy(obs: SimObserver, rng: random.Random, n_items: int = 15) -> float:
    """Accuracy an observer would score on a reference round of n_items."""
    truth = [rng.choice(CLASSES) for _ in range(n_items)]
    return sum(report(obs, t, rng) == t for t in truth) / n_items


def run(panel_sizes=(1, 2, 3, 4, 5, 7), reps: int = 30, n_items: int = 120, pool_size: int = 40, seed: int = 2026) -> dict[int, dict[str, list[float]]]:
    rng = random.Random(seed)
    results: dict[int, dict[str, list[float]]] = {k: {m: [] for m in METHODS} for k in panel_sizes}
    for rep in range(reps):
        pool = observer_pool(pool_size, rng)
        prior = {o.name: calibration_accuracy(o, rng) for o in pool}
        truth = {i: rng.choices(CLASSES, weights=(0.4, 0.35, 0.25))[0] for i in range(n_items)}
        for k in panel_sizes:
            labels = []
            for i, t in truth.items():
                for o in rng.sample(pool, k):
                    labels.append((i, o.name, report(o, t, rng)))
            estimates = {
                "majority": majority_vote(labels),
                "ds_ml": dawid_skene(labels, classes=CLASSES, default_accuracy=None, class_prior_share=0.0).estimates(),
                "dawid_skene": dawid_skene(labels, classes=CLASSES).estimates(),
                "ds_calibrated": dawid_skene(labels, classes=CLASSES, prior_accuracy=prior, prior_strength=5).estimates(),
            }
            for name, est in estimates.items():
                results[k][name].append(sum(est[i] == truth[i] for i in truth) / n_items)
    return results


def reading(results: dict[int, dict[str, list[float]]]) -> list[str]:
    """Statements generated from the numbers, so the text cannot drift from the table."""
    lines = []
    mean = {k: {m: float(np.mean(v)) for m, v in r.items()} for k, r in results.items()}
    worse_ml = [k for k in sorted(mean) if mean[k]["ds_ml"] < mean[k]["majority"] - 0.01]
    if worse_ml:
        lines.append(f"- Plain maximum-likelihood Dawid-Skene did **worse** than majority vote with {', '.join(map(str, worse_ml))} observer(s) per site-week. With few labels per observer, EM overfits their confusion matrices. With single-label items the class prior can also collapse onto one class. This is why AquaSentinel uses MAP estimation with a default accuracy prior (0.7, 2 pseudo-observations) and a Dirichlet prior on the class distribution.")
    for k in sorted(mean):
        d = mean[k]["dawid_skene"] - mean[k]["majority"]
        c = mean[k]["ds_calibrated"] - mean[k]["majority"]
        lines.append(f"- {k} observer(s): Dawid-Skene with default prior {'+' if d >= 0 else ''}{d:.3f}, with calibration prior {'+' if c >= 0 else ''}{c:.3f} versus majority vote.")
    return lines


def write_report(results: dict[int, dict[str, list[float]]]) -> Path:
    REPORTS.mkdir(parents=True, exist_ok=True)
    sizes = sorted(results)
    fig, ax = plt.subplots(figsize=(7, 4.2))
    for key, (label, colour, marker) in METHODS.items():
        mean = [np.mean(results[k][key]) for k in sizes]
        sd = [np.std(results[k][key]) for k in sizes]
        ax.errorbar(sizes, mean, yerr=sd, label=label, color=colour, marker=marker, capsize=3, linewidth=2)
    ax.set_xlabel("Observers per site-week")
    ax.set_ylabel("Share of items with true class recovered")
    ax.set_title("SIMULATED observers: recovering the true class")
    ax.set_ylim(0.3, 1.0)
    ax.grid(alpha=0.3)
    ax.legend(loc="lower right", fontsize=8)
    fig.tight_layout()
    png = REPORTS / "calibration_sim.png"
    fig.savefig(png, dpi=150)

    rows = ["| Observers | " + " | ".join(v[0] for v in METHODS.values()) + " |", "|---" * (len(METHODS) + 1) + "|"]
    for k in sizes:
        rows.append(f"| {k} | " + " | ".join(f"{np.mean(results[k][m]):.3f} ± {np.std(results[k][m]):.3f}" for m in METHODS) + " |")
    md = REPORTS / "calibration.md"
    md.write_text("\n".join([
        "# Calibration simulation (SIMULATED DATA)",
        "",
        "**Every number on this page comes from simulated observers. No real volunteer data is used.**",
        "",
        "Generated by `python -m analysis.calibration_sim` (seed 2026, 30 repetitions, 120 items per repetition, pool of 40 observers).",
        "",
        "## Set-up",
        "",
        "- Three classes (absent, present, extensive), as on the OAH A/P/E scale. True class frequencies 40/35/25 %.",
        "- Observer pool: 30 % careful (accuracy 0.85 to 0.95), 40 % average (0.6 to 0.8), 30 % biased: they report *present* or *extensive* hard banks as *absent* 80 % of the time (the bias the calibration feedback targets).",
        "- Each observer also completes a simulated 15-item calibration round; its accuracy seeds the calibration prior (5 pseudo-observations).",
        "- For each panel size k, every item is labelled by k observers drawn at random from the pool.",
        "",
        "## Tuning disclosure",
        "",
        "The two prior settings used by AquaSentinel (default accuracy 0.7 with 2 pseudo-observations; class prior share 1/3) were chosen from a grid (strength 2, 5, 10 by class pseudo-counts 0, 10, 40 on 120 items) on a **separate** run with seed 7 and 8 repetitions. The table below is a fresh run with seed 2026. The maximum-likelihood column shows what happens without the priors.",
        "",
        "## Result",
        "",
        "![Simulated comparison](calibration_sim.png)",
        "",
        "Mean ± standard deviation across repetitions of the share of items whose true class was recovered:",
        "",
        *rows,
        "",
        "## Reading it",
        "",
        *reading(results),
        "",
        "## Limits",
        "",
        "- Simulated observers follow the model's own assumptions (independent errors given the true class). Real volunteers may copy each other, visit together, or drift over time.",
        "- Site states are held fixed within a week; real streams change after rain.",
        "- The biased group is a single, strong bias. Real biases will be weaker and more varied.",
        "",
    ]) + "\n", encoding="utf-8")
    return md


def main() -> None:
    path = write_report(run())
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
