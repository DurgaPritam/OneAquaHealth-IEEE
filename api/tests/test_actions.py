from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlmodel import Session, select

from api import models as m
from api.actions import drafting


def make_score(session: Session, site: str, total: float, dominant: str, checkin_ids: list[int], alert: bool = True,
               habitat_questions: dict | None = None, dead_birds: int = 0) -> m.RiskScore:
    factors = [
        {"name": "habitat", "value": 0.5, "inputs": {"questions": habitat_questions or {}}},
        {"name": "host_signal", "value": 0.3, "inputs": {"count": dead_birds}},
    ]
    rs = m.RiskScore(site_id=site, week="2026-W38", total=total, band="high", explanation="x", config_version="t",
                     dominant=dominant, alert=alert, checkin_ids=checkin_ids, factors=factors)
    session.add(rs)
    session.commit()
    session.refresh(rs)
    return rs


@pytest.fixture()
def world(session: Session):  # type: ignore[no-untyped-def]
    for sid in ("C1", "C2", "C3"):
        session.add(m.Site(id=sid, name=f"Site {sid}", city_id="CO", city_name="Coimbra", lat=40.2, lon=-8.4))
    for oid in ("OBS-AAAAAA", "OBS-BBBBBB"):
        session.add(m.Observer(id=oid))
    session.commit()
    ids = []
    for i, oid in enumerate(("OBS-AAAAAA", "OBS-BBBBBB")):
        c = m.CheckIn(client_uuid=f"u{i}", site_id="C1", observer_id=oid, observed_at=datetime(2026, 9, 19, tzinfo=timezone.utc), consent=True)
        session.add(c)
        session.flush()
        ids.append(c.id)
    session.commit()
    return ids


def test_measures_link_to_the_catalogue() -> None:
    doc = drafting.measures()
    assert doc["source_url"] == "https://doi.org/10.5281/zenodo.20040211"
    for mid, mdef in doc["measures"].items():
        if mdef["catalogue"]:
            assert mdef["section"] and mdef["page"], mid
    for driver in doc["drivers"].values():
        for mid in driver["measures"]:
            assert mid in doc["measures"]


def test_driver_mapping(world, session: Session) -> None:  # type: ignore[no-untyped-def]
    pol = make_score(session, "C1", 0.7, "habitat", world, habitat_questions={"water_sewage_smell": {"expected": 0.9}, "flow_NP": {"expected": 0.2}})
    still = make_score(session, "C2", 0.7, "habitat", [], habitat_questions={"flow_NP": {"expected": 0.9}})
    pred = make_score(session, "C3", 0.7, "predator_deficit", [])
    assert drafting.driver_for(pol) == "organic_pollution"
    assert drafting.driver_for(still) == "stagnation"
    assert drafting.driver_for(pred) == "predator_deficit"


def test_drafts_only_for_alerts_and_always_routes_dead_birds(world, session: Session) -> None:  # type: ignore[no-untyped-def]
    make_score(session, "C1", 0.72, "predator_deficit", world)
    make_score(session, "C2", 0.2, "habitat", [], alert=False, dead_birds=2)
    make_score(session, "C3", 0.3, "habitat", [], alert=False)
    drafts = drafting.draft_for_city(session, "CO")
    kinds = sorted((a.site_id, a.measure_id) for a in drafts)
    assert kinds == [("C1", "M4.1.2"), ("C2", "veterinary_notification")]
    c1 = next(a for a in drafts if a.site_id == "C1")
    assert c1.status == m.ActionStatus.drafted and c1.contributors == ["OBS-AAAAAA", "OBS-BBBBBB"]
    assert drafting.draft_for_city(session, "CO") == []  # no duplicate drafts
    assert session.exec(select(m.Message)).all() == []  # drafting sends nothing


def test_maladaptation_warning_on_edit(world, session: Session) -> None:  # type: ignore[no-untyped-def]
    make_score(session, "C1", 0.72, "habitat", world, habitat_questions={"flow_NP": {"expected": 1.0}})
    action = drafting.draft_for_city(session, "CO")[0]
    assert action.warnings == []
    edited = drafting.edit(session, action, None, None, "M4.6.7")
    assert edited.title == "Retention ponds and floodable parks"
    assert "mosquito" in edited.warnings[0]
    with pytest.raises(ValueError):
        drafting.edit(session, action, None, None, "M9.9.9")


def test_approval_messages_every_contributor_and_is_final(world, session: Session) -> None:  # type: ignore[no-untyped-def]
    make_score(session, "C1", 0.72, "vector_presence", world)
    action = drafting.draft_for_city(session, "CO")[0]
    msgs = drafting.decide(session, action, True, "officer:CO-01", "Visit booked")
    assert {x.observer_id for x in msgs} == {"OBS-AAAAAA", "OBS-BBBBBB"}
    assert all("led to an action" in x.text and action.title in x.text for x in msgs)
    assert action.status == m.ActionStatus.approved and action.approved_by == "officer:CO-01" and action.decided_at
    with pytest.raises(ValueError):
        drafting.decide(session, action, False, "officer:CO-01", None)
    with pytest.raises(ValueError):
        drafting.edit(session, action, "x", None, None)


def test_dismissal_tells_volunteers_the_alert_was_reviewed(world, session: Session) -> None:  # type: ignore[no-untyped-def]
    make_score(session, "C1", 0.72, "vector_presence", world)
    action = drafting.draft_for_city(session, "CO")[0]
    msgs = drafting.decide(session, action, False, "officer:CO-01", "Already handled")
    assert all("helped raise an alert" in x.text for x in msgs)
    with pytest.raises(ValueError):
        drafting.decide(session, drafting.draft_for_city(session, "CO")[0] if False else action, True, " ", None)


def test_action_endpoints(client, site) -> None:  # type: ignore[no-untyped-def]
    assert "measures" in client.get("/api/actions/measures").json()
    assert client.post("/api/actions/draft", params={"city_id": "CO"}).json() == []
    a = client.post("/api/actions", json={"site_id": "C1", "driver": "stagnation", "measure_id": "verification_visit",
                                          "title": "t", "rationale": "r"}).json()
    assert client.post(f"/api/actions/{a['id']}/edit", json={"measure_id": "M4.6.1"}).json()["warnings"]
    res = client.post(f"/api/actions/{a['id']}/approve", json={"officer": "officer:CO-01"}).json()
    assert res["action"]["status"] == "approved" and res["messages"] == []
    assert client.post(f"/api/actions/{a['id']}/approve", json={"officer": "officer:CO-01"}).status_code == 409
