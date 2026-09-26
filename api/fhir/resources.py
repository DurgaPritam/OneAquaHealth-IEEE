"""Pure builders: api.models rows in, FHIR R4 resource dicts out.

References are passed in as ready-made reference strings (urn:uuid:... inside a
transaction Bundle), so every builder is a plain function of its inputs.
No builder writes a name, e-mail, phone or address for a person, and none
records infection, cause of death or a diagnosis.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from html import escape
from typing import Any, Optional

from api import models as m
from api.fhir import codes as c

Resource = dict[str, Any]

DEAD_BIRD_NOTE = ("Report only: count, place and time. No diagnosis or cause of death is made. "
                  "Do not touch dead birds; the report is routed to veterinary teams.")
RISK_NOTE_SUFFIX = " This index describes conditions that favour mosquito vectors, never infection status."


# ---------------------------------------------------------------- helpers


def iso(dt: datetime) -> str:
    """FHIR dateTime in UTC with seconds precision."""
    aware = dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    return aware.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def meta(profile_url: str, synthetic: bool) -> dict[str, Any]:
    out: dict[str, Any] = {"profile": [profile_url]}
    if synthetic:
        out["tag"] = [dict(c.SYNTHETIC_TAG)]
    return out


def narrative(text: str) -> dict[str, str]:
    return {"status": "generated", "div": f'<div xmlns="http://www.w3.org/1999/xhtml"><p>{escape(text)}</p></div>'}


def ref(target: str, display: Optional[str] = None) -> dict[str, str]:
    out = {"reference": target}
    if display:
        out["display"] = display
    return out


def unit_quantity(value: float, unit: str = "1") -> dict[str, Any]:
    """A dimensionless quantity (UCUM "1"); ``unit`` is the human-readable name (e.g. larvae)."""
    return {"value": value, "unit": unit, "system": c.UCUM, "code": "1"}


def answer_concept(answer: str) -> dict[str, Any]:
    """A citizen answer or AI label: coded when AquaSentinelCodes defines it, otherwise text only (e.g. a species name)."""
    if answer in c.ANSWER_CODES:
        return {"coding": [c.coding(c.AS, answer)], "text": answer}
    return {"text": answer}


def component(code_system: str, code: str, **value: Any) -> dict[str, Any]:
    return {"code": {"coding": [c.coding(code_system, code)]}, **value}


# ---------------------------------------------------------------- people, places, organisations


def location(site: m.Site) -> Resource:
    return {
        "resourceType": "Location",
        "meta": meta(c.P_SITE, site.synthetic),
        "text": narrative(f"Stream site {site.id} {site.name} ({site.city_name})"),
        "identifier": [{"system": c.SID_SITE, "value": site.id}],
        "status": "active",
        "name": site.name,
        "mode": "instance",
        "position": {"latitude": m.round_coord(site.lat), "longitude": m.round_coord(site.lon)},
    }


def practitioner(observer: m.Observer) -> Resource:
    """Pseudonymous observer: identifier only. Team, tier and calibration stay out of the Practitioner."""
    return {
        "resourceType": "Practitioner",
        "meta": meta(c.P_OBSERVER, observer.synthetic),
        "text": narrative(f"Pseudonymous observer {observer.id}"),
        "identifier": [{"system": c.SID_OBSERVER, "value": observer.id}],
        "active": True,
    }


def organization(city_id: str, city_name: str, synthetic: bool) -> Resource:
    res: Resource = {
        "resourceType": "Organization",
        "text": narrative(f"AquaSentinel city dashboard for {city_name}"),
        "identifier": [{"system": c.SID_CITY, "value": city_id}],
        "active": True,
        "name": f"AquaSentinel city dashboard, {city_name}",
    }
    if synthetic:
        res["meta"] = {"tag": [dict(c.SYNTHETIC_TAG)]}
    return res


def risk_engine_device(config_version: str) -> Resource:
    return {
        "resourceType": "Device",
        "text": narrative(f"AquaSentinel risk index engine, configuration {config_version}"),
        "deviceName": [{"name": "AquaSentinel vector-habitat risk index", "type": "user-friendly-name"}],
        "version": [{"value": config_version}],
    }


# ---------------------------------------------------------------- citizen findings


def finding_codes(f: m.Finding) -> tuple[Optional[str], Optional[str]]:
    """(OAH indicator code or None, AquaSentinel code or None) for a finding."""
    subject = f.subject
    if f.type == m.FindingType.larvae:
        return "diptera", "larval-posture" if subject == "larval_posture" else "larval-dip-count"
    if f.type == m.FindingType.adult_mosquito:
        return "diptera", "adult-mosquito-key"
    if f.type == m.FindingType.habitat:
        return "hydrology", None
    if f.type == m.FindingType.predator:
        if subject == "amphibians":
            return "amphibians", None
        if subject == "insectivorous_birds":
            return "birds", None
        if subject == "bats":
            return None, "bats"
        group = c.label_groups().get(f.citizen_answer or "")
        oah = {"bird": "birds", "amphibian": "amphibians"}.get(group or "")
        return oah, "predator-photo"
    return None, None


def finding_code(f: m.Finding) -> dict[str, Any]:
    oah, own = finding_codes(f)
    codings = []
    if oah:
        codings.append(c.coding(c.OAH, oah, c.OAH_DISPLAY[oah]))
    if own:
        codings.append(c.coding(c.AS, own))
    return {"coding": codings, "text": f.subject}


def finding_value(f: m.Finding) -> dict[str, Any]:
    """The citizen's own answer: a count as a Quantity, otherwise the answer as a CodeableConcept."""
    if f.count is not None and f.subject != "larval_posture":
        unit = {"larvae": "larvae", "predator": "birds" if f.subject == "insectivorous_birds" else "animals"}.get(f.type.value, "items")
        return {"valueQuantity": unit_quantity(f.count, unit)}
    if f.citizen_answer:
        return {"valueCodeableConcept": answer_concept(f.citizen_answer)}
    return {}


def ai_components(f: m.Finding) -> list[dict[str, Any]]:
    """AI suggestion, confidence, provider and the citizen's decision. Never for unanswered (pending) findings."""
    if not f.ai_label or f.status == m.FindingStatus.pending:
        return []
    out = [component(c.AS, "ai-suggestion", valueCodeableConcept=answer_concept(f.ai_label))]
    if f.ai_confidence is not None:
        out.append(component(c.AS, "ai-confidence", valueQuantity=unit_quantity(round(f.ai_confidence, 3))))
    out.append(component(c.AS, "ai-provider", valueString=f.ai_provider or "unknown"))
    out.append(component(c.AS, "citizen-decision", valueCodeableConcept={"coding": [c.coding(c.AS, f.status.value)]}))
    return out


def ai_note(f: m.Finding) -> Optional[str]:
    if not f.ai_label or f.status == m.FindingStatus.pending:
        return None
    conf = "" if f.ai_confidence is None else f", confidence {f.ai_confidence:.2f}"
    reason = f" {f.ai_reason}" if f.ai_reason else ""
    return f"AI suggestion ({f.ai_provider or 'unknown'}{conf}): {f.ai_label}.{reason} Citizen decision: {f.status.value}."


def extra_components(f: m.Finding) -> list[dict[str, Any]]:
    out = []
    if f.subject == "larval_dips":
        for n in (f.data or {}).get("dips", []):
            out.append(component(c.AS, "dip-count", valueQuantity=unit_quantity(int(n), "larvae")))
    if f.key_label and f.key_label in c.ANSWER_CODES:
        out.append(component(c.AS, "guided-key-result", valueCodeableConcept=answer_concept(f.key_label)))
    return out


def has_citizen_value(f: m.Finding) -> bool:
    return f.status != m.FindingStatus.pending and (f.count is not None or bool(f.citizen_answer))


def finding_observation(f: m.Finding, checkin: m.CheckIn, subject: str, performer: str, promoted: bool) -> Resource:
    """A citizen finding. Promoted findings with an OAH code conform to ObservationIndicatorsOah (status final)."""
    oah, _ = finding_codes(f)
    final = promoted and oah is not None
    res: Resource = {
        "resourceType": "Observation",
        "meta": meta(c.P_INDICATOR if final else c.P_CITIZEN, f.synthetic),
        "text": narrative(f"Citizen finding {f.subject} at {checkin.site_id}"),
        "identifier": [{"system": c.SID_FINDING, "value": str(f.id)}],
        "status": "final" if final else "preliminary",
        "code": finding_code(f),
        "subject": ref(subject),
        "effectiveDateTime": iso(checkin.observed_at),
        "performer": [ref(performer)],
        **finding_value(f),
    }
    comps = extra_components(f) + ai_components(f)
    if comps:
        res["component"] = comps
    note = ai_note(f)
    if note:
        res["note"] = [{"text": note}]
    return res


def dead_bird_observation(f: m.Finding, checkin: m.CheckIn, subject: str, performer: str) -> Resource:
    """Count, place and time only. No AI, identification, interpretation or cause of death."""
    return {
        "resourceType": "Observation",
        "meta": meta(c.P_DEAD_BIRD, f.synthetic),
        "text": narrative(f"Dead bird report at {checkin.site_id}: {f.count or 0} seen. No diagnosis is made."),
        "identifier": [{"system": c.SID_FINDING, "value": str(f.id)}],
        "status": "preliminary",
        "code": {"coding": [c.coding(c.AS, "dead-bird-report")]},
        "subject": ref(subject),
        "effectiveDateTime": iso(checkin.observed_at),
        "performer": [ref(performer)],
        "valueQuantity": unit_quantity(f.count or 0, "birds"),
        "note": [{"text": DEAD_BIRD_NOTE}],
    }


# ---------------------------------------------------------------- stream check answers


def answer_value(key: str, answer: Any) -> Optional[dict[str, Any]]:
    """Component value for one stream-check answer, or None if the answer is not on the question's scale."""
    info = c.answer_key_index()[key]
    scale = info["scale"]
    if scale.get("type") == "integer":
        try:
            n = int(answer)
        except (TypeError, ValueError):
            return None
        return {"valueQuantity": unit_quantity(n)} if scale["min"] <= n <= scale["max"] else None
    for opt in scale["options"]:
        if str(answer) == opt["value"]:
            return {"valueCodeableConcept": {"coding": [c.coding(c.OAH, opt["fhir_code"])]}}
    return None


def stream_check_observations(checkin: m.CheckIn, subject: str, performer: str, promoted: bool) -> list[Resource]:
    """One Observation per section (hydrology, morophology, foam); one per vegetation answer (OAH slices allow one each)."""
    index = c.answer_key_index()
    by_section: dict[str, list[dict[str, Any]]] = {}
    vegetation: list[Resource] = []
    for key, answer in sorted((checkin.answers or {}).items()):
        if key not in index:
            continue
        value = answer_value(key, answer)
        if value is None:
            continue
        info = index[key]
        if key in c.VEGETATION_COMPONENT:
            vegetation.append(_vegetation(checkin, subject, performer, promoted, info["indicator"], key, value))
        else:
            by_section.setdefault(info["section"]["id"], []).append(component(c.AS_QUESTIONS, key, **value))
    sections = {s["id"]: s for s in c.questions()["sections"]}
    out = [_section(checkin, subject, performer, promoted, sections[sid], comps) for sid, comps in by_section.items()]
    return out + vegetation


def _stream_base(checkin: m.CheckIn, subject: str, performer: str, promoted: bool, profile_url: str, indicator: str, title: str) -> Resource:
    return {
        "resourceType": "Observation",
        "meta": meta(profile_url if promoted else c.P_CITIZEN, checkin.synthetic),
        "text": narrative(f"Stream check {title} at {checkin.site_id}"),
        "status": "final" if promoted else "preliminary",
        "code": {"coding": [c.coding(c.OAH, indicator, c.OAH_DISPLAY[indicator])], "text": title},
        "subject": ref(subject),
        "effectiveDateTime": iso(checkin.observed_at),
        "performer": [ref(performer)],
    }


def _section(checkin: m.CheckIn, subject: str, performer: str, promoted: bool, section: dict[str, Any], comps: list[dict[str, Any]]) -> Resource:
    res = _stream_base(checkin, subject, performer, promoted, c.P_INDICATOR, section["fhir_indicator"], f"stream check: {section['id']}")
    res["component"] = comps
    return res


def _vegetation(checkin: m.CheckIn, subject: str, performer: str, promoted: bool, indicator: str, key: str, value: dict[str, Any]) -> Resource:
    res = _stream_base(checkin, subject, performer, promoted, c.P_VEGETATION, indicator, f"stream check: {key}")
    res["component"] = [component(c.OAH, c.VEGETATION_COMPONENT[key], **value)]
    return res


# ---------------------------------------------------------------- provenance


def reliability_extension(observer: m.Observer, reliability: Optional[float]) -> dict[str, Any]:
    tier = observer.tier.value if observer.tier.value in c.TIERS else "new"
    parts: list[dict[str, Any]] = []
    if reliability is not None:
        parts.append({"url": "dawidSkene", "valueDecimal": round(float(reliability), 4)})
    parts.append({"url": "calibrationTier", "valueCoding": c.coding(c.AS, tier)})
    kappa = (observer.calibration or {}).get("overall_kappa")
    if kappa is not None:
        parts.append({"url": "calibrationKappa", "valueDecimal": round(float(kappa), 4)})
    parts.append({"url": "method", "valueString": "MAP Dawid-Skene over the city's stream checks in the risk window, seeded with calibration agreement"})
    return {"url": c.EXT_RELIABILITY, "extension": parts}


def provenance(checkin: m.CheckIn, observer: m.Observer, targets: list[str], location_ref: str, performer: str,
               reliability: Optional[float]) -> Resource:
    return {
        "resourceType": "Provenance",
        "meta": meta(c.P_PROVENANCE, checkin.synthetic),
        "text": narrative(f"Findings of check-in {checkin.client_uuid} by {observer.id}"),
        "target": [ref(t) for t in targets],
        "recorded": iso(checkin.created_at),
        "location": ref(location_ref),
        "agent": [{
            "extension": [reliability_extension(observer, reliability)],
            "type": {"coding": [c.coding(c.PROVENANCE_TYPE, "author", "Author")]},
            "who": ref(performer),
        }],
    }


# ---------------------------------------------------------------- risk, actions, messages, summary


def week_period(week: str) -> tuple[date, date]:
    """ISO week "2026-W38" -> (Monday, Sunday)."""
    year, w = week.split("-W")
    monday = date.fromisocalendar(int(year), int(w), 1)
    return monday, monday + timedelta(days=6)


def risk_observation(score: m.RiskScore, subject: str, device: str, performer: str, window_days: int) -> Resource:
    """Risk index for one site and week. Performer is the city dashboard organisation, device the index engine."""
    end = date.fromisoformat(score.as_of) if score.as_of else week_period(score.week)[1]
    comps = [component(c.AS, "risk-band", valueCodeableConcept={"coding": [c.coding(c.AS, score.band)]})] if score.band in c.RISK_BANDS else []
    for fac in score.factors or []:
        if fac.get("name") not in c.RISK_FACTORS:
            continue
        value = fac.get("value")
        body = {"valueQuantity": unit_quantity(round(float(value), 4))} if value is not None else {
            "dataAbsentReason": {"coding": [c.coding(c.DATA_ABSENT, "not-asked", "Not Asked")]}}
        comps.append(component(c.AS, fac["name"], **body))
    comps += [
        component(c.AS, "index-range-low", valueQuantity=unit_quantity(score.range_low)),
        component(c.AS, "index-range-high", valueQuantity=unit_quantity(score.range_high)),
        component(c.AS, "site-data-coverage", valueQuantity=unit_quantity(score.coverage)),
    ]
    return {
        "resourceType": "Observation",
        "meta": meta(c.P_RISK, score.synthetic),
        "text": narrative(f"Vector-habitat risk index for {score.site_id}, {score.week}: {score.total:.2f} ({score.band})"),
        "identifier": [{"system": c.SID_RISK, "value": str(score.id)}],
        "status": "preliminary",
        "code": {"coding": [c.coding(c.AS, "vector-habitat-risk-index")]},
        "subject": ref(subject),
        "effectivePeriod": {"start": (end - timedelta(days=window_days - 1)).isoformat(), "end": end.isoformat()},
        "performer": [ref(performer)],
        "device": ref(device),
        "valueQuantity": unit_quantity(score.total),
        "component": comps,
        "note": [{"text": score.explanation + RISK_NOTE_SUFFIX}],
    }


SERVICE_CATEGORY = {  # data/measures.json "service" -> ServiceRequest category
    "sewage-inspection": "sewage-inspection",
    "water-quality": "sewage-inspection",
    "veterinary-notification": "veterinary-notification",
    "riparian-restoration": "habitat-restoration",
    "vector-habitat-verification": "vector-control-visit",
    "flow-restoration": "vector-control-visit",
    "water-retention": "vector-control-visit",
}


def action_category(action: m.Action) -> str:
    """Map an approved action to its ServiceRequest category: the measure's service in data/measures.json first,
    then keywords in the measure id, then the dominant driver."""
    from api.actions.drafting import measures

    service = measures()["measures"].get(action.measure_id, {}).get("service")
    if service in SERVICE_CATEGORY:
        return SERVICE_CATEGORY[service]
    measure = action.measure_id.lower()
    if "sewage" in measure or "pollution" in measure:
        return "sewage-inspection"
    if "veterin" in measure or action.driver == "host_signal":
        return "veterinary-notification"
    if "riparian" in measure or "vegetation" in measure or action.driver == "predator_deficit":
        return "habitat-restoration"
    return "vector-control-visit"


def service_request(action: m.Action, subject: str, requester: str, reason: Optional[str]) -> Resource:
    category = action_category(action)
    notes = [f"Drafted from the dominant driver {action.driver} (measure {action.measure_id}) and approved by a city officer. {action.rationale}"]
    if action.decision_note:
        notes.append(action.decision_note)
    if category == "veterinary-notification":
        notes.append("Routing only. No diagnosis is made or implied. Do not touch dead birds.")
    res: Resource = {
        "resourceType": "ServiceRequest",
        "meta": meta(c.P_ACTION, action.synthetic),
        "text": narrative(f"Approved action at {action.site_id}: {action.title}"),
        "identifier": [{"system": c.SID_ACTION, "value": str(action.id)}],
        "status": "active",
        "intent": "order",
        "category": [{"coding": [c.coding(c.AS, category)]}],
        "code": {"text": action.title},
        "subject": ref(subject),
        "authoredOn": iso(action.decided_at or action.created_at),
        "requester": ref(requester),
        "note": [{"text": n} for n in notes],
    }
    if reason:
        res["reasonReference"] = [ref(reason)]
    return res


def communication(message: m.Message, recipient: str, about: Optional[str]) -> Resource:
    kind = message.kind if message.kind in ("alert_raised", "action_taken") else "alert_raised"
    res: Resource = {
        "resourceType": "Communication",
        "meta": meta(c.P_MESSAGE, message.synthetic),
        "text": narrative(message.text),
        "identifier": [{"system": c.SID_MESSAGE, "value": str(message.id)}],
        "status": "completed",
        "category": [{"coding": [c.coding(c.AS, kind)]}],
        "recipient": [ref(recipient)],
        "sent": iso(message.created_at),
        "payload": [{"contentString": message.text}],
    }
    if about:
        res["about"] = [ref(about)]
    return res


def measure_report(city_name: str, week: str, scores: list[m.RiskScore], risk_refs: dict[int, str], reporter: str,
                   generated: datetime) -> Resource:
    monday, sunday = week_period(week)
    count = len(scores)
    mean = round(sum(s.total for s in scores) / count, 4) if count else 0.0
    strata = [{"value": {"text": s.site_id}, "measureScore": unit_quantity(s.total)} for s in sorted(scores, key=lambda s: s.site_id)]
    groups = [
        {"code": {"coding": [c.coding(c.AS, "sites-assessed")]}, "measureScore": unit_quantity(count, "sites")},
        {"code": {"coding": [c.coding(c.AS, "sites-alert")]}, "measureScore": unit_quantity(sum(s.alert for s in scores), "sites")},
        {"code": {"coding": [c.coding(c.AS, "sites-needing-data")]}, "measureScore": unit_quantity(sum(s.needs_data for s in scores), "sites")},
        {"code": {"coding": [c.coding(c.AS, "vector-habitat-risk-index")]}, "measureScore": unit_quantity(mean),
         "stratifier": [{"code": [{"coding": [c.coding(c.AS, "site")]}], "stratum": strata}]},
    ]
    res: Resource = {
        "resourceType": "MeasureReport",
        "meta": meta(c.P_CITY_WEEK, any(s.synthetic for s in scores)),
        "text": narrative(f"{city_name}, {week}: {count} sites scored, mean vector-habitat index {mean:.2f}"),
        "status": "complete",
        "type": "summary",
        "measure": c.MEASURE_URL,
        "date": iso(generated),
        "period": {"start": monday.isoformat(), "end": sunday.isoformat()},
        "reporter": ref(reporter),
        "group": groups,
    }
    evaluated = [risk_refs[s.id] for s in scores if s.id in risk_refs]
    if evaluated:
        res["evaluatedResource"] = [ref(r) for r in evaluated]
    return res
