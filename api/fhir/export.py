"""Read rows from the database and export them as FHIR R4 transaction Bundles.

lifecycle_bundle: one check-in -> Location, Practitioner, Observations for its
answered findings and stream-check answers, and a Provenance with the observer's
reliability.

city_week_bundle: one city and ISO week -> Organization, risk engine Device,
Locations, a risk index Observation per site, the MeasureReport, ServiceRequests
for approved Actions and Communications for volunteer Messages.

Promotion rule (documented in fhir/README.md): a citizen finding is exported as
final under the OAH indicator profile only when the citizen has answered it, it
is not flagged for expert review, it has an OAH indicator code, and the
observer's Dawid-Skene reliability is known and at least PROMOTION_MIN_RELIABILITY.
Everything else is preliminary in the AquaSentinel citizen-finding profile.
Findings whose AI suggestion the citizen has not answered are never exported.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, time, timedelta, timezone
from typing import Any, Optional

from sqlmodel import Session, select

from api import models as m
from api.fhir import resources as r
from api.fhir.bundle import TransactionBuilder, identifier_query, urn
from api.fhir import codes as c

Resource = dict[str, Any]

PROMOTION_MIN_RELIABILITY = 0.6
DEFAULT_WINDOW_DAYS = 14


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _window_days() -> int:
    try:
        from api.risk.config import load_config

        return int(load_config()["window_days"])
    except Exception:  # config missing: fall back to the documented default
        return DEFAULT_WINDOW_DAYS


# ---------------------------------------------------------------- reliability


def observer_reliability(session: Session, checkin: m.CheckIn) -> Optional[float]:
    """Dawid-Skene reliability of the check-in's observer across the city's stream checks in the risk window.

    Uses the same estimator and calibration priors as the risk index (api.risk.service). Returns None when the
    observer has no habitat answers in the window, in which case nothing is promoted.
    """
    from api.risk.config import load_config
    from api.risk.service import habitat_posteriors, prior_accuracy

    cfg = load_config()
    site = session.get(m.Site, checkin.site_id)
    if site is None:
        return None
    as_of = _aware(checkin.observed_at).date()
    start = datetime.combine(as_of - timedelta(days=cfg["window_days"] - 1), time.min, tzinfo=timezone.utc)
    end = datetime.combine(as_of, time.max, tzinfo=timezone.utc)
    site_ids = [s.id for s in session.exec(select(m.Site).where(m.Site.city_id == site.city_id)).all()]
    checkins = [x for x in session.exec(select(m.CheckIn).where(m.CheckIn.site_id.in_(site_ids))).all()  # type: ignore[attr-defined]
                if start <= _aware(x.observed_at) <= end]
    observer_ids = {x.observer_id for x in checkins}
    observers = session.exec(select(m.Observer).where(m.Observer.id.in_(observer_ids))).all() if observer_ids else []  # type: ignore[attr-defined]
    _, reliability = habitat_posteriors(checkins, list(cfg["habitat"]["questions"]), prior_accuracy(list(observers)))
    value = reliability.get(checkin.observer_id)
    return None if value is None else float(value)


def is_promoted(finding_status: m.FindingStatus, reliability: Optional[float]) -> bool:
    if finding_status in (m.FindingStatus.pending, m.FindingStatus.expert_review):
        return False
    return reliability is not None and reliability >= PROMOTION_MIN_RELIABILITY


# ---------------------------------------------------------------- lifecycle


def exportable_findings(findings: list[m.Finding]) -> list[m.Finding]:
    """Drop findings the citizen has not answered (pending AI suggestions, or no count and no answer)."""
    out = []
    for f in findings:
        if f.type == m.FindingType.dead_bird:
            if f.status != m.FindingStatus.pending and f.count:
                out.append(f)
        elif r.has_citizen_value(f):
            out.append(f)
    return out


def lifecycle_bundle(session: Session, checkin_id: int, *, reliability: Optional[float] = None,
                     compute_reliability: bool = True, now: Optional[datetime] = None) -> Resource:
    """Transaction Bundle for one check-in. Raises LookupError if it does not exist, PermissionError without consent."""
    checkin = session.get(m.CheckIn, checkin_id)
    if checkin is None:
        raise LookupError(f"check-in {checkin_id} not found")
    if not checkin.consent:
        raise PermissionError(f"check-in {checkin_id} has no consent to share")
    site = session.get(m.Site, checkin.site_id)
    observer = session.get(m.Observer, checkin.observer_id)
    if site is None or observer is None:
        raise LookupError(f"check-in {checkin_id} has no site or observer")
    if reliability is None and compute_reliability:
        reliability = observer_reliability(session, checkin)

    tx = TransactionBuilder(f"checkin-{checkin.client_uuid}")
    loc = tx.add(urn("Location", site.id), r.location(site), identifier_query(c.SID_SITE, site.id))
    who = tx.add(urn("Practitioner", observer.id), r.practitioner(observer), identifier_query(c.SID_OBSERVER, observer.id))

    promoted = reliability is not None and reliability >= PROMOTION_MIN_RELIABILITY
    targets: list[str] = []
    for i, obs in enumerate(r.stream_check_observations(checkin, loc, who, promoted)):
        targets.append(tx.add(urn("Observation", f"checkin-{checkin.client_uuid}-answers-{i}"), obs))

    findings = session.exec(select(m.Finding).where(m.Finding.checkin_id == checkin.id).order_by(m.Finding.id)).all()  # type: ignore[arg-type]
    for f in exportable_findings(list(findings)):
        if f.type == m.FindingType.dead_bird:
            res = r.dead_bird_observation(f, checkin, loc, who)
        else:
            res = r.finding_observation(f, checkin, loc, who, is_promoted(f.status, reliability))
        targets.append(tx.add(urn("Observation", f"finding-{f.id}"), res))

    if targets:
        tx.add(urn("Provenance", f"checkin-{checkin.client_uuid}"),
               r.provenance(checkin, observer, targets, loc, who, reliability))
    return tx.build(r.iso(now or datetime.now(timezone.utc)))


# ---------------------------------------------------------------- city week


def _approved_actions(session: Session, site_ids: list[str], score_ids: set[int], week: str) -> list[m.Action]:
    monday, sunday = r.week_period(week)
    rows = session.exec(select(m.Action).where(m.Action.site_id.in_(site_ids), m.Action.status == m.ActionStatus.approved)).all()  # type: ignore[attr-defined]
    out = []
    for a in rows:
        decided = _aware(a.decided_at or a.created_at).date()
        if (a.risk_score_id is not None and a.risk_score_id in score_ids) or monday <= decided <= sunday:
            out.append(a)
    return sorted(out, key=lambda a: a.id or 0)


def _messages(session: Session, action_ids: set[int], observer_ids: set[str], week: str) -> list[m.Message]:
    monday, sunday = r.week_period(week)
    out = []
    for msg in session.exec(select(m.Message)).all():
        if msg.action_id is not None:
            if msg.action_id in action_ids:
                out.append(msg)
        elif msg.observer_id in observer_ids and monday <= _aware(msg.created_at).date() <= sunday:
            out.append(msg)
    return sorted(out, key=lambda x: x.id or 0)


def city_week_bundle(session: Session, city_id: str, week: str, *, now: Optional[datetime] = None) -> Resource:
    """Transaction Bundle for one city and ISO week (e.g. "2026-W38"). Raises LookupError for an unknown city."""
    r.week_period(week)  # validates the week format
    sites = sorted(session.exec(select(m.Site).where(m.Site.city_id == city_id)).all(), key=lambda s: s.id)
    if not sites:
        raise LookupError(f"city {city_id} has no sites")
    by_id = {s.id: s for s in sites}
    city_name = sites[0].city_name
    scores = sorted(session.exec(select(m.RiskScore).where(m.RiskScore.site_id.in_(list(by_id)), m.RiskScore.week == week)).all(),  # type: ignore[attr-defined]
                    key=lambda s: s.site_id)
    generated = now or datetime.now(timezone.utc)
    synthetic = any(s.synthetic for s in scores)

    tx = TransactionBuilder(f"city-{city_id}-{week}")
    org = tx.add(urn("Organization", city_id), r.organization(city_id, city_name, synthetic), identifier_query(c.SID_CITY, city_id))

    def site_ref(site_id: str) -> str:
        return tx.add(urn("Location", site_id), r.location(by_id[site_id]), identifier_query(c.SID_SITE, site_id))

    risk_refs: dict[int, str] = {}
    if scores:
        versions = sorted({s.config_version for s in scores})
        device = tx.add(urn("Device", "risk-engine-" + "-".join(versions)), r.risk_engine_device(", ".join(versions)))
        window = _window_days()
        for s in scores:
            risk_refs[s.id] = tx.add(urn("Observation", f"risk-{s.id}"), r.risk_observation(s, site_ref(s.site_id), device, org, window))
    tx.add(urn("MeasureReport", f"{city_id}-{week}"), r.measure_report(city_name, week, list(scores), risk_refs, org, generated))

    actions = _approved_actions(session, list(by_id), set(risk_refs), week)
    action_refs: dict[int, str] = {}
    for a in actions:
        reason = risk_refs.get(a.risk_score_id) if a.risk_score_id is not None else None
        action_refs[a.id] = tx.add(urn("ServiceRequest", f"action-{a.id}"), r.service_request(a, site_ref(a.site_id), org, reason))

    contributors = _city_observers(session, list(by_id))
    for msg in _messages(session, set(action_refs), contributors, week):
        observer = session.get(m.Observer, msg.observer_id)
        if observer is None:
            continue
        who = tx.add(urn("Practitioner", observer.id), r.practitioner(observer), identifier_query(c.SID_OBSERVER, observer.id))
        about = action_refs.get(msg.action_id) if msg.action_id is not None else None
        tx.add(urn("Communication", f"message-{msg.id}"), r.communication(msg, who, about))
    return tx.build(r.iso(generated))


def _city_observers(session: Session, site_ids: list[str]) -> set[str]:
    rows = session.exec(select(m.CheckIn.observer_id).where(m.CheckIn.site_id.in_(site_ids))).all()  # type: ignore[attr-defined]
    return set(rows)


def resources_by_type(bundle: Resource) -> dict[str, list[Resource]]:
    """Convenience for callers and tests: bundle resources grouped by resourceType."""
    out: dict[str, list[Resource]] = defaultdict(list)
    for e in bundle.get("entry", []):
        out[e["resource"]["resourceType"]].append(e["resource"])
    return dict(out)


__all__ = ["lifecycle_bundle", "city_week_bundle", "observer_reliability", "is_promoted", "PROMOTION_MIN_RELIABILITY",
           "resources_by_type", "exportable_findings"]
