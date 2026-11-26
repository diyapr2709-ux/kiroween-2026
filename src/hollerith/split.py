"""Evaluation split (ADR-001 §4): k-fold by fact, both query directions, leakage removed.

For each fold:
  * test facts  — the held-out forward facts of that fold;
  * excluded    — any OTHER fact that connects the same two entities as a test fact, in either
                  direction (synonym / parallel-edge leakage); neither trained nor tested;
  * train facts — everything else; a further slice is carved off as validation for tuning;
  * queries     — for every test fact (s, r, o): (s, r, ?) -> o and (o, r⁻¹, ?) -> s.
Each query records whether the gold answer is reachable within T hops of the training graph,
which is the oracle upper bound for any walker, and whether the query entity exists in train.

Files written: splits/fold{k}.{train,val,test}.jsonl with one {"s","r","o"} per line
(the format docs/arena/checks/check_leakage.py expects) and splits/meta.json.
"""
from __future__ import annotations

import json
import random
from dataclasses import asdict, dataclass
from pathlib import Path

from .code_table import RELATIONS
from .deck import Deck, Fact
from .graph import Graph, forward_facts, with_inverses

DEFAULT_FOLDS = 5
DEFAULT_HOPS = 3
VAL_FRACTION = 0.1


@dataclass(frozen=True)
class Query:
    fold: int
    subject: str
    relation: str
    gold: str
    fact_seq: int
    direction: str  # "fwd" or "inv"
    reachable: bool
    answerable: bool  # subject exists in the training graph


@dataclass
class Fold:
    k: int
    train: list[Fact]
    val: list[Fact]
    test: list[Fact]
    excluded: list[Fact]
    queries: list[Query]


def _pair(f: Fact) -> frozenset[str]:
    return frozenset((f.subject, f.object))


def make_folds(deck: Deck, k: int = DEFAULT_FOLDS, seed: int = 0, hops: int = DEFAULT_HOPS) -> list[Fold]:
    facts = forward_facts(deck)
    rng = random.Random(seed)
    order = facts[:]
    rng.shuffle(order)
    buckets = [order[i::k] for i in range(k)]
    folds: list[Fold] = []
    for i in range(k):
        test = sorted(buckets[i], key=lambda f: f.sequence)
        test_pairs = {_pair(f) for f in test}
        test_set = {f.triple() for f in test}
        rest = [f for f in facts if f.triple() not in test_set]
        excluded = [f for f in rest if _pair(f) in test_pairs]
        trainable = [f for f in rest if _pair(f) not in test_pairs]
        vrng = random.Random(seed * 1000 + i)
        shuffled = trainable[:]
        vrng.shuffle(shuffled)
        n_val = max(1, round(len(shuffled) * VAL_FRACTION))
        val = sorted(shuffled[:n_val], key=lambda f: f.sequence)
        train = sorted(shuffled[n_val:], key=lambda f: f.sequence)
        # Policies train on train ∪ val cards' graph structure only via `train`; val is for tuning.
        g = Graph(with_inverses(train, deck))
        queries: list[Query] = []
        for f in test:
            for s, r, gold, d in ((f.subject, f.relation, f.object, "fwd"),
                                  (f.object, RELATIONS[f.relation], f.subject, "inv")):
                answerable = g.has(s)
                reachable = answerable and gold in g.reachable_within(s, hops)
                queries.append(Query(i, s, r, gold, f.sequence, d, reachable, answerable))
        folds.append(Fold(i, train, val, test, excluded, queries))
    return folds


def assert_no_leakage(fold: Fold, deck: Deck) -> None:
    """Fail loudly if any test fact, its inverse, or any same-pair edge is in the training cards."""
    train_cards = with_inverses(fold.train + fold.val, deck)
    train_triples = {f.triple() for f in train_cards}
    train_pairs = {_pair(f) for f in train_cards}
    for f in fold.test:
        if f.triple() in train_triples:
            raise AssertionError(f"LEAK fold {fold.k}: test fact in train {f.triple()}")
        if (f.object, RELATIONS[f.relation], f.subject) in train_triples:
            raise AssertionError(f"LEAK fold {fold.k}: inverse of test fact in train {f.triple()}")
        if _pair(f) in train_pairs:
            raise AssertionError(f"LEAK fold {fold.k}: another edge between {set(_pair(f))} in train")


def _write_jsonl(path: Path, facts: list[Fact]) -> None:
    path.write_text("".join(json.dumps({"s": f.subject, "r": f.relation, "o": f.object, "seq": f.sequence}) + "\n" for f in facts))


def write_folds(folds: list[Fold], out_dir: str | Path, deck: Deck, seed: int, hops: int) -> dict:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    meta: dict = {"seed": seed, "k": len(folds), "hops": hops, "deck_cards": len(deck), "folds": []}
    for fold in folds:
        assert_no_leakage(fold, deck)
        _write_jsonl(out / f"fold{fold.k}.train.jsonl", with_inverses(fold.train, deck))
        _write_jsonl(out / f"fold{fold.k}.val.jsonl", with_inverses(fold.val, deck))
        _write_jsonl(out / f"fold{fold.k}.test.jsonl", fold.test)
        (out / f"fold{fold.k}.queries.jsonl").write_text(
            "".join(json.dumps(asdict(q)) + "\n" for q in fold.queries))
        q = fold.queries
        meta["folds"].append({
            "k": fold.k, "train_facts": len(fold.train), "val_facts": len(fold.val),
            "test_facts": len(fold.test), "excluded_facts": len(fold.excluded),
            "queries": len(q), "answerable": sum(x.answerable for x in q),
            "reachable": sum(x.reachable for x in q),
        })
    tot_q = sum(f["queries"] for f in meta["folds"])
    meta["total_queries"] = tot_q
    meta["reachable_rate"] = sum(f["reachable"] for f in meta["folds"]) / tot_q if tot_q else 0.0
    meta["answerable_rate"] = sum(f["answerable"] for f in meta["folds"]) / tot_q if tot_q else 0.0
    meta["excluded_total"] = sum(f["excluded_facts"] for f in meta["folds"])
    (out / "meta.json").write_text(json.dumps(meta, indent=2))
    return meta


def read_queries(out_dir: str | Path, k: int) -> list[Query]:
    rows = []
    for line in (Path(out_dir) / f"fold{k}.queries.jsonl").read_text().splitlines():
        if line.strip():
            rows.append(Query(**json.loads(line)))
    return rows
