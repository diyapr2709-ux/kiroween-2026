# Spec input 1 — P0 scaffold + Loop 1: card encoder, deck, lint, MCP server

*This is the brief Diya gives Kiro. Kiro generates its own spec (requirements → design → tasks) from
it under `.kiro/specs/01-card-encoder/`. Claude Code validates the result against the exit criteria
at the bottom and writes `docs/arena/loop-1-findings.md`. Source of decisions: [ADR-001](ADR-001-direction.md).*

---

## Paste into Kiro (start of brief)

You are building **Hollerith's Ghost**, a Kiroween 2026 entry (Resurrection category). The whole
app is built with Kiro; this is Loop 1 of 3. Produce a spec with requirements, design and a task
list, then implement it. Keep the task list to **≤ 8 small tasks**; if a task fails twice, simplify
the task in the spec rather than patching around it.

### What the product is
A knowledge graph of computing history 1880–1960 where **every fact is an IBM 80-column punched
card**, encoded with the IBM 029 keypunch code. A learned walker (Loop 2) answers multi-hop
questions by walking the cards; a web card-reader (Loop 3) replays the walk. **The deck file is the
only database.** Nothing in the app may hold facts anywhere else.

### Stack and conventions
- Python 3.12, `uv` project (`pyproject.toml`), package `hollerith` under `src/hollerith/`.
- Dependencies for this loop: `numpy`, `hypothesis`, `pytest`, `mcp` (Python MCP SDK). No torch.
- MIT `LICENSE`. `.gitignore` must **not** exclude `.kiro/`.
- Everything must run offline. No network calls anywhere in this loop.
- Code is plain, typed, and small. Prefer one module per concern.

### P0 — Kiro project scaffold (first task)
Create under `.kiro/`:
1. `steering/hollerith.md` — **the single source of truth** for the encoding standard:
   - the IBM 029 character set and its hole codes (rows 12, 11, 0, 1–9): digits = single punch in
     rows 0–9; A–I = 12 + 1–9; J–R = 11 + 1–9; S–Z = 0 + 2–9; space = no punch; `&` = 12; `-` = 11;
     `/` = 0‑1; and the 029 specials `. , $ * ( ) ' = + ; : ? ! " # @ % < > _ |` with their 8‑punch
     combinations. Lowercase input is upper-cased; any character outside the set is **rejected**.
   - the column layout: **1–20 subject · 21–35 relation · 36–55 object · 56–63 source code ·
     64–72 reserved (blank in the deck) · 73–80 sequence number**, zero-padded 8 digits, unique,
     ascending.
   - the **source reference list**: ≤ 10 fixed references (e.g. `IBMARCH` = IBM Archives
     timeline, `CHM` = Computer History Museum timeline, `WIKI-xx` = named Wikipedia articles),
     each with an ≤ 8-char code. Every card's cols 56–63 hold one of these codes; nothing else is
     allowed there.
   - the **relation vocabulary** (≤ 12 relations, each with its inverse name), e.g.
     `FOUNDED/FOUNDED_BY`, `BUILT/BUILT_BY`, `WORKED_AT/EMPLOYED`, `RENAMED_TO/RENAMED_FROM`,
     `INFLUENCED/INFLUENCED_BY`, `USED/USED_BY`. No two relations may mean the same thing.
   - an **abbreviation table** for entity names longer than 20 columns (e.g.
     `TABULATING MACHINE CO`), so every entity has exactly one canonical ≤ 20-char form.
2. `steering/science.md` — fixed seeds `[0, 1, 2]`; every number reported with mean ± std and the
   command that regenerates it; leakage gate must fail loudly; the claims the project must NOT make
   (beats LLMs/embeddings; generalises beyond this deck; comparable to published MINERVA numbers;
   narration is factually correct — it is only grounded).
3. `steering/product.md` — primary user: a curious learner of computing history who wants
   *"tell me how X led to Y, and prove it."* Every answer cites card sequence numbers. An entity
   not in the deck returns **`NO CARDS, NO ANSWER`**; a dead end is a **jammed card**. Never
   invent a fact that is not on a card.
4. `hooks/` — two agent hooks: (a) on save of `data/cards.deck` → run the card lint, the round-trip
   property test and (once it exists in Loop 2) the leakage gate; (b) on save of `src/**` or
   `tests/**` → run `pytest -q`.
5. `settings/mcp.json` — registers the project's own MCP server (below) as `hollerith-deck`.
6. `specs/01-card-encoder/` (this loop), plus empty skeletons `02-walker-eval/`, `03-reader-ui/`.

### Loop 1 — functional requirements
**R1 Encoder/decoder** (`src/hollerith/hollerith_code.py`)
- `encode(text: str) -> Card` produces a 12 × 80 boolean hole matrix from an ≤ 80-char string,
  right-padded with spaces; `decode(card) -> str` inverts it exactly.
- Round trip is exact for every string over the 029 set, including the empty string and 80-char
  strings. Strings > 80 chars and characters outside the set raise `CardEncodingError`.
- The code table is loaded from (or verified against) `steering/hollerith.md`, not duplicated.

**R2 Deck format** (`src/hollerith/deck.py`)
- `data/cards.deck` is a text file, one 80-character line per card, layout as above, cols 56–63
  a source code, cols 64–72 blank, cols 73–80 the sequence number.
- `Deck.load(path)`, `Deck.cards`, `Deck.triples()`, `Deck.neighbours(entity)`,
  `Deck.find(subject=None, relation=None, object=None)`. **Neighbour lookup is implemented as a
  sort/select pass over columns 1–20 and 36–55 of the card text** (a simulated IBM 082 sorter),
  not via a separate dict-of-facts built at import time — the deck is the database.
- `Deck.save(path)` writes cards back verbatim; `Deck.punch(subject, relation, object, source)`
  appends a card and its inverse card (same source) with the next two sequence numbers.

**R3 Card lint** (`src/hollerith/lint.py`, CLI `hollerith lint data/cards.deck`)
Fails (non-zero exit, one line per problem) on: line ≠ 80 chars; field overflow; character outside
the 029 set; cols 56–63 not a code from the source list; cols 64–72 not blank; sequence not
unique/ascending; **dangling entity** (appears
only as object and never as subject, or vice versa, after inverses); **missing inverse** (every
`(s, r, o)` must have `(o, r⁻¹, s)`); relation not in the vocabulary; **relation-synonym check**:
two relations whose (subject, object) pair sets have Jaccard overlap > 0.5 fail.

**R4 The deck itself** (`data/cards.deck`)
- **Target 100 facts = 200 cards (100 forward + 100 inverse lines) — range 75–150 facts.** Every
  card carries a source code from the steering list.
  Domain: computing history 1880–1960 (Hollerith, the 1890 census, Tabulating Machine Co, CTR,
  IBM, Watson Sr., Zuse, Turing, Aiken, Harvard Mark I, ENIAC, Eckert, Mauchly, von Neumann,
  EDVAC, UNIVAC, Remington Rand, Hopper, the IBM 701/650/029/082, Fortran, Backus, …).
- Draft the facts from your own knowledge, keep them to the relation vocabulary, and only include
  facts you are confident are true and can attribute to one of the listed sources. A file header
  comment is **not** allowed — the file is cards only.
- **Protocol (do not skip):** the deck is committed **before** any evaluation split exists. The
  commit message must be `deck: initial 100 facts / 200 cards`. Loop 2 depends on this ordering.

**R5 MCP server** (`src/hollerith/mcp_server.py`, stdio) — **two tools only**
`punch_card(subject, relation, object, source)` → appends card + inverse, returns both lines;
`query_deck(entity, relation=None)` → matching cards with sequence numbers. (Decode and lint are
CLI commands, not MCP tools.) **Kiro must use this server itself when authoring R4** — punch the
cards through `punch_card`, then run `hollerith lint` before committing. Keep the chat transcript
of those tool calls; it goes in the Kiro write-up.

**R5b CLI** (`hollerith decode <line>`) → text, fields, and the hole matrix as 12 rows of `.`/`O`.

**R6 Tests** (`tests/`)
- `test_roundtrip.py` with `hypothesis`: encode→decode identity on ≥ 10 000 generated strings over
  the 029 alphabet (lengths 0–80), plus explicit cases for empty, 80-char, 81-char (rejected), a
  lowercase string (upper-cased), and each rejected character class.
- `test_code_table.py`: every character's hole pattern matches the table in `hollerith.md`; no two
  characters share a pattern.
- `test_deck.py`: layout enforcement, inverse presence, neighbours via sorter pass, punch appends
  two cards with correct sequence.
- `test_lint.py`: one failing fixture per lint rule.

### Definition of done (Kiro checks these before reporting back)
- `uv run pytest -q` passes; `uv run hollerith lint data/cards.deck` exits 0.
- The save hook fires on `data/cards.deck` and runs the lint + round-trip test.
- `uv run python -m hollerith.mcp_server` starts and answers `query_deck("HOLLERITH")`.
- `.kiro/` is committed and not ignored; `LICENSE` is MIT.

## (end of paste)

---

## Claude Code validation plan for Loop 1 (not for Kiro)
1. Independent IBM 029 reference table under `docs/arena/checks/` compared character-by-character
   against `steering/hollerith.md` and the encoder's output.
2. Own hypothesis run at 20 000 cases with a different seed; adversarial strings: NUL, tabs,
   non-ASCII, 81 chars, mixed case.
3. `hollerith lint` on mutated decks: swapped columns, missing inverse, duplicate sequence,
   synonym relation pair.
4. Verify `Deck.neighbours` reads the card text (no hidden dict) by inspection.
5. `git log` shows `.kiro/specs/01-card-encoder/` committed before `src/`; deck commit present;
   every card's cols 56–63 is a listed source code.
6. Spot-check 30 random forward cards for factual accuracy (Diya + Claude Code); record the error
   rate for Limitations.
7. Reviewer subagent pass; findings → `loop-1-findings.md` (blocker / major / minor, each with the
   failing command).

**Exit:** 100 % round-trip on ≥ 10 k cases; all R3 rules enforced; all tests pass under the hook;
MCP server answers; deck committed before split.
