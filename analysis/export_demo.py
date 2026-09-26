"""Export the static-demo snapshot and the risk golden fixture.

The snapshot holds the real ENORA sites, the labelled synthetic Coimbra season,
real Open-Meteo weather for the season, and the Python-computed weekly scores.
The browser demo (web/src/lib/local) loads it and recomputes with the TypeScript
port; data/fixtures/risk_golden.json pins that port to the Python results.

Usage: .venv/bin/python -m analysis.export_demo
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from api import models as m
from api import seed
from api.risk import weather as wx
from api.risk.config import load_config
from api.risk.service import compute_city

ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT = ROOT / "web" / "public" / "demo" / "snapshot.json"
GOLDEN = ROOT / "data" / "fixtures" / "risk_golden.json"
CITY = "CO"
AS_OF = date(2026, 9, 20)
WEATHER_START = date(2026, 7, 20)


def _dump(rows: list[Any]) -> list[dict[str, Any]]:
    return [r.model_dump(mode="json") for r in rows]


def main() -> None:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        sites = seed.load_sites()
        seed.seed_sites(session, sites)
        seed.seed_synthetic(session, sites, CITY)
        for as_of in seed.season_weeks():
            compute_city(session, CITY, as_of)
        golden_rows = compute_city(session, CITY, AS_OF, store=False)

        city_sites = session.exec(select(m.Site).where(m.Site.city_id == CITY)).all()
        weather: dict[str, list[dict[str, Any]]] = {}
        for s in city_sites:
            cell = f"{round(s.lat, 1)}_{round(s.lon, 1)}"
            if cell not in weather:
                weather[cell] = wx.daily(s.lat, s.lon, WEATHER_START, AS_OF)

        snapshot = {
            "about": "AquaSentinel static demo. Sites are real (ENORA API). Observers, check-ins, findings, scores and actions are SYNTHETIC. Weather is real (Open-Meteo, CC BY 4.0).",
            "synthetic": True,
            "city": CITY,
            "as_of": AS_OF.isoformat(),
            "config": load_config(),
            "sites": _dump(session.exec(select(m.Site)).all()),
            "observers": _dump(session.exec(select(m.Observer)).all()),
            "checkins": _dump(session.exec(select(m.CheckIn).order_by(m.CheckIn.id)).all()),
            "findings": _dump(session.exec(select(m.Finding).order_by(m.Finding.id)).all()),
            "risk_scores": _dump(session.exec(select(m.RiskScore).order_by(m.RiskScore.id)).all()),
            "weather": weather,
        }
    SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
    SNAPSHOT.write_text(json.dumps(snapshot, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    GOLDEN.write_text(json.dumps({"as_of": AS_OF.isoformat(), "rows": [
        {k: r[k] for k in ("site_id", "total", "band", "season", "site", "dominant", "coverage", "range_low", "range_high", "needs_data", "alert", "checkin_ids")}
        | {"factors": {f["name"]: f["value"] for f in r["factors"]}}
        for r in golden_rows
    ]}, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {SNAPSHOT.relative_to(ROOT)} ({SNAPSHOT.stat().st_size // 1024} KB) and {GOLDEN.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
