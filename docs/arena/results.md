# Results — Hollerith's Ghost

Every number here has the command that regenerates it. Deck: `data/cards.deck` at commit noted per
table. Protocol: [ADR-001 §4](ADR-001-direction.md). Statistics: `docs/arena/checks/stats.py`.

## Pre-registered protocol (fixed 2026-11-26, before any policy existed)

| Item | Value | Why |
|---|---|---|
| Test universe | **B — testable facts:** both endpoints have ≥ 2 distinct neighbours in the full deck → **144 of 196 facts**, 288 queries (both directions) | a held-out leaf fact has no alternative path by construction; testing it measures deck shape, not learning (eval-scientist ruling) |
| Secondary report | **A — all 196 facts**, 392 queries, shown next to its ceiling | honesty: the full-deck number is never hidden |
| Folds / seeds | 5-fold by fact, split seed 0; policy seeds 0, 1, 2 | each fact tested exactly once; pooled n unchanged vs 10-fold |
| Leakage gate | every edge between a test pair removed from the walkable cards, both directions; independent check `docs/arena/checks/check_leakage.py` | synonym / parallel-edge leaks |
| Walking graph | train ∪ val cards; val facts are tuning queries with their own edge masked | val cards are context, not test |
| Max hops T | **4** | reachability 34.7 % (T=3) → 40.3 % (T=4) → 43.8 % (T=5); 4 cards still fit the reader; fixed before training |
| Ranking | filtered (all known answers removed), gold takes the mean rank of its tie group, unreached = rank ∞ | tie at the top is not a Hit@1; same rule for every system |
| Exit test | paired bootstrap 95 % CI on ΔHits@1 vs the stronger baseline excludes 0 **and** McNemar exact p < 0.025 (Holm, two modes) **and** sign in 3/3 seeds | `stats.py` |
| Headline mode | RL pre-registered; SL is the fallback reported either way | prevents picking the winner after the fact |

Reachability (oracle upper bound for any walker) is reported beside every Hits@1.

## Deck structure (commit `a743536`+)

`uv run hollerith split --out splits --hops 4` and the degree script in [log.md](log.md) 18:20 entry.

| | value |
|---|---|
| facts / cards / entities | 196 / 392 / 151 |
| relation pairs | 12 |
| mean out-degree | 2.6; 53 entities (35 %) are degree-1 leaves |
| testable facts (B) | 144 |
| excluded same-pair facts | 4 |

## Baselines — universe B (primary), T = 4

`uv run hollerith eval --systems random_walk,frequency --seeds 0,1,2 --folds 5 --split-seed 0 --hops 4 --universe testable --out results`

| system | Hits@1 | Hits@10 | MRR | Hits@1 (reachable subset) | coverage |
|---|---|---|---|---|---|
| *reachability ceiling* | 0.403 | — | — | 1.000 | — |
| frequency | 0.035 ± 0.000 | 0.222 ± 0.000 | 0.081 ± 0.000 | 0.034 | 0.288 |
| random_walk | 0.000 ± 0.000 | 0.267 ± 0.000 | 0.061 ± 0.000 | 0.000 | 0.403 |

288 queries, reachable 0.403, answerable 0.903, 4 excluded same-pair facts. Run time 0.3 s (M4).
`python3 -I docs/arena/checks/stats.py results/hits1.csv --system frequency --baselines random_walk` →
frequency beats random walk on Hits@1 (Δ +0.035, CI excludes 0, McNemar p < 1e-6, 3/3 seeds): the bar a
walker must clear is **frequency**, the stronger baseline.

Reference run at T = 3 (same command with `--hops 3`): reachable 0.347, answerable 0.903;
frequency Hits@1 0.035 ± 0.000, Hits@10 0.222, MRR 0.081; random_walk Hits@1 0.000, Hits@10 0.240, MRR 0.050.

## Baselines — universe A (secondary), T = 3

`uv run hollerith eval --systems random_walk,frequency --seeds 0,1,2 --folds 5 --split-seed 0 --hops 3 --universe all --out results_all`

reachable 0.301, answerable 0.806, 392 queries.

| system | Hits@1 | Hits@10 | MRR | Hits@1 (reachable) | coverage |
|---|---|---|---|---|---|
| frequency | 0.023 ± 0.000 | 0.179 ± 0.000 | 0.062 ± 0.000 | 0.034 | 0.224 |
| random_walk | 0.000 ± 0.000 | 0.212 ± 0.000 | 0.046 ± 0.000 | 0.000 | 0.301 |

Baselines are deterministic, hence ± 0.000 over seeds.

## Walker — universe B (primary), T = 4, 5 folds × 3 seeds

Policy (ADR D2, no LSTM): bilinear action scorer `s(a) = <q, R[r_a]> + <q, E[e_a]>`, `q = R[r_q] + mean(history)`,
softmax over out-cards + NO_OP, dim 32, 40 epochs, Adam lr 0.05. RL: REINFORCE, 20 rollouts/query, moving-average
baseline (0.9), entropy 0.02, action dropout 0.1. SL: teacher forcing on BFS shortest path with the query card masked.
Beam B = 64. Hyperparameters fixed before the first full-deck run; nothing tuned on test.

`uv run hollerith eval --systems policy_rl,policy_sl,frequency,random_walk --seeds 0,1,2 --folds 5 --split-seed 0 --hops 4 --universe testable --out results`

| system | Hits@1 | Hits@10 | MRR | Hits@1 (reachable subset, diagnostic) | coverage | train time / run |
|---|---|---|---|---|---|---|
| *reachability ceiling* | 0.403 | — | — | 1.000 | — | — |
| policy_rl (pre-registered headline) | *3-seed run in progress* | | | | | ≈ 46 s |
| policy_sl | **0.073 ± 0.006** | 0.274 ± 0.003 | 0.129 ± 0.004 | 0.181 ± 0.014 | 0.315 | ≈ 0.8 s |
| frequency | 0.035 ± 0.000 | 0.222 ± 0.000 | 0.081 ± 0.000 | 0.034 | 0.288 | — |
| random_walk | 0.000 ± 0.000 | 0.267 ± 0.000 | 0.061 ± 0.000 | 0.000 | 0.403 | — |

Exit test, `python3 -I docs/arena/checks/stats.py results/hits1.csv --system policy_sl --baselines frequency,random_walk --alpha 0.025 --boot 5000`:
**ΔHits@1 (policy_sl − frequency) = +0.038, 95 % bootstrap CI [+0.017, +0.059], McNemar b=61 c=28 p = 0.00061 (< 0.025), sign holds in 3/3 seeds → PASS.**

Deviation recorded: RL training is ≈ 46 s per fold-seed run (target ≤ 30 s); the full suite (15 RL + 15 SL runs + baselines)
is ≈ 12 min, within the 15-min ceiling. Hyperparameters were not reduced after seeing results.

## Must-not claims (eval-scientist)
Beats LLMs or embeddings · "the graph improves accuracy over the LLM" · reasons better · generalises
beyond this deck · comparable to published MINERVA/Lin numbers (no LSTM here) · narration is factually
correct (it is only grounded in cards).
