"""Dawid-Skene EM for one categorical question.

Dawid, A. P. and Skene, A. M. (1979). Maximum likelihood estimation of observer
error-rates using the EM algorithm. Journal of the Royal Statistical Society C, 28(1), 20-28.

Items are (site, week) pairs; each observer may answer an item zero or more
times. The model learns a class prior and one confusion matrix per observer,
then returns a posterior over the true class for every item. Calibration
results can seed each observer's confusion matrix with a prior accuracy, which
matters most when an observer has few overlapping items.
"""

from __future__ import annotations

from collections.abc import Hashable, Sequence
from dataclasses import dataclass, field

import numpy as np

Label = Hashable
ItemId = Hashable
ObserverId = Hashable


@dataclass
class DSResult:
    classes: list[Label]
    items: list[ItemId]
    observers: list[ObserverId]
    posterior: np.ndarray  # items x classes
    prior: np.ndarray  # classes
    confusion: np.ndarray  # observers x true class x reported class
    iterations: int
    converged: bool
    log_likelihood: list[float] = field(default_factory=list)

    def estimate(self, item: ItemId) -> Label:
        return self.classes[int(np.argmax(self.posterior[self.items.index(item)]))]

    def estimates(self) -> dict[ItemId, Label]:
        return {item: self.classes[int(i)] for item, i in zip(self.items, np.argmax(self.posterior, axis=1))}

    def confidence(self, item: ItemId) -> float:
        return float(np.max(self.posterior[self.items.index(item)]))

    def reliability(self) -> dict[ObserverId, float]:
        """Expected accuracy of each observer: sum over classes of prior times diagonal."""
        diag = np.einsum("okk->ok", self.confusion)
        return {obs: float(diag[i] @ self.prior) for i, obs in enumerate(self.observers)}


def majority_vote(labels: Sequence[tuple[ItemId, ObserverId, Label]]) -> dict[ItemId, Label]:
    """Plain majority; ties broken by the first label seen for the item."""
    counts: dict[ItemId, dict[Label, int]] = {}
    for item, _obs, label in labels:
        counts.setdefault(item, {}).setdefault(label, 0)
        counts[item][label] += 1
    return {item: max(c, key=lambda k: c[k]) for item, c in counts.items()}


def dawid_skene(
    labels: Sequence[tuple[ItemId, ObserverId, Label]],
    classes: Sequence[Label] | None = None,
    prior_accuracy: dict[ObserverId, float] | None = None,
    prior_strength: float = 2.0,
    default_accuracy: float | None = 0.7,
    class_prior_share: float = 1 / 3,
    smoothing: float = 0.01,
    max_iter: int = 200,
    tol: float = 1e-6,
) -> DSResult:
    """Run EM. ``labels`` is a list of (item, observer, reported class).

    ``prior_accuracy`` maps observers to an accuracy from calibration; it adds
    ``prior_strength`` pseudo-observations spread according to that accuracy.
    Observers without a calibration get ``default_accuracy`` (a Bayesian
    Dawid-Skene prior). Without it EM overfits when observers have few labels:
    in our simulation plain EM recovered fewer true classes than majority vote
    for panels of one to three observers. Pass ``default_accuracy=None`` for
    the original maximum-likelihood estimator.
    ``smoothing`` keeps every confusion cell positive so logs stay finite.
    """
    if not labels:
        raise ValueError("No labels")
    cls = list(classes) if classes is not None else sorted({lab for _, _, lab in labels}, key=str)
    items = list(dict.fromkeys(i for i, _, _ in labels))
    observers = list(dict.fromkeys(o for _, o, _ in labels))
    k_of = {c: n for n, c in enumerate(cls)}
    i_of = {c: n for n, c in enumerate(items)}
    o_of = {c: n for n, c in enumerate(observers)}
    n_i, n_o, n_k = len(items), len(observers), len(cls)

    # counts[i, o, l] = times observer o reported class l for item i
    counts = np.zeros((n_i, n_o, n_k))
    for item, obs, lab in labels:
        if lab not in k_of:
            raise ValueError(f"Label {lab!r} not in classes {cls}")
        counts[i_of[item], o_of[obs], k_of[lab]] += 1

    class_prior_alpha = class_prior_share * n_i
    pseudo = _prior_pseudo_counts(observers, n_k, prior_accuracy, prior_strength, default_accuracy)

    # Initialise with soft majority vote
    t = counts.sum(axis=1) + 1e-9
    t /= t.sum(axis=1, keepdims=True)

    history: list[float] = []
    converged = False
    it = 0
    for it in range(1, max_iter + 1):
        prior, confusion = _m_step(t, counts, pseudo, smoothing, class_prior_alpha)
        t, ll = _e_step(counts, prior, confusion)
        history.append(ll)
        if len(history) > 1 and abs(history[-1] - history[-2]) < tol * max(1.0, abs(history[-2])):
            converged = True
            break
    prior, confusion = _m_step(t, counts, pseudo, smoothing, class_prior_alpha)
    return DSResult(cls, items, observers, t, prior, confusion, it, converged, history)


def _prior_pseudo_counts(observers: list[ObserverId], n_k: int, prior_accuracy: dict[ObserverId, float] | None,
                         strength: float, default_accuracy: float | None) -> np.ndarray:
    pseudo = np.zeros((len(observers), n_k, n_k))
    for o, obs in enumerate(observers):
        acc = (prior_accuracy or {}).get(obs, default_accuracy)
        if acc is None:
            continue
        acc = float(np.clip(acc, 1.0 / n_k, 0.999))
        off = (1 - acc) / (n_k - 1) if n_k > 1 else 0.0
        pseudo[o] = strength * (np.full((n_k, n_k), off) + np.eye(n_k) * (acc - off))
    return pseudo


def _m_step(t: np.ndarray, counts: np.ndarray, pseudo: np.ndarray, smoothing: float,
            class_prior_alpha: float = 0.0) -> tuple[np.ndarray, np.ndarray]:
    alpha = smoothing + class_prior_alpha
    prior = (t.sum(axis=0) + alpha) / (t.shape[0] + alpha * t.shape[1])
    # confusion[o, k, l] = sum_i t[i, k] * counts[i, o, l]
    confusion = np.einsum("ik,iol->okl", t, counts) + pseudo + smoothing
    confusion /= confusion.sum(axis=2, keepdims=True)
    return prior, confusion


def _e_step(counts: np.ndarray, prior: np.ndarray, confusion: np.ndarray) -> tuple[np.ndarray, float]:
    # log p(item answers | true k) = sum_o sum_l counts[i,o,l] * log confusion[o,k,l]
    log_like = np.einsum("iol,okl->ik", counts, np.log(confusion)) + np.log(prior)
    m = log_like.max(axis=1, keepdims=True)
    post = np.exp(log_like - m)
    norm = post.sum(axis=1, keepdims=True)
    ll = float((np.log(norm) + m).sum())
    return post / norm, ll
