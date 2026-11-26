"""Split correctness, leakage gate, reachability, filtered ranking, baselines."""
import math
from pathlib import Path

import pytest

from hollerith import Deck
from hollerith.baselines import Frequency, RandomWalk
from hollerith.code_table import RELATIONS
from hollerith.evaluate import evaluate_system, filtered_rank, run, summarise
from hollerith.graph import Graph, forward_facts, with_inverses
from hollerith.split import assert_no_leakage, make_folds, write_folds

REPO = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def deck() -> Deck:
    return Deck.load(REPO / "data" / "cards.deck")


@pytest.fixture(scope="module")
def folds(deck):
    return make_folds(deck, k=5, seed=0, hops=3)


def test_every_testable_fact_is_tested_exactly_once(deck, folds) -> None:
    from hollerith.split import testable_facts
    facts = testable_facts(deck)
    tested = [f.triple() for fold in folds for f in fold.test]
    assert sorted(tested) == sorted(f.triple() for f in facts)
    assert len(set(tested)) == len(facts)


def test_two_queries_per_test_fact_in_both_directions(folds) -> None:
    for fold in folds:
        assert len(fold.queries) == 2 * len(fold.test)
        dirs = {q.direction for q in fold.queries}
        assert dirs == {"fwd", "inv"}
        for q in fold.queries:
            if q.direction == "inv":
                assert q.relation in RELATIONS.values()


def test_leakage_gate_passes_and_catches_a_planted_leak(deck, folds) -> None:
    for fold in folds:
        assert_no_leakage(fold, deck)
    bad = folds[0]
    bad.train.append(bad.test[0])  # plant the leak
    with pytest.raises(AssertionError, match="LEAK"):
        assert_no_leakage(bad, deck)
    bad.train.pop()


def test_same_pair_edges_are_excluded_not_trained(deck, folds) -> None:
    for fold in folds:
        test_pairs = {frozenset((f.subject, f.object)) for f in fold.test}
        for f in fold.train + fold.val:
            assert frozenset((f.subject, f.object)) not in test_pairs
        for f in fold.excluded:
            assert frozenset((f.subject, f.object)) in test_pairs


def test_split_is_deterministic_under_seed(deck) -> None:
    a = make_folds(deck, k=5, seed=0)
    b = make_folds(deck, k=5, seed=0)
    c = make_folds(deck, k=5, seed=1)
    assert [[f.triple() for f in x.test] for x in a] == [[f.triple() for f in x.test] for x in b]
    assert [[f.triple() for f in x.test] for x in a] != [[f.triple() for f in x.test] for x in c]


def test_reachability_is_consistent_with_bfs(deck, folds) -> None:
    from hollerith.split import walking_graph
    fold = folds[0]
    g = walking_graph(fold, deck)
    for q in fold.queries[:40]:
        path = g.shortest_path(q.subject, q.gold, 3)
        assert q.reachable == (path is not None), q


def test_write_folds_matches_harness_format(tmp_path, deck, folds) -> None:
    meta = write_folds(folds, tmp_path, deck, seed=0, hops=3)
    assert (tmp_path / "fold0.train.jsonl").exists() and (tmp_path / "meta.json").exists()
    line = (tmp_path / "fold0.test.jsonl").read_text().splitlines()[0]
    assert all(k in line for k in ('"s"', '"r"', '"o"'))
    assert meta["total_queries"] == sum(len(f.queries) for f in folds)
    assert 0 < meta["reachable_rate"] <= 1


def test_filtered_rank_rules() -> None:
    scores = {"A": 0.5, "B": 0.5, "C": 0.2, "D": 0.1}
    assert filtered_rank(scores, "C", set()) == 3.0
    assert filtered_rank(scores, "A", set()) == 1.5          # tied at top -> mean rank, not a Hit@1
    assert filtered_rank(scores, "A", {"B"}) == 1.0          # B is another true answer -> filtered
    assert math.isinf(filtered_rank(scores, "Z", set()))     # unreached


def test_random_walk_is_a_distribution_and_deterministic(deck, folds) -> None:
    from hollerith.split import walking_graph
    g = walking_graph(folds[0], deck)
    rw = RandomWalk(hops=3)
    rw.fit(g, folds[0].train, folds[0].val, seed=0)
    s = g.entities[0]
    a = rw.scores(s, "FOUNDED")
    assert abs(sum(a.values()) - 1.0) < 1e-9
    rw.fit(g, folds[0].train, folds[0].val, seed=99)
    assert rw.scores(s, "FOUNDED") == a
    assert rw.scores("NOT AN ENTITY", "FOUNDED") == {}


def test_frequency_counts_tails(deck, folds) -> None:
    from hollerith.split import walking_graph
    g = walking_graph(folds[0], deck)
    fq = Frequency()
    fq.fit(g, folds[0].train, folds[0].val, seed=0)
    sc = fq.scores("ANYONE", "WORKED AT")
    assert sc and max(sc.values()) >= 2  # BELL LABS / MIT / UNIV OF MANCHESTER are frequent tails


def test_evaluate_rows_cover_all_queries_and_seeds(deck, folds) -> None:
    res = evaluate_system(Frequency(), folds, deck, seeds=[0, 1])
    n_q = sum(len(f.queries) for f in folds)
    assert len(res) == 2 * n_q
    summ = summarise(res, [0, 1])["frequency"]
    assert summ["hits1"]["std"] == 0.0  # deterministic system
    assert 0 <= summ["hits1"]["mean"] <= summ["hits10"]["mean"] <= 1


def test_run_end_to_end_writes_csv_and_summary(tmp_path) -> None:
    summary = run(REPO / "data" / "cards.deck", {"frequency": Frequency(), "random_walk": RandomWalk(3)},
                  tmp_path, seeds=[0], k=5, split_seed=0, hops=3)
    csv_lines = (tmp_path / "hits1.csv").read_text().splitlines()
    assert csv_lines[0] == "seed,query,frequency,random_walk"
    assert len(csv_lines) - 1 == summary["queries"]
    assert "uv run hollerith eval" in summary["command"]


# ---- pre-registered test universe (eval-scientist ruling on L2-F1) ----------------------
from hollerith.split import neighbour_counts, testable_facts


def test_testable_rule_requires_two_neighbours_at_both_ends(deck) -> None:
    nb = neighbour_counts(deck)
    tf = testable_facts(deck)
    assert tf and len(tf) < len(forward_facts(deck))
    for f in tf:
        assert nb[f.subject] >= 2 and nb[f.object] >= 2
    leaves = {e for e, n in nb.items() if n < 2}
    assert leaves  # the deck does have leaf entities
    for f in forward_facts(deck):
        if f.subject in leaves or f.object in leaves:
            assert f.triple() not in {t.triple() for t in tf}


def test_testable_universe_tests_each_testable_fact_once_and_keeps_leaves_in_train(deck) -> None:
    folds = make_folds(deck, k=5, seed=0, universe="testable")
    tested = sorted(f.triple() for fold in folds for f in fold.test)
    assert tested == sorted(f.triple() for f in testable_facts(deck))
    testable = {f.triple() for f in testable_facts(deck)}
    for fold in folds:
        for f in forward_facts(deck):
            if f.triple() not in testable:
                in_train = f.triple() in {t.triple() for t in fold.train}
                in_excl = f.triple() in {t.triple() for t in fold.excluded}
                assert in_train or in_excl, f  # never in test, never in val
        for f in fold.val:
            assert f.triple() in testable
        assert_no_leakage(fold, deck)


def test_all_universe_still_available(deck) -> None:
    folds = make_folds(deck, k=5, seed=0, universe="all")
    assert sum(len(f.test) for f in folds) == len(forward_facts(deck))
    with pytest.raises(ValueError):
        make_folds(deck, universe="some")
