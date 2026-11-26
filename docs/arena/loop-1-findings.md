# Loop 1 findings — card encoder, deck, lint, CLI

**Scope reviewed:** `src/hollerith/*.py`, `tests/*.py`, `data/cards.deck`, `pyproject.toml` at commit
`c435787` (Claude-Code-built core; see [authorship.md](authorship.md)).
**Reviewer:** independent subagent, hostile brief, 19 tool calls, fresh clone included.
**Validation harness:** `docs/arena/checks/` (results in [log.md](log.md)).
**Status:** Claude Code's part — all findings fixed in the follow-up commit. **Loop 1 is NOT closed:**
Kiro's part (`.kiro/` scaffold, steering, hooks, MCP server, authored cards — [spec-input-1.md](spec-input-1.md) v2)
does not exist yet.

## Blockers
None.

## Majors (all fixed)

| # | Finding | Demonstration | Fix | Verified by |
|---|---|---|---|---|
| M1 | `Deck.punch` accepted duplicates hidden by whitespace, **self-loops** (`IBM FOUNDED IBM `), ghost entities with a leading blank, and an empty subject. Lint caught only the blank/duplicate cases. `MCP punch_card` would have exposed all of this to Kiro. | `d.punch("IBM","FOUNDED","IBM ",…)` succeeded; lint clean | `punch` strips + upper-cases every field, rejects empty, self-loop after normalisation; `punch_fields` rejects empty; lint rules *self-loop* and *leading blank* added | `tests/test_deck.py::test_punch_rejects` (10 cases), `test_punch_strips_and_uppercases`; `tests/test_lint.py::test_self_loop`, `test_leading_blank_in_field` |
| M2 | `Deck.load` enforced only the charset. A deck with `ABCDEFGH` in cols 73–80 or garbage in 64–72 loaded, then `.facts()` / `hollerith show` crashed with a raw `ValueError` traceback. "Layout enforced" (ADR §3 MUST 1) held only in lint. | load `alpha_seq.deck` → `ValueError: invalid literal for int()` | `Deck.load` runs `lint.line_problems` per line and raises `DeckError` with the line number; `Fact.from_card` raises `DeckError`; CRLF rejected | `test_load_rejects_layout_violations` (8 cases), `test_load_rejects_crlf`, `test_corrupt_deck_exits_2` |
| M3 | An inverse relation was accepted on a forward (odd) card; the 2k−1 / 2k pairing the Loop 2 split-by-fact relies on was a convention nothing enforced. | `d.punch("FOO CO","FOUNDED BY","SOMEONE","WIKI")` succeeded; both lints passed | `punch` requires a forward relation (error names the forward form); lint rules *odd card count*, *card 2k mirrors 2k−1*, *sequence +1*, *forward card carries forward relation* | `test_punch_inverse_error_names_the_forward_form`; `test_lint.py::test_forward_card_with_inverse_relation`, `test_second_card_must_mirror_first`, `test_pair_sequence_must_be_consecutive`, `test_odd_card_count` |
| M4 | `cli.py` had zero tests; mutations `cmd_lint → return 0` and `NO CARDS → return 0` survived the suite. Hook (a) depends entirely on these exit codes. | mutation testing | `tests/test_cli.py`: every subcommand's exit code and output; exit 2 for unreadable deck | 12 CLI tests |

## Minors (all fixed)

| # | Finding | Fix |
|---|---|---|
| m1 | `hollerith lint /nonexistent` → raw `FileNotFoundError` | `main` catches `OSError`/`DeckError` → `error:` + exit 2 |
| m2 | `decode` of an 80-char lowercase line failed while 79 chars succeeded | `decode` always goes through `encode` |
| m3 | CRLF deck loaded and linted clean (universal newlines) | strict byte read; `\r` is an error in both load and lint |
| m4 | `test_shipped_deck_is_clean` and the steering test used cwd-relative paths → silently **skipped** when pytest ran from elsewhere | anchored on `Path(__file__).parents[1]`; shipped-deck test now *fails* if the deck is missing |
| m5 | Only 24 of 61 characters pinned in pytest (`<`, `¬` … unpinned) | all 61 pinned; `test_known_table_is_complete` |
| m6 | Surviving mutations: Jaccard `>`→`>=`, dropped never-an-object rule, dropped neighbours seq-sort, `pytest.raises(Exception)` | boundary test at exactly 0.5; dangling-object test; insertion-order ≠ sequence-order test; `CardEncodingError` asserted |
| m7 | Steering-doc test was a substring check ("FOUNDED" satisfied by "FOUNDED BY"); hole patterns unchecked | word-boundary regex; every character's `12-8-3`-style pattern must appear |

## Spec checks (reviewer)
- `neighbours` is a real sort + bisect over card text per call, no import-time index — **honoured**.
- The deck is the only fact store (`code_table.py` holds vocabulary only) — **honoured**.
- Inverses and dangling entities enforced by lint and punch — **honoured**.
- Fresh clone at `c435787`: `git clone → uv sync → uv run pytest` → green; `data/` and `uv.lock` tracked — **no fragility** beyond m4.

## Deck accuracy — 30 forward cards, `random.Random(2026).sample(odd_cards, 30)`
**29 TRUE, 1 DOUBTFUL, 0 FALSE.** Doubtful: `[215] TOM KILBURN INVENTED WILLIAMS TUBE` — Williams holds the
1946 patent; Kilburn co-developed it. **Fixed:** replaced by `TOM KILBURN BUILT MANCHESTER BABY`. Sequence
numbers shifted (deck regenerated; no split exists yet, so the commit-before-split protocol holds).
Spot-check was done by the reviewer, not the deck's author. Error rate for Limitations: 1/30 doubtful, 0/30 false.

## Still open before Loop 1 closes
1. Kiro's group A/B/C from spec-input-1 v2 (`.kiro/` scaffold, MCP server, ≥5 Kiro-punched cards).
2. `tests/test_code_table.py::test_steering_doc_agrees_if_present` currently **skipped** — un-skips when Kiro writes `.kiro/steering/hollerith.md`; must then pass.
3. Hook (a) fires on a deck save and fails on a 79-column card (manual check once hooks exist).
4. MCP `punch_card` with relation `KNOWS` returns an error string, does not crash.
