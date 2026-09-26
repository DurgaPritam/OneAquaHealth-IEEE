from __future__ import annotations

import math
from datetime import date, datetime, timezone

import pytest
from sqlmodel import Session

from api import models as m
from api.risk import factors as f
from api.risk.config import band_for, load_config
from api.risk.index import combine, score_site
from api.risk.service import compute_city, iso_week

CFG = load_config()


def days(temps, precip=None):  # type: ignore[no-untyped-def]
    precip = precip or [0.0] * len(temps)
    return [{"date": f"2026-09-{i + 1:02d}", "tmean": t, "precip": p} for i, (t, p) in enumerate(zip(temps, precip))]


# ------------------------------------------------------------------ factors


def test_temperature_degree_days() -> None:
    x = f.temperature(days([24.3] * 14), CFG)  # 10 DD a day -> 140 DD -> saturates
    assert x.value == 1.0 and x.inputs["degree_days"] == pytest.approx(140)
    x = f.temperature(days([14.3] * 14), CFG)
    assert x.value == 0.0
    x = f.temperature(days([19.75] * 14), CFG)  # 5.45 * 14 = 76.3 DD
    assert x.value == pytest.approx(76.3 / 109, abs=1e-3)


def test_temperature_declines_above_optimum() -> None:
    hot = f.temperature(days([30.0] * 14), CFG)
    assert 0 < hot.value < 1 and "declines" in hot.explanation
    assert f.temperature(days([36.0] * 14), CFG).value == 0.0


def test_dry_spell_counts_back_from_last_day() -> None:
    x = f.dry_spell(days([20] * 14, [5, 0, 0, 12] + [0] * 10), CFG)
    assert x.inputs["dry_days"] == 10 and x.value == 1.0
    x = f.dry_spell(days([20] * 3, [0, 0, 8]), CFG)
    assert x.value == 0.0


def test_missing_data_is_none_not_zero() -> None:
    for x in (f.temperature([], CFG), f.dry_spell([], CFG), f.habitat({}, CFG), f.vector_presence([], CFG),
              f.predator_deficit([], CFG), f.host_signal(None, CFG)):
        assert x.value is None


def test_habitat_weights_questions() -> None:
    post = {"flow_NP": {"expected": 1.0, "n_reports": 2}, "sub_OM": {"expected": 0.0, "n_reports": 2}}
    x = f.habitat(post, CFG)
    w = CFG["habitat"]["questions"]
    assert x.value == pytest.approx(w["flow_NP"] / (w["flow_NP"] + w["sub_OM"]), abs=1e-4)
    assert "no perceptible flow" in x.explanation


def test_vector_presence_is_reliability_weighted() -> None:
    reports = [{"per_dip": 6.0, "weight": 0.9}, {"per_dip": 0.0, "weight": 0.3}]
    x = f.vector_presence(reports, CFG)
    mean = (6 * 0.9) / 1.2
    assert x.value == pytest.approx(1 - math.exp(-mean / 3), abs=1e-4)


def test_predator_deficit() -> None:
    none = f.predator_deficit([{"amphibians": "none", "birds": 0, "bats": "none", "weight": 1}], CFG)
    rich = f.predator_deficit([{"amphibians": "seen", "birds": 8, "bats": "seen", "weight": 1}], CFG)
    assert none.value == 1.0 and rich.value == 0.0


def test_host_signal_never_diagnoses() -> None:
    x = f.host_signal([{"count": 2}], CFG)
    assert x.value == pytest.approx(2 / 3, abs=1e-4)
    assert "not a diagnosis" in x.explanation
    for word in ("infected", "positive", "West Nile virus in"):
        assert word not in x.explanation
    assert f.host_signal([], CFG).value == 0.0


# ------------------------------------------------------------------ combination


def all_factors(temp=1.0, dry=1.0, hab=None, vec=None, pred=None, host=None):  # type: ignore[no-untyped-def]
    vals = {"temperature": temp, "dry_spell": dry, "habitat": hab, "vector_presence": vec, "predator_deficit": pred, "host_signal": host}
    return [f.Factor(k, k.title(), v, "") for k, v in vals.items()]


def test_index_is_season_times_site() -> None:
    tw, sw = CFG["site_weights"], CFG["season_weights"]
    out = combine(all_factors(temp=0.8, dry=0.4, hab=1.0, vec=0.5), CFG)
    season = (sw["temperature"] * 0.8 + sw["dry_spell"] * 0.4) / (sw["temperature"] + sw["dry_spell"])
    site = (tw["habitat"] * 1.0 + tw["vector_presence"] * 0.5) / (tw["habitat"] + tw["vector_presence"])
    assert out["season"] == pytest.approx(season, abs=1e-4) and out["site"] == pytest.approx(site, abs=1e-4)
    assert out["total"] == pytest.approx(season * site, abs=1e-4)
    assert sum(x["contribution"] for x in out["factors"]) == pytest.approx(out["total"], abs=1e-3)
    assert out["dominant"] == "habitat"


def test_cold_weather_switches_the_index_off() -> None:
    out = combine(all_factors(temp=0.0, dry=0.0, hab=1.0, vec=1.0, pred=1.0, host=1.0), CFG)
    assert out["total"] == 0.0 and not out["alert"]


def test_weather_alone_never_alerts() -> None:
    out = combine(all_factors(temp=1.0, dry=1.0), CFG)
    assert out["total"] == 0.0 and out["needs_data"] and not out["alert"]
    assert out["range_low"] == 0.0 and out["range_high"] == 1.0
    assert "needs a stream check" in out["explanation"]


def test_missing_site_factors_widen_the_range() -> None:
    tw = CFG["site_weights"]
    out = combine(all_factors(hab=0.5, vec=0.5, pred=0.5), CFG)
    missing = tw["host_signal"] / sum(tw.values())
    assert out["range_high"] - out["range_low"] == pytest.approx(missing, abs=1e-3)
    assert not out["needs_data"]


def test_every_factor_is_visible_in_the_output() -> None:
    out = score_site({}, CFG)
    assert {x["name"] for x in out["factors"]} == set(CFG["season_weights"]) | set(CFG["site_weights"])
    assert out["total"] == 0.0 and out["coverage"] == 0.0


def test_bands_and_config_fingerprint() -> None:
    assert band_for(0.1, CFG) == "low" and band_for(0.6, CFG) == "high" and band_for(0.95, CFG) == "very_high"
    assert CFG["fingerprint"].startswith(CFG["version"] + "+")
    assert iso_week(date(2026, 9, 20)) == "2026-W38"


# ------------------------------------------------------------------ service with trace


def fake_weather(url, params):  # type: ignore[no-untyped-def]
    from datetime import date as d, timedelta

    start, end = d.fromisoformat(params["start_date"]), d.fromisoformat(params["end_date"])
    n = (end - start).days + 1
    return {"daily": {"time": [(start + timedelta(days=i)).isoformat() for i in range(n)],
                      "temperature_2m_mean": [24.0] * n, "precipitation_sum": [0.0] * n}}


def add_checkin(session: Session, site: str, obs: str, answers: dict, larvae: int, when: datetime) -> m.CheckIn:
    c = m.CheckIn(client_uuid=f"{site}-{obs}-{when.isoformat()}", site_id=site, observer_id=obs, observed_at=when, consent=True, answers=answers)
    session.add(c)
    session.flush()
    session.add(m.Finding(checkin_id=c.id, type=m.FindingType.larvae, subject="larval_dips", count=larvae, data={"dips": [larvae, 0, 0, 0, 0]}))
    session.add(m.Finding(checkin_id=c.id, type=m.FindingType.predator, subject="amphibians", citizen_answer="none"))
    return c


def test_compute_city_traces_every_score(session: Session, tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    from api.risk import weather

    monkeypatch.setattr(weather, "CACHE_DIR", tmp_path)
    for sid in ("C1", "C2"):
        session.add(m.Site(id=sid, name=sid, city_id="CO", city_name="Coimbra", lat=40.2, lon=-8.43))
    for oid in ("OBS-AAAAAA", "OBS-BBBBBB"):
        session.add(m.Observer(id=oid))
    session.commit()
    when = datetime(2026, 9, 18, 9, tzinfo=timezone.utc)
    c1 = add_checkin(session, "C1", "OBS-AAAAAA", {"flow_NP": "extensive", "sub_OM": "present"}, 20, when)
    add_checkin(session, "C1", "OBS-BBBBBB", {"flow_NP": "extensive"}, 15, when)
    old = add_checkin(session, "C2", "OBS-AAAAAA", {"flow_NP": "absent"}, 0, datetime(2026, 8, 1, tzinfo=timezone.utc))
    session.commit()

    rows = {r["site_id"]: r for r in compute_city(session, "CO", date(2026, 9, 20), fetch=fake_weather)}
    c1_row, c2_row = rows["C1"], rows["C2"]
    # C2 has only weather: a high point estimate, but a wide range, no alert, and flagged as needing data
    assert c2_row["needs_data"] and not c2_row["alert"]
    assert c2_row["range_high"] - c2_row["range_low"] > 0.5
    assert not c1_row["needs_data"] and c1_row["range_high"] - c1_row["range_low"] < 0.2
    assert c1_row["alert"]
    assert c1.id in c1_row["checkin_ids"] and old.id not in c2_row["checkin_ids"]  # outside the 14-day window
    factors = {x["name"]: x for x in c1_row["factors"]}
    trace = factors["habitat"]["inputs"]["questions"]["flow_NP"]["raw"]
    assert {r["checkin_id"] for r in trace} >= {c1.id}
    assert len(factors["temperature"]["inputs"]["days"]) == 14
    assert factors["host_signal"]["value"] == 0.0 and rows["C2"]["factors"][5]["value"] is None
    stored = session.get(m.RiskScore, c1_row["id"])
    assert stored.week == "2026-W38" and stored.dominant == c1_row["dominant"] and stored.checkin_ids == c1_row["checkin_ids"]
    # recompute replaces, not duplicates
    compute_city(session, "CO", date(2026, 9, 20), fetch=fake_weather)
    from sqlmodel import select

    assert len(session.exec(select(m.RiskScore)).all()) == 2


def test_weather_failure_means_no_data(session: Session, tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    from api.risk import weather

    monkeypatch.setattr(weather, "CACHE_DIR", tmp_path)
    session.add(m.Site(id="X1", name="x", city_id="XX", city_name="X", lat=1, lon=1))
    session.commit()

    def down(url, params):  # type: ignore[no-untyped-def]
        raise OSError("offline")

    row = compute_city(session, "XX", date(2026, 9, 20), fetch=down)[0]
    assert all(x["value"] is None for x in row["factors"])
    assert row["coverage"] == 0.0 and "No weather data" in row["explanation"]


def test_risk_endpoints(client, site) -> None:  # type: ignore[no-untyped-def]
    assert client.get("/api/risk/latest").json() == []
    assert client.get("/api/risk/history/C1").json() == []
