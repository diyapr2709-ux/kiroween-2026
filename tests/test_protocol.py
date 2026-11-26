"""Mutation-killing protocol tests from the Loop 2 review: no test card is ever walkable,
the evaluator never hands a system the full deck, masking is real, and the history gradient is right.
"""
import math
from pathlib import Path

import numpy as np
import pytest

from hollerith import Deck
from hollerith.baselines import Ranker
from hollerith.code_table import INVERSE
from hollerith.evaluate import evaluate_system, filtered_rank
from hollerith.graph import Graph
from hollerith.policy import Policy
from hollerith.split import make_folds, walking_graph

REPO = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def deck() -> Deck:
    return Deck.load(REPO / "data" / "cards.deck")


@pytest.fixture(scope="module")
def folds(deck):
    return make_folds(deck, k=5, seed=0, hops=4)


class SpyRanker(Ranker):
    """Records the graph it is fitted on and answers nothing."""
    name = "spy"

    def __init__(self) -> None:
        self.graphs = []

    def fit(self, graph, train_facts, val_facts, seed) -> None:
        self.graphs.append((graph, list(train_facts), list(val_facts)))

    def scores(self, subject, relation):
        return {}


def test_evaluator_never_fits_on_a_test_card(deck, folds) -> None:
    spy = SpyRanker()
    evaluate_system(spy, folds, deck, seeds=[0])
    assert len(spy.graphs) == len(folds)
    for fold, (graph, train, val) in zip(folds, spy.graphs):
        walkable = graph.triples()
        assert len(walkable) < len(deck.facts())  # not the full deck
        for f in fold.test:
            assert f.triple() not in walkable
            assert (f.object, INVERSE[f.relation], f.subject) not in walkable
        for f in fold.excluded:
            assert f.triple() not in walkable
        assert {f.triple() for f in train} <= walkable and {f.triple() for f in val} <= walkable


def test_every_beam_path_card_is_walkable(deck, folds) -> None:
    """Proof by exhaustion on one fold: no test, inverse-of-test or excluded card appears in any beam path."""
    fold = folds[0]
    g = walking_graph(fold, deck)
    forbidden = {f.triple() for f in fold.test} | {(f.object, INVERSE[f.relation], f.subject) for f in fold.test} \
        | {f.triple() for f in fold.excluded}
    p = Policy(mode="sl", epochs=3, hops=4)
    p.fit(g, fold.train, fold.val, seed=0)
    assert p.g is g
    n_cards = 0
    for q in fold.queries:
        if not q.answerable:
            continue
        for e, lp, path, probs in p.beam_search(q.subject, q.relation):
            for card in path:
                assert card.triple() in g.triples() and card.triple() not in forbidden
                n_cards += 1
    assert n_cards > 100


def test_training_masks_the_query_card_and_its_inverse(deck, folds) -> None:
    fold = folds[0]
    g = walking_graph(fold, deck)
    p = Policy(mode="sl", epochs=0, hops=4)
    p.fit(g, fold.train, fold.val, seed=0)
    f = fold.train[0]
    masked = p._masked(f.subject, f.relation, f.object)
    acts = p._actions(f.subject, masked)
    assert all(a is None or a.triple() != f.triple() for a in acts)
    inv_acts = p._actions(f.object, masked)
    assert all(a is None or a.triple() != (f.object, INVERSE[f.relation], f.subject) for a in inv_acts)
    assert len(p._actions(f.subject, set())) > len(acts)  # masking removed something


def test_subject_is_filtered_for_every_system(deck, folds) -> None:
    target = next(q.gold for q in folds[0].queries if q.answerable)

    class SubjectLover(Ranker):
        """Puts all its mass on the query entity itself, then on `target`."""
        name = "lover"

        def fit(self, graph, train_facts, val_facts, seed):
            pass

        def scores(self, subject, relation):
            return {subject: 10.0, target: 1.0}

    res = evaluate_system(SubjectLover(), folds[:1], deck, seeds=[0])
    hits = [r for r, q in zip(res, folds[0].queries) if q.gold == target and q.answerable]
    misses = [r for r, q in zip(res, folds[0].queries) if q.gold != target and q.answerable]
    assert hits and all(r.rank == 1.0 for r in hits)       # subject removed, target is alone at the top
    assert misses and all(math.isinf(r.rank) for r in misses)  # the subject's mass never ranks anything


def test_history_gradient_matches_finite_difference(deck, folds) -> None:
    g = walking_graph(folds[0], deck)
    p = Policy(mode="sl", epochs=0, hops=4, dim=6)
    p.fit(g, folds[0].train, folds[0].val, seed=1)
    s = g.entities[5]
    rq_i = p.ridx["WORKED AT"]
    hist = [p.ridx["FOUNDED"], p.ridx["LED"]]
    acts = p._actions(s, set())
    ri, ei = p._features(acts, s)
    a = 0

    def logp() -> float:
        q = p.R[rq_i] + p.R[hist].mean(axis=0)
        return math.log(p._softmax(p._scores(q, ri, ei))[a])

    q = p.R[rq_i] + p.R[hist].mean(axis=0)
    probs = p._softmax(p._scores(q, ri, ei))
    gR, gE = np.zeros_like(p.R), np.zeros_like(p.E)
    p._accumulate(gR, gE, [(q, ri, ei, probs, a, rq_i, hist)], lambda pr: (1.0, 0.0))
    eps = 1e-6
    worst = 0.0
    for idx in [(hist[0], 2), (hist[1], 4), (rq_i, 1), (ri[a], 0)]:
        p.R[idx] += eps
        up = logp()
        p.R[idx] -= 2 * eps
        down = logp()
        p.R[idx] += eps
        worst = max(worst, abs((up - down) / (2 * eps) - gR[idx]))
    assert worst < 1e-5, worst


def test_simple_paths_flag_changes_name_and_forbids_revisits(deck, folds) -> None:
    g = walking_graph(folds[0], deck)
    a = Policy(mode="sl", epochs=2, hops=4, simple_paths=True)
    a.fit(g, folds[0].train, folds[0].val, seed=0)
    assert a.name == "policy_sl_simple"
    for q in folds[0].queries[:30]:
        for e, lp, path, probs in a.beam_search(q.subject, q.relation):
            ents = [q.subject] + [c.object for c in path]
            assert len(set(ents)) == len(ents)
    b = Policy(mode="sl", epochs=0, hops=4)
    assert b.name == "policy_sl" and b.simple_paths is False
