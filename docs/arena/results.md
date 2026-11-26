# Results — Hollerith's Ghost

Every number here has the command that regenerates it. Protocol: [ADR-001 §4](ADR-001-direction.md).
Statistics: `docs/arena/checks/stats.py` (corrected 2026-11-26 after the Loop 2 review — see §"Statistics
correction"). Deck: `data/cards.deck`, 196 facts / 392 cards, committed before any split existed.

## Headline (honest; final wording awaits the RL rows — eval-scientist)

**The pre-registered criterion was not met.** On the pre-registered set of 144 multi-hop-testable facts
(288 queries, reachability ceiling 40.3 %), the supervised walker reaches Hits@1 0.073 against a frequency
baseline of 0.035 (seed-to-seed sd 0.007 — optimiser noise, not the uncertainty of the estimate). The
difference is positive in every seed (Δ +0.031 / +0.045 / +0.038) but fails the test under every reading:
fact-clustered 95 % CI [−0.001, +0.080]; per-seed McNemar p = 0.136 / 0.029 / 0.061 vs α = 0.025;
seed-majority McNemar p = 0.12. RL is reported alongside under Holm once its re-run completes.
Every narrated answer cites the cards on its path (faithfulness 657/657).

**Disclosure — choice of T.** The ADR said "T likely 3". T = 4 was fixed *after* measuring the universe's
reachability at T = 3 / 4 / 5 (34.7 / 40.3 / 43.8 %) — a structural measurement with no model involved and
before any training — and *before* any policy result was seen. It was not changed afterwards.

What we do **not** claim or say: that the result is "significant", "near-significant" or "trending"; that any
single seed passes (seed 1's p = 0.029 does not clear α = 0.025 either); that the walker beats an LLM or
embeddings, "reasons", or "learned to reason"; that it generalises beyond this deck; that its numbers are
comparable to published MINERVA/Lin results; that narrated answers are factually correct — they are *grounded*,
and 33 % of pulled-card answers are grounded and wrong. We did not and will not choose between RL and SL after
seeing which passes, nor change T, the universe or the test to rescue the result.

## Pre-registered protocol (fixed 2026-11-26 before any policy existed)

| Item | Value |
|---|---|
| Test universe | **B — testable facts**: both endpoints have ≥ 2 distinct neighbours in the full deck → 144 of 196 facts, 288 queries (both directions). Leaf facts always stay in train. **A** (all 196 facts) reported alongside. |
| Folds / seeds | 5-fold by fact, split seed 0; policy seeds 0, 1, 2 |
| Leakage gate | every edge between a test pair removed from the walkable cards, both directions; `docs/arena/checks/check_leakage.py --folds splits` (train ∪ val vs test): 0 leaks |
| Walking graph | train ∪ val cards; val facts are tuning queries with their own card masked |
| Max hops T | 4 (fixed before training) |
| Ranking | filtered (all known answers removed); the query entity removed for every system; gold takes the **mean** rank of its tie group (neutral); unreached = rank ∞ |
| Exit test | fact-clustered paired bootstrap 95 % CI on ΔHits@1 vs the stronger baseline excludes 0 **and** McNemar exact p < 0.025 **in every seed** **and** sign in every seed |
| Headline mode | RL pre-registered; SL reported either way |

## Deck structure

`uv run hollerith split --out splits` — facts 196 / cards 392 / entities 151 / relation pairs 12 / mean out-degree 2.6 /
degree-1 entities 53 (35 %) / testable facts 144 / excluded same-pair facts 4 / reachable 0.403 / answerable 0.903.

## Universe B (primary), T = 4, 5 folds × 3 seeds

`uv run hollerith eval --systems policy_rl,policy_sl,policy_rl_simple,frequency,random_walk --seeds 0,1,2 --folds 5 --split-seed 0 --hops 4 --universe testable --out results`
(RL ≈ 46 s per fold-seed; full suite ≈ 13 min on an M4 — over the 30 s/run target, within the 15-min ceiling.)

| system | Hits@1 | Hits@10 | MRR | Hits@1 on reachable subset (diagnostic) | coverage |
|---|---|---|---|---|---|
| *reachability ceiling* | 0.403 | — | — | 1.000 | — |
| policy_rl (pre-registered headline) | *re-run in progress under the corrected evaluator; v1 run: 0.072 ± 0.002* | 0.263 | 0.120 | 0.178 | 0.302 |
| policy_sl | **0.073 ± 0.007** | 0.274 ± 0.003 | 0.129 ± 0.005 | 0.181 ± 0.017 | 0.315 |
| policy_sl_simple (ablation: no entity revisits) | 0.044 ± 0.004 | 0.279 ± 0.008 | 0.109 ± 0.007 | 0.109 ± 0.010 | 0.368 |
| frequency | 0.035 ± 0.000 | 0.222 ± 0.000 | 0.082 ± 0.000 | 0.034 | 0.288 |
| random_walk | 0.017 ± 0.000 | 0.274 ± 0.000 | 0.081 ± 0.000 | 0.043 | 0.403 |

± is the sample sd over 3 seeds. Baselines are deterministic.

### Exit test — `python3 -I docs/arena/checks/stats.py results/hits1.csv --system policy_sl --baselines frequency,random_walk --alpha 0.025 --boot 10000 --seed 0`

```
ΔHits@1 (policy_sl − frequency) = +0.038   95% fact-clustered bootstrap CI [-0.001, +0.080]   facts=144 queries=288
McNemar exact, seed 0: b=19 c=10 p=0.136  FAIL   seed 1: b=22 c=9 p=0.0295  FAIL   seed 2: b=20 c=9 p=0.0614  FAIL
McNemar on seed-majority vote (information only): b=18 c=9 p=0.122
sign of Δ in every seed: True (+0.031, +0.045, +0.038)
EXIT CRITERION: FAIL
```
Ablation `policy_sl_simple`: Δ +0.009, CI [−0.022, +0.042], per-seed p 0.83 / 0.83 / 0.54 — FAIL.
`policy_rl` rows and its test are appended when the re-run completes.

### Statistics correction (2026-11-26, Loop 2 review)
The first version of `stats.py` pooled (seed, query) rows (n = 864) and reported CI [+0.017, +0.059], McNemar
p = 0.0006, PASS. That was pseudo-replication: the baselines are identical across seeds, so pooling tripled
the discordant counts. The corrected script averages over seeds per query, bootstraps over facts, and runs
McNemar per seed. The pooled PASS is withdrawn.

### Architecture note
The walker as pre-registered allows a walk to revisit an entity (as MINERVA does). A **simple-paths**
variant (no revisits) was added after the first results, because the product walker oscillated
(A→B→A→B) on dead-end questions; it is OFF for the evaluation above and ON for the shipped product
walker. Its evaluation is reported as the ablation row — it is weaker on Hits@1.

## Universe A (secondary), T = 3 — `--universe all --hops 3`, baselines only
392 queries, reachable 0.301, answerable 0.806. frequency Hits@1 0.023, random_walk 0.000 (pre subject-filter fix).

## Product walker (Loop 3)
`uv run hollerith train --mode sl --seed 0` (1.9 s, simple paths, full deck). Over the 392 card-derived questions
(`hollerith.questions`), each asked once directly and once with its own card pulled:

| | count | share |
|---|---|---|
| direct card found | 317 / 392 | 81 % (the rest parse to a relation the entity has no card for) |
| pull-a-card: walker recovers the pulled answer | 134 / 392 | 34 % |
| pull-a-card: jam (unknown path shape or low confidence) | 74 / 392 | 19 % |
| pull-a-card: **grounded but wrong** | 131 / 392 | 33 % |
| pull-a-card: no cards | 53 / 392 | 14 % |

Faithfulness — `python3 -I docs/arena/checks/check_faithfulness.py <traces> --deck data/cards.deck`: **657 answered,
657 faithful, rate 1.000**, 74 jams, 53 no-cards. Narration is templated from path cards only, so this is by
construction; the check guards regressions.
