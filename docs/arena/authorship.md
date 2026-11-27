# Authorship ledger

Kiroween judges score how Kiro was used. This ledger exists so that every claim about who
wrote what is checkable against `git log`. It is updated whenever authorship of a path changes.

**Decision (2026-11-26, Diya, three times):** Claude Code was told to build application code
in addition to its orchestrator/validator role. The original contract (Kiro writes all of
`src/`, `tests/`, `.kiro/`) was relaxed by Diya for `src/`, `tests/` and `data/`. It was **not**
relaxed for `.kiro/`: everything under `.kiro/` is written by Kiro, or it does not exist.

| Path | Author | Notes |
|---|---|---|
| `docs/arena/**` | Claude Code | arena reports, ADR, spec inputs, findings, validation harness |
| `.claude/agents/**` | Claude Code | arena agent definitions (Claude Code tooling, not the app) |
| `pyproject.toml`, `LICENSE`, `.gitignore`, `README.md` (stub) | Claude Code | Loop 1 scaffold |
| `src/hollerith/code_table.py` | Claude Code | 029 table, layout, relation vocabulary, sources |
| `src/hollerith/hollerith_code.py` | Claude Code | Card, encode, decode, punch_fields |
| `src/hollerith/deck.py` | Claude Code | Deck as database, sorter-pass neighbours, punch |
| `src/hollerith/lint.py` | Claude Code | card lint rules |
| `src/hollerith/cli.py` | Claude Code | `hollerith lint/decode/punch/show/neighbours` |
| `tests/test_roundtrip.py`, `test_code_table.py`, `test_deck.py`, `test_lint.py` | Claude Code | Loop 1 tests |
| `data/cards.deck` | Claude Code (authored from training knowledge; reviewer spot-checked 30 cards: 29 true, 1 doubtful → replaced) | source codes name the reference family, not page-level citations |
| `src/hollerith/{graph,split,baselines,evaluate}.py`, `tests/test_split_eval.py`, `tests/test_protocol.py` | Claude Code | Loop 2 evaluation protocol (universe B, leakage gate, baselines, filtered ranking) |
| `src/hollerith/policy.py`, `tests/test_policy.py` | Claude Code | the walker (RL + SL, beam decoding) |
| `src/hollerith/{parse,narrate,trace,questions}.py`, `tests/test_ask.py`, `tests/test_questions.py` | Claude Code | Loop 3 CLI side: parser, templated narrator, `ask` pipeline, trace JSON, pull-a-card |
| `tests/test_cli.py`, `tests/test_stats_harness.py` | Claude Code | |
| `README.md` | Claude Code draft; Diya finalises | "How this was built" must match this table |
| `.kiro/**` | **Kiro only** | specs, steering, hooks, MCP config — none written yet (spec-input-1 v2) |
| `src/hollerith/mcp_server.py`, `tests/test_mcp_server.py` | **Kiro** (assigned, spec-input-1 v2) | not written yet |
| `web/**`, `hollerith precompute`, `.github/workflows/pages.yml` | **Kiro** (assigned, spec-input-2) | not written yet |
| `docs/kiro/**` | **Kiro** | tool-call transcripts for the write-up |

Git evidence: commits Claude Code makes carry a `Co-Authored-By: Claude …` trailer. Kiro's
commits carry Kiro's. The README's "How this was built" section must match this table.

Commit notes:
- `3231d20` "Initialize Hollerith's Ghost project" — author/committer Diya, no trailer. Contains
  the Claude-Code-written files listed above (arena docs, agents, Loop 1 code and tests). The
  commit author is the person who pressed commit, not the author of the files; this table is
  authoritative for the latter.
