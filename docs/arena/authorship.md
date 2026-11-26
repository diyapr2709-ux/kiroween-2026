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
| `data/cards.deck` | Claude Code (authored from training knowledge; 30-card spot check pending) | source codes name the reference family, not page-level citations |
| `.kiro/**` | **Kiro only** | specs, steering, hooks, MCP config — none written yet |
| `src/hollerith/mcp_server.py` | *unassigned* | proposed for Kiro |
| Loop 2 (`split.py`, `policy.py`, `baselines.py`, `evaluate.py`) | *unassigned* | Diya decides |
| Loop 3 (`parse.py`, `narrate.py`, `trace.py`, `web/`) | *unassigned* | Diya decides |

Git evidence: commits Claude Code makes carry a `Co-Authored-By: Claude …` trailer. Kiro's
commits carry Kiro's. The README's "How this was built" section must match this table.

Commit notes:
- `3231d20` "Initialize Hollerith's Ghost project" — author/committer Diya, no trailer. Contains
  the Claude-Code-written files listed above (arena docs, agents, Loop 1 code and tests). The
  commit author is the person who pressed commit, not the author of the files; this table is
  authoritative for the latter.
