"""Build factor inputs from stored check-ins and weather, then score and store every site in a city.

Reliability: for each habitat question, Dawid-Skene runs across all sites of the
city in the window, seeded with each observer's calibration agreement. A site's
answer becomes the posterior expected A/P/E score. Counts (larvae, birds) are
weighted by each observer's estimated reliability.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from typing import Any

from sqlmodel import Session, select

from api import models as m
from api.reliability.dawid_skene import dawid_skene
from api.risk import weather as wx
from api.risk.config import load_config
from api.risk.factors import APE_SCORE
from api.risk.index import score_site

APE = ("absent", "present", "extensive")
DEFAULT_RELIABILITY = 0.7


def iso_week(d: date) -> str:
    y, w, _ = d.isocalendar()
    return f"{y}-W{w:02d}"


def _window(as_of: date, days: int) -> tuple[datetime, datetime]:
    start = datetime.combine(as_of - timedelta(days=days - 1), time.min, tzinfo=timezone.utc)
    end = datetime.combine(as_of, time.max, tzinfo=timezone.utc)
    return start, end


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def prior_accuracy(observers: list[m.Observer]) -> dict[str, dict[str, float]]:
    """Per observer and question, the calibration agreement (falls back to the observer's mean)."""
    out: dict[str, dict[str, float]] = {}
    for o in observers:
        per_q = (o.calibration or {}).get("per_question", {})
        if not per_q:
            continue
        mean = sum(v["agreement"] for v in per_q.values()) / len(per_q)
        out[o.id] = {"_mean": mean, **{q: v["agreement"] for q, v in per_q.items()}}
    return out


def habitat_posteriors(checkins: list[m.CheckIn], questions: list[str], priors: dict[str, dict[str, float]]) -> tuple[dict[str, dict[str, dict[str, Any]]], dict[str, float]]:
    """Per site and question: expected score, class posterior and the check-ins used. Also observer reliability."""
    per_site: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    rel_sum: dict[str, float] = defaultdict(float)
    rel_n: dict[str, int] = defaultdict(int)
    for q in questions:
        labels = [(c.site_id, c.observer_id, c.answers[q]) for c in checkins if c.answers.get(q) in APE]
        if not labels:
            continue
        prior = {o: p.get(q, p["_mean"]) for o, p in priors.items()}
        res = dawid_skene(labels, classes=APE, prior_accuracy=prior, prior_strength=5)
        for o, r in res.reliability().items():
            rel_sum[o] += r
            rel_n[o] += 1
        for site in res.items:
            post = res.posterior[res.items.index(site)]
            used = [c for c in checkins if c.site_id == site and c.answers.get(q) in APE]
            per_site[site][q] = {
                "expected": round(float(sum(p * APE_SCORE[k] for p, k in zip(post, APE))), 4),
                "posterior": {k: round(float(p), 4) for k, p in zip(APE, post)},
                "n_reports": len(used),
                "raw": [{"checkin_id": c.id, "observer": c.observer_id, "answer": c.answers[q]} for c in used],
            }
    reliability = {o: rel_sum[o] / rel_n[o] for o in rel_sum}
    return per_site, reliability


def site_inputs(site: m.Site, checkins: list[m.CheckIn], findings: dict[int, list[m.Finding]], habitat: dict[str, dict[str, Any]],
                reliability: dict[str, float], weather: list[dict[str, Any]], as_of: date) -> dict[str, Any]:
    mine = [c for c in checkins if c.site_id == site.id]
    larval, predators, dead = [], [], []
    for c in mine:
        w = round(reliability.get(c.observer_id, DEFAULT_RELIABILITY), 4)
        fs = findings.get(c.id, [])
        by_subject = {f.subject: f for f in fs}
        dips = by_subject.get("larval_dips")
        if dips and dips.count is not None:
            n_dips = len(dips.data.get("dips", [])) or 5
            larval.append({"checkin_id": c.id, "observer": c.observer_id, "per_dip": round(dips.count / n_dips, 3), "weight": w})
        amph = by_subject.get("amphibians")
        birds = by_subject.get("insectivorous_birds")
        bats = by_subject.get("bats")
        if amph or birds or bats:
            predators.append({
                "checkin_id": c.id, "observer": c.observer_id, "weight": w,
                "amphibians": amph.citizen_answer if amph else None,
                "birds": birds.count if birds else None,
                "bats": bats.citizen_answer if bats else None,
            })
        for f in fs:
            if f.type == m.FindingType.dead_bird and f.count:
                dead.append({"checkin_id": c.id, "count": f.count, "date": _aware(c.observed_at).date().isoformat()})
    latest = max((_aware(c.observed_at).date() for c in mine), default=None)
    age = (as_of - latest).days if latest else None
    weather_age = (as_of - date.fromisoformat(weather[-1]["date"])).days if weather else None
    return {
        "weather": weather,
        "habitat": habitat,
        "larval": larval,
        "predators": predators,
        "dead_birds": dead if mine else None,
        "data_age": {"temperature": weather_age, "dry_spell": weather_age, "habitat": age, "vector_presence": age,
                     "predator_deficit": age, "host_signal": age},
        "checkin_ids": [c.id for c in mine],
    }


def compute_city(session: Session, city_id: str, as_of: date, fetch: wx.Fetch | None = None, store: bool = True) -> list[dict[str, Any]]:
    cfg = load_config()
    days = cfg["window_days"]
    start, end = _window(as_of, days)
    sites = session.exec(select(m.Site).where(m.Site.city_id == city_id)).all()
    site_ids = [s.id for s in sites]
    checkins = [c for c in session.exec(select(m.CheckIn).where(m.CheckIn.site_id.in_(site_ids))).all()  # type: ignore[attr-defined]
                if start <= _aware(c.observed_at) <= end]
    findings: dict[int, list[m.Finding]] = defaultdict(list)
    if checkins:
        for f in session.exec(select(m.Finding).where(m.Finding.checkin_id.in_([c.id for c in checkins]))).all():  # type: ignore[attr-defined]
            findings[f.checkin_id].append(f)
    observers = session.exec(select(m.Observer).where(m.Observer.id.in_({c.observer_id for c in checkins}))).all() if checkins else []  # type: ignore[attr-defined]
    habitat, reliability = habitat_posteriors(checkins, list(cfg["habitat"]["questions"]), prior_accuracy(list(observers)))
    kwargs = {"fetch": fetch} if fetch else {}

    out = []
    for site in sites:
        try:
            weather = wx.window(site.lat, site.lon, as_of, days, **kwargs)
        except Exception:  # network down: weather factors become "no data", never zero
            weather = []
        inputs = site_inputs(site, checkins, findings, habitat.get(site.id, {}), reliability, weather, as_of)
        result = score_site(inputs, cfg)
        synthetic = any(c.synthetic for c in checkins if c.site_id == site.id)
        row = {"site_id": site.id, "week": iso_week(as_of), "as_of": as_of.isoformat(), **result,
               "checkin_ids": inputs["checkin_ids"], "synthetic": synthetic,
               "observer_reliability": {o: round(r, 3) for o, r in reliability.items() if any(c.observer_id == o and c.site_id == site.id for c in checkins)}}
        if store:
            _upsert(session, row)
        out.append(row)
    if store:
        session.commit()
    return out


def _upsert(session: Session, row: dict[str, Any]) -> None:
    existing = session.exec(select(m.RiskScore).where(m.RiskScore.site_id == row["site_id"], m.RiskScore.week == row["week"])).first()
    rs = existing or m.RiskScore(site_id=row["site_id"], week=row["week"], total=0, band="", explanation="", config_version="")
    rs.total, rs.band, rs.explanation, rs.config_version = row["total"], row["band"], row["explanation"], row["config_version"]
    rs.factors = row["factors"]
    rs.dominant, rs.coverage, rs.as_of = row["dominant"], row["coverage"], row["as_of"]
    rs.range_low, rs.range_high, rs.needs_data, rs.alert = row["range_low"], row["range_high"], row["needs_data"], row["alert"]
    rs.checkin_ids = row["checkin_ids"]
    rs.synthetic = row["synthetic"]
    session.add(rs)
    session.flush()
    row["id"] = rs.id
