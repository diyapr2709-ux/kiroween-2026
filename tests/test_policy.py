"""Walker: gradients, determinism, beam decoding, learning on a toy graph, path for every answer."""
import math

import numpy as np
import pytest

from hollerith import Deck
from hollerith.graph import Graph
from hollerith.policy import Policy, _bfs_masked


def toy_deck() -> Deck:
    """A graph where the held-out fact has an alternative 2-hop path that depends on the relation.

    Pattern: X WORKED AT A, A MERGED INTO B  =>  X WORKED AT B (composition WORKED AT ∘ MERGED INTO).
    """
    d = Deck()
    for i in range(12):
        x, a, b = f"P{i}", f"CO{i}", f"BIG{i % 4}"
        d.punch(x, "WORKED AT", a, "WIKI")
        d.punch(a, "MERGED INTO", b, "WIKI")
        d.punch(x, "WORKED AT", b, "WIKI")
        d.punch(x, "BORN IN", f"TOWN{i % 3}", "WIKI")
    return d


@pytest.fixture(scope="module")
def toy():
    deck = toy_deck()
    facts = [f for f in deck.facts() if f.relation == "WORKED AT" and f.object.startswith("BIG")]
    train, test = facts[:9], facts[9:]
    keep = {f.triple() for f in test} | {(f.object, "EMPLOYED", f.subject) for f in test}
    graph = Graph([f for f in deck.facts() if f.triple() not in keep])
    return deck, graph, train, test


def _fit(mode: str, toy, seed: int = 0, **kw) -> Policy:
    deck, graph, train, test = toy
    p = Policy(mode=mode, hops=3, dim=16, epochs=kw.pop("epochs", 30), rollouts=10, lr=0.1, **kw)
    p.fit(graph, train, [], seed)
    return p


def test_bfs_masked_finds_alternative_path(toy) -> None:
    deck, graph, train, test = toy
    f = train[0]
    path = _bfs_masked(graph, f.subject, f.object, 3, {f.triple(), (f.object, "EMPLOYED", f.subject)})
    assert path is not None and [x.relation for x in path] == ["WORKED AT", "MERGED INTO"]


@pytest.mark.parametrize("mode", ["sl", "rl"])
def test_learns_the_composition_on_held_out_facts(mode, toy) -> None:
    deck, graph, train, test = toy
    p = _fit(mode, toy, epochs=40)
    hits = sum(p.walk(f.subject, f.relation).answer == f.object for f in test)
    assert hits >= 2, f"{mode}: {hits}/3 held-out facts answered"
    res = p.walk(test[0].subject, test[0].relation)
    assert res.path and res.answer == res.path[-1].object  # the deck ends on the answer


@pytest.mark.parametrize("mode", ["sl", "rl"])
def test_deterministic_under_seed(mode, toy) -> None:
    a, b = _fit(mode, toy, seed=3, epochs=5), _fit(mode, toy, seed=3, epochs=5)
    assert np.allclose(a.R, b.R) and np.allclose(a.E, b.E)
    c = _fit(mode, toy, seed=4, epochs=5)
    assert not np.allclose(a.R, c.R)


def test_scores_are_log_probs_and_every_scored_entity_has_a_path(toy) -> None:
    deck, graph, train, test = toy
    p = _fit("sl", toy, epochs=5)
    f = test[0]
    for e, lp, path, probs in p.beam_search(f.subject, f.relation):
        assert lp <= 0 and len(probs) == 3
        assert (path and path[-1].object == e) or (not path and e == f.subject)
    sc = p.scores(f.subject, f.relation)
    assert f.subject not in sc  # staying put is not an answer


def test_unknown_entity_or_relation_gives_no_answer(toy) -> None:
    p = _fit("sl", toy, epochs=2)
    assert p.walk("NOBODY", "WORKED AT").answer is None
    assert p.walk("P0", "KNOWS").answer is None
    assert p.scores("NOBODY", "WORKED AT") == {}


def test_gradient_matches_finite_difference(toy) -> None:
    """Closed-form ∇ log π(a) checked against a numerical derivative on one step."""
    deck, graph, train, test = toy
    p = Policy(mode="sl", hops=2, dim=8, epochs=0)
    p.fit(graph, train, [], seed=0)
    s, rq = train[0].subject, train[0].relation
    acts = p._actions(s, set())
    ri, ei = p._features(acts, s)
    rq_i = p.ridx[rq]
    a = 0

    def logp() -> float:
        q = p.R[rq_i]
        return math.log(p._softmax(p._scores(q, ri, ei))[a])

    q = p.R[rq_i].copy()
    probs = p._softmax(p._scores(q, ri, ei))
    gR, gE = np.zeros_like(p.R), np.zeros_like(p.E)
    p._accumulate(gR, gE, [(q, ri, ei, probs, a, rq_i, [])], lambda pr: (1.0, 0.0))
    eps = 1e-5
    for idx in [(rq_i, 0), (ri[a], 1), (rq_i, 3)]:
        base = logp()
        p.R[idx] += eps
        num = (logp() - base) / eps
        p.R[idx] -= eps
        assert abs(num - gR[idx]) < 1e-3, (idx, num, gR[idx])
    e_idx = (ei[a], 2)
    base = logp()
    p.E[e_idx] += eps
    num = (logp() - base) / eps
    p.E[e_idx] -= eps
    assert abs(num - gE[e_idx]) < 1e-3


def test_invalid_mode() -> None:
    with pytest.raises(ValueError):
        Policy(mode="qlearning")
