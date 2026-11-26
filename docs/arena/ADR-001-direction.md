# ADR-001 — Direction for Hollerith's Ghost

**Status:** PROPOSED v1.1 — two arena rounds complete; awaiting Diya's approval. Nothing below is built.
**Date:** 2026-11-26 (Thanksgiving; 0 build hours today). v1.1 incorporates round 2 (§10).
**Deadline:** Fri Dec 4 2026 14:00 PT / 17:00 ET, fixed
**Budget:** ≤12 h hands-on build time, solo, all code written by Kiro
**Inputs:** four arena reports (`scope-risk`, `eval-scientist`, `judge-sim`, `product-design`), arbitrated in one round under the rules in [log.md](log.md). Environment facts also in log.md.

---

## 0. Preconditions (block Loop 1)

| # | Precondition | Evidence found | Owner |
|---|---|---|---|
| **P0** | **Kiro is reachable.** Diya is using **Kiro web** (`app.kiro.dev/session`), not the desktop IDE — nothing is installed locally (`which kiro; ls ~/.kiro` → nothing). Kiro web operates on a **GitHub repository**, so the repo must be pushed before Kiro can write `/.kiro` or `src/`. Remote `github.com/diyapr2709-ux/kiroween-2026` exists and `gh` is authenticated, but the repo has **zero commits**. First commit = `docs/arena/` + `.claude/agents/` (Claude Code's work, attributed as such), so history shows the arena preceded the code. | `git remote -v; git log` | Diya approves the push; Claude Code runs it |
| P1 | Kiro quota / plan limits checked (scope-risk risk #1) | — | Diya |
| P2 | Repo is public with an OSI license (MIT) and `/.kiro` is **not** gitignored — published rule | judge-sim, 2025 rules | Kiro spec L1 task 1 |
| P3 | Rubric mismatch acknowledged (§7) | judge-sim | Diya |

## 1. The decision in one paragraph

Build **"an AI that shows its receipts."** A hand-curated graph of computing history 1880–1960 (**100 facts = 200 cards with inverses**, range 75–150 facts) is stored *only* as a deck of IBM 029 punched cards — the deck file is the database, and every card carries a source code. A MINERVA-style walker (REINFORCE, **pre-registered as the headline mode**, with a supervised-on-BFS-paths mode built first as the fallback; both tested at Holm-corrected α) answers held-out `(entity, relation, ?)` queries by walking the deck; beam search guarantees a path for every answer. The walk is replayed in a **static web card-reader** (hosted on GitHub Pages — a working URL is a published requirement). The narrator cites card sequence numbers (cols 73–80); a deterministic faithfulness check confirms every named entity and every cited card is on the path. A dead end is a **jammed card**, and an entity not in the deck returns **"NO CARDS, NO ANSWER"** — the product's answer to hallucination. Evaluation follows the eval-scientist's protocol (10-fold CV × 3 seeds, filtered ranking, paired bootstrap + McNemar vs. the stronger of random-walk and frequency baselines). The LLM-only baseline is reported as a *memorisation reference*, not a bar to beat.

## 2. Decisions on the four open questions

| | Decision | Arbitration |
|---|---|---|
| **D1 Graph source** | **Hand-curated: 100 facts → 200 cards** (inverses), ≤12 relations, no synonym relations. **Curation protocol:** all cards authored and committed *before* the split is generated (git history proves order); the test set is never inspected while authoring; relation-pair Jaccard overlap > 0.5 fails the lint; **every card cites a source code in cols 56–63** drawn from a fixed list of ≤10 references in steering. 30 random cards spot-checked by Diya; error rate and BFS-reachability rate (the measure of authoring inflation) go in Limitations. Headline says "100 facts / 200 cards", never "300–1,000". | 3 of 4 agents hand-curated. `eval-scientist` preferred Wikidata; round 2: ACCEPTED hand-curated given commit-before-split + per-card source + reachability report. Wikidata cut: rate limits, 20-column label collisions, no rubric gain. |
| **D2 Policy** | **One policy, two training modes**, built **SL first** then RL: `--train sl` (supervised on BFS-discovered paths) and `--train rl` (REINFORCE + moving-average baseline + entropy + action dropout). Both decoded by **beam search B=64**. **Architecture: no LSTM.** Softmax over action scores from (query-relation, current-entity, candidate-relation, candidate-target) embeddings with path history as the mean of previous relation embeddings → closed-form gradients, numpy only. **Pre-registration:** RL is the headline mode; both modes are tested at Holm-Bonferroni-corrected α (0.025 each); if RL fails and SL passes, the headline reports SL and states RL's failure. | `eval-scientist` round 2: "headline = whichever passes" is post-hoc selection → fixed by pre-registration + correction. `scope-risk` round 2: numpy LSTM backprop is a trap → linear-softmax policy or torch; arbiter picks numpy-linear for fresh-clone speed and discloses the deviation from MINERVA's LSTM. |
| **D3 UI** | **Static web page** (plain HTML/JS, IBM Plex Mono) that replays trace JSON produced by the CLI. **Hosted on GitHub Pages.** No backend. Precomputed traces for the suggested questions; typed questions on the hosted page resolve against precomputed `(e, r)` beam results with templated narration. LLM parser + LLM narrator run in the local CLI, with cached responses committed so the fresh-clone gate runs `--offline`. | All four: web. `judge-sim`: URL required, +2 Design +1 Presentation vs terminal. `scope-risk`'s "drop hosting" overruled by the published rule (C4); its own static-replayer design makes hosting ~0.25 h. |
| **D4 Kiro features** | See §5. **MCP server does real work:** a Kiro-written stdio server exposing the deck with **two tools** (`punch_card`, `query_deck`) that Kiro itself uses while authoring cards; lint and decode stay CLI. **Visibility is a MUST:** the write-up includes a transcript/screenshot of Kiro calling the tools, and the 20-s IDE clip shows one call. Cols 56–63 = source code (deck); cols 64–72 = blank in deck, **step confidence** punched on the *read* copy of path cards (stretch S2). | `judge-sim` round 2: deck-MCP scores 8/10 vs 6.5 for Wikidata fact-check, *but drops to ~5 if judges can't see it* → visibility made MUST. `scope-risk` round 2: 2 tools not 4 saves 0.25 h → accepted. |

## 3. Locked scope (MUST) and cut list

### MUST — the product
1. Deck file (`cards.deck`, 80-char lines) is the **only** fact store; encoder/decoder with IBM 029 code table; invalid characters rejected; layout 1–20 / 21–35 / 36–55 / 73–80 enforced.
2. Every edge has its inverse; no dangling entities; relation vocabulary fixed in steering.
3. Walker with RL + SL modes, beam decoding, path for every answer; `hollerith ask "<question>"` → trace JSON.
4. Parser: LLM with **regex fallback** for the suggested questions. Unknown entity → `NO CARDS, NO ANSWER` card.
5. Narrator: LLM, constrained to path cards, cites `[seq]`; **templated fallback**; deterministic faithfulness check.
6. Web reader with **one animation**: cards drop into the stacker one at a time (~0.7 s apart, CSS `animation-delay`), each with a whole-card amber hole-glow, in step with one green-bar line printing. Hopper of **4 suggested questions**; green-bar listing with `[seq]` citations linked to cards; **jam** = card tilts in the throat, red CHECK lamp lights, card goes to the reject pocket; **hover a column to decode its character**; **type-ahead chips** limited to known entities and relations so every typed question resolves; off-graph → `NO CARDS, NO ANSWER` card. Typed-question listing is labelled `LISTING MODE — full narration in CLI`.
7. **Pull-a-card, precomputed:** the CLI precompute re-runs each suggested question once per path card with that card's edge masked (~12 extra traces); clicking PULL on a card swaps in its trace, which reroutes or jams, with templated narration. The feature that makes the cards proof rather than costume (~0.5 h).
8. Hosted URL (GitHub Pages), MIT license, `/.kiro` committed.
9. Evaluation per §4; `docs/arena/results.md` with every regenerating command.
10. ≤3-min video (incl. 20-s IDE clip of the hook firing and an MCP tool call), README with results table + Limitations + the LLM-only sentence from §10, Kiro write-up with MCP transcript, Devpost text, blog draft.

### SHOULD (stretch, in this order, only if the loop closed early)
- S1 Keypunch animation for the question (character-by-character, clack) (~0.5 h).
- S2 Step confidence punched in cols 64–72 on the read copy of path cards (~0.5 h; judge-sim: ≈ +0.3, invisible to non-experts).
- S3 LLM-only baseline on an **entity-anonymised** deck (`Entity_047`) (~0.25 h + API).
- S4 Click an entity on a card to ask the follow-up (~0.5 h).
- S5 Column-by-column light-bar scan; crumple on jam.

### CUT NOW
Wikidata as source · any web backend · LLM-as-judge faithfulness · hyperparameter sweeps · >3 hops · keypunch-your-own-fact (new entity has no embedding) · TransE · sound / physics · mobile · accounts · share URL · PNG export · terminal UI · LSTM policy · `decode_card` / `lint_deck` as MCP tools (CLI instead).

### CUT ON TRIGGER (kill-switches)
| Trigger | Action |
|---|---|
| L1 not closed by **Nov 28 EOD** | shrink deck to 150 triples |
| L2: neither RL nor SL passes exit criterion by **Dec 1 noon ET** | headline becomes the SL mode with the honest CI; RL reported as negative result |
| Web reader shows no deck after **1.5 h** | drop to the staggered reveal only (CSS `animation-delay`, no glow) + listing; keep jam tilt + lamp |
| Video not recorded by **Dec 3 noon PT** | stop all polish, record what exists |
| **Code freeze Dec 3 18:00 PT.** Dec 4 is slack only. | |

## 4. Evaluation protocol (eval-scientist veto applied)

- **Split:** **5-fold** CV by *fact*, 20 % held out per fold, queries in both directions → **200 pooled queries** at 100 facts (Hits@1 CI ≈ ±7 pp; each fact tested exactly once, so pooled n is identical to 10-fold at half the runs). Validation = one further fold held out of each training fold for tuning only. Reachability drop from the sparser training graph is reported.
- **Leakage gate (fail loudly):** for every test triple, *every* edge between {h, t} in both directions is removed from the training graph; the query's own edge is masked during training rollouts; relation pairs with Jaccard(h,t-pair sets) > 0.5 fail. Test entities absent from training are dropped and counted.
- **Reachability report:** share of test queries with a ≤T-hop path in the training graph; metrics on all queries and on the reachable subset. **BFS reachability is the oracle upper bound.** (This answers "why not BFS": with the edge held out, BFS can only enumerate candidates — it cannot pick the answer; the walker learns which paths imply which relation.)
- **Ranking:** filtered (Lin et al.), ties broken pessimistically by mean rank of the tie group. Unreached target → rank ∞ (MRR 0, miss). Beam coverage reported.
- **Metrics:** Hits@1, Hits@10, MRR; 3 fixed seeds; mean ± std over seeds *and* paired bootstrap (10 k) 95 % CI over queries.
- **Baselines:** random walk computed *exactly* as row e of Pᵀ (same action space incl. inverses and NO_OP, same T, no sampling variance); **frequency** (most frequent tail for r); LLM-only (same model & version, temperature 0, question + full entity list → top-10 IDs; non-mapping output = miss; **one run over all ~200 pooled queries**, responses cached and committed, policy Hits@1 reported on the same queries so the comparison is paired).
- **L2 exit criterion** (replaces "non-overlapping std"): paired-bootstrap 95 % CI on ΔHits@1 vs **max(random walk, frequency)** excludes 0 **and** McNemar exact p < **0.025** (Holm-Bonferroni across the two modes) **and** the sign holds in all 3 seeds. **Pre-registered headline mode: RL.**
- **Compute:** single training run ≤ 30 s on the M4; full suite (5 folds × 3 seeds × 2 modes = 30 runs) with `multiprocessing` regenerates in ≤ 15 min CPU *serial worst case*, one command.
- **Headline claim (and only this):** *"On an N-triple deck of 1880–1960 computing history, a learned walker answers held-out multi-hop queries better than random-walk and frequency baselines (ΔHits@1 = x, 95 % CI [a, b], n queries), and every narrated answer cites the cards on its path."*
- **Must-not claims:** beats LLMs or embeddings; **"the graph improves accuracy over the LLM"**; "reasons better"; generalises beyond this deck; comparable to published MINERVA/Lin numbers (and the policy has no LSTM); narration is factually correct (it is only *grounded*).
- **README sentence for the LLM-only result (judge-sim, adopted):** *"An LLM alone answers many of these questions from memory, so we report it as a memorisation reference rather than a target: the walker's claim is that every answer cites the cards it came from, and it refuses when no card exists."* Reported prominently even if higher.

## 5. Kiro-feature plan — what, where, what it proves

| Kiro feature | Location | What it does here | Visible evidence |
|---|---|---|---|
| **Specs** (requirements / design / tasks) | `.kiro/specs/01-card-encoder/`, `02-walker-eval/`, `03-reader-ui/` | one spec per loop; revised from `docs/arena/loop-N-findings.md` | spec v1 → v2 diff in README "How Kiro built this"; commits show spec landed before code; task checkboxes align with commits |
| **Steering** | `.kiro/steering/hollerith.md` | 029 code table, column layout, relation vocabulary — *single source of truth* the encoder, lint and UI all read | judge opens one file and sees the whole encoding standard |
| | `.kiro/steering/science.md` | seeds, leakage gate, claim/no-claim list from §4 | tests enforce it |
| | `.kiro/steering/product.md` | primary user, "NO CARDS, NO ANSWER", citation rule, tone | narrator prompt and UI copy trace to it |
| **Agent hooks** | `.kiro/hooks/` | (a) on save of `cards.deck` → card lint (20-col overflow, non-029 chars, Jaccard) + round-trip property test + leakage gate; (b) on save of `src/**` → test suite | 20-s IDE clip in the video of the hook firing |
| **MCP** | `.kiro/settings/mcp.json` → `src/hollerith/mcp_server.py` | Kiro-written stdio server: `punch_card`, `query_deck`; Kiro calls it while authoring cards | server in repo, config points at it, **transcript/screenshot of Kiro calling the tools in the write-up (MUST), one call in the 20-s IDE clip** |
| **Property-based tests** | `tests/test_roundtrip.py` (`hypothesis`) | encode→decode on ≥10 k random strings incl. empty, 80-char, invalid | hook output |
| **Disclosure** | README, one line | "Claude Code was used as an independent reviewer; it wrote no application code. Its review notes are in `docs/arena/`." | neutral per judge-sim if stated plainly and kept out of the video |

## 6. Loop plan, exit criteria, hour budget

| Loop | Dates | Scope | Exit criteria | h |
|---|---|---|---|---|
| **P0** | Nov 27 am | Kiro install; scaffold: 3 steering files, 3 spec skeletons, 2 hooks, MCP config, MIT license, `uv` project | `/.kiro` committed; hook fires on a dummy save | 0.5 |
| **L1** | Nov 27–28 | 029 encoder/decoder; deck format incl. source code cols 56–63; card lint; 2-tool MCP server; curated deck (100 facts / 200 cards) | 100 % round-trip on ≥10 k hypothesis cases; invalid chars rejected; layout enforced; no dangling entities; every edge has inverse; Jaccard lint passes; every card has a valid source code; MCP `query_deck` answers; all tests pass under the hook; deck committed before any split | 2.0 |
| **L2** | Nov 29–Dec 1 | 5-fold split + leakage gate + reachability; policy SL first then RL, beam; baselines; stats; `results.md` | leakage gate passes; §4 exit criterion met by the pre-registered mode (or fallback with RL failure stated); suite ≤15 min; deterministic under seed; path for every answer; `results.md` with commands | 3.5 |
| **L3** | Dec 1–2 | parser + narrator + faithfulness check; CLI → trace JSON incl. pull-a-card traces; web reader (one animation, jam, hover-decode, chips); precompute; GitHub Pages; fresh-clone gate | faithfulness ≥95 % over ≥50 questions (LLM narrator) and 100 % (templated); unknown entity → NO CARDS card; dead end → jam; pull-a-card reroutes or jams on all 4 questions; hosted URL live; `git clone → uv sync → make demo --offline` passes on a clean checkout; demo < 3 min | 3.5 |
| **Pack** | Dec 2–3 | video script + record; README (results, Limitations, How-Kiro-built-this); Kiro write-up; Devpost; blog draft | all five artifacts exist; freeze Dec 3 18:00 PT | 1.75 |
| **Submit** | Dec 4 am ET | — | submitted | — |
| | | | **Total committed** | **11.25** |
| | | | **Buffer** | **0.75** |

Buffer is thin and `scope-risk` warns the UI line is the most likely to overrun (its estimate: the original MUST list was under-costed by ~0.75 h; round 2 removed ~0.75 h of animation from it). The SHOULD list (§3) is funded only from loops that close early; the trigger table funds overruns. Each loop allows max 3 Kiro iterations; a challenger pass runs after each loop and once before submission.

## 7. Rubric — flagged for Diya (changes the pitch)

`judge-sim` could verify only the **2025** rules (Devpost 2026 page returned 403): **three** equally weighted criteria — *Potential Value*, *Implementation (Kiro use: variety and depth)*, *Quality & Design* — plus required artifacts (public repo, OSI license, `/.kiro` at root, working app URL, ≤3-min video, Kiro write-up). CLAUDE.md's five-criterion rubric is not the published one. Consequence: Potential Value and Kiro use each carry ~33 %, so the "answers you can audit" reframe and the real MCP/hook/steering work matter more than animation polish. The plan above is scored against both rubrics:

| Criterion (CLAUDE.md) | As proposed | After this ADR | Why |
|---|---|---|---|
| Potential Impact | 4 | 6 | audit framing, named user, hosted URL, NO-CARDS answer to hallucination |
| Kiro use | 7 | 8.5 | real MCP server, project-specific hook, steering as source of truth, spec evolution shown |
| Design | 6 | 8 | web reader, jam card, decode-on-hover, Plex Mono |
| Innovation | 7 | 8 | deck is the database; confidence in holes (stretch) |
| Presentation | 6 | 8 | scripted hero moment: question → cards → jam → backtrack → cited answer |
| **Weighted** | **6.0** | **≈7.7** | |

**Diya decides:** keep the five-criterion rubric as the internal target (it is a superset), or re-weight CLAUDE.md to the published three. The plan does not change either way; the *video script* would.

## 8. Risks carried forward (open after arbitration)
1. **Kiro overhead** (scope-risk #1, 4×5). Mitigation: ≤5 tasks per spec task-list; a task that fails twice is simplified in the spec, never hand-patched.
2. **Fact quality of a Kiro-drafted deck.** 200 triples spot-checked at 30; Limitations says so.
3. **LLM-only likely scores ≥ walker on Hits@1** (eval-scientist, uncertain). Pitch does not depend on beating it; S3 anonymised control is the cheapest rebuttal.
4. **RL may not pass** — covered by SL mode; RL then reported as a negative result.
5. **Rubric uncertainty** (§7).

## 9. Deferred to spec inputs
Exact relation vocabulary and the ≤10-entry source-reference list (Loop 1 steering); T (max hops, likely 3); abbreviation table for entities > 20 columns.

## 10. Round 2 — contests and rulings (arena rounds now exhausted)

Each agent was sent the round-1 arbitration and asked to accept or contest. Every agent accepted the majority of rulings; three contests were live.

| Contest | Raised by | Ruling | Why |
|---|---|---|---|
| **Pull-a-card back to MUST** | `product-design` (its #1 overturn); `judge-sim` (+1 on Design, Innovation *and* Presentation — best stretch by far) | **Upheld**, as the precomputed ≤0.5 h variant. Funded by `scope-risk`'s own savings: MCP 4→2 tools (−0.25 h), keypunch animation → stretch, scan bar + crumple cut (−0.5 h). | Two agents independently named it the single load-bearing feature; without it judge-sim scores the cards as costume. Net budget unchanged. |
| **Eval protocol too large** | `scope-risk` (60 runs ≠ ≤60 s/run); `judge-sim` (cut to 3 seeds + bootstrap, drop CV and McNemar) | **5-fold × 3 seeds × 2 modes = 30 runs ≤ 30 s, multiprocessing.** McNemar kept. | `eval-scientist`'s own first cut was folds (pooled n unchanged; 2 seeds would break the sign test). Judge-sim's cut overruled under rule 3 — the veto holds; CV costs Kiro ~0 extra and McNemar costs no runtime. |
| **Post-hoc headline selection** | `eval-scientist` ("RL if it passes else SL" lets us pick the winner after seeing results) | **Pre-register RL as headline; Holm-Bonferroni α = 0.025 per mode; if RL fails and SL passes, say so.** | Correct objection to the arbiter's own round-1 compromise. Costs nothing. |

Accepted without contest in round 2: hosting; deck-MCP (8/10 vs 6.5 for Wikidata fact-check, conditional on visibility → made MUST); LLM-only as memorisation reference (credibility gain; sentence adopted); hand-curated deck with per-card source code; templated narration for typed questions (labelled `LISTING MODE`); type-ahead chips (20 min) so typed questions resolve; SL built before RL; no-LSTM numpy policy; fallback keeps the staggered reveal.

Dissent recorded, not adopted: `scope-risk` would also move jam and hover-to-decode to stretch (−1 h). Overruled: jam *is* the pitch's answer to hallucination, and hover-to-decode is what makes raw holes legible to a judge (judge-sim's Design deduction). Both are cheap (tilt + lamp; tooltip).

---
**Next action on approval:** Diya pastes `docs/arena/spec-input-1.md` into Kiro for P0 + Loop 1.
