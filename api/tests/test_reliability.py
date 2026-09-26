from __future__ import annotations

import random

import numpy as np
import pytest

from api.reliability.dawid_skene import dawid_skene, majority_vote
from api.reliability.kappa import cohen_kappa, confusions, tier_for


# ------------------------------------------------------------------ kappa


def test_kappa_perfect_and_chance() -> None:
    ref = ["a", "b", "a", "b"]
    assert cohen_kappa(ref, ref) == 1.0
    assert cohen_kappa(ref, ["b", "a", "b", "a"]) == pytest.approx(-1.0)
    assert cohen_kappa(["a", "a", "a"], ["a", "a", "a"]) == 1.0  # single class, perfect
    assert cohen_kappa(["a", "a", "a"], ["b", "b", "b"]) == 0.0


def test_kappa_known_value() -> None:
    # Classic 2x2 example: po = 0.7, pe = 0.5 -> kappa 0.4
    ref = ["y"] * 5 + ["n"] * 5
    ans = ["y"] * 4 + ["n"] + ["y"] * 2 + ["n"] * 3
    assert cohen_kappa(ref, ans) == pytest.approx(0.4)


def test_kappa_rejects_bad_input() -> None:
    with pytest.raises(ValueError):
        cohen_kappa([], [])


def test_tiers() -> None:
    assert tier_for(None) == "new"
    assert tier_for(0.2) == "new"
    assert tier_for(0.5) == "calibrated"
    assert tier_for(0.85) == "trusted"


def test_confusions_sorted() -> None:
    out = confusions([("bank", "extensive", "absent"), ("bank", "extensive", "absent"), ("flow", "present", "absent"), ("flow", "a", "a")])
    assert out[0].count == 2 and out[0].reference == "extensive"
    assert len(out) == 2


# ------------------------------------------------------------------ Dawid-Skene


def simulate(n_items: int, accuracies: list[float], classes=("absent", "present", "extensive"), seed=0,
             bias: dict[int, dict[str, str]] | None = None):
    rng = random.Random(seed)
    truth = {i: rng.choice(classes) for i in range(n_items)}
    labels = []
    for i, true in truth.items():
        for o, acc in enumerate(accuracies):
            b = (bias or {}).get(o, {})
            if true in b and rng.random() < 0.9:
                lab = b[true]
            elif rng.random() < acc:
                lab = true
            else:
                lab = rng.choice([c for c in classes if c != true])
            labels.append((i, f"o{o}", lab))
    return truth, labels


def accuracy(est: dict, truth: dict) -> float:
    return sum(est[i] == truth[i] for i in truth) / len(truth)


def test_em_converges_and_log_likelihood_never_decreases() -> None:
    _, labels = simulate(150, [0.9, 0.8, 0.6, 0.4, 0.4])
    res = dawid_skene(labels, classes=["absent", "present", "extensive"])
    assert res.converged
    diffs = np.diff(res.log_likelihood)
    assert (diffs > -1e-6).all()
    assert np.allclose(res.posterior.sum(axis=1), 1.0)
    assert np.allclose(res.confusion.sum(axis=2), 1.0)


def test_em_beats_majority_with_mixed_observers() -> None:
    truth, labels = simulate(300, [0.95, 0.9, 0.45, 0.45, 0.4], seed=3)
    ds = dawid_skene(labels, classes=["absent", "present", "extensive"]).estimates()
    mv = majority_vote(labels)
    assert accuracy(ds, truth) > accuracy(mv, truth)


def test_em_learns_a_systematic_bias() -> None:
    # observer 0 reports extensive as absent; EM should learn that and undo it
    truth, labels = simulate(300, [0.9, 0.85, 0.85], seed=5, bias={0: {"extensive": "absent"}})
    res = dawid_skene(labels, classes=["absent", "present", "extensive"])
    o0 = res.observers.index("o0")
    k_ext, k_abs = res.classes.index("extensive"), res.classes.index("absent")
    assert res.confusion[o0, k_ext, k_abs] > 0.7
    rel = res.reliability()
    assert rel["o0"] < rel["o1"]


def test_single_observer_returns_their_answers() -> None:
    labels = [(i, "solo", lab) for i, lab in enumerate(["a", "b", "a", "a", "b"])]
    res = dawid_skene(labels)
    assert res.estimates() == {i: lab for i, _, lab in labels}


def test_single_item_single_answer() -> None:
    res = dawid_skene([("site-week", "o1", "present")], classes=["absent", "present"])
    assert res.estimate("site-week") == "present"


def test_unanimous_observers_give_high_confidence() -> None:
    labels = [(i, f"o{o}", "present" if i % 2 else "absent") for i in range(10) for o in range(4)]
    res = dawid_skene(labels)
    for i in range(10):
        assert res.estimate(i) == ("present" if i % 2 else "absent")
        assert res.confidence(i) > 0.95


def test_calibration_prior_breaks_a_tie_toward_the_reliable_observer() -> None:
    labels = [("x", "good", "extensive"), ("x", "poor", "absent")]
    classes = ["absent", "present", "extensive"]
    res = dawid_skene(labels, classes=classes, prior_accuracy={"good": 0.95, "poor": 0.4}, prior_strength=10)
    assert res.estimate("x") == "extensive"


def test_unknown_label_rejected() -> None:
    with pytest.raises(ValueError):
        dawid_skene([("x", "o", "purple")], classes=["absent"])
    with pytest.raises(ValueError):
        dawid_skene([])


# ------------------------------------------------------------------ calibration


def test_reference_set_is_labelled_by_construction_never_ai() -> None:
    from api.reliability.calibration import reference_items

    items = reference_items()
    assert len(items) >= 15
    for it in items:
        assert it["labelled_by"] in ("construction", "team panel", "expert")
        assert "ai" not in it["labelled_by"].lower()
        assert it["synthetic"] is True


def test_public_items_hide_answers() -> None:
    from api.reliability.calibration import public_items

    assert all("answer" not in it and "rationale" not in it for it in public_items())


def test_perfect_round_is_trusted() -> None:
    from api.reliability.calibration import reference_items, score

    out = score({it["id"]: it["answer"] for it in reference_items()})
    assert out["overall_kappa"] == 1.0 and out["tier"] == "trusted" and out["feedback"] == []


def test_bank_bias_is_explained() -> None:
    from api.reliability.calibration import reference_items, score

    answers = {it["id"]: it["answer"] for it in reference_items()}
    answers["rs01"] = "absent"  # concrete rated as natural
    answers["rs02"] = "present"  # mossy concrete rated as partly natural
    out = score(answers)
    top = out["feedback"][0]
    assert top["key"] == "calib.fb.bank_CC.under" and top["count"] == 2
    assert out["per_question"]["bank_CC"]["kappa"] < 1.0


def test_posture_confusion_is_a_swap() -> None:
    from api.reliability.calibration import direction

    assert direction("posture", "angled", "flat") == "swap"
    assert direction("cover5", "5", "2") == "under"
    assert direction("ape", "absent", "extensive") == "over"


def test_calibration_endpoint_sets_tier(client) -> None:  # type: ignore[no-untyped-def]
    from api.reliability.calibration import reference_items

    oid = client.put("/api/observers/OBS-CAL123", json={}).json()["id"]
    items = client.get("/api/calibration/items").json()
    assert len(items) == len(reference_items())
    wrong = {it["id"]: "absent" for it in reference_items()}
    res = client.post(f"/api/calibration/{oid}", json={"answers": wrong}).json()
    assert res["tier"] == "new"
    right = {it["id"]: it["answer"] for it in reference_items()}
    res = client.post(f"/api/calibration/{oid}", json={"answers": right}).json()
    assert res["tier"] == "trusted"
    obs = client.get(f"/api/observers/{oid}").json()
    assert obs["tier"] == "trusted" and obs["calibration"]["overall_kappa"] == 1.0
    assert client.post(f"/api/calibration/{oid}", json={"answers": {}}).status_code == 422


def test_class_prior_does_not_collapse_with_single_label_items() -> None:
    # Regression: plain EM put all items in one class when every item had one label from a different observer.
    rng = random.Random(1)
    classes = ("absent", "present", "extensive")
    labels = [(i, f"o{rng.randrange(40)}", rng.choice(classes)) for i in range(120)]
    res = dawid_skene(labels, classes=classes)
    assert res.prior.max() < 0.6
    assert res.estimates() == {i: lab for i, _, lab in labels}
    collapsed = dawid_skene(labels, classes=classes, default_accuracy=None, class_prior_share=0.0)
    assert sum(collapsed.estimates()[i] == lab for i, _, lab in labels) < 110  # documents the failure the priors fix
