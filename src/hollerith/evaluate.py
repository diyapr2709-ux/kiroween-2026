"""Filtered ranking, Hits@k and MRR over the folds (ADR-001 §4), for any `Ranker`.

Filtered ranking (Lin et al.): other entities that are also true answers to (s, r, ?) anywhere
in the full deck are removed from the candidate list before ranking the gold answer.
Ties: the gold answer takes the MEAN rank of its tie group (pessimistic enough that a tie at
the top is not a Hit@1). An unreached gold (no score) has rank ∞: Hits miss, MRR 0.

Output: results/hits1.csv (seed, query, <system>, ...) for docs/arena/checks/stats.py, and
results/summary.json with Hits@1/Hits@10/MRR per system (mean ± std over seeds), reachability,
and the exact command that produced it.
"""
from __future__ import annotations

import csv
import json
import math
import statistics
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from .baselines import Ranker
from .deck import Deck
from .graph import Graph, with_inverses
from .split import Fold, Query, make_folds, walking_graph


@dataclass
class QueryResult:
    seed: int
    query_id: str
    system: str
    rank: float  # inf if unreached
    reachable: bool
    answerable: bool

    @property
    def hit1(self) -> int:
        return int(self.rank <= 1.0)

    @property
    def hit10(self) -> int:
        return int(self.rank <= 10.0)

    @property
    def rr(self) -> float:
        return 0.0 if math.isinf(self.rank) else 1.0 / self.rank


def filtered_rank(scores: dict[str, float], gold: str, known_answers: set[str]) -> float:
    if gold not in scores:
        return math.inf
    g = scores[gold]
    greater = ties = 0
    for e, s in scores.items():
        if e != gold and e in known_answers:
            continue  # filtered: another true answer
        if s > g:
            greater += 1
        elif s == g:
            ties += 1  # includes gold itself
    return greater + (ties + 1) / 2.0


def known_answers_index(deck: Deck) -> dict[tuple[str, str], set[str]]:
    idx: dict[tuple[str, str], set[str]] = {}
    for f in deck.facts():
        idx.setdefault((f.subject, f.relation), set()).add(f.object)
    return idx


def evaluate_system(system: Ranker, folds: list[Fold], deck: Deck, seeds: list[int]) -> list[QueryResult]:
    known = known_answers_index(deck)
    out: list[QueryResult] = []
    for seed in seeds:
        for fold in folds:
            system.fit(walking_graph(fold, deck), fold.train, fold.val, seed)
            for q in fold.queries:
                qid = f"f{q.fold}-{q.fact_seq:08d}-{q.direction}"
                scores = system.scores(q.subject, q.relation) if q.answerable else {}
                rank = filtered_rank(scores, q.gold, known.get((q.subject, q.relation), set()))
                out.append(QueryResult(seed, qid, system.name, rank, q.reachable, q.answerable))
    return out


def summarise(results: list[QueryResult], seeds: list[int]) -> dict:
    by_sys: dict[str, dict] = {}
    systems = sorted({r.system for r in results})
    for name in systems:
        rows = [r for r in results if r.system == name]
        per_seed = {}
        for s in seeds:
            rs = [r for r in rows if r.seed == s]
            reach = [r for r in rs if r.reachable]
            per_seed[s] = {
                "n": len(rs),
                "hits1": sum(r.hit1 for r in rs) / len(rs),
                "hits10": sum(r.hit10 for r in rs) / len(rs),
                "mrr": sum(r.rr for r in rs) / len(rs),
                "hits1_reachable": (sum(r.hit1 for r in reach) / len(reach)) if reach else None,
                "coverage": sum(not math.isinf(r.rank) for r in rs) / len(rs),
            }
        def ms(key):
            vals = [per_seed[s][key] for s in seeds if per_seed[s][key] is not None]
            if not vals:
                return None
            return {"mean": statistics.fmean(vals), "std": statistics.pstdev(vals) if len(vals) > 1 else 0.0}
        by_sys[name] = {k: ms(k) for k in ("hits1", "hits10", "mrr", "hits1_reachable", "coverage")}
        by_sys[name]["n_queries"] = per_seed[seeds[0]]["n"]
    return by_sys


def write_results(results: list[QueryResult], folds: list[Fold], out_dir: str | Path, seeds: list[int], command: str) -> dict:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    systems = sorted({r.system for r in results})
    table: dict[tuple[int, str], dict[str, int]] = {}
    for r in results:
        table.setdefault((r.seed, r.query_id), {})[r.system] = r.hit1
    with (out / "hits1.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["seed", "query", *systems])
        for (seed, qid) in sorted(table):
            w.writerow([seed, qid, *[table[(seed, qid)].get(s, 0) for s in systems]])
    queries = [q for fold in folds for q in fold.queries]
    summary = {
        "command": command,
        "generated": time.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "seeds": seeds,
        "folds": len(folds),
        "queries": len(queries),
        "reachable_rate": sum(q.reachable for q in queries) / len(queries),
        "answerable_rate": sum(q.answerable for q in queries) / len(queries),
        "excluded_facts": sum(len(f.excluded) for f in folds),
        "systems": summarise(results, seeds),
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2))
    return summary


def format_table(summary: dict) -> str:
    lines = [f"universe={summary.get('universe', '?')} ({summary.get('facts_testable', '?')}/{summary.get('facts_total', '?')} facts)  queries={summary['queries']}  "
             f"reachable={summary['reachable_rate']:.3f}  answerable={summary['answerable_rate']:.3f}  excluded_facts={summary['excluded_facts']}",
             f"{'system':14} {'Hits@1':>15} {'Hits@10':>15} {'MRR':>15} {'Hits@1|reach':>15} {'coverage':>10}"]
    for name, m in summary["systems"].items():
        def c(k, w=15):
            v = m[k]
            return f"{'—':>{w}}" if v is None else f"{v['mean']:.3f} ± {v['std']:.3f}".rjust(w)
        lines.append(f"{name:14} {c('hits1')} {c('hits10')} {c('mrr')} {c('hits1_reachable')} {c('coverage', 10)}")
    return "\n".join(lines)


def run(deck_path: str | Path, systems: dict[str, Ranker], out_dir: str | Path, seeds: list[int],
        k: int, split_seed: int, hops: int, universe: str = "testable") -> dict:
    deck = Deck.load(deck_path)
    folds = make_folds(deck, k=k, seed=split_seed, hops=hops, universe=universe)
    from .split import assert_no_leakage
    for fold in folds:
        assert_no_leakage(fold, deck)
    results: list[QueryResult] = []
    for sysm in systems.values():
        results.extend(evaluate_system(sysm, folds, deck, seeds))
    command = ("uv run hollerith eval --systems " + ",".join(systems) + f" --seeds {','.join(map(str, seeds))}"
               f" --folds {k} --split-seed {split_seed} --hops {hops} --universe {universe}")
    summary = write_results(results, folds, out_dir, seeds, command)
    summary["universe"] = universe
    from .split import forward_facts, testable_facts
    summary["facts_total"] = len(forward_facts(deck))
    summary["facts_testable"] = len(testable_facts(deck))
    (Path(out_dir) / "summary.json").write_text(json.dumps(summary, indent=2))
    return summary
