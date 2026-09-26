"""Draft actions from alerts and handle officer decisions.

Nothing here sends anything by itself: drafts wait in a queue until an officer
approves, edits or dismisses them. Volunteers who contributed are told what happened.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

from sqlmodel import Session, select

from api import models as m

ROOT = Path(__file__).resolve().parents[2]
POLLUTION_QUESTIONS = {"water_sewage_smell", "water_foam", "water_colour_unusual", "sub_OM"}


@lru_cache
def measures() -> dict[str, Any]:
    return json.loads((ROOT / "data" / "measures.json").read_text(encoding="utf-8"))


def measure(measure_id: str) -> dict[str, Any]:
    try:
        return measures()["measures"][measure_id]
    except KeyError:
        raise ValueError(f"Unknown measure {measure_id}") from None


def warnings_for(measure_id: str) -> list[str]:
    """Maladaptation guard: measures the Catalogue itself says can create mosquito habitat."""
    w = measure(measure_id).get("mosquito_warning")
    return [w] if w else []


def driver_for(score: m.RiskScore) -> str | None:
    """Map the dominant site factor to an action driver; habitat splits into stagnation or pollution."""
    if score.dominant != "habitat":
        return score.dominant
    habitat = next((f for f in score.factors if f["name"] == "habitat"), None)
    questions = (habitat or {}).get("inputs", {}).get("questions", {})
    if not questions:
        return "stagnation"
    top = max(questions, key=lambda q: questions[q]["expected"])
    return "organic_pollution" if top in POLLUTION_QUESTIONS else "stagnation"


def contributors(session: Session, score: m.RiskScore) -> list[str]:
    if not score.checkin_ids:
        return []
    rows = session.exec(select(m.CheckIn).where(m.CheckIn.id.in_(score.checkin_ids))).all()  # type: ignore[attr-defined]
    return sorted({c.observer_id for c in rows})


def _dead_birds(score: m.RiskScore) -> int:
    host = next((f for f in score.factors if f["name"] == "host_signal"), None)
    return int((host or {}).get("inputs", {}).get("count", 0) or 0)


def _open_draft(session: Session, site_id: str, measure_id: str) -> m.Action | None:
    return session.exec(select(m.Action).where(m.Action.site_id == site_id, m.Action.measure_id == measure_id,
                                               m.Action.status == m.ActionStatus.drafted)).first()


def _draft(session: Session, score: m.RiskScore, driver: str, measure_id: str, rationale: str) -> m.Action | None:
    if _open_draft(session, score.site_id, measure_id):
        return None
    mdef = measure(measure_id)
    action = m.Action(
        site_id=score.site_id, risk_score_id=score.id, driver=driver, measure_id=measure_id, title=mdef["title"],
        rationale=rationale, contributors=contributors(session, score), warnings=warnings_for(measure_id), synthetic=score.synthetic,
    )
    session.add(action)
    return action


def draft_for_city(session: Session, city_id: str) -> list[m.Action]:
    """Draft one action per alerting site (dominant driver), plus a veterinary notification wherever dead birds were reported."""
    site_ids = {s.id for s in session.exec(select(m.Site).where(m.Site.city_id == city_id)).all()}
    latest: dict[str, m.RiskScore] = {}
    for r in session.exec(select(m.RiskScore).order_by(m.RiskScore.week)).all():
        if r.site_id in site_ids:
            latest[r.site_id] = r
    drafted = []
    for score in latest.values():
        if score.alert and (driver := driver_for(score)):
            if driver == "host_signal":
                driver = "stagnation"  # the vet notification below covers dead birds; the alert still needs a habitat check
            first = measures()["drivers"][driver]["measures"][0]
            label = measures()["drivers"][driver]["label"]
            rationale = f"Index {score.total:.2f} ({score.band.replace('_', ' ')}) in week {score.week}. Main driver: {label.lower()}. {score.explanation}"
            if a := _draft(session, score, driver, first, rationale):
                drafted.append(a)
        if (n := _dead_birds(score)) > 0:
            rationale = f"{n} dead bird(s) reported in week {score.week}. Route to the veterinary team; no diagnosis is made."
            if a := _draft(session, score, "host_signal", "veterinary_notification", rationale):
                drafted.append(a)
    session.commit()
    for a in drafted:
        session.refresh(a)
    return drafted


def _site_name(session: Session, site_id: str) -> str:
    site = session.get(m.Site, site_id)
    return f"{site.name} ({site.id})" if site else site_id


def edit(session: Session, action: m.Action, title: str | None, rationale: str | None, measure_id: str | None) -> m.Action:
    if action.status != m.ActionStatus.drafted:
        raise ValueError("Only drafted actions can be edited")
    if measure_id:
        mdef = measure(measure_id)
        action.measure_id = measure_id
        action.warnings = warnings_for(measure_id)
        action.title = title or mdef["title"]
    elif title:
        action.title = title
    if rationale:
        action.rationale = rationale
    session.add(action)
    session.commit()
    session.refresh(action)
    return action


def decide(session: Session, action: m.Action, approve: bool, officer: str, note: str | None) -> list[m.Message]:
    """Approve or dismiss a draft and tell every contributing volunteer. Returns the messages sent."""
    if action.status != m.ActionStatus.drafted:
        raise ValueError("This action has already been decided")
    if not officer.strip():
        raise ValueError("An officer must be named")
    action.status = m.ActionStatus.approved if approve else m.ActionStatus.dismissed
    action.approved_by = officer.strip()
    action.decision_note = note
    action.decided_at = datetime.now(timezone.utc)
    place = _site_name(session, action.site_id)
    if approve:
        kind, text = "action_taken", f"Your observation at {place} led to an action: {action.title}. Approved by the city."
    else:
        kind, text = "alert_raised", f"Your observation at {place} helped raise an alert. The city reviewed it and decided no action is needed now."
    msgs = [m.Message(observer_id=o, action_id=action.id, kind=kind, text=text, synthetic=action.synthetic) for o in action.contributors]
    session.add(action)
    session.add_all(msgs)
    session.commit()
    for msg in msgs:
        session.refresh(msg)
    return msgs
