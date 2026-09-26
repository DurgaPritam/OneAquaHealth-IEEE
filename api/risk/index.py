"""Combine factors into the index: seasonal suitability x site conditions.

Both parts are weighted means over the factors that have data. Missing site
factors widen the reported range instead of being treated as zero.
"""

from __future__ import annotations

from typing import Any

from api.risk import factors as f
from api.risk.config import band_for, load_config

SEASON = ("temperature", "dry_spell")
SITE = ("habitat", "vector_presence", "predator_deficit", "host_signal")


def _weighted(xs: list[f.Factor], weights: dict[str, float]) -> tuple[float | None, float, float, float]:
    """(mean over present, share of weight present, lower bound, upper bound) with missing in [0, 1]."""
    total_w = sum(weights[x.name] for x in xs)
    present = [x for x in xs if x.value is not None]
    pw = sum(weights[x.name] for x in present)
    known = sum(weights[x.name] * x.value for x in present)  # type: ignore[operator]
    mean = known / pw if pw else None
    return mean, pw / total_w, known / total_w, (known + total_w - pw) / total_w


def combine(factor_list: list[f.Factor], cfg: dict[str, Any]) -> dict[str, Any]:
    sw, tw = cfg["season_weights"], cfg["site_weights"]
    season_f = [x for x in factor_list if x.name in SEASON]
    site_f = [x for x in factor_list if x.name in SITE]
    season, _, season_lo, season_hi = _weighted(season_f, sw)
    site, coverage, site_lo, site_hi = _weighted(site_f, tw)

    gate = season if season is not None else 1.0  # no weather: assume the upper bound and say so
    total = round(gate * (site if site is not None else 0.0), 4)
    range_low = round((season_lo if season is not None else 0.0) * site_lo, 4)
    range_high = round((season_hi if season is not None else 1.0) * site_hi, 4)

    present_site = [x for x in site_f if x.value is not None]
    pw = sum(tw[x.name] for x in present_site)
    for x in season_f:
        x.weight = sw[x.name]
        x.contribution = 0.0  # weather scales the index; it does not add to it
    for x in site_f:
        x.weight = tw[x.name]
        x.contribution = round(gate * tw[x.name] * x.value / pw, 4) if (x.value is not None and pw) else 0.0

    needs_data = coverage < cfg["min_coverage"]
    band = band_for(total, cfg)
    dominant = max(present_site, key=lambda x: x.contribution).name if present_site else None
    parts = [f"{x.label} {x.value:.2f}" for x in sorted(present_site, key=lambda x: -x.contribution)]
    explanation = (f"Index {total:.2f} ({band.replace('_', ' ')}) = seasonal suitability "
                   f"{'n/a' if season is None else f'{season:.2f}'} x site conditions {'n/a' if site is None else f'{site:.2f}'}.")
    if parts:
        explanation += " Site factors: " + "; ".join(parts) + "."
    if season is None:
        explanation += " No weather data: seasonal suitability assumed 1 (upper bound)."
    missing = [x.label for x in site_f if x.value is None]
    if missing:
        explanation += f" No data for: {', '.join(missing)} (site data coverage {coverage:.0%}); the index could be {range_low:.2f} to {range_high:.2f}."
    if needs_data:
        explanation += " Too little site data to raise an alert: this site needs a stream check."
    return {
        "total": total,
        "band": band,
        "season": None if season is None else round(season, 4),
        "site": None if site is None else round(site, 4),
        "dominant": dominant,
        "coverage": round(coverage, 3),
        "range_low": range_low,
        "range_high": range_high,
        "needs_data": needs_data,
        "alert": total >= cfg["alert_threshold"] and not needs_data,
        "factors": [x.to_dict() for x in factor_list],
        "explanation": explanation,
        "config_version": cfg["fingerprint"],
    }


def score_site(inputs: dict[str, Any], cfg: dict[str, Any] | None = None) -> dict[str, Any]:
    """Score one site from prepared inputs (see api/risk/service.py for how they are built)."""
    cfg = cfg or load_config()
    factor_list = [
        f.temperature(inputs.get("weather", []), cfg),
        f.dry_spell(inputs.get("weather", []), cfg),
        f.habitat(inputs.get("habitat", {}), cfg),
        f.vector_presence(inputs.get("larval", []), cfg),
        f.predator_deficit(inputs.get("predators", []), cfg),
        f.host_signal(inputs.get("dead_birds"), cfg),
    ]
    ages = inputs.get("data_age", {})
    for x in factor_list:
        x.data_age_days = ages.get(x.name)
    return combine(factor_list, cfg)
