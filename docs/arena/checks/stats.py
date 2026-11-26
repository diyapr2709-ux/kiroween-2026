"""Loop 2 statistics (ADR-001 §4): paired bootstrap CI on ΔHits@1, McNemar exact test,
and the sign-over-seeds check. Standard library only.

Input: a CSV with one row per (seed, query) and 0/1 columns for each system, e.g.
    seed,query,policy,random_walk,frequency
    0,Q001,1,0,1
Exit 0 if the exit criterion holds for `--system` vs the stronger of `--baselines`, else 1.

Usage:
  python -I docs/arena/checks/stats.py results/hits1.csv --system policy_rl \
      --baselines random_walk,frequency --alpha 0.025 --boot 10000 --seed 0
"""
from __future__ import annotations

import argparse
import csv
import math
import random
import sys
from collections import defaultdict


def mcnemar_exact(b: int, c: int) -> float:
    """Two-sided exact McNemar p-value for discordant counts b (A right, B wrong) and c."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(0, k + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def bootstrap_ci(a: list[int], b: list[int], iters: int, rng: random.Random, level: float = 0.95):
    n = len(a)
    diffs = []
    for _ in range(iters):
        idx = [rng.randrange(n) for _ in range(n)]
        diffs.append(sum(a[i] - b[i] for i in idx) / n)
    diffs.sort()
    lo = diffs[int((1 - level) / 2 * iters)]
    hi = diffs[int((1 + level) / 2 * iters) - 1]
    return lo, hi


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--system", required=True)
    ap.add_argument("--baselines", required=True, help="comma-separated columns")
    ap.add_argument("--alpha", type=float, default=0.025, help="Holm-corrected per-mode alpha")
    ap.add_argument("--boot", type=int, default=10_000)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()
    rng = random.Random(args.seed)

    by_seed: dict[str, dict[str, dict[str, int]]] = defaultdict(lambda: defaultdict(dict))
    with open(args.csv, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            for col, v in row.items():
                if col in ("seed", "query"):
                    continue
                by_seed[row["seed"]][col][row["query"]] = int(v)
    seeds = sorted(by_seed)
    systems = sorted({c for s in seeds for c in by_seed[s]})
    print(f"seeds: {seeds}; systems: {systems}")

    def mean_hits(col: str) -> float:
        vals = [by_seed[s][col][q] for s in seeds for q in by_seed[s][col]]
        return sum(vals) / len(vals)

    def per_seed(col: str) -> list[float]:
        return [sum(by_seed[s][col].values()) / len(by_seed[s][col]) for s in seeds]

    baselines = args.baselines.split(",")
    strongest = max(baselines, key=mean_hits)
    print(f"strongest baseline: {strongest} (Hits@1 {mean_hits(strongest):.3f})")
    for col in systems:
        ps = per_seed(col)
        mu = sum(ps) / len(ps)
        sd = (sum((p - mu) ** 2 for p in ps) / max(1, len(ps) - 1)) ** 0.5
        print(f"  {col:16} Hits@1 {mu:.3f} ± {sd:.3f} (over {len(ps)} seeds)")

    # Paired over (seed, query): pool all seeds; the pairing is query-wise within seed.
    a, b = [], []
    for s in seeds:
        for q in sorted(by_seed[s][args.system]):
            a.append(by_seed[s][args.system][q])
            b.append(by_seed[s][strongest][q])
    delta = (sum(a) - sum(b)) / len(a)
    lo, hi = bootstrap_ci(a, b, args.boot, rng)
    bc = sum(1 for x, y in zip(a, b) if x == 1 and y == 0)
    cb = sum(1 for x, y in zip(a, b) if x == 0 and y == 1)
    p = mcnemar_exact(bc, cb)
    signs = [ps_sys - ps_base for ps_sys, ps_base in zip(per_seed(args.system), per_seed(strongest))]
    sign_ok = all(d > 0 for d in signs)

    print(f"ΔHits@1 ({args.system} − {strongest}) = {delta:+.3f}  95% bootstrap CI [{lo:+.3f}, {hi:+.3f}]  n={len(a)}")
    print(f"McNemar exact: b={bc} c={cb} p={p:.4g} (alpha {args.alpha})")
    print(f"sign holds in all seeds: {sign_ok} ({['%+.3f' % d for d in signs]})")
    ok = lo > 0 and p < args.alpha and sign_ok
    print("EXIT CRITERION:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
