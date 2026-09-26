"""FHIR exporter: bundle structure, references, privacy, no diagnosis, synthetic tags, AI handling."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

import pytest
from sqlmodel import Session

from api import models as m
from api.fhir import (
    PROMOTION_MIN_RELIABILITY,
    city_week_bundle,
    is_promoted,
    lifecycle_bundle,
    observer_reliability,
    resources_by_type,
)
from api.fhir import codes as c
from api.fhir.resources import action_category, week_period

NOW = datetime(2026, 9, 21, 10, 0, tzinfo=timezone.utc)
ROOT = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------- fixtures


@pytest.fixture()
def lifecycle_db(session: Session) -> dict[str, Any]:
    site = m.Site(id="C1", name="Exploratório", city_id="CO", city_name="Coimbra", lat=40.19787, lon=-8.42865)
    site2 = m.Site(id="C2", name="Estação Cbr-B", city_id="CO", city_name="Coimbra", lat=40.2, lon=-8.41)
    observer = m.Observer(id="OBS-7F3K2Q", team="Mondego Stream Keepers", tier=m.ObserverTier.calibrated,
                          calibration={"overall_kappa": 0.71}, synthetic=True)
    session.add_all([site, site2, observer])
    session.commit()
    checkin = m.CheckIn(client_uuid="11111111-1111-1111-1111-111111111111", site_id="C1", observer_id=observer.id,
                        observed_at=datetime(2026, 9, 20, 9, 0, tzinfo=timezone.utc), lat=40.198, lon=-8.429, consent=True,
                        answers={"flow_NP": "extensive", "flow_RU": "absent", "bank_left_CC": "present", "barriers": 1,
                                 "mac_free_floating": "present", "rip_trees": "2", "water_sewage_smell": "present",
                                 "not_a_question": "present", "sub_OM": "maybe"},
                        synthetic=True)
    session.add(checkin)
    session.commit()
    F = m.FindingStatus
    common = {"checkin_id": checkin.id, "synthetic": True}
    findings = {
        "dips": m.Finding(type=m.FindingType.larvae, subject="larval_dips", count=12, data={"dips": [4, 3, 2, 2, 1]},
                          ai_label="larvae_present", ai_confidence=0.82, ai_reason="Wriggling shapes", ai_provider="mock",
                          status=F.confirmed, **common),
        "posture": m.Finding(type=m.FindingType.larvae, subject="larval_posture", citizen_answer="angled", key_label="culex_type",
                             status=F.manual, **common),
        "amphibians": m.Finding(type=m.FindingType.predator, subject="amphibians", citizen_answer="heard", status=F.manual, **common),
        "bats": m.Finding(type=m.FindingType.predator, subject="bats", citizen_answer="seen", status=F.manual, **common),
        "adult": m.Finding(type=m.FindingType.adult_mosquito, subject="adult_mosquito", ai_label="plain_culex_type",
                           ai_confidence=0.58, ai_reason="Brown body", ai_provider="mock", key_label="striped_aedes_type",
                           citizen_answer="striped_aedes_type", status=F.corrected, **common),
        "review": m.Finding(type=m.FindingType.predator, subject="predator_photo", ai_label="Pelophylax lessonae", ai_confidence=0.41,
                            ai_provider="mock", citizen_answer="Pelophylax lessonae", status=F.expert_review, **common),
        "pending": m.Finding(type=m.FindingType.habitat, subject="habitat_photo", ai_label="dry_channel", ai_confidence=0.66,
                             ai_reason="UNANSWERED-SUGGESTION-REASON", ai_provider="mock", status=F.pending, **common),
        "rejected_empty": m.Finding(type=m.FindingType.predator, subject="predator_photo", ai_label="Apus apus", ai_confidence=0.3,
                                    ai_provider="mock", status=F.rejected, **common),
        "dead": m.Finding(type=m.FindingType.dead_bird, subject="dead_bird", count=2, data={"handled": False}, status=F.manual, **common),
    }
    session.add_all(findings.values())
    session.commit()
    return {"site": site, "observer": observer, "checkin": checkin, "findings": findings}


def walk(node: Any) -> Iterator[tuple[str, Any]]:
    if isinstance(node, dict):
        for k, v in node.items():
            yield k, v
            yield from walk(v)
    elif isinstance(node, list):
        for v in node:
            yield from walk(v)


def finding_ids(bundle: dict[str, Any]) -> set[str]:
    return {i["value"] for e in bundle["entry"] for i in e["resource"].get("identifier", []) if i["system"] == c.SID_FINDING}


def by_finding(bundle: dict[str, Any], finding: m.Finding) -> dict[str, Any]:
    for e in bundle["entry"]:
        for i in e["resource"].get("identifier", []):
            if i["system"] == c.SID_FINDING and i["value"] == str(finding.id):
                return e["resource"]
    raise KeyError(finding.id)


def component_values(res: dict[str, Any], code: str) -> list[dict[str, Any]]:
    return [comp for comp in res.get("component", []) if comp["code"]["coding"][0]["code"] == code]


# ---------------------------------------------------------------- lifecycle bundle


def test_lifecycle_is_a_transaction_bundle(session: Session, lifecycle_db: dict[str, Any]) -> None:
    bundle = lifecycle_bundle(session, lifecycle_db["checkin"].id, reliability=0.9, now=NOW)
    assert bundle["resourceType"] == "Bundle" and bundle["type"] == "transaction"
    assert bundle["timestamp"] == "2026-09-21T10:00:00Z"
    kinds = resources_by_type(bundle)
    assert len(kinds["Location"]) == 1 and len(kinds["Practitioner"]) == 1 and len(kinds["Provenance"]) == 1
    urls = [e["fullUrl"] for e in bundle["entry"]]
    assert len(urls) == len(set(urls))
    for e in bundle["entry"]:
        assert re.fullmatch(r"urn:uuid:[0-9a-f-]{36}", e["fullUrl"])
        assert e["request"]["method"] == "POST" and e["request"]["url"] == e["resource"]["resourceType"]
        assert "id" not in e["resource"]
    assert kinds["Location"][0]["identifier"][0] == {"system": c.SID_SITE, "value": "C1"}
    assert kinds["Location"][0]["position"] == {"latitude": 40.198, "longitude": -8.429}


def test_references_resolve_inside_the_bundle(session: Session, lifecycle_db: dict[str, Any]) -> None:
    bundle = lifecycle_bundle(session, lifecycle_db["checkin"].id, reliability=0.9, now=NOW)
    urls = {e["fullUrl"] for e in bundle["entry"]}
    refs = [v for k, v in walk(bundle) if k == "reference"]
    assert refs and all(r in urls for r in refs)
    prov = resources_by_type(bundle)["Provenance"][0]
    observations = {e["fullUrl"] for e in bundle["entry"] if e["resource"]["resourceType"] == "Observation"}
    assert {t["reference"] for t in prov["target"]} == observations


def test_practitioner_has_no_personal_fields(session: Session, lifecycle_db: dict[str, Any]) -> None:
    bundle = lifecycle_bundle(session, lifecycle_db["checkin"].id, reliability=0.9, now=NOW)
    prac = resources_by_type(bundle)["Practitioner"][0]
    assert set(prac) <= {"resourceType", "meta", "text", "identifier", "active"}
    assert prac["identifier"] == [{"system": c.SID_OBSERVER, "value": "OBS-7F3K2Q"}]
    text = json.dumps(bundle)
    assert "Mondego Stream Keepers" not in text  # team names never leave the database
    for e in bundle["entry"]:
        if e["resource"]["resourceType"] != "Location":  # a site has a place name; nothing else has any name
            assert not {"name", "telecom", "address", "gender", "birthDate", "photo"} & set(e["resource"])


def test_dead_bird_records_count_place_time_only(session: Session, lifecycle_db: dict[str, Any]) -> None:
    bundle = lifecycle_bundle(session, lifecycle_db["checkin"].id, reliability=0.9, now=NOW)
    dead = by_finding(bundle, lifecycle_db["findings"]["dead"])
    assert dead["meta"]["profile"] == [c.P_DEAD_BIRD]
    assert dead["valueQuantity"]["value"] == 2
    assert dead["subject"]["reference"].startswith("urn:uuid:") and dead["effectiveDateTime"] == "2026-09-20T09:00:00Z"
    assert not {"interpretation", "component", "valueCodeableConcept", "method", "bodySite", "specimen"} & set(dead)
    assert any("No diagnosis" in n["text"] for n in dead["note"])
    assert not any(k == "interpretation" for k, _ in walk(bundle))


def test_synthetic_records_are_tagged(session: Session, lifecycle_db: dict[str, Any]) -> None:
    bundle = lifecycle_bundle(session, lifecycle_db["checkin"].id, reliability=0.9, now=NOW)
    assert c.SYNTHETIC_TAG in bundle["meta"]["tag"]
    kinds = resources_by_type(bundle)
    assert "tag" not in kinds["Location"][0]["meta"]  # the real ENORA site is not synthetic
    for kind in ("Practitioner", "Observation", "Provenance"):
        for res in kinds[kind]:
            assert c.SYNTHETIC_TAG in res["meta"]["tag"], kind


def test_real_records_carry_no_synthetic_tag(session: Session, lifecycle_db: dict[str, Any]) -> None:
    for obj in [lifecycle_db["observer"], lifecycle_db["checkin"], *lifecycle_db["findings"].values()]:
        obj.synthetic = False
        session.add(obj)
    session.commit()
    bundle = lifecycle_bundle(session, lifecycle_db["checkin"].id, reliability=0.9, now=NOW)
    assert "meta" not in bundle
    assert all("tag" not in e["resource"].get("meta", {}) for e in bundle["entry"])


def test_unanswered_ai_suggestions_are_not_exported(session: Session, lifecycle_db: dict[str, Any]) -> None:
    f = lifecycle_db["findings"]
    bundle = lifecycle_bundle(session, lifecycle_db["checkin"].id, reliability=0.9, now=NOW)
    ids = finding_ids(bundle)
    assert str(f["pending"].id) not in ids
    assert str(f["rejected_empty"].id) not in ids  # rejected with nothing in its place: no citizen value
    assert "UNANSWERED-SUGGESTION-REASON" not in json.dumps(bundle)
    assert {str(f[k].id) for k in ("dips", "posture", "amphibians", "bats", "adult", "review", "dead")} == ids


def test_ai_suggestion_and_citizen_answer_are_both_kept(session: Session, lifecycle_db: dict[str, Any]) -> None:
    bundle = lifecycle_bundle(session, lifecycle_db["checkin"].id, reliability=0.9, now=NOW)
    adult = by_finding(bundle, lifecycle_db["findings"]["adult"])
    assert adult["valueCodeableConcept"]["coding"][0]["code"] == "striped_aedes_type"  # the citizen's answer
    assert component_values(adult, "ai-suggestion")[0]["valueCodeableConcept"]["coding"][0]["code"] == "plain_culex_type"
    assert component_values(adult, "ai-confidence")[0]["valueQuantity"]["value"] == 0.58
    assert component_values(adult, "ai-provider")[0]["valueString"] == "mock"
    assert component_values(adult, "citizen-decision")[0]["valueCodeableConcept"]["coding"][0]["code"] == "corrected"
    assert component_values(adult, "guided-key-result")[0]["valueCodeableConcept"]["coding"][0]["code"] == "striped_aedes_type"
    assert "AI suggestion (mock" in adult["note"][0]["text"]
    manual = by_finding(bundle, lifecycle_db["findings"]["amphibians"])
    assert not component_values(manual, "ai-suggestion") and "note" not in manual


def test_larval_dips_map_to_oah_diptera_with_each_dip(session: Session, lifecycle_db: dict[str, Any]) -> None:
    bundle = lifecycle_bundle(session, lifecycle_db["checkin"].id, reliability=0.9, now=NOW)
    dips = by_finding(bundle, lifecycle_db["findings"]["dips"])
    assert {"system": c.OAH, "code": "diptera", "display": "Diptera"} in dips["code"]["coding"]
    assert dips["valueQuantity"]["value"] == 12
    assert [x["valueQuantity"]["value"] for x in component_values(dips, "dip-count")] == [4, 3, 2, 2, 1]
    bats = by_finding(bundle, lifecycle_db["findings"]["bats"])
    assert bats["meta"]["profile"] == [c.P_CITIZEN]  # no OAH code for bats: our own profile


def test_promotion_needs_citizen_answer_and_reliability(session: Session, lifecycle_db: dict[str, Any]) -> None:
    f = lifecycle_db["findings"]
    high = lifecycle_bundle(session, lifecycle_db["checkin"].id, reliability=0.9, now=NOW)
    dips = by_finding(high, f["dips"])
    assert dips["status"] == "final" and dips["meta"]["profile"] == [c.P_INDICATOR]
    review = by_finding(high, f["review"])
    assert review["status"] == "preliminary" and review["meta"]["profile"] == [c.P_CITIZEN]
    low = lifecycle_bundle(session, lifecycle_db["checkin"].id, reliability=PROMOTION_MIN_RELIABILITY - 0.01, now=NOW)
    unknown = lifecycle_bundle(session, lifecycle_db["checkin"].id, compute_reliability=False, now=NOW)
    for bundle in (low, unknown):
        for res in resources_by_type(bundle)["Observation"]:
            assert res["status"] == "preliminary"
            assert res["meta"]["profile"][0] in (c.P_CITIZEN, c.P_DEAD_BIRD)
    assert not is_promoted(m.FindingStatus.pending, 1.0)
    assert not is_promoted(m.FindingStatus.expert_review, 1.0)
    assert is_promoted(m.FindingStatus.corrected, PROMOTION_MIN_RELIABILITY)


def test_provenance_carries_reliability_and_tier(session: Session, lifecycle_db: dict[str, Any]) -> None:
    bundle = lifecycle_bundle(session, lifecycle_db["checkin"].id, reliability=0.8642, now=NOW)
    agent = resources_by_type(bundle)["Provenance"][0]["agent"][0]
    ext = agent["extension"][0]
    assert ext["url"] == c.EXT_RELIABILITY
    parts = {x["url"]: x for x in ext["extension"]}
    assert parts["dawidSkene"]["valueDecimal"] == 0.8642
    assert parts["calibrationTier"]["valueCoding"]["code"] == "calibrated"
    assert parts["calibrationKappa"]["valueDecimal"] == 0.71
    no_rel = lifecycle_bundle(session, lifecycle_db["checkin"].id, compute_reliability=False, now=NOW)
    parts = {x["url"] for x in resources_by_type(no_rel)["Provenance"][0]["agent"][0]["extension"][0]["extension"]}
    assert "dawidSkene" not in parts and "calibrationTier" in parts


def test_stream_check_answers_use_oah_codes(session: Session, lifecycle_db: dict[str, Any]) -> None:
    bundle = lifecycle_bundle(session, lifecycle_db["checkin"].id, reliability=0.9, now=NOW)
    stream = [r for r in resources_by_type(bundle)["Observation"] if "identifier" not in r]
    by_code: dict[str, list[dict[str, Any]]] = {}
    for res in stream:
        by_code.setdefault(res["code"]["coding"][0]["code"], []).append(res)
    assert set(by_code) == {"hydrology", "morophology", "foam", "macrophytes", "riparianVegetation"}
    flow_comps = {comp["code"]["coding"][0]["code"]: comp for res in by_code["hydrology"] for comp in res["component"]}
    assert flow_comps["flow_NP"]["valueCodeableConcept"]["coding"][0] == {"system": c.OAH, "code": "extensive"}
    assert flow_comps["barriers"]["valueQuantity"]["value"] == 1
    assert "bank_left_CC" in {comp["code"]["coding"][0]["code"] for comp in by_code["morophology"][0]["component"]}
    assert "sub_OM" not in json.dumps(stream)  # "maybe" is not on the A/P/E scale: dropped
    assert "not_a_question" not in json.dumps(bundle)
    rip = by_code["riparianVegetation"][0]
    assert rip["meta"]["profile"] == [c.P_VEGETATION]
    assert rip["component"] == [{"code": {"coding": [{"system": c.OAH, "code": "trees"}]},
                                 "valueCodeableConcept": {"coding": [{"system": c.OAH, "code": "21-40-percent"}]}}]


def test_lifecycle_refuses_missing_or_unconsented(session: Session, lifecycle_db: dict[str, Any]) -> None:
    with pytest.raises(LookupError):
        lifecycle_bundle(session, 99999)
    checkin = lifecycle_db["checkin"]
    checkin.consent = False
    session.add(checkin)
    session.commit()
    with pytest.raises(PermissionError):
        lifecycle_bundle(session, checkin.id)


def test_export_is_deterministic(session: Session, lifecycle_db: dict[str, Any]) -> None:
    a = lifecycle_bundle(session, lifecycle_db["checkin"].id, reliability=0.9, now=NOW)
    b = lifecycle_bundle(session, lifecycle_db["checkin"].id, reliability=0.9, now=NOW)
    assert a == b


def test_reliability_is_computed_from_stream_checks(session: Session) -> None:
    from api import seed

    sites = seed.load_sites()
    seed.seed_sites(session, sites)
    seed.seed_synthetic(session, sites, "CO")
    from sqlmodel import select

    checkin = session.exec(select(m.CheckIn).order_by(m.CheckIn.observed_at.desc())).first()  # type: ignore[attr-defined]
    rel = observer_reliability(session, checkin)
    assert rel is not None and 0.0 <= rel <= 1.0
    bundle = lifecycle_bundle(session, checkin.id, now=NOW)
    parts = {x["url"]: x for x in resources_by_type(bundle)["Provenance"][0]["agent"][0]["extension"][0]["extension"]}
    assert parts["dawidSkene"]["valueDecimal"] == round(rel, 4)


# ---------------------------------------------------------------- city week bundle


@pytest.fixture()
def city_db(session: Session, lifecycle_db: dict[str, Any]) -> dict[str, Any]:
    factors = [{"name": "temperature", "value": None}, {"name": "vector_presence", "value": 0.8}, {"name": "host_signal", "value": 1.0}]
    s1 = m.RiskScore(site_id="C1", week="2026-W38", total=0.62, band="high", factors=factors, explanation="Index 0.62 (high).",
                     config_version="abc123", coverage=0.9, range_low=0.5, range_high=0.7, alert=True, as_of="2026-09-20",
                     checkin_ids=[lifecycle_db["checkin"].id], synthetic=True)
    s2 = m.RiskScore(site_id="C2", week="2026-W38", total=0.1, band="low", factors=[], explanation="Index 0.10 (low).",
                     config_version="abc123", coverage=0.2, needs_data=True, as_of="2026-09-20", synthetic=True)
    old = m.RiskScore(site_id="C1", week="2026-W37", total=0.4, band="moderate", factors=[], explanation="old",
                      config_version="abc123", as_of="2026-09-13", synthetic=True)
    session.add_all([s1, s2, old])
    session.commit()
    approved = m.Action(site_id="C1", risk_score_id=s1.id, driver="vector_presence", measure_id="verification-visit",
                        title="Verification visit", rationale="High larvae.", status=m.ActionStatus.approved,
                        approved_by="officer-1", decided_at=NOW, synthetic=True)
    vet = m.Action(site_id="C1", risk_score_id=s1.id, driver="host_signal", measure_id="veterinary-notification",
                   title="Notify veterinary services", rationale="Dead birds.", status=m.ActionStatus.approved,
                   decided_at=NOW, synthetic=True)
    drafted = m.Action(site_id="C1", risk_score_id=s1.id, driver="habitat", measure_id="sewage-inspection",
                       title="DRAFTED-NOT-APPROVED", rationale="x", status=m.ActionStatus.drafted, synthetic=True)
    session.add_all([approved, vet, drafted])
    session.commit()
    msg = m.Message(observer_id="OBS-7F3K2Q", action_id=approved.id, kind="action_taken", text="Your observation led to an action.",
                    created_at=NOW, synthetic=True)
    session.add(msg)
    session.commit()
    return {"s1": s1, "s2": s2, "approved": approved, "vet": vet, "drafted": drafted, "msg": msg}


def test_city_week_bundle_structure(session: Session, city_db: dict[str, Any]) -> None:
    bundle = city_week_bundle(session, "CO", "2026-W38", now=NOW)
    assert bundle["type"] == "transaction" and c.SYNTHETIC_TAG in bundle["meta"]["tag"]
    kinds = resources_by_type(bundle)
    assert len(kinds["MeasureReport"]) == 1 and len(kinds["Observation"]) == 2 and len(kinds["Organization"]) == 1
    urls = {e["fullUrl"] for e in bundle["entry"]}
    assert all(r in urls for k, r in walk(bundle) if k == "reference")
    report = kinds["MeasureReport"][0]
    assert report["measure"] == c.MEASURE_URL
    assert report["period"] == {"start": "2026-09-14", "end": "2026-09-20"}
    groups = {g["code"]["coding"][0]["code"]: g for g in report["group"]}
    assert groups["sites-assessed"]["measureScore"]["value"] == 2
    assert groups["sites-alert"]["measureScore"]["value"] == 1
    assert groups["sites-needing-data"]["measureScore"]["value"] == 1
    strata = groups["vector-habitat-risk-index"]["stratifier"][0]["stratum"]
    assert [(s["value"]["text"], s["measureScore"]["value"]) for s in strata] == [("C1", 0.62), ("C2", 0.1)]
    assert len(report["evaluatedResource"]) == 2


def test_risk_observation_keeps_every_factor(session: Session, city_db: dict[str, Any]) -> None:
    bundle = city_week_bundle(session, "CO", "2026-W38", now=NOW)
    risk = next(r for r in resources_by_type(bundle)["Observation"] if r["valueQuantity"]["value"] == 0.62)
    assert risk["status"] == "preliminary" and risk["meta"]["profile"] == [c.P_RISK]
    comps = {comp["code"]["coding"][0]["code"]: comp for comp in risk["component"]}
    assert comps["risk-band"]["valueCodeableConcept"]["coding"][0]["code"] == "high"
    assert comps["vector_presence"]["valueQuantity"]["value"] == 0.8
    assert "dataAbsentReason" in comps["temperature"]  # missing data stays missing, never zero
    assert risk["effectivePeriod"] == {"start": "2026-09-07", "end": "2026-09-20"}
    assert "never infection status" in risk["note"][0]["text"]


def test_only_approved_actions_become_service_requests(session: Session, city_db: dict[str, Any]) -> None:
    bundle = city_week_bundle(session, "CO", "2026-W38", now=NOW)
    requests = resources_by_type(bundle)["ServiceRequest"]
    assert len(requests) == 2
    assert "DRAFTED-NOT-APPROVED" not in json.dumps(bundle)
    cats = {r["category"][0]["coding"][0]["code"]: r for r in requests}
    assert set(cats) == {"vector-control-visit", "veterinary-notification"}
    vet = cats["veterinary-notification"]
    assert any("No diagnosis" in n["text"] for n in vet["note"])
    for r in requests:
        assert r["status"] == "active" and r["intent"] == "order" and r["requester"]["reference"].startswith("urn:uuid:")
        assert r["reasonReference"][0]["reference"] in {e["fullUrl"] for e in bundle["entry"]}
    assert "officer-1" not in json.dumps(bundle)  # officer identity is not exported


def test_messages_become_communications_to_pseudonymous_observers(session: Session, city_db: dict[str, Any]) -> None:
    bundle = city_week_bundle(session, "CO", "2026-W38", now=NOW)
    kinds = resources_by_type(bundle)
    comm = kinds["Communication"][0]
    assert comm["category"][0]["coding"][0]["code"] == "action_taken"
    assert comm["payload"] == [{"contentString": "Your observation led to an action."}]
    by_url = {e["fullUrl"]: e["resource"] for e in bundle["entry"]}
    assert by_url[comm["recipient"][0]["reference"]]["identifier"][0]["value"] == "OBS-7F3K2Q"
    assert by_url[comm["about"][0]["reference"]]["resourceType"] == "ServiceRequest"
    for prac in kinds["Practitioner"]:
        assert set(prac) <= {"resourceType", "meta", "text", "identifier", "active"}


def test_city_week_rejects_unknown_city_and_bad_week(session: Session, city_db: dict[str, Any]) -> None:
    with pytest.raises(LookupError):
        city_week_bundle(session, "XX", "2026-W38")
    with pytest.raises(ValueError):
        city_week_bundle(session, "CO", "2026-38")


def test_action_category_mapping() -> None:
    def action(measure: str, driver: str) -> m.Action:
        return m.Action(site_id="C1", driver=driver, measure_id=measure, title="t", rationale="r")

    assert action_category(action("sewage-inspection", "habitat")) == "sewage-inspection"
    assert action_category(action("anything", "host_signal")) == "veterinary-notification"
    assert action_category(action("riparian-vegetation-recovery", "predator_deficit")) == "habitat-restoration"
    assert action_category(action("verification-visit", "vector_presence")) == "vector-control-visit"
    assert week_period("2026-W38")[0].isoformat() == "2026-09-14"


# ---------------------------------------------------------------- FSH stays in sync


def test_stream_check_code_system_matches_questions() -> None:
    import importlib.util

    spec = importlib.util.spec_from_file_location("gen_question_codes", ROOT / "fhir" / "scripts" / "gen_question_codes.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    expected = mod.render(json.loads((ROOT / "data" / "questions.json").read_text(encoding="utf-8")))
    assert (ROOT / "fhir" / "input" / "fsh" / "stream-check-questions.fsh").read_text(encoding="utf-8") == expected
    codes = set(re.findall(r"^\* #(\S+)", expected, flags=re.M))
    assert codes == set(c.answer_key_index())


def test_answer_codes_exist_in_fsh_code_system() -> None:
    fsh = (ROOT / "fhir" / "input" / "fsh" / "terminology.fsh").read_text(encoding="utf-8")
    defined = set(re.findall(r"^\* #(\S+)", fsh, flags=re.M))
    used = set(c.ANSWER_CODES) | set(c.RISK_FACTORS) | set(c.RISK_BANDS) | set(c.TIERS) | set(c.DECISIONS) | {
        "synthetic", "larval-dip-count", "dip-count", "larval-posture", "adult-mosquito-key", "bats", "predator-photo",
        "dead-bird-report", "vector-habitat-risk-index", "ai-suggestion", "ai-confidence", "ai-provider", "citizen-decision",
        "guided-key-result", "risk-band", "index-range-low", "index-range-high", "site-data-coverage", "sites-assessed",
        "sites-alert", "sites-needing-data", "site", "vector-control-visit", "sewage-inspection", "veterinary-notification",
        "habitat-restoration", "alert_raised", "action_taken"}
    assert used <= defined, used - defined


def test_fhir_http_routes(client, site, observer) -> None:  # type: ignore[no-untyped-def]
    from api.tests.conftest import checkin_payload

    cid = client.post("/api/checkins", json=checkin_payload(observer["id"])).json()["checkin"]["id"]
    bundle = client.get(f"/api/fhir/checkin/{cid}").json()
    assert bundle["resourceType"] == "Bundle" and bundle["type"] == "transaction"
    assert client.get("/api/fhir/checkin/999999").status_code == 404
    assert client.get("/api/fhir/city/CO/week/not-a-week").status_code in (404, 422)
