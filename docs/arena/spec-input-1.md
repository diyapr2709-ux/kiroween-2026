# Spec input 1 (revised) — Kiro's Loop 1: `.kiro/` scaffold, steering, hooks, MCP server

*Revision history: v1 (Nov 26 17:00) asked Kiro to build the whole encoder/deck. At 17:30 Diya had
Claude Code build the encoder, deck, lint, CLI and tests instead (see [authorship.md](authorship.md),
ADR §11). This v2 gives Kiro the pieces that are still unbuilt and that judges look at first.
Claude Code validates against the exit criteria at the bottom and writes `loop-1-findings.md`.*

---

## Paste into Kiro (start of brief)

You are working on **Hollerith's Ghost**, a Kiroween 2026 entry (Resurrection category): a
knowledge graph of computing history 1880–1964 where **every fact is an IBM 80-column punched
card**, encoded with the IBM 029 code. A learned walker (Loop 2) will answer multi-hop questions
by walking the cards; a web card-reader (Loop 3) will replay the walk. **The deck file
`data/cards.deck` is the only database.**

Read first, do not modify: `src/hollerith/code_table.py` (the encoding standard: code table,
column layout, relation vocabulary, source codes), `src/hollerith/deck.py` (the `Deck` API),
`src/hollerith/cli.py`, `README.md`. Run `uv run pytest -q` — 80 tests pass, 1 is skipped until
you write the steering doc.

Produce a spec (requirements → design → tasks, **≤ 8 tasks**) under `.kiro/specs/01-card-tooling/`,
then implement it. If a task fails twice, simplify the task in the spec; never patch around it.

### Task group A — Kiro project scaffold (`.kiro/`)
1. **`steering/hollerith.md`** — the encoding standard in prose, mirroring `code_table.py` exactly:
   the full 029 character → hole-rows table (rows 12, 11, 0, 1–9), the column layout
   (1–20 subject · 21–35 relation · 36–55 object · 56–63 source code · 64–72 reserved blank ·
   73–80 sequence), the twelve relation pairs with their inverses, and the three source codes
   with what they mean. State the two rules: letters are upper-cased; any character outside the
   set is rejected. The existing test `tests/test_code_table.py::test_steering_doc_agrees_if_present`
   will un-skip and check that every relation and source name appears in your doc.
2. **`steering/science.md`** — fixed seeds `[0, 1, 2]`; every reported number carries mean ± std
   and the exact command that regenerates it; the leakage gate must fail loudly; claims the
   project must NOT make: beats LLMs or embeddings; "the graph improves accuracy over the LLM";
   generalises beyond this deck; comparable to published MINERVA numbers; narration is factually
   correct (it is only *grounded* in cards).
3. **`steering/product.md`** — primary user: a curious learner of computing history who wants
   *"tell me how X led to Y, and prove it."* Every answer cites card sequence numbers in the form
   `[00000012]`. An entity not in the deck returns **`NO CARDS, NO ANSWER`**; a dead end is a
   **jammed card**. Never state a fact that is not on a card on the path.
4. **Agent hooks** under `.kiro/hooks/`: (a) on save of `data/cards.deck` → run
   `uv run hollerith lint data/cards.deck && uv run pytest -q tests/test_lint.py tests/test_deck.py`;
   (b) on save of `src/**/*.py` or `tests/**/*.py` → run `uv run pytest -q`.
5. **`settings/mcp.json`** registering the server from group B as `hollerith-deck`
   (command `uv`, args `run python -m hollerith.mcp_server`, cwd = repo root).
6. Spec skeletons `.kiro/specs/02-walker-eval/` and `.kiro/specs/03-reader-ui/` (requirements
   headings only).

### Task group B — MCP server (`src/hollerith/mcp_server.py`)
Add the Python MCP SDK (`mcp`) to `pyproject.toml` dependencies. A stdio server with **exactly
two tools**, both thin wrappers over the existing `Deck` API — do not re-implement the deck:
- `punch_card(subject, relation, object, source)` → calls `Deck.load("data/cards.deck").punch(...)`,
  saves, returns both 80-column lines (fact and inverse) and their sequence numbers. On a
  `DeckError` return the error text; never crash the server.
- `query_deck(entity, relation=None)` → `Deck.neighbours(entity)` filtered by relation if given;
  returns `[{"seq", "subject", "relation", "object", "source", "line"}]`, or `"NO CARDS"` if empty.
Tests in `tests/test_mcp_server.py`: both tools against a temp deck copy; a bad relation returns
an error string; an unknown entity returns `NO CARDS`.

### Task group C — use the server to author cards (this is the evidence judges want)
With the server registered, use **`query_deck`** to inspect what the deck already says about
three entities of your choice, then use **`punch_card`** to add **≥ 5 new facts you are confident
are true** about computing history 1880–1964, within the relation vocabulary, each with a source
code. Then run `uv run hollerith lint data/cards.deck` (must be clean) and `uv run pytest -q`.
Keep the chat transcript of the tool calls — it goes into the Kiro write-up and the demo video.

### Definition of done (check before reporting back)
- `uv run pytest -q` passes with **0 skipped**.
- `uv run hollerith lint data/cards.deck` exits 0; the deck has ≥ 10 more lines than before.
- Both hooks fire on their triggers.
- `uv run python -m hollerith.mcp_server` starts and answers `query_deck("HERMAN HOLLERITH")`.
- `.kiro/` is committed and not ignored; commits land in this order: spec → steering/hooks/mcp.json → server → cards.
- Work on a branch and **open a pull request to `main`** titled `kiro: loop 1 — .kiro scaffold, MCP server, cards`
  with a description listing which steering docs, hooks and tools you created and which cards you punched.

## (end of paste)

---

## Claude Code validation plan for Loop 1 (not for Kiro)
Already run against the Claude-Code-built core (results in [log.md](log.md) 17:30 entry):
round-trip 20 000 cases 0 failures; independent 029 table agreement; deck lint clean (both lints);
80 tests pass; CLI smoke incl. `NO CARDS`.
Remaining, after Kiro's part lands:
1. `uv run pytest -q` → 0 skipped (steering agreement test active).
2. Hook (a): edit one card to 79 chars, save → hook must fail; revert.
3. MCP: start server via `mcp` dev client, call both tools; `punch_card` with relation `KNOWS`
   must return an error, not crash.
4. `python3 -I docs/arena/checks/check_deck.py data/cards.deck --sources WIKI,IBMARCH,CHM` on the
   grown deck; `git log` shows spec commit before server commit.
5. Reviewer subagent + 30-card fact spot check (not by the deck's author).
6. Findings → `loop-1-findings.md` (blocker / major / minor, each with the failing command).

**Exit:** all of the above pass; every card Kiro punched is on-vocabulary and lint-clean; Kiro's
tool-call transcript saved under `docs/kiro/` (Kiro writes it) for the write-up.
