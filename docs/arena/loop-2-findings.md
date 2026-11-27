# Loop 2 findings — walker + evaluation

**Scope reviewed:** `src/hollerith/{graph,split,baselines,evaluate,policy}.py`, tests, `docs/arena/checks/{check_leakage,stats}.py`
at commit `09d66f1` plus the uncommitted working tree. **Reviewer:** independent subagent, 26 tool calls, including
finite-difference checks, a beam-path leak proof over 15,047 cards, 25 mutations, and a statistics re-analysis.
**Verdict at review time:** not ready to close. **Status now:** every finding fixed; the honest statistical result
is recorded in [results.md](results.md). Loop 2's Claude Code part closes with a **negative-leaning result**
(positive effect, not significant at the pre-registered bar). RL re-run pending.

## Blocker (fixed)

| Finding | Fix |
|---|---|
| **Post-hoc architecture change.** A simple-paths (no-revisit) constraint added after seeing results dropped policy_sl Hits@1 0.073 → 0.044 and failed the exit test; `results.md` numbers came from HEAD while the working tree differed in 102 CSV rows. | `simple_paths` is a flag, **OFF for evaluation** (the walker as pre-registered), **ON for the product walker** (oscillation is unacceptable UX). The ON variant is evaluated and reported as an ablation row. Disclosed in results.md "Architecture note". |

## Majors (fixed)

| Finding | Evidence | Fix |
|---|---|---|
| **Pooled-seed statistics were pseudo-replication.** Baselines identical across seeds; pooling n=864 tripled discordant counts (b=61, c=28 ≈ 3 × 20/9). Per-seed McNemar p = 0.136 / 0.029 / 0.061; fact-clustered CI [−0.001, +0.080]. | reviewer's `stats_reanalysis.py` | `stats.py` rewritten: seed-averaged per-query hits, fact-clustered bootstrap, McNemar per seed (all must pass), sample sd. `tests/test_stats_harness.py` pins that identical seeds do not inflate significance. **Pooled PASS withdrawn.** |
| **Random walk Hits@1 0.000 was an artefact**: beam search dropped the query entity but the random walk kept its NO_OP mass, so the subject was argmax in 149/260 queries. | `ranking_ties.py` | Evaluator removes the query entity for every system. Random walk Hits@1 → 0.017, MRR 0.081. Frequency remains the stronger baseline. `test_subject_is_filtered_for_every_system`. |
| Independent leakage gate never read val cards, but the walking graph is train ∪ val. | `grep -c val check_leakage.py` → 0 | `--folds` unions `fold*.val.jsonl` into `fold*.walk.jsonl` before checking. Re-run: 0 leaks. |
| 25/25 mutations survived the suite (evaluate on full deck, filter off, entropy sign, history gradient, masking off, baseline-order swap); no tests for `stats.py`. | `mut/` | `tests/test_protocol.py`: evaluator never fits on a test card; every beam path card is walkable (exhaustive on one fold); training masks query card + inverse; subject filtered; history-gradient FD (max error < 1e-5); simple-paths flag. `tests/test_stats_harness.py`. |

## Minors (fixed)
Tie rule wording ("pessimistic" → neutral mean rank, documented); population vs sample sd aligned (sample);
stale `splits/meta.json` at T=3 regenerated at T=4; `--boot 10000` everywhere.

## Verified clean by the reviewer
Leakage: 15,047 beam path cards across all folds ∈ walking graph, none test/inverse/excluded; `policy.g is walking_graph`;
`known_answers_index` over the full deck is the standard filtered protocol (no system sees it); val used only for reporting;
`testable_facts` structure-only; split RNG independent of policy RNG. Gradients: FD error 4.7e-10 (SL), 1.6e-10 (entropy),
4.2e-10 (RL); entropy sign, baseline update order, NO_OP-kept dropout, Adam ascent for both objectives correct.
Reproducibility: two runs byte-identical.

## Honest result (final)
See results.md "Headline". Both modes are better than frequency in every seed by ~4 points of Hits@1 on a 288-query
test set with a 40 % ceiling; neither meets the pre-registered test (RL per-seed McNemar p 0.052 / 0.087 / 0.043;
SL 0.136 / 0.029 / 0.061; α 0.025). RL ≈ SL (paired Δ −0.001). The simple-path ablations are weaker, RL-simple below
frequency. eval-scientist confirmed the headline wording and the per-seed reading.

## Loop 2 status
**Claude Code's half is complete and verified; the loop's exit criterion ("§4 exit criterion met by the
pre-registered mode") is NOT met** on its one full attempt. Per the operating rules this is a decision for Diya,
not for the arbiter: accept the honest negative-leaning result (the pitch rests on receipts, not on accuracy; the
challenger judged further RL work low-value), or spend remaining hours on a disclosed variant. Kiro's Loop 1 part
(`.kiro/`, MCP server) remains not started.
