"""Backtest of seasonal suitability against ECDC West Nile virus first-case dates.

Runs exactly the plan pre-registered in analysis/BACKTEST_PLAN.md (commit a6b76a7):
weekly seasonal suitability from the production risk code and Open-Meteo archive
weather, compared with the first locally acquired human case per NUTS 3 region.
Nothing here is tuned; every rule is taken from the plan.

Usage: .venv/bin/python -m analysis.backtest
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import time
import unicodedata
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy.stats import mannwhitneyu  # noqa: E402

from api.risk import weather  # noqa: E402
from api.risk.config import load_config  # noqa: E402
from api.risk.index import score_site  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "eval" / "reports"
REGIONS_FILE = ROOT / "data" / "ecdc" / "backtest_regions.json"
PLAN_COMMIT = "a6b76a7"
REPO = "https://github.com/DurgaPritam/OneAquaHealth-IEEE"
PRIMARY_THETA = 0.50
SECONDARY_THETAS = (0.30, 0.70)
SEASONS = (2018, 2019, 2020, 2021, 2023)
PRIMARY_SEASONS = (2018, 2019, 2021, 2023)
EXCEL_EPOCH = date(1899, 12, 30)

# Pre-registered hashes (analysis/BACKTEST_PLAN.md section 2).
EXPECTED_HASHES = {
    "config/risk.yaml": "7258cf66619ccfd0122c5b23731fe0dade431c2c1069c36c02c7c418c8fa54b2",
    "api/risk/factors.py": "3fdc304d1a3b98f9b015bb97645cac2902fc932ce1ba47b0cc1d8367ad888681",
    "api/risk/index.py": "e2f06cd0af3ebf94468c1fc29e5425b34690a46f4d3fb9f2576caeece3a7dfd4",
    "data/ecdc/wnv_2018.xlsx": "3e88053d21e8d6a2bf59b8c77a979a1282ca5b0a62724e6c9573dc141d65101c",
    "data/ecdc/wnv_2019.xlsx": "c14c59418ab12a6b5d12a77f01c5da8e749b9cc919fda2efc4b77ee72a964181",
    "data/ecdc/wnv_2020.xlsx": "c86bf58f8c5f3408554a4f77be6030a874b39255f0c8a8bfb5cafb52a5b60808",
    "data/ecdc/wnv_2021.xlsx": "ec67b3eb4353c944307b07b4be3b8a2f6f9dbcf62d91e3531aff18ed7d36228b",
    "data/ecdc/wnv_2023.xlsx": "706b3d9a7f3735a0fdd2580b901423b95861d6f2d939638805857cb5f6e11ad6",
}

Week = tuple[date, float | None]


# ------------------------------------------------------------------ pure pieces (tested without network)


def parse_case_date(value: Any) -> date | None:
    """ECDC first-case cell to a date. Handles Excel serial numbers (2018 file), timestamps, ISO strings and blanks."""
    if value is None or value is pd.NaT:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float, np.integer, np.floating)):
        if isinstance(value, float) and math.isnan(value):
            return None
        return EXCEL_EPOCH + timedelta(days=int(value))
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, pd.Timestamp):
        return None if pd.isna(value) else value.date()
    text = str(value).strip()
    if not text or text.lower() in ("nan", "nat", "none"):
        return None
    return date.fromisoformat(text[:10])


def norm_name(name: str) -> str:
    """Region name for matching across files: accents and curly apostrophes removed, lower case."""
    return unicodedata.normalize("NFKD", str(name).replace("’", "'")).encode("ascii", "ignore").decode().lower().strip()


def evaluation_sundays(season: int) -> list[date]:
    """Every Sunday from the first on or after 1 April to the last on or before 30 November."""
    d = date(season, 4, 1)
    d += timedelta(days=(6 - d.weekday()) % 7)
    out = []
    while d <= date(season, 11, 30):
        out.append(d)
        d += timedelta(days=7)
    return out


@dataclass
class Crossing:
    crossing: date | None  # first of the two consecutive weeks
    signal: date | None  # the Sunday that completes the second week
    left_censored: bool = False


def signal_date(weeks: Sequence[Week], theta: float) -> Crossing:
    """First week W with S(W) >= theta and S(W + 7 days) >= theta. A missing value breaks the run."""
    for (d0, s0), (d1, s1) in zip(weeks, weeks[1:]):
        if s0 is None or s1 is None or (d1 - d0).days != 7:
            continue
        if s0 >= theta and s1 >= theta:
            return Crossing(d0, d1, left_censored=d0 == weeks[0][0])
    return Crossing(None, None)


def lead_weeks(case: date, signal: date | None) -> float | None:
    """Weeks from the signal date to the first case, one decimal. Positive means the signal came first."""
    if signal is None:
        return None
    return round((case - signal).days / 7, 1)


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score 95% interval for a proportion k / n."""
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (max(0.0, centre - half), min(1.0, centre + half))


def weeks_at_or_above(weeks: Sequence[Week], theta: float) -> int:
    return sum(1 for _, s in weeks if s is not None and s >= theta)


def season_max(weeks: Sequence[Week]) -> float | None:
    vals = [s for _, s in weeks if s is not None]
    return max(vals) if vals else None


def weekly_suitability(daily: list[dict[str, Any]], sundays: Sequence[date], cfg: dict[str, Any]) -> list[Week]:
    """Seasonal suitability for each Sunday from the 14-day window ending on it, via the production index."""
    by_day = {r["date"]: r for r in daily}
    n = cfg["window_days"]
    out: list[Week] = []
    for sunday in sundays:
        rows = [by_day[d.isoformat()] for d in (sunday - timedelta(days=i) for i in range(n - 1, -1, -1)) if d.isoformat() in by_day]
        s = score_site({"weather": rows}, cfg)["season"] if rows else None
        out.append((sunday, s))
    return out


# ------------------------------------------------------------------ inputs


def check_hashes() -> list[tuple[str, str, str, bool]]:
    out = []
    for rel, expected in EXPECTED_HASHES.items():
        actual = hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()
        out.append((rel, expected, actual, actual == expected))
    return out


def load_ecdc(season: int) -> dict[tuple[str, str], date | None]:
    """(country code, normalised region name) to first human case date, re-read from the cached file."""
    countries = {"Portugal": "PT", "France": "FR", "Italy": "IT", "Belgium": "BE", "Norway": "NO"}
    df = pd.read_excel(ROOT / "data" / "ecdc" / f"wnv_{season}.xlsx", header=0)
    out: dict[tuple[str, str], date | None] = {}
    if season <= 2020:
        country = df.iloc[:, 0].ffill()
        for c, name, first in zip(country, df.iloc[:, 1], df.iloc[:, 2]):
            if isinstance(name, str) and c in countries:
                out[(countries[c], norm_name(name))] = parse_case_date(first)
    else:
        for code, name, first in zip(df.iloc[:, 0], df.iloc[:, 1], df.iloc[:, 2]):
            if isinstance(code, str) and code[:2] in countries.values():
                out[(code[:2], norm_name(name))] = parse_case_date(first)
    return out


def _fetch_with_retry(url: str, params: dict[str, Any]) -> dict[str, Any]:
    for attempt in range(5):
        try:
            data = weather._http(url, params)
            time.sleep(0.3)
            return data
        except Exception:  # noqa: BLE001 - rate limits and timeouts: back off and retry
            if attempt == 4:
                raise
            time.sleep(5 * (attempt + 1))
    raise RuntimeError("unreachable")


def season_weather(lat: float, lon: float, season: int, fetch: Callable[..., dict[str, Any]] = _fetch_with_retry) -> list[dict[str, Any]]:
    return weather.daily(lat, lon, date(season, 3, 15), date(season, 11, 30), fetch=fetch, cache_dir=ROOT / "var" / "weather")


# ------------------------------------------------------------------ run


@dataclass
class RegionSeason:
    role: str
    name: str
    nuts3: str | None
    country: str
    season: int
    case: date | None
    primary: bool
    lat: float
    lon: float
    weeks: list[Week] = field(default_factory=list)

    def crossing(self, theta: float) -> Crossing:
        return signal_date(self.weeks, theta)

    def lead(self, theta: float) -> float | None:
        return None if self.case is None else lead_weeks(self.case, self.crossing(theta).signal)


def build_region_seasons() -> tuple[list[RegionSeason], list[str]]:
    doc = json.loads(REGIONS_FILE.read_text(encoding="utf-8"))
    ecdc = {s: load_ecdc(s) for s in SEASONS}
    mismatches: list[str] = []
    out: list[RegionSeason] = []
    for reg in doc["regions"]:
        for s in reg["seasons"]:
            case = parse_case_date(s["first_human_case"])
            if reg["role"] == "positive":
                again = ecdc[s["season"]].get((reg["country"], norm_name(reg["name"])))
                if again != case:
                    mismatches.append(f"{reg['name']} {s['season']}: list {case}, file {again}")
            out.append(RegionSeason(reg["role"], reg["name"], reg["nuts3"], reg["country"], s["season"], case, s["primary"], reg["lat"], reg["lon"]))
    return out, mismatches


def compute(rs: list[RegionSeason]) -> None:
    cfg = load_config()
    for i, r in enumerate(rs, 1):
        daily = season_weather(r.lat, r.lon, r.season)
        r.weeks = weekly_suitability(daily, evaluation_sundays(r.season), cfg)
        if i % 20 == 0:
            print(f"  weather and index: {i}/{len(rs)}")


# ------------------------------------------------------------------ summaries


def _fmt(x: float | None, nd: int = 1) -> str:
    return "n/a" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{x:.{nd}f}"


def summarise(group: list[RegionSeason], theta: float, case_override: Callable[[RegionSeason], date] | None = None) -> dict[str, Any]:
    leads, before, left = [], 0, 0
    for r in group:
        case = case_override(r) if case_override else r.case
        c = r.crossing(theta)
        lw = lead_weeks(case, c.signal) if case else None
        if lw is not None:
            leads.append(lw)
            if c.signal < case:  # strictly before, as pre-registered
                before += 1
        left += c.left_censored
    n = len(group)
    lo, hi = wilson(before, n)
    arr = np.array(leads) if leads else None
    return {
        "n": n, "crossed": len(leads), "misses": n - len(leads), "left_censored": left,
        "median": None if arr is None else float(np.median(arr)),
        "q1": None if arr is None else float(np.percentile(arr, 25)),
        "q3": None if arr is None else float(np.percentile(arr, 75)),
        "min": None if arr is None else float(arr.min()), "max": None if arr is None else float(arr.max()),
        "before": before, "share": before / n if n else float("nan"), "lo": lo, "hi": hi,
    }


def summary_row(label: str, s: dict[str, Any]) -> str:
    return (f"| {label} | {s['n']} | {s['crossed']} | {s['misses']} | {_fmt(s['median'])} ({_fmt(s['q1'])} to {_fmt(s['q3'])}) | "
            f"{_fmt(s['min'])} to {_fmt(s['max'])} | {s['before']}/{s['n']} = {s['share']:.0%} ({s['lo']:.0%} to {s['hi']:.0%}) |")


SUMMARY_HEAD = ("| Group | n | Crossed | Misses | Median lead, weeks (IQR) | Range, weeks | Signal before case (Wilson 95%) |\n"
                "|---|---|---|---|---|---|---|")


def summary_table(pos: list[RegionSeason], theta: float) -> list[str]:
    lines = [SUMMARY_HEAD, summary_row("All", summarise(pos, theta))]
    for s in PRIMARY_SEASONS:
        g = [r for r in pos if r.season == s]
        lines.append(summary_row(str(s), summarise(g, theta)))
    for c in ("FR", "IT"):
        g = [r for r in pos if r.country == c]
        lines.append(summary_row({"FR": "France", "IT": "Italy"}[c], summarise(g, theta)))
    return lines


def contrast(pos: list[RegionSeason], neg: list[RegionSeason], theta: float) -> list[str]:
    lines = ["| Measure | Positives median (IQR), n | Negative controls median (IQR), n | Mann-Whitney U | p (two-sided) |", "|---|---|---|---|---|"]
    for label, fn in (("Weeks at or above 0.50", lambda r: weeks_at_or_above(r.weeks, theta)), ("Seasonal maximum of S", lambda r: season_max(r.weeks))):
        a = [fn(r) for r in pos if fn(r) is not None]
        b = [fn(r) for r in neg if fn(r) is not None]
        u, p = mannwhitneyu(a, b, alternative="two-sided")
        nd = 0 if label.startswith("Weeks") else 2
        q = lambda x: f"{_fmt(float(np.median(x)), nd)} ({_fmt(float(np.percentile(x, 25)), nd)} to {_fmt(float(np.percentile(x, 75)), nd)}), {len(x)}"  # noqa: E731
        lines.append(f"| {label} | {q(a)} | {q(b)} | {u:.0f} | {p:.3g} |")
    return lines


# ------------------------------------------------------------------ figures

BLUE, ORANGE = "#2a78d6", "#eb6834"
NEG_COLOURS = ["#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#4a3aa7"]
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e4e3df"


def _style(ax: Any) -> None:
    ax.grid(color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(MUTED)
    ax.tick_params(colors=MUTED, labelsize=9)


def figure_leadtime(pos: list[RegionSeason], path: Path) -> None:
    rng = np.random.default_rng(0)
    rows = [str(s) for s in PRIMARY_SEASONS] + ["No crossing"]
    fig, ax = plt.subplots(figsize=(8, 4.2))
    for country, colour, marker, label in (("IT", BLUE, "o", "Italy"), ("FR", ORANGE, "s", "France")):
        xs, ys, mx = [], [], []
        for r in pos:
            if r.country != country:
                continue
            lw = r.lead(PRIMARY_THETA)
            if lw is None:
                mx.append(rows.index("No crossing"))
            else:
                xs.append(lw)
                ys.append(rows.index(str(r.season)) + rng.uniform(-0.22, 0.22))
        ax.scatter(xs, ys, s=36, color=colour, marker=marker, alpha=0.8, edgecolors="white", linewidths=0.8, label=f"{label} (n={sum(r.country == country for r in pos)})")
        if mx:
            ax.scatter([0] * len(mx), [m + rng.uniform(-0.22, 0.22) for m in mx], s=36, color=colour, marker=marker, alpha=0.8, edgecolors="white", linewidths=0.8)
    ax.axvline(0, color=INK, linewidth=1.2)
    if not any(r.lead(PRIMARY_THETA) is None for r in pos):
        ax.text(0.3, rows.index("No crossing"), "none: every positive region-season crossed", color=MUTED, fontsize=8, va="center")
    ax.set_yticks(range(len(rows)), rows)
    ax.set_ylim(len(rows) - 0.4, -0.5)
    ax.set_xlabel("Lead time: weeks from signal date to first human case (positive = signal first)", color=INK, fontsize=9)
    ax.set_title("Lead time of the weather-only signal (S ≥ 0.50 for two weeks) before the first human WNV case,\n"
                 "119 positive region-seasons, ECDC 2018, 2019, 2021, 2023", fontsize=10, color=INK, loc="left")
    _style(ax)
    ax.legend(loc="lower right", fontsize=8, frameon=False)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def _doy_x(d: date) -> float:
    return (date(2001, d.month, d.day) - date(2001, 1, 1)).days


def figure_trajectories(rs: list[RegionSeason], path: Path) -> None:
    fig, axes = plt.subplots(len(SEASONS), 1, figsize=(8, 11), sharex=True)
    month_ticks = [date(2001, m, 1) for m in range(4, 13)]
    for ax, season in zip(axes, SEASONS):
        pos = [r for r in rs if r.role == "positive" and r.season == season]
        neg = [r for r in rs if r.role == "negative_control" and r.season == season]
        sundays = evaluation_sundays(season)
        x = [_doy_x(d) for d in sundays]
        if pos:
            mat = np.array([[np.nan if s is None else s for _, s in r.weeks] for r in pos], dtype=float)
            ax.fill_between(x, np.nanpercentile(mat, 25, axis=0), np.nanpercentile(mat, 75, axis=0), color=BLUE, alpha=0.18, linewidth=0)
            ax.plot(x, np.nanmedian(mat, axis=0), color=BLUE, linewidth=2, label="Positive regions: median, with IQR band")
            if season != 2020:
                for r in pos:
                    ax.plot([_doy_x(r.case)] * 2, [-0.06, -0.01], color=BLUE, linewidth=1)
        for r, colour in zip(sorted(neg, key=lambda r: r.name), NEG_COLOURS):
            vals = [np.nan if s is None else s for _, s in r.weeks]
            ax.plot(x, vals, color=colour, linewidth=2, label=f"{r.name} ({r.nuts3})")
        ax.axhline(PRIMARY_THETA, color=INK, linewidth=1, linestyle="--")
        ax.set_ylim(-0.08, 1.02)
        ax.set_ylabel("S", color=INK, fontsize=9)
        note = (f", {len(pos)} positive regions (case dates not plotted: year inconsistent in file)" if season == 2020
                else f", {len(pos)} positive regions (ticks at bottom: first human case dates)")
        ax.set_title(f"{season}{note}", fontsize=9, color=INK, loc="left")
        _style(ax)
    axes[-1].set_xticks([_doy_x(d) for d in month_ticks], [d.strftime("%b") for d in month_ticks])
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=2, fontsize=8, frameon=False)
    fig.suptitle("Weekly seasonal suitability S (weather only, 14-day window), positive regions versus the five OAH\n"
                 "research-city regions (negative controls). Dashed line: pre-registered threshold 0.50", fontsize=10, color=INK, x=0.02, ha="left")
    fig.tight_layout(rect=(0, 0.05, 1, 0.97))
    fig.savefig(path, dpi=150)
    plt.close(fig)


# ------------------------------------------------------------------ report


def write_weekly_csv(rs: list[RegionSeason], path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["role", "region", "nuts3", "country", "season", "primary", "first_human_case", "week_ending", "iso_week", "seasonal_suitability"])
        for r in rs:
            for d, s in r.weeks:
                iso = d.isocalendar()
                w.writerow([r.role, r.name, r.nuts3 or "", r.country, r.season, r.primary, r.case or "", d.isoformat(),
                            f"{iso[0]}-W{iso[1]:02d}", "" if s is None else s])


def write_report(rs: list[RegionSeason], hashes: list[tuple[str, str, str, bool]], mismatches: list[str]) -> Path:
    pos = [r for r in rs if r.role == "positive" and r.primary]
    pos2020 = [r for r in rs if r.role == "positive" and not r.primary]
    neg = [r for r in rs if r.role == "negative_control"]
    missing_weeks = sum(1 for r in rs for _, s in r.weeks if s is None)
    total_weeks = sum(len(r.weeks) for r in rs)
    prim = summarise(pos, PRIMARY_THETA)
    neg_crossed = [r for r in neg if r.crossing(PRIMARY_THETA).signal]

    deviations = [
        "- **Call path for S.** The plan said `api.risk.index.combine` would be called with the two weather factors only. "
        "`combine` divides by the total site weight, which is zero when no site factor is passed, so the script calls the production "
        "`api.risk.index.score_site` with weather only; the four site factors are then present with no data (value None), exactly as for a "
        "live site with no citizen data. S is the `season` value it returns (rounded to 4 decimals by the production code). This changes "
        "no weight, threshold or formula and cannot change S.",
    ]
    bad = [h for h in hashes if not h[3]]
    for rel, exp, act, _ in bad:
        deviations.append(f"- **Hash mismatch** for `{rel}`: expected `{exp[:16]}...`, found `{act[:16]}...`.")
    if mismatches:
        deviations.append("- **Case dates in the region list differ from a re-read of the ECDC files**: " + "; ".join(mismatches))

    L: list[str] = []
    L += ["# Backtest: weather-only seasonal suitability against ECDC West Nile virus first-case dates", "",
          f"Pre-registered plan: [analysis/BACKTEST_PLAN.md]({REPO}/blob/{PLAN_COMMIT}/analysis/BACKTEST_PLAN.md), committed in "
          f"[{PLAN_COMMIT}]({REPO}/commit/{PLAN_COMMIT}) before any weather was fetched or any index value computed. "
          "Generated by `analysis/backtest.py` (`npm run eval`). Real data; nothing here is synthetic.", "",
          "## Limits (read first)", "",
          "1. **First-case date only.** ECDC gives one first human case date per region-season, not weekly incidence (OQ-6). The column is "
          "\"First human case reported\"; the files do not say whether it is onset, diagnosis or notification, so lead times may include an unknown reporting delay.",
          "2. **One point per region.** Each NUTS 3 region is represented by Open-Meteo reanalysis weather at its administrative seat. Several seats are coastal.",
          "3. **Weather only.** No historical citizen data exist, so this tests only the seasonal gate of the index, not the site conditions that are meant to say *where* risk is.",
          "4. **Thresholds from another species.** 14.3 °C and 109 degree-days come from *Culex tarsalis*; European transmission is mainly by *Culex pipiens* (OQ-9).",
          "5. **Missing and faulty seasons.** 2022, 2024 and 2025 are not available (OQ-5). All 2020 first-case dates are in 2021 in the file (OQ-12), so 2020 positives are only in a labelled sensitivity check.",
          f"6. **Unbalanced positives.** {sum(r.country == 'IT' for r in pos)} of {len(pos)} primary positive region-seasons are Italian, mostly in the Po valley. Portugal, Belgium and Norway have no positive region.",
          "7. **Negative controls are not proven negatives**, and 25 region-seasons from five regions give an imprecise specificity estimate.",
          "8. **Name matching for 2018 to 2020**; four regions have no NUTS code in the cached files.",
          "9. **Not disease prediction.** Nothing here describes infection status of any place, bird or person. S describes weather that favours vectors.",
          "10. **Region-seasons are not independent** (neighbouring provinces share weather and outbreaks), so the Mann-Whitney p-values are descriptive.", "",
          "## Input hashes and deviations", "",
          "| File | Pre-registered SHA-256 | Matches |", "|---|---|---|"]
    L += [f"| `{rel}` | `{exp[:16]}...` | {'yes' if ok else '**no**'} |" for rel, exp, _, ok in hashes]
    L += ["", "### Deviations from the pre-registered plan", ""] + deviations + [""]
    L += ["## Data", "",
          f"- Positive region-seasons analysed: {len(pos)} primary (2018 to 2023 without 2020) and {len(pos2020)} in the 2020 sensitivity check; "
          f"negative-control region-seasons: {len(neg)} (five OAH research-city regions, 2018, 2019, 2020, 2021, 2023).",
          f"- Weekly values: {total_weeks}; weeks with no weather value: {missing_weeks}.",
          f"- Case dates re-read from the ECDC files and compared with `data/ecdc/backtest_regions.json`: {len(mismatches)} mismatches.",
          "- Dataset provided by ECDC based on data provided by public health authorities, scientific institutes or health care providers in the "
          "relevant reporting countries and/or by WHO. Weather data by Open-Meteo.com (CC BY 4.0). Region points: Open-Meteo geocoding (GeoNames).", "",
          "## Headline", "",
          f"- At the pre-registered threshold 0.50, {prim['crossed']} of {prim['n']} positive region-seasons produced a signal; "
          f"{prim['before']} ({prim['share']:.0%}, Wilson 95% {prim['lo']:.0%} to {prim['hi']:.0%}) had it strictly before the first human case. "
          f"Median lead time {_fmt(prim['median'])} weeks (IQR {_fmt(prim['q1'])} to {_fmt(prim['q3'])}).",
          f"- **Negative controls crossed the same threshold in {len(neg_crossed)} of {len(neg)} region-seasons.** "
          + ("S therefore has little or no specificity for where transmission happens; it behaves as a seasonal gate, as the plan expected."
             if len(neg_crossed) >= len(neg) / 2 else "S separated positives from most negative controls at this threshold."),
          "", "## Table 1. Primary result, threshold 0.50", "",
          "Signal date: the Sunday completing the second consecutive week with S ≥ 0.50. Lead time = first case date minus signal date. "
          "\"Signal before case\" counts misses and late signals as failures.", ""]
    L += summary_table(pos, PRIMARY_THETA)
    L += ["", f"Left-censored (already at or above 0.50 in the first April week): {prim['left_censored']}.", "",
          "## Table 2. Negative controls, threshold 0.50", "",
          "| Region | NUTS 3 | Season | Crossed | Signal date | Weeks at or above 0.50 | Seasonal maximum of S |", "|---|---|---|---|---|---|---|"]
    for r in sorted(neg, key=lambda r: (r.name, r.season)):
        c = r.crossing(PRIMARY_THETA)
        L.append(f"| {r.name} | {r.nuts3} | {r.season} | {'yes' if c.signal else 'no'} | {c.signal or 'n/a'} | "
                 f"{weeks_at_or_above(r.weeks, PRIMARY_THETA)} | {_fmt(season_max(r.weeks), 2)} |")
    lo, hi = wilson(len(neg_crossed), len(neg))
    L += ["", f"Negative-control region-seasons that crossed: {len(neg_crossed)}/{len(neg)} = {len(neg_crossed) / len(neg):.0%} (Wilson 95% {lo:.0%} to {hi:.0%}).", "",
          "## Table 3. Contrast, positives versus negative controls (threshold 0.50)", ""]
    L += contrast(pos, neg, PRIMARY_THETA)
    L += ["", "## Table 4. Secondary thresholds", ""]
    for theta in SECONDARY_THETAS:
        nc = sum(1 for r in neg if r.crossing(theta).signal)
        L += [f"### Threshold {theta:.2f}", ""] + summary_table(pos, theta)
        L += ["", f"Negative controls crossing: {nc}/{len(neg)}. Left-censored positives: {summarise(pos, theta)['left_censored']}.", ""]
    s20 = summarise(pos2020, PRIMARY_THETA, case_override=lambda r: date(2020, r.case.month, r.case.day))
    L += ["## Table 5. 2020 sensitivity check (2020 dates assumed, not verified)", "",
          "Case year set to 2020, month and day kept, threshold 0.50. Not part of the primary result.", "",
          SUMMARY_HEAD, summary_row("Italy 2020", s20), "",
          "## Figures", "",
          "![Lead time per positive region-season](backtest_leadtime.png)", "",
          "![Weekly seasonal suitability by season](backtest_trajectories.png)", "",
          "Per-week values for every region-season: [backtest_weekly.csv](backtest_weekly.csv).", "",
          "## What this shows and what it does not", ""]
    L += interpretation(prim, neg, len(neg_crossed), len(neg))
    L += ["", "## Appendix. Every primary positive region-season, threshold 0.50", "",
          "| Region | NUTS 3 | Season | First human case | Signal date | Lead, weeks |", "|---|---|---|---|---|---|"]
    for r in sorted(pos, key=lambda r: (r.season, r.country, r.name)):
        c = r.crossing(PRIMARY_THETA)
        L.append(f"| {r.name} | {r.nuts3 or 'n/a'} | {r.season} | {r.case} | {c.signal or 'no crossing'} | {_fmt(r.lead(PRIMARY_THETA))} |")
    path = REPORTS / "backtest.md"
    path.write_text("\n".join(L) + "\n", encoding="utf-8")
    return path


def interpretation(prim: dict[str, Any], neg: list[RegionSeason], neg_crossed: int, n_neg: int) -> list[str]:
    out = []
    useful = prim["median"] is not None and prim["median"] > 0 and prim["share"] >= 0.5
    if useful:
        out.append(f"- Pre-stated lead-time criterion met: median lead {_fmt(prim['median'])} weeks > 0 and {prim['share']:.0%} of positives signalled before the case.")
    else:
        out.append("- Pre-stated test of usefulness **failed**: the weather gate gives no useful lead time at threshold 0.50 (median lead not above zero, or fewer than half signalled before the case).")
    if neg_crossed >= n_neg / 2:
        out.append(f"- The weather gate is **not specific**: {neg_crossed} of {n_neg} negative-control region-seasons also crossed. A positive lead time here mostly reflects that summer arrives before cases do, not that S picks out places with transmission.")
    else:
        out.append(f"- {neg_crossed} of {n_neg} negative-control region-seasons crossed.")
    south = [weeks_at_or_above(r.weeks, PRIMARY_THETA) for r in neg if r.country in ("PT", "FR", "IT")]
    north = [weeks_at_or_above(r.weeks, PRIMARY_THETA) for r in neg if r.country in ("BE", "NO")]
    out.append(f"- Post hoc reading of Table 3 (not pre-registered): the difference in weeks at or above 0.50 comes from the two northern controls. "
               f"Coimbra, Toulouse and Benevento had a median of {np.median(south):.0f} weeks, similar to the positives; Ghent and Oslo had {np.median(north):.0f}. "
               "The contrast is consistent with the climate of the regions compared rather than with a transmission signal.")
    out.append("- This supports using S only as a multiplier (\"is the season suitable?\") and never alerting on weather alone, which is how the index is built (min_coverage in config/risk.yaml). "
               "It does not test the site factors, which need citizen data that do not exist for past seasons.")
    return out


def main() -> None:
    REPORTS.mkdir(parents=True, exist_ok=True)
    hashes = check_hashes()
    for rel, _, _, ok in hashes:
        if not ok:
            print(f"DEVIATION: hash mismatch for {rel}")
    rs, mismatches = build_region_seasons()
    print(f"backtest: {len(rs)} region-seasons")
    compute(rs)
    write_weekly_csv(rs, REPORTS / "backtest_weekly.csv")
    figure_leadtime([r for r in rs if r.role == "positive" and r.primary], REPORTS / "backtest_leadtime.png")
    figure_trajectories(rs, REPORTS / "backtest_trajectories.png")
    print(f"wrote {write_report(rs, hashes, mismatches)}")


if __name__ == "__main__":
    main()
