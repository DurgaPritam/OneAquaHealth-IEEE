"""Seed the database: real ENORA sites plus a labelled synthetic season.

Usage: .venv/bin/python -m api.seed [--city CO] [--reset]
"""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from sqlmodel import Session, SQLModel, select

from api import models as m
from api import synthetic
from api.db import engine, init_db
from api.risk.service import compute_city

ROOT = Path(__file__).resolve().parent.parent
SITES_FILE = ROOT / "data" / "sites.json"


def load_sites() -> list[dict[str, Any]]:
    return json.loads(SITES_FILE.read_text(encoding="utf-8"))["sites"]


def seed_sites(session: Session, sites: list[dict[str, Any]]) -> int:
    added = 0
    for s in sites:
        if session.get(m.Site, s["code"]) is None:
            session.add(m.Site(
                id=s["code"], name=s["name"], city_id=s["city"]["id"], city_name=s["city"]["name"],
                lat=s["latitude"], lon=s["longitude"], altitude=s.get("altitude"), synthetic=False,
            ))
            added += 1
    session.commit()
    return added


def seed_synthetic(session: Session, sites: list[dict[str, Any]], city_id: str) -> tuple[int, int]:
    profiles, _truths, payloads = synthetic.scenario(sites, city_id=city_id)
    for p in profiles:
        if session.get(m.Observer, p.code) is None:
            session.add(m.Observer(id=p.code, team=p.team, synthetic=True))
    session.commit()
    n = 0
    for payload in payloads:
        if session.exec(select(m.CheckIn).where(m.CheckIn.client_uuid == payload["client_uuid"])).first():
            continue
        findings = payload.pop("findings")
        payload["observed_at"] = datetime.fromisoformat(payload["observed_at"])
        payload["lat"], payload["lon"] = m.round_coord(payload["lat"]), m.round_coord(payload["lon"])
        checkin = m.CheckIn(**payload)
        session.add(checkin)
        session.flush()
        session.add_all(m.Finding(checkin_id=checkin.id, **f) for f in findings)
        n += 1
    session.commit()
    return len(profiles), n


def season_weeks(weeks: int = 6) -> list[date]:
    """Sundays of the synthetic season, matching api.synthetic.scenario's end date."""
    end = date(2026, 9, 20)
    return [end - timedelta(weeks=weeks - 1 - i) for i in range(weeks)]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--city", default="CO", help="ENORA city id for the synthetic season")
    parser.add_argument("--reset", action="store_true", help="drop all tables first")
    parser.add_argument("--no-risk", action="store_true", help="skip computing weekly risk scores (needs network for weather)")
    args = parser.parse_args()
    if args.reset:
        SQLModel.metadata.drop_all(engine)
    init_db()
    sites = load_sites()
    with Session(engine) as session:
        added = seed_sites(session, sites)
        observers, checkins = seed_synthetic(session, sites, args.city)
        print(f"sites added: {added}; synthetic observers: {observers}; synthetic check-ins: {checkins}")
        if not args.no_risk:
            for as_of in season_weeks():
                rows = compute_city(session, args.city, as_of)
                alerts = sum(r["alert"] for r in rows)
                print(f"risk {as_of}: {len(rows)} sites, {alerts} alerts, weather-backed {sum(1 for r in rows if r['factors'][0]['value'] is not None)}")


if __name__ == "__main__":
    main()
