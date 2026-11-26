"""Loop 2 statistics (ADR-001 §4), corrected after the Loop 2 review.

The unit of analysis is the QUERY (and its fact), not the (seed, query) pair: seeds are repeated
measures of the same queries and the baselines are identical across seeds, so pooling rows
across seeds triples the discordant counts (pseudo-replication). This script therefore:

  1. averages each system's Hit@1 over seeds per query (values in {0, 1/3, 2/3, 1});
  2. bootstraps ΔHits@1 by resampling FACTS (both directions of a fact move together);
  3. runs McNemar's exact test PER SEED — the pre-registered criterion requires every seed to
     pass at alpha — and also reports the test on the seed-majority vote for information;
  4. checks that the sign of ΔHits@1 holds in every seed.

Input: CSV `seed,query,<system>,...` with 0/1 cells; query ids look like `f0-00000012-fwd`, and
the fact id is the middle field. Exit 0 iff the criterion holds for --system vs the stronger of
--baselines (by mean Hits@1).

Usage:
  python3 -I docs/arena/checks/stats.py results/hits1.csv --system policy_rl \
      --baselines frequency,random_walk --alpha 0.025 --boot 10000 --seed 0
"""
from __future__ import annotations

import argparse
import csv
import math
import random
import statistics
import sys
from collections import defaultdict


def mcnemar_exact(b: int, c: int) -> float:
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(0, k + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def fact_of(query_id: str) -> str:
    parts = query_id.split("-")
    return parts[1] if len(parts) >= 2 else query_id


def load(path: str):
    by_seed: dict[str, dict[str, dict[str, int]]] = defaultdict(lambda: defaultdict(dict))
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            for col, v in row.items():
                if col in ("seed", "query"):
                    continue
                by_seed[row["seed"]][col][row["query"]] = int(v)
    return by_seed


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--system", required=True)
    ap.add_argument("--baselines", required=True)
    ap.add_argument("--alpha", type=float, default=0.025)
    ap.add_argument("--boot", type=int, default=10_000)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()
    rng = random.Random(args.seed)

    by_seed = load(args.csv)
    seeds = sorted(by_seed)
    systems = sorted({c for s in seeds for c in by_seed[s]})
    queries = sorted(by_seed[seeds[0]][args.system])
    print(f"seeds: {seeds}; systems: {systems}; queries: {len(queries)}")

    def per_seed_hits(col: str) -> list[float]:
        return [statistics.fmean(by_seed[s][col].values()) for s in seeds]

    def query_mean(col: str) -> dict[str, float]:
        return {q: statistics.fmean(by_seed[s][col][q] for s in seeds) for q in queries}

    for col in systems:
        ps = per_seed_hits(col)
        sd = statistics.stdev(ps) if len(ps) > 1 else 0.0
        print(f"  {col:18} Hits@1 {statistics.fmean(ps):.3f} ± {sd:.3f} (sample sd over {len(ps)} seeds)")

    baselines = args.baselines.split(",")
    strongest = max(baselines, key=lambda c: statistics.fmean(per_seed_hits(c)))
    print(f"strongest baseline: {strongest}")

    sys_q, base_q = query_mean(args.system), query_mean(strongest)
    delta = statistics.fmean(sys_q[q] - base_q[q] for q in queries)

    # Fact-clustered paired bootstrap on seed-averaged per-query hits.
    facts: dict[str, list[str]] = defaultdict(list)
    for q in queries:
        facts[fact_of(q)].append(q)
    fact_ids = sorted(facts)
    diffs = []
    for _ in range(args.boot):
        sample = [fact_ids[rng.randrange(len(fact_ids))] for _ in fact_ids]
        num = den = 0.0
        for fid in sample:
            for q in facts[fid]:
                num += sys_q[q] - base_q[q]
                den += 1
        diffs.append(num / den)
    diffs.sort()
    lo, hi = diffs[int(0.025 * args.boot)], diffs[int(0.975 * args.boot) - 1]

    # McNemar per seed (criterion) and on the seed-majority vote (information).
    per_seed_p = []
    for s in seeds:
        b = sum(1 for q in queries if by_seed[s][args.system][q] == 1 and by_seed[s][strongest][q] == 0)
        c = sum(1 for q in queries if by_seed[s][args.system][q] == 0 and by_seed[s][strongest][q] == 1)
        per_seed_p.append((s, b, c, mcnemar_exact(b, c)))
    maj = {q: int(sys_q[q] > 0.5) for q in queries}
    bmaj = {q: int(base_q[q] > 0.5) for q in queries}
    b_m = sum(1 for q in queries if maj[q] and not bmaj[q])
    c_m = sum(1 for q in queries if not maj[q] and bmaj[q])
    p_maj = mcnemar_exact(b_m, c_m)

    signs = [a - b for a, b in zip(per_seed_hits(args.system), per_seed_hits(strongest))]
    sign_ok = all(d > 0 for d in signs)

    print(f"ΔHits@1 ({args.system} − {strongest}) = {delta:+.3f}   95% fact-clustered bootstrap CI [{lo:+.3f}, {hi:+.3f}]   "
          f"facts={len(fact_ids)} queries={len(queries)}")
    for s, b, c, p in per_seed_p:
        print(f"McNemar exact, seed {s}: b={b} c={c} p={p:.4g}  {'pass' if p < args.alpha else 'FAIL'} (alpha {args.alpha})")
    print(f"McNemar on seed-majority vote (information only): b={b_m} c={c_m} p={p_maj:.4g}")
    print(f"sign of Δ in every seed: {sign_ok} ({['%+.3f' % d for d in signs]})")
    ok = lo > 0 and all(p < args.alpha for _, _, _, p in per_seed_p) and sign_ok
    print("EXIT CRITERION:", "PASS" if ok else "FAIL",
          "(CI excludes 0 AND every per-seed McNemar p < alpha AND sign in every seed)")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
