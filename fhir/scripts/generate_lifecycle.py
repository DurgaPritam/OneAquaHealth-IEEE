"""Build an in-memory database from api.seed's synthetic Coimbra season and export FHIR Bundles.

Writes to fhir/output/generated/ (gitignored):
  lifecycle-checkin.json   one check-in: Location, Practitioner, Observations, Provenance
  lifecycle-city-week.json the city week: MeasureReport, risk Observations, ServiceRequests, Communications

Everything is synthetic and tagged so. Weather is switched off (no network, no cache), so the
seasonal factor is "no data" and the index reports its upper bound, exactly as the live
system does when Open-Meteo is unreachable. The approved actions and messages stand in for
the Phase 7 officer workflow and are labelled synthetic.

Usage: .venv/bin/python fhir/scripts/generate_lifecycle.py [--out DIR]
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from sqlalchemy.pool import StaticPool  # noqa: E402
from sqlmodel import Session, SQLModel, create_engine, select  # noqa: E402

from api import models as m  # noqa: E402
from api import seed  # noqa: E402
from api.fhir import city_week_bundle, lifecycle_bundle, observer_reliability  # noqa: E402
from api.fhir.export import PROMOTION_MIN_RELIABILITY  # noqa: E402
from api.risk import weather  # noqa: E402
from api.risk.service import compute_city, iso_week  # noqa: E402

CITY = "CO"
FIXED_NOW = datetime(2026, 9, 21, 10, 0, tzinfo=timezone.utc)


def no_network(_url: str, _params: dict[str, Any]) -> dict[str, Any]:
    raise RuntimeError("weather disabled for a reproducible offline export")


def build_db() -> Session:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)
    session = Session(engine)
    sites = seed.load_sites()
    seed.seed_sites(session, sites)
    seed.seed_synthetic(session, sites, CITY)
    weather.CACHE_DIR = Path(tempfile.mkdtemp(prefix="aquasentinel-noweather-"))
    for as_of in seed.season_weeks():
        compute_city(session, CITY, as_of, fetch=no_network)
    return session


def pick_checkin(session: Session, week_end: datetime) -> m.CheckIn:
    """A check-in in the last week with a dead bird and a reliable observer, else the first reliable one."""
    start = week_end - timedelta(days=13)
    rows = [c for c in session.exec(select(m.CheckIn).order_by(m.CheckIn.id)).all()
            if start.date() <= c.observed_at.date() <= week_end.date()]
    best = None
    for c in rows:
        rel = observer_reliability(session, c)
        if rel is None or rel < PROMOTION_MIN_RELIABILITY:
            continue
        types = {f.type for f in session.exec(select(m.Finding).where(m.Finding.checkin_id == c.id)).all()}
        if m.FindingType.dead_bird in types:
            return c
        best = best or c
    if best is None:
        raise SystemExit("no check-in with a reliable observer in the window")
    return best


def add_ai_findings(session: Session, checkin: m.CheckIn) -> None:
    """Show every AI path: confirmed, corrected, expert review and one unanswered suggestion that must not be exported."""
    checkin.created_at = checkin.observed_at + timedelta(minutes=5)  # received time, fixed for a reproducible export
    session.add(checkin)
    common = {"checkin_id": checkin.id, "synthetic": True, "ai_provider": "mock"}
    session.add_all([
        m.Finding(type=m.FindingType.predator, subject="predator_photo", ai_label="Motacilla alba", ai_confidence=0.74,
                  ai_reason="Black, white and grey bird walking on the bank", citizen_answer="Motacilla alba",
                  status=m.FindingStatus.confirmed, **common),
        m.Finding(type=m.FindingType.adult_mosquito, subject="adult_mosquito", ai_label="plain_culex_type", ai_confidence=0.58,
                  ai_reason="Brown body without clear stripes", key_label="striped_aedes_type", citizen_answer="striped_aedes_type",
                  status=m.FindingStatus.corrected, **common),
        m.Finding(type=m.FindingType.predator, subject="predator_photo", ai_label="Pelophylax lessonae", ai_confidence=0.41,
                  ai_reason="Green frog in shallow water", citizen_answer="Pelophylax lessonae",
                  status=m.FindingStatus.expert_review, data={"plausibility": {"status": "implausible"}}, **common),
        m.Finding(type=m.FindingType.habitat, subject="habitat_photo", ai_label="standing_water", ai_confidence=0.66,
                  ai_reason="Still water at the edge", status=m.FindingStatus.pending, **common),
    ])
    session.commit()


def approve_actions(session: Session, week: str) -> None:
    """Run the production officer workflow: draft from alerts (api.actions.drafting) and approve every draft."""
    from api.actions import drafting

    for action in drafting.draft_for_city(session, CITY):
        drafting.decide(session, action, True, "officer:CO-01", f"Approved for the {week} demo export")
        action.decided_at = FIXED_NOW
        session.add(action)
    session.commit()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "fhir" / "output" / "generated")
    args = parser.parse_args()
    session = build_db()
    last = seed.season_weeks()[-1]
    week = iso_week(last)
    checkin = pick_checkin(session, datetime.combine(last, datetime.min.time(), tzinfo=timezone.utc))
    add_ai_findings(session, checkin)
    approve_actions(session, week)
    args.out.mkdir(parents=True, exist_ok=True)
    outputs = {
        "lifecycle-checkin.json": lifecycle_bundle(session, checkin.id, now=FIXED_NOW),
        "lifecycle-city-week.json": city_week_bundle(session, CITY, week, now=FIXED_NOW),
    }
    for name, bundle in outputs.items():
        (args.out / name).write_text(json.dumps(bundle, indent=2, ensure_ascii=False), encoding="utf-8")
        kinds: dict[str, int] = {}
        for e in bundle["entry"]:
            kinds[e["resource"]["resourceType"]] = kinds.get(e["resource"]["resourceType"], 0) + 1
        print(f"{name}: {len(bundle['entry'])} entries {kinds}")


if __name__ == "__main__":
    main()
