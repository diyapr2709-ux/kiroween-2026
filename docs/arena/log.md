# Arena decision log — Hollerith's Ghost

Claude Code is orchestrator / validator / challenger. It writes only under `docs/arena/`.
Kiro writes all application code, tests and `/.kiro`. Every decision below is logged with its
rationale so it can be audited later. Times are US Eastern unless stated.

---

## 2026-11-26 — Phase 0 kickoff

**State of repo:** empty (`git init` only, no commits, no `.kiro/`, no `src/`).

**Spawned four arena subagents in parallel**, each briefed with the same project context and a
role-specific question set, each capped at ≤400 words with a ranked list:

| Agent | Owns | Must settle |
|---|---|---|
| `scope-risk` | ≤12 h build budget, cut list, kill-switches | hour budget per component; D1–D3 from a schedule standpoint; which standards are expensive |
| `eval-scientist` | validity of the evaluation | split construction on a tiny graph, leakage paths, Hits@k from a walk policy, fair baselines, the honest headline claim |
| `judge-sim` | Kiroween rubric scoring | /10 per criterion, where points are lost, what "sufficient Kiro use" looks like in `/.kiro`, Resurrection fit |
| `product-design` | real user, complete-product loop, UI direction | primary user, core loop, web vs terminal, how the card metaphor becomes load-bearing, 3-min demo story |

**Arbiter rule set (fixed before results arrive, to avoid anchoring):**
1. Any conflict is resolved by the agent whose domain the conflict belongs to, unless it breaks a
   non-negotiable (Kiro writes all code; deadline fixed; scientific standards).
2. Schedule beats ambition: if `scope-risk` and any other agent disagree on *whether* to build
   something, `scope-risk` wins unless the feature is required to score on a rubric criterion
   (`judge-sim` adjudicates that).
3. `eval-scientist` has veto over any metric, claim or baseline.
4. Max 2 arbitration rounds; disagreements left after round 2 are recorded as open risks in the ADR.

**Environment facts gathered while agents run** (commands: `cal 11 2026; cal 12 2026`, `which kiro`,
`ls ~/.kiro`, `python3 --version`, `node --version`, `sysctl machdep.cpu.brand_string hw.ncpu hw.memsize`):

| Fact | Value | Consequence |
|---|---|---|
| Calendar | Thu Nov 26 → Fri Dec 4 2026 = 8 days | matches brief; Loop 1 starts tomorrow |
| **Kiro installed?** | **No.** No `kiro` / `kiro-cli` binary, no `/Applications/Kiro*.app`, no `~/.kiro` | **Day-0 blocker.** Nothing in `/.kiro` can exist until Kiro is installed and signed in. Goes into ADR as precondition P0. |
| Python | 3.12.13 + `uv` present; numpy / torch / hypothesis **not** installed | Python stack is viable. A numpy-only policy avoids a torch install on every fresh clone (fresh-clone gate gets faster and less fragile). `hypothesis` is a one-line add for property-based tests. |
| Node | v25.9.0 + npm present; no pnpm/bun | A static web UI (plain HTML/JS or Vite) is viable without a new toolchain. |
| Hardware | Apple M4, 10 cores, 24 GB | "<5 min CPU training" is a comfortable budget on this machine; the fresh-clone gate must still assume a slower machine. |

### Reports received (2 of 4) — positions recorded before arbitration

**`product-design`** — Primary user: curious learner of computing history ("tell me how X led to Y, and prove it"). Reframe: *"an AI that shows its receipts"* — the deck is the citation. UI: **web**. Core loop: hopper of 4 suggested questions → question keypunched → reader animation → green-bar narration citing `[seq]` → inspect / pull a card / click entity → save deck. Load-bearing ideas (≤1 h each): *pull-a-card* (remove a card, narrator re-runs, answer reroutes or jams); *confidence punched in columns 56–72* (policy step probability as digits — makes the RL visible). Must: suggested questions, reader animation, jam + reject pocket, `[seq]` citations, hover-to-decode a column, off-graph → "NO CARDS, NO ANSWER". Cut: keypunch-your-own-fact, Wikidata, terminal, mobile, accounts. 3-min demo story with timestamps supplied.

**`scope-risk`** — 9.5 h work + 2.5 h buffer. D1 hand-curated; D2 REINFORCE (baseline+entropy+action dropout) decoded by beam search, with a pre-agreed supervised-on-BFS-paths fallback (~0.5 h) if Hits@1 isn't ≥15 pts over random walk by Dec 1 noon; D3 **static web page replaying JSON traces written by the CLI** (no backend). Drop now: Wikidata, web backend, LLM-judge faithfulness, hyperparameter sweeps, >3 hops, hosting, sound/physics. Kill-switches: L1 late → 150 triples; web UI no deck after 1.5 h → `rich` terminal; video not recorded by Dec 3 noon PT → stop polish; **code freeze Dec 3 18:00 PT**. Top risk: Kiro overhead (≤5 tasks per spec; never hand-patch code). Commit cached LLM responses and run fresh-clone gate `--offline`; keep regex parser fallback. Faithfulness: deterministic entity-on-path check, not an LLM judge. LLM-only baseline: cut to 1 run, temperature 0, ~50 questions. Nov 26 is Thanksgiving → 0 h today.

**Early agreement:** D1 hand-curated; D3 web; Wikidata cut; deterministic faithfulness check.
**Early conflicts to arbitrate once all four are in:**
- C1 — `product-design` SHOULD list (click-entity follow-up, pull-a-card, PNG export, sound, share URL) vs `scope-risk` 1.5 h web budget and "no sound/physics". Rule 2 (schedule wins unless rubric-required) → needs `judge-sim`.
- C2 — `scope-risk` wants 3-seed runs under 5 min each; fine. But its "≥15 pts over random walk" kill-switch threshold and "non-overlapping std" exit criterion both need `eval-scientist` sign-off (rule 3).
- C3 — `scope-risk` cuts LLM-only baseline to 1 run / 50 q; `eval-scientist` must confirm that still counts as a baseline.

**`judge-sim`** (3 of 4) — **Rules check (2025 edition verified via kiro.dev blog + dev.to; 2026 Devpost rules page returned 403; 2026 deadline Dec 4 and a Best Resurrection prize confirmed via third-party listing only).** Published criteria are THREE, equally weighted: *Potential Value*, *Implementation* (Kiro use — "variety and depth"), *Quality & Design*. Our 5×20% rubric is not the published one: Innovation folds into Quality & Design; Presentation isn't scored separately; Kiro use and Potential Value (our weakest) are ~33% each. **Required artifacts:** public repo with OSI license, `/.kiro` at root and not gitignored, **a working app URL**, video ≤3 min, write-up of Kiro use. Score as proposed: 6.0/10 (≈5.8 under the 3-criterion rubric). Weakest: Potential Impact 4/10 ("BFS answers these exactly — why RL?"; no user). Kiro artifacts by points/hour: (1) README "How Kiro built this" with spec v1→v2 diff and commits showing specs landed before code; (2) steering doc `hollerith.md` holding the 029 table + column layout as single source of truth; (3) project-specific hook: editing triples → card lint (20-col overflow, non-029 chars) + round-trip test + leakage gate; (4) 20-s IDE clip of a task running and the hook firing; (5) an MCP server that does real work — a config file alone earns ~nothing. Claude Code as validator: neutral if disclosed in one line, kept out of the video, review docs in a separate folder, Kiro task checkboxes aligned with commits. Resurrection is currently a **skin**; load-bearing fixes: the deck file *is* the database; neighbour lookup = simulated IBM 082 sorter pass on cols 1–20; 029 charset + 20-col fields force consistent entity names; narrator cites seq numbers (73–80) and the faithfulness check verifies every cited card is on the path. Top improvement: reframe value as *"answers you can audit; a jam means 'I don't know', not a hallucination"* and show the LLM-only baseline hallucinating (+2). Add a BFS oracle as upper bound (credibility). UI: **web** (+2 Design, +1 Presentation vs terminal); precompute demo-question paths so the demo can't fail.

**Agreement now 3/3:** D1 hand-curated; D3 web; "AI that shows its receipts / audit" framing; deterministic faithfulness via `[seq]` citations; cards must be load-bearing not decorative.
**New conflicts:**
- C4 — **Hosting.** `scope-risk` drops hosting; `judge-sim` says a working app URL is *required*. Static-page-replaying-JSON (scope-risk's own D3) makes this cheap: GitHub Pages / Netlify drag-drop, ~0.25 h. Arbiter leans: hosting is non-negotiable; static deploy resolves it.
- C5 — **MCP server.** `judge-sim` wants a real MCP server (Wikidata SPARQL fact-check per triple, ID punched in 56–72); `scope-risk` drops Wikidata; `product-design` wants 56–72 for policy confidence. Two claims on the same columns and a 1 h cost. Needs arbitration.
- C6 — **Rubric itself.** CLAUDE.md's rubric is Diya's; published is 3-criterion. Arbiter will score against both and flag to Diya — this is a "changes the pitch" item.
- C7 — "Why RL, not BFS?" — needs `eval-scientist`'s answer; the honest framing may be that BFS is the oracle and RL is the learned approximation that generalises to unseen queries.

**`eval-scientist`** (4 of 4; sources: ar5iv 1711.05851, 1808.10568) — Validity threats ranked: (1) shortcut leakage beyond inverses (named inverse pairs, synonym relations) → remove every edge between {h,t} both directions, flag relation pairs with Jaccard > 0.5, mask the query edge during training rollouts; (2) 30 test queries → ±18 pp CI → **10-fold CV, both directions, pooled**; (3) unreachable held-out queries → report reachable share, metrics on all and on reachable subset; (4) filtered ranking, pessimistic ties; (5) **"non-overlapping std" over n=3 is not a test** → paired bootstrap 95 % CI on ΔHits@1 excludes 0 + McNemar p<0.05 + sign in all 3 seeds, vs max(random walk, **frequency baseline**). Random walk computed exactly as row e of Pᵀ. LLM-only: same model, temp 0, question + entity list → top-10 IDs; likely ≥60 % Hits@1 from memorisation → treat as reference, control with entity-anonymised deck. Hits@k via beam B=64, unreached = rank ∞. D1: prefers Wikidata (defensibility). D2: prefers learned scorer + beam (REINFORCE seed-sensitive on ~240 triples; MINERVA lost to DistMult on UMLS/Kinship). Headline and must-not claims supplied.

### Arbitration (round 1 of 2; no round 2 needed)

| Conflict | Resolution | Rule |
|---|---|---|
| C1 product SHOULD list vs 1.5 h UI budget | MUST = 4 suggested q, reader animation, jam + reject, `[seq]` citations, hover-decode, NO CARDS. Pull-a-card → S1 stretch. Sound/share/PNG/click-follow-up cut or stretch. | 2 (judge-sim: hero moment + load-bearing cards are the rubric-relevant parts; the rest is polish) |
| C2 exit criterion | eval-scientist's bootstrap + McNemar + sign test replaces "non-overlapping std"; "≥15 pts" kill-switch threshold dropped in favour of the test itself | 3 (veto) |
| C3 LLM-only budget | one run, temp 0, fixed 100-query subsample, cached & committed; anonymised control → S3 stretch | 3 defines it, 2 sizes it |
| C4 hosting | required by published rules → GitHub Pages static deploy (~0.25 h) | non-negotiable beats schedule |
| C5 MCP server / cols 56–72 | deck-MCP (`punch/decode/query/lint`) that Kiro uses while authoring — real work, offline, on-theme. Cols 56–72 → step confidence (stretch S2). Wikidata fact-check cut. | 1 (judge-sim owns "real work"; scope-risk owns the Wikidata cut) |
| C6 rubric mismatch | ADR scores against both; flagged to Diya as pitch-affecting (§7) | operating rule: ask before pitch changes |
| C7 why RL not BFS | BFS reachability = oracle upper bound; with the edge held out BFS cannot pick an answer. Goes in README. | 3 |
| D1 | hand-curated with commit-before-split protocol + Jaccard lint | 2, with eval's mitigation adopted |
| D2 | build RL **and** SL modes on one network (+0.5 h), report both; removes the Dec-1 gamble | arbiter compromise between scope-risk and eval |

**Budget after arbitration:** 11.25 h committed, 0.75 h buffer. Thin; trigger table in ADR §3 funds overruns.

**Output (v1.0):** ADR-001 drafted, stopped for approval.

### 2026-11-26 17:05 — Diya: "kiro will be accessible in a few mins, build rest of the code meanwhile" → declined
Writing application code is the one contract line that disqualifies the entry (Kiro must write all of `src/`, `tests/`, `.kiro/`; git history must show it). Instead: wrote [spec-input-1.md](spec-input-1.md) (P0 + Loop 1 brief for Kiro) and the arena agent definitions in `.claude/agents/` (`scope-risk`, `eval-scientist`, `judge-sim`, `product-design`, plus `challenger`, which CLAUDE.md requires after each loop). `.claude/agents/` is Claude Code tooling, not the app, and Diya asked for these files explicitly.

### 2026-11-26 17:08 — Diya: "resolve conflicts using agentic arena" → round 2 run
Each agent received the round-1 arbitration table and the rulings that went against it; asked to accept or contest with a budget-fitting alternative. All four replied.

| Agent | Accepted | Contested |
|---|---|---|
| `scope-risk` | hosting; MCP (if 2 tools); RL+SL both built (SL first) | 60-run eval contradicts ≤60 s/run → 5-fold × 3 × 2 = 30 runs ≤30 s, multiprocessing; numpy LSTM is a trap → linear-softmax policy; would move keypunch, jam, hover-decode to stretch (−1 h) |
| `eval-scientist` | hand-curated (with per-card source + reachability report); LLM-only reference (run all ~200, paired); anonymised control as stretch; folds → 5 first if needed | "headline = whichever passes" is post-hoc selection → pre-register or Holm-Bonferroni |
| `judge-sim` | deck-MCP 8/10 vs Wikidata 6.5 — *conditional on visibility*; LLM-only sentence supplied; Innovation 7.5, Design 6.5 as revised | would cut CV + McNemar to fund pull-a-card (+1 on three criteria) |
| `product-design` | templated typed-question narration (label `LISTING MODE`); one animation (cards drop + glow + line prints); fallback keeps staggered reveal | pull-a-card → MUST as precomputed ≤0.5 h variant; type-ahead chips (20 min) |

**Final rulings (ADR §10):** pull-a-card MUST (precomputed), funded by MCP 4→2 tools and keypunch/scan/crumple → stretch; eval = 5-fold × 3 seeds × 2 modes, McNemar kept (veto); RL pre-registered as headline, Holm α=0.025 per mode; no-LSTM numpy policy, SL built first; per-card source code in cols 56–63; MCP visibility (transcript + IDE clip) MUST; type-ahead chips MUST. Dissent not adopted: `scope-risk` on jam/hover-decode → stretch (jam is the pitch; hover-decode is a tooltip). Budget unchanged at 11.25 h / 0.75 h buffer; UI line flagged as most likely to overrun.

**Output (v1.1):** [ADR-001-direction.md](ADR-001-direction.md) §10; [spec-input-1.md](spec-input-1.md) updated to match. **STOPPED** for Diya's approval. Open for Diya: P0 (install Kiro — in progress per Diya), P1 (quota), §7 rubric choice, approve/amend ADR v1.1.

### 2026-11-26 17:20 — Diya: "build code also" (second time) → validation harness built, app code still Kiro's
Built `docs/arena/checks/` — Claude Code's independent validation harness, attributed as such, imported by nothing in the app: `ibm029_ref.py` (61-char 029 table, unique patterns), `check_roundtrip.py` (hypothesis, cross-checks Kiro's hole patterns against the reference), `check_deck.py` (layout / inverses / dangling / source codes / Jaccard), `check_leakage.py` (same-pair edge removal, exit 2 on leak), `stats.py` (paired bootstrap + McNemar exact + sign-over-seeds → PASS/FAIL), `check_faithfulness.py` (off-path entity / off-path citation), `selftest.sh`.
**Self-test output** (`bash docs/arena/checks/selftest.sh`): all 6 sections pass — 3 000 generated round-trip cases, 0 failures; broken deck rejected; inverse leak caught; synthetic stats PASS (ΔHits@1 +0.225, CI [+0.172, +0.278], McNemar p=9e-15); faithfulness 50/51 with the unfaithful trace reported. *Caveat:* the synthetic deck has 3 entities, so the off-path-entity rule was not exercised (TURING not in vocab); it is exercised once the real deck exists.
Still declined: writing `src/`, `tests/`, `.kiro/`. Reason unchanged — those must be Kiro's for the entry to survive judging, and the write-up must be truthful about authorship.

### 2026-11-26 17:25 — Diya shares `app.kiro.dev/session` → Kiro is WEB, not desktop
Consequence: Kiro works on a GitHub repo. Remote exists (`diyapr2709-ux/kiroween-2026`), `gh` authenticated, **zero commits**. P0 revised in ADR: first commit is `docs/arena/` + `.claude/agents/`, pushed, so Kiro's spec commits land after the arena. Awaiting Diya's go-ahead to commit and push (outward-facing action).

### 2026-11-26 17:30 — Diya: "but start building out on code as well" (third time) → Loop 1 built by Claude Code
Contract relaxed by Diya for `src/`, `tests/`, `data/`; **not** for `.kiro/`. Authorship ledger opened: [authorship.md](authorship.md). ADR §11 records the rubric consequence.
Built: `pyproject.toml` (uv, hatchling, `hollerith` CLI), MIT `LICENSE`, `.gitignore` (does not ignore `.kiro/`), `src/hollerith/{code_table,hollerith_code,deck,lint,cli}.py`, `tests/test_{roundtrip,code_table,deck,lint}.py`, `data/cards.deck`.
**Verification (commands and output):**
- `uv run pytest -q` → **80 passed, 1 skipped** (skip = steering-doc agreement test; `.kiro/steering/hollerith.md` not written yet). Round-trip property test runs 10 000 hypothesis cases ×2 (text-level and exact 80-column card-level).
- `uv run --with hypothesis python -I docs/arena/checks/check_roundtrip.py --cases 20000 --seed 7` → **20 000 cases, 0 failures**; app hole patterns equal the independent 029 table for all 61 characters; 13 invalid-input classes rejected with `CardEncodingError`.
- Deck authored via `Deck.punch` (scratch script, not in repo): **196 facts → 392 cards, 151 entities, 24 relation names (12 pairs)**; `uv run hollerith lint` → clean. Source codes: IBMARCH for IBM-world cards, CHM for machine built/used/succeeded, WIKI otherwise — reference *families*, not page citations (Limitations).
- `uv run hollerith neighbours "HERMAN HOLLERITH"` → 8 cards in sequence order via the sorter pass; `neighbours "ADA LOVELACE"` → `NO CARDS`, exit 1.
- **Harness defect found and fixed:** `check_deck.py` inferred inverses from any co-occurring (s,o)/(o,s) pair and raised 4 false "more than one inverse" failures (HOLLERITH both FOUNDED and LED TMC). Rewritten to require an inverse to cover *every* card of a relation. Re-run clean; a deliberately broken 3-card deck still trips `missing inverse` / `dangling`.
Still Kiro-only: `.kiro/**`. Proposed for Kiro: MCP server; Loop 2 or Loop 3 (ADR §11). Open: Diya's Kiro-scope choice; push approval; 30-card spot check (not by the author).

### 2026-11-26 17:40 — Diya: "github connected now use kiro" → repo already on GitHub; pushed deck + arena
Found commit `3231d20` (author/committer Diya, no trailer, 17:28) already on `origin/main` with everything but the deck. Pushed `c435787` (deck 196/392, ADR v1.1, authorship ledger, harness fixes). Committed to `main` directly — Diya's workflow here, and Kiro web reads `main`. Gave Diya the paste from spec-input-1 v2.

### 2026-11-26 17:55 — Loop 1 reviewer subagent report → 4 majors, 7 minors, 0 blockers; all fixed
Report and fixes in [loop-1-findings.md](loop-1-findings.md). Fixes committed as `8c58a1d` and pushed.
**Verification (commands and output):**
- `uv run pytest -q` → **160 passed, 1 skipped** (skip = steering-doc agreement test awaiting Kiro). Was 80; +80 tests cover strict load (8 layout violations), punch rejection (10 cases), card pairing, all 61 characters pinned, 12 CLI exit-code tests.
- `uv run --with hypothesis python -I docs/arena/checks/check_roundtrip.py --cases 5000 --seed 11` → 0 failures against the rebuilt encoder.
- `python3 -I docs/arena/checks/check_deck.py data/cards.deck --sources WIKI,IBMARCH,CHM` → 0 problems; `uv run hollerith lint` → clean.
- Reviewer's five adversarial `punch` calls re-run: duplicate-with-whitespace, self-loop-with-whitespace, empty subject, inverse-on-forward → rejected with `DeckError`; `" HOLLERITH"` → now normalised to `HOLLERITH` (correct; previously created a ghost entity).
- Deck accuracy (reviewer, seed 2026, 30 forward cards): 29 TRUE, 1 DOUBTFUL (Kilburn/Williams tube → replaced with Kilburn BUILT Manchester Baby), 0 FALSE.
- Fresh clone at `c435787` (reviewer): green.
**Loop 1 status: Claude Code's half closed; Kiro's half (spec-input-1 v2 groups A/B/C) not started.** Exit criteria still open: steering test un-skips and passes; hooks fire; MCP server answers; ≥5 Kiro-punched cards lint-clean.

### 2026-11-26 18:20 — Loop 2 evaluation infrastructure built (Claude Code); first honest numbers; reachability finding
Rationale for building this before Diya's who-builds-the-policy decision: the measuring stick belongs to the validator regardless of who builds the thing measured; it duplicates nothing either way. Commit `a743536`.
Built: `graph.py` (view over cards, BFS), `split.py` (5-fold by fact, both directions, same-pair exclusion, val slice, reachability + answerability per query, `assert_no_leakage`, JSONL in the harness format), `baselines.py` (`Ranker` interface; exact random walk = row of Pᵀ over out-cards + NO_OP; frequency), `evaluate.py` (filtered ranking, mean-rank ties, rank ∞ when unreached, Hits@1/10, MRR, reachable-subset Hits@1, coverage, `hits1.csv` + `summary.json` with the regenerating command), CLI `split`/`eval`, 12 tests. `numpy` added.
**Verification:** `uv run pytest -q` → **172 passed, 1 skipped**. `uv run hollerith split` → 392 queries, excluded_facts 4. `python3 -I docs/arena/checks/check_leakage.py --folds splits` → 0 leaks in 5 folds. `uv run hollerith eval --systems random_walk,frequency --seeds 0,1,2` (0.25 s):

| system | Hits@1 | Hits@10 | MRR | Hits@1 (reachable) | coverage |
|---|---|---|---|---|---|
| frequency | 0.020 ± 0.000 | 0.158 ± 0.000 | 0.055 ± 0.000 | 0.011 | 0.191 |
| random_walk | 0.000 ± 0.000 | 0.179 ± 0.000 | 0.036 ± 0.000 | 0.000 | 0.235 |

`stats.py frequency vs random_walk`: Δ=+0.020, 95 % CI [+0.013, +0.029], McNemar p=1.2e-7, sign in 3/3 → the harness's PASS/FAIL logic works on real output.

**FINDING L2-F1 (major, structural): reachability ceiling 23.5 %.** Only 92/392 gold answers are within 3 hops of the training graph; 77 % of query entities exist in train. Hops sweep: T=3 23.5 %, 4 27.6 %, 5 29.1 %, 6 30.6 %, 8 36.7 %. Cause: 53/151 entities (35 %) are degree-1 leaves (LOCATION OF 12, BIRTHPLACE OF 8, INVENTED BY 6, BUILT BY 6 …). By relation: SUCCEEDED 56 %, WORKED AT 33 %, … LOCATED IN 5 %, BORN IN 8 %, RENAMED 0 %. **No walker can exceed 23.5 % Hits@1 overall.** Options A (report both) / B (pre-registered testable-fact universe, degree ≥ 2 both ends) / C (densify deck ~100 facts) / D (drop place relations from test) sent to `eval-scientist` (validity) and `scope-risk` (hours) for a ruling. Commands: `uv run hollerith split --hops N`; degree diagnostics script in log history.

**`scope-risk` ruling on L2-F1 (18:40):** A+B, ≤0.35 h; if the ceiling under B is still <50 %, stop and ship A's reporting. Reject C (0.85 h, authoring toward paths). D subsumed by B. Kill-switch becomes a headline choice: by Dec 1 noon, if RL trails SL by ≥10 pts on the reachable subset or its CI includes 0, headline SL and report RL as ablation; always show the ceiling beside Hits@1. Recommended split: Kiro builds UI + MCP + `.kiro/`; Claude Code builds the policy → 8.1 h remaining work, 1.15 h buffer (0.15 h if Kiro builds policy *and* UI). Flagged Claude-Code-writes-`src/` as a blocker — already ruled by Diya (ADR §11); README discloses. Awaiting `eval-scientist` for the exact "testable fact" rule before implementing B.

**`eval-scientist` ruling on L2-F1 (18:45):** B primary (testable iff both endpoints ≥ 2 distinct neighbours in the full deck; structure-only rule, defines the task rather than selecting results); A secondary beside the ceiling; C rejected (authoring toward paths); D rejected (post-hoc). Baselines re-run on the identical universe. Reachable-subset Hits@1 is a labelled diagnostic, not the test. Mean-rank ties confirmed. Revised headline template recorded in results.md. Warned the 40–60 % estimate was unchecked.

### 2026-11-26 19:00 — Universe B implemented; walking graph = train ∪ val; T = 4 pre-registered
`split.testable_facts`, `--universe testable|all` on `split`/`eval`; `Ranker.fit(graph, train_facts, val_facts, seed)` so every system walks the same graph; val cards stay in the graph (their facts are masked tuning queries). Tests: 176 passed, 1 skipped. Independent leakage gate: 0 leaks.
**Real figures (eval-scientist asked):** B = 144/196 facts, 288 queries; reachable **34.7 % (T=3), 40.3 % (T=4), 43.8 % (T=5)**; answerable 90.3 % (the rest: an entity's other edges fell in the same test fold). A at T=3: reachable 30.1 %, answerable 80.6 %. Baselines B/T=3: frequency Hits@1 0.035, random walk 0.000. Under scope-risk's rule (<50 % → stop, ship A's reporting) no further spend on the ceiling. **T = 4 fixed now, before any policy**: lifts the ceiling for all systems equally and a 4-card answer fits the reader. Full table and commands: [results.md](results.md). Time on L2-F1: ~0.3 h (cap 0.35).

### 2026-11-26 19:30 — Walker built (Claude Code); SL passes the pre-registered exit test; RL running
Decision: proceed with the policy without Diya's explicit who-builds-what answer, following `scope-risk`'s recommended split (Kiro: UI + MCP + `.kiro/`; Claude Code: policy); not pitch-changing; reassignable. `policy.py` per ADR D2 (no LSTM, numpy, closed-form gradients verified by finite differences; RL + SL on the same parameters; beam B=64; query entity never an answer). Commit pushed.
**Verification:** `uv run pytest -q` → **185 passed, 1 skipped**; toy composition learned by both modes.
**Results (universe B, T=4, 3 seeds; `results.md`):** policy_sl Hits@1 **0.073 ± 0.006**, Hits@10 0.274, MRR 0.129, reachable-subset 0.181; frequency 0.035; random walk 0.000. `stats.py`: Δ +0.038, CI [+0.017, +0.059], McNemar p=0.0006 < 0.025, sign 3/3 → **PASS**. SL ≈ 0.8 s/run.
RL seed 0 (5 folds): Hits@1 0.073, reachable-subset 0.181 — same as SL — but **46 s/run** (target ≤30 s; suite ≈12 min, within 15-min ceiling). Not reducing rollouts/epochs after seeing results; deviation recorded. Full 3-seed RL run started in background; Loop 2 reviewer subagent spawned on the policy/eval code and on the pooled-seed statistics question.

### 2026-11-26 20:15 — Loop 3 `ask` pipeline built; RL v1 run finished; Loop 2 reviewer: NOT ready — statistics were wrong
Built `parse.py` (deterministic entity + relation-shape parser, aliases), `narrate.py` (templated, cites `[seq]`), `trace.py` (`ask` pipeline: direct card → walker → jam/no_cards; trace JSON schema; `--pull SEQ`; model save/load), `questions.py` (one natural question per card; all 392 parse back), CLI `train`/`ask`. Product rules added after smoke tests: walks are simple paths (oscillation A→B→A→B found on "Who founded Ferranti?"); a path whose relation chain never explained the asked relation in training is a **jam ("unknown path shape")**; 1-card inferred answers narrated as inferred.
RL v1 (3 seeds, 13 min): policy_rl 0.072 ± 0.002 — same as SL; RL vs SL paired Δ −0.001.
**Loop 2 reviewer (26 tool calls):** BLOCKER — the simple-paths change was post-hoc and drops SL to 0.044/FAIL; MAJOR — pooled-seed statistics were pseudo-replication (per-seed McNemar p 0.136/0.029/0.061; fact-clustered CI includes 0); MAJOR — random walk 0.000 was a subject-mass artefact (→ 0.017); MAJOR — leakage harness ignored val; MAJOR — 25/25 mutations survived. Clean: leak proof over 15,047 beam cards, FD gradients 1e-10, reproducibility. Full report: [loop-2-findings.md](loop-2-findings.md).
**Fixes:** `simple_paths` flag OFF for eval / ON for product, ablation reported; evaluator filters the subject for all systems; `stats.py` rewritten (seed-averaged, fact-clustered bootstrap, per-seed McNemar); leakage gate unions val; 14 new protocol/stats tests. **Pooled PASS withdrawn.**
**Honest Loop 2 result (corrected):** policy_sl 0.073 ± 0.007 vs frequency 0.035; Δ +0.038, sign 3/3, CI [−0.001, +0.080], per-seed p 0.136/0.029/0.061 → **does not meet the pre-registered bar**. [results.md](results.md) rewritten with this headline. RL re-run under the corrected evaluator in progress (background, ~13 min).
**Product numbers:** faithfulness 657/657 = 100 %; pull-a-card over 392 cards: recovered 34 %, jam 19 %, grounded-but-wrong 33 %, no cards 14 %.

**`eval-scientist` on the revised headline (20:40):** wording accepted with fixes — lead with "criterion not met"; ± is seed sd (optimiser noise), the CI is the uncertainty; publish only with RL rows under Holm; **disclose that T=4 followed the reachability sweep** (structural, pre-training). Keep per-seed all-must-pass McNemar (conservative reading; majority vote would be a forking path and fails anyway, p=0.12); the fact-clustered bootstrap is the more valid test and fails too → "fails under every reading". Must-not additions recorded in results.md and ADR §4. All applied; spec-input-2 (Kiro web reader) written and pushed; challenger #1 spawned.

**Hours used:** ~5.0 h of 12. **Hours left:** ~7.0.
