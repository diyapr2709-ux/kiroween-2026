# Challenger pass 1 — after Loop 2, before the web reader

**Agent:** `challenger` (fresh clone of `4bb9dec`, 12 tool calls). **Arbiter rulings and status below each item.**

## Break it — what the clone showed

Fresh clone → `uv sync` → `uv run pytest -q`: 222 passed, no API key needed. Then:

| Sev | Command | What happened | Ruling / status |
|---|---|---|---|
| **BLOCKER** | `hollerith ask … --pull abc` | `ValueError` traceback | **Fixed** (`227 tests`): non-integers and unknown sequence numbers → one-line error, exit 1 |
| **MAJOR (a lie)** | fresh clone, no `models/`: `hollerith ask "Who founded IBM?"` | `NO CARDS, NO ANSWER` — the real cause was the gitignored, untrained model | **Fixed:** `ask` trains the walker on first run (≈ 2 s) and says so on stderr; a missing model can never masquerade as "no cards" |
| MAJOR | `hollerith ask "Who founded Ferranti?"` | 4-hop wander FERRANTI → … → MANCHESTER BABY, then JAM | **Fixed:** product walker prunes beams to prefixes of relation chains known for the asked relation → jams where the shape stops being known (now 1 card, "low confidence"). Product-only flag `chain_prune`; evaluation unaffected and disclosed |
| MAJOR | 200-char question naming three entities | silently picked the longest match | **Fixed:** ≥ 2 distinct entities → `NO CARDS … AMBIGUOUS: names X, Y`; a shorter entity inside a longer one ("IBM" in "IBM 701") is not ambiguous |
| minor | `--pull 99999`, `--pull -1`; text mode hid pulls | accepted silently | **Fixed:** rejected; text mode prints `pulled:` |
| minor | `split --folds 0/1/500` | exit 0, nonsense folds | **Fixed:** 2 ≤ k ≤ facts |
| minor | `train --deck empty.deck` | "trained on 0 cards" | **Fixed:** error |
| minor | `eval --systems bogus` | known list omitted `*_simple` | **Fixed** |
| minor | pytest collected helper `testable_facts` as a test | warning | **Fixed:** `python_functions = test_*` |
| note | `ask` exits 1 on jam / no_cards by design | a `set -e` demo script would abort on the hero jam | **Kept**; the demo script must not use `set -e` (noted for the video shot list) |

Clean: empty deck, 79-column line, lowercase + punctuation, `¬`, unknown entity, `--epochs 0`, `show 99999`, 81-char decode.

## Beat existing work (MINERVA / Lin et al.)
Challenger's cheapest plausible lift: **train RL only on queries that have a path under the mask, warm-started from
SL** (~60 % of RL training queries have no alternative path, so most rollouts return zero reward and only add
baseline noise). Expected: RL runtime 46 s → ~20 s (would meet the missed 30 s target); +1–2 pp Hits@1 plausible;
**not enough to guarantee the per-seed McNemar bar** (seed 0 needs ~5 more correct answers). Reward shaping (Lin) and
an LSTM judged not to pay on a 392-card closed deck; seed ensembling would help the product walker but breaks the
per-seed test.
**Ruling: not adopted for the pre-registered evaluation** (it would be a post-hoc change to the headline system). It
may be run as a disclosed variant `policy_rl_v2` if hours remain after Kiro's work lands — expected value is low.

## Beat the field (Kiroween rubric)
Top-10 % Resurrection entries show, per published criterion: a one-paragraph value pitch judges can repeat
(Potential Value); `/.kiro` with specs that evolved, steering that the code visibly obeys, hooks that fire, an MCP
server that does real work, and a write-up that matches the commits (Implementation); a polished hosted demo with a
scripted hero moment (Quality & Design).
**Our gap:** `.kiro/` does not exist; the README is a stub; `authorship.md` truthfully says Claude Code wrote the core.
**Implementation is currently ≈ 0.** Cheapest Potential-Value move: the README *is* the product — pitch, 3-command
quickstart, the honest results table, hosted URL, "How Kiro built this".

## Ranked improvements (gain per hour)
1. **Kiro lands `.kiro/` + MCP server** (≤ 1.5 h Kiro) — spec-input-1 v2 already says exactly this. Implementation 1 → 6.
2. ~~CLI hardening~~ — **done above** (0.5 h Claude Code).
3. **README as the product** (0.5 h) — scheduled for the submission pack; needs the RL rows first.
4. ~~Jam early~~ — **done above**; pull-a-card "grounded but wrong" did **not** fall (33 % → 34 %): shape pruning
   fixes wandering, not wrong endpoints. Recorded in results.md.
5. RL reachable-only + SL warm start — not adopted (above).

## The thing most likely to get us marked down
A judge opens the repo and finds no `/.kiro`, a stub README, and a ledger stating Claude Code wrote the encoder, deck,
walker, evaluation and CLI. However honest, that reads as "built with the wrong tool" on the one criterion that is
Kiro-specific, and the honest headline ("criterion not met") gives Potential Value nothing to offset it. **Until
Kiro's commits visibly own `.kiro/`, the MCP server and the web reader, every other improvement is cosmetic.**
Arbiter agrees; this is the message to Diya.
