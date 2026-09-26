"""Synthetic observers and check-ins with a known ground truth.

Everything produced here is labelled ``synthetic: true``. Each site gets a latent
true state; each observer has a latent confusion pattern (for example a habit of
rating hard banks as natural). Check-in answers are drawn from those, so the
reliability engine can be scored against a truth we control.
"""

from __future__ import annotations

import random
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

APE = ("absent", "present", "extensive")
COVER = ("1", "2", "3", "4", "5")

# Questions that carry a latent site-level truth in the scenario.
LATENT_QUESTIONS = ("flow_NP", "sub_OM", "bank_right_CC", "bank_left_CC", "water_sewage_smell", "rip_trees")


@dataclass
class SiteTruth:
    site_id: str
    answers: dict[str, str]
    larvae_mean: float  # expected larvae per dip
    culex_share: float  # share of larvae resting at an angle (Culex-type)
    amphibians: bool
    insectivorous_birds: int
    dead_birds: int


@dataclass
class ObserverProfile:
    code: str
    accuracy: float  # probability of reporting the true class
    bias: dict[str, dict[str, str]] = field(default_factory=dict)  # question -> {true: reported}
    team: str = ""


def site_truth(site_id: str, degradation: float, rng: random.Random) -> SiteTruth:
    """Latent site state from a degradation level in [0, 1]."""

    def ape(p: float) -> str:
        r = rng.random()
        return "extensive" if r < p * 0.6 else "present" if r < p else "absent"

    answers = {
        "flow_NP": ape(0.25 + 0.6 * degradation),
        "sub_OM": ape(0.2 + 0.6 * degradation),
        "bank_right_CC": ape(degradation),
        "bank_left_CC": ape(degradation),
        "water_sewage_smell": ape(0.7 * degradation - 0.1),
        "rip_trees": COVER[max(0, min(4, int(round(4 * (1 - degradation) + rng.gauss(0, 0.6)))))],
    }
    stagnant = answers["flow_NP"] != "absent"
    return SiteTruth(
        site_id=site_id,
        answers=answers,
        larvae_mean=(1.0 + 9.0 * degradation) if stagnant else 0.3,
        culex_share=0.85,
        amphibians=rng.random() > degradation,
        insectivorous_birds=max(0, int(round(6 * (1 - degradation) + rng.gauss(0, 1)))),
        dead_birds=1 if degradation > 0.75 and rng.random() < 0.35 else 0,
    )


def observer_profiles(n: int, rng: random.Random) -> list[ObserverProfile]:
    teams = ("Mondego Stream Keepers", "Vale das Flores School", "Coimbra Birders")
    profiles = []
    for i in range(n):
        accuracy = rng.choice((0.92, 0.85, 0.75, 0.6))
        bias: dict[str, dict[str, str]] = {}
        if i % 4 == 1:  # rates hard banks as natural
            bias["bank_right_CC"] = {"present": "absent", "extensive": "present"}
            bias["bank_left_CC"] = {"present": "absent", "extensive": "present"}
        if i % 5 == 2:  # over-reports stagnant water
            bias["flow_NP"] = {"absent": "present"}
        profiles.append(ObserverProfile(code=f"OBS-SYN{i:03d}", accuracy=accuracy, bias=bias, team=teams[i % 3]))
    return profiles


def report(true: str, question: str, scale: tuple[str, ...], obs: ObserverProfile, rng: random.Random) -> str:
    """Reported answer given the true class and the observer's confusion pattern."""
    biased = obs.bias.get(question, {}).get(true)
    if biased is not None and rng.random() < 0.8:
        return biased
    if rng.random() < obs.accuracy:
        return true
    return rng.choice([v for v in scale if v != true])


def make_checkin(truth: SiteTruth, obs: ObserverProfile, when: datetime, rng: random.Random, lat: float, lon: float) -> dict[str, Any]:
    answers = {
        q: report(v, q, COVER if q == "rip_trees" else APE, obs, rng) for q, v in truth.answers.items()
    }
    findings: list[dict[str, Any]] = []
    dips = [max(0, int(rng.expovariate(1 / truth.larvae_mean))) if truth.larvae_mean > 0 else 0 for _ in range(5)]
    findings.append({"type": "larvae", "subject": "larval_dips", "count": sum(dips), "data": {"dips": dips}, "status": "manual", "synthetic": True})
    if sum(dips):
        posture = "angled" if rng.random() < truth.culex_share else "flat"
        findings.append({
            "type": "larvae", "subject": "larval_posture", "citizen_answer": posture,
            "key_label": "culex_type" if posture == "angled" else "anopheles_type",
            "status": "manual", "synthetic": True,
        })
    findings.append({
        "type": "predator", "subject": "amphibians",
        "citizen_answer": ("heard" if rng.random() < 0.6 else "seen") if truth.amphibians and rng.random() < obs.accuracy else "none",
        "status": "manual", "synthetic": True,
    })
    findings.append({"type": "predator", "subject": "bats", "citizen_answer": "seen" if truth.amphibians and rng.random() < 0.5 else "none",
                     "status": "manual", "synthetic": True})
    findings.append({
        "type": "predator", "subject": "insectivorous_birds",
        "count": max(0, truth.insectivorous_birds + rng.choice((-1, 0, 0, 1))), "status": "manual", "synthetic": True,
    })
    if truth.dead_birds:
        findings.append({"type": "dead_bird", "subject": "dead_bird", "count": truth.dead_birds, "status": "manual", "synthetic": True})
    return {
        "client_uuid": str(uuid.UUID(int=rng.getrandbits(128))),
        "site_id": truth.site_id,
        "observer_id": obs.code,
        "observed_at": when.isoformat(),
        "lat": lat + rng.uniform(-0.0004, 0.0004),
        "lon": lon + rng.uniform(-0.0004, 0.0004),
        "consent": True,
        "answers": answers,
        "findings": findings,
        "synthetic": True,
    }


def scenario(sites: list[dict[str, Any]], city_id: str = "CO", weeks: int = 6, observers: int = 12, seed: int = 42,
             end: datetime | None = None) -> tuple[list[ObserverProfile], list[SiteTruth], list[dict[str, Any]]]:
    """Build a synthetic season for one city. Returns observers, truths and check-in payloads."""
    rng = random.Random(seed)
    end = end or datetime(2026, 9, 20, 9, 0, tzinfo=timezone.utc)
    city_sites = [s for s in sites if s["city"]["id"] == city_id]
    profiles = observer_profiles(observers, rng)
    truths = [site_truth(s["code"], rng.betavariate(1.6, 1.8), rng) for s in city_sites]
    by_code = {s["code"]: s for s in city_sites}
    checkins = []
    for week in range(weeks):
        for truth in truths:
            for obs in rng.sample(profiles, k=rng.choice((0, 1, 1, 2, 3))):
                when = end - timedelta(weeks=weeks - 1 - week, days=rng.randint(0, 6), hours=rng.randint(0, 8))
                site = by_code[truth.site_id]
                checkins.append(make_checkin(truth, obs, when, rng, site["latitude"], site["longitude"]))
    return profiles, truths, checkins
