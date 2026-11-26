"""Baselines (ADR-001 §4). Both are deterministic; `seed` is accepted for interface parity.

RandomWalk  — exact T-step distribution from the query entity over the training graph, action
              space = out-cards ∪ NO_OP (stay), uniform. Computed as row s of Pᵀ with numpy, so
              it has no sampling variance. Score(o) = probability mass at o after T steps;
              zero mass means "unreached" (rank ∞).
Frequency   — most frequent tail for the query relation in the training cards. Score(o) = count
              of (·, r, o) in train; zero means unreached.
"""
from __future__ import annotations

import numpy as np

from .graph import Graph


class Ranker:
    """Interface every system implements. `scores` maps entity -> score; absent = unreached."""

    name = "ranker"

    def fit(self, train: Graph, val: Graph | None, seed: int) -> None:  # pragma: no cover - interface
        raise NotImplementedError

    def scores(self, subject: str, relation: str) -> dict[str, float]:  # pragma: no cover - interface
        raise NotImplementedError


class RandomWalk(Ranker):
    name = "random_walk"

    def __init__(self, hops: int = 3) -> None:
        self.hops = hops

    def fit(self, train: Graph, val: Graph | None, seed: int) -> None:
        self.g = train
        n = len(train.entities)
        P = np.zeros((n, n), dtype=np.float64)
        for e, i in train.index.items():
            outs = train.edges(e)
            deg = len(outs) + 1  # + NO_OP
            P[i, i] += 1.0 / deg
            for f in outs:
                P[i, train.index[f.object]] += 1.0 / deg
        self.PT = np.linalg.matrix_power(P, self.hops)

    def scores(self, subject: str, relation: str) -> dict[str, float]:
        if subject not in self.g.index:
            return {}
        row = self.PT[self.g.index[subject]]
        return {self.g.entities[j]: float(row[j]) for j in np.nonzero(row > 0)[0]}


class Frequency(Ranker):
    name = "frequency"

    def fit(self, train: Graph, val: Graph | None, seed: int) -> None:
        counts: dict[str, dict[str, int]] = {}
        for f in train.facts:
            counts.setdefault(f.relation, {})
            counts[f.relation][f.object] = counts[f.relation].get(f.object, 0) + 1
        self.counts = counts

    def scores(self, subject: str, relation: str) -> dict[str, float]:
        return {o: float(c) for o, c in self.counts.get(relation, {}).items()}


BASELINES: dict[str, type[Ranker]] = {RandomWalk.name: RandomWalk, Frequency.name: Frequency}
