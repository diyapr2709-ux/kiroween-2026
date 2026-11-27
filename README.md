# Hollerith's Ghost

**An AI that shows its receipts.** Every fact it knows is an IBM 80-column punched card. Ask it a question about
the history of computing (1880–1964) and it answers by walking from card to card, then shows you the deck it
read — every sentence cites a card by its sequence number, and nothing is said that is not punched on a card on
the path. When no path exists, the card **jams** and it says so. When it has never heard of the thing you asked
about: **NO CARDS, NO ANSWER.**

Built for the [Kiroween 2026](https://kiro.devpost.com) hackathon, *Resurrection* category: a 1928 storage
medium brought back as the only database of a 2026 knowledge-graph walker.

## Quickstart (no API key, no network)

```bash
git clone https://github.com/diyapr2709-ux/kiroween-2026.git && cd kiroween-2026
uv sync                                   # Python 3.12, numpy only
uv run hollerith ask "Who founded the Tabulating Machine Company?"
uv run hollerith ask "Who founded the Tabulating Machine Company?" --pull 2    # pull the card it read; watch it reroute
uv run hollerith ask "Who founded Ferranti?"                                   # no such card: the reader jams
```

The first `ask` trains the walker on the deck (about 2 s) and saves it under `models/`. `uv run pytest -q` runs
the test suite (≈ 230 tests, 13 s). Hosted card reader: *URL added when Loop 3 lands.*

## What is in the deck

`data/cards.deck` is the entire database: **392 lines of exactly 80 characters**, one card each — 196 facts of
computing history and their inverse cards. Columns 1–20 subject · 21–35 relation · 36–55 object · 56–63 source code ·
73–80 sequence number, in the IBM 029 character set. Every hole pattern is derived from the text with the real 029
code (`hollerith decode "HOLLERITH"` shows the 12 × 80 hole matrix). Neighbour lookup is a simulated IBM 082 sorter
pass over columns 1–20. There is no other store of facts anywhere in the program.

```
HERMAN HOLLERITH    FOUNDED        TABULATING MACH CO  IBMARCH          00000001
TABULATING MACH CO  FOUNDED BY     HERMAN HOLLERITH    IBMARCH          00000002
```

## How it answers

1. **Parse** — a deterministic parser finds the entity named in your question and the relation its shape asks for
   (`"Who founded X?"` → `(X, FOUNDED BY, ?)`). Unknown entity → `NO CARDS`. Two entities → `AMBIGUOUS`.
2. **Direct card** — if a card `(X, FOUNDED BY, ·)` exists, that one card is the answer and the receipt.
3. **Walk** — otherwise a MINERVA-style walker (a learned policy over cards, no LSTM, numpy) walks up to 4 cards
   from X by beam search. The path is the answer's receipt.
4. **Jam** — if the walk's best path has low probability, or its relation chain never explained a `FOUNDED BY`
   question during training, the reader jams and shows the cards it read up to the dead end. No answer is invented.
5. **Narrate** — the listing is templated from the path cards only, so it cannot name an entity that is not on a card
   it cites. Faithfulness is 100 % by construction and checked on 662 traces.

**Pull a card.** `--pull SEQ` removes a card before walking. If you pull the card the answer was read from, the walker
either finds another route (and shows it) or jams. That is what makes the cards load-bearing rather than decorative.

## Results — honest version

Full protocol, every number and the command that regenerates it: [`docs/arena/results.md`](docs/arena/results.md).

**The pre-registered criterion was not met.** On a pre-registered set of 144 multi-hop-testable facts (288 queries;
reachability ceiling 40.3 % — the fraction of held-out answers any walker could reach at all), the supervised walker
reaches Hits@1 **0.073** against a frequency baseline of **0.035** (random walk 0.017). It is higher in every seed, but
the difference fails the pre-registered test under every reading (fact-clustered 95 % CI [−0.001, +0.080]; per-seed
McNemar p = 0.136 / 0.029 / 0.061 vs α = 0.025). The RL and supervised modes score the same (0.072 vs 0.073).

| system | Hits@1 | Hits@10 | MRR |
|---|---|---|---|
| reachability ceiling | 0.403 | — | — |
| walker (supervised) | 0.073 | 0.274 | 0.129 |
| walker (REINFORCE) | 0.072 | 0.263 | 0.120 |
| frequency baseline | 0.035 | 0.222 | 0.082 |
| exact random walk | 0.017 | 0.274 | 0.081 |

Product side, over the 392 card-derived questions with the gold card pulled: the walker recovers the answer 35 % of
the time, jams 15 %, says NO CARDS 17 % — and **34 % of the time gives an answer that is fully grounded in cards and
wrong**. That last number is why the receipts exist.

An LLM alone answers many of these questions from memory, so if we report one it will be a memorisation reference,
not a target: the walker's claim is that every answer cites the cards it came from, and it refuses when no card exists.

## Limitations

- **Small, hand-authored deck.** 196 facts written from general knowledge by the reviewer-AI that also wrote the code;
  30 random cards spot-checked (29 true, 1 doubtful and replaced). Source codes (`WIKI`, `IBMARCH`, `CHM`) name the
  reference family consulted, not page-level citations. 35 % of entities are leaves (cities, birthplaces), which is
  why most held-out facts have no alternative path at all.
- **Grounded is not correct.** A third of inferred answers are wrong while citing real cards. The system makes
  hallucination *visible*; it does not make it rare.
- **The effect is not statistically established.** See above; we do not say "significant", "trending", or "reasons".
- **No LLM-only baseline was run** (no API key was available), so nothing here compares the walker to an LLM.
- **Not comparable to published MINERVA numbers:** different graph, no LSTM history encoder, 4-hop limit, filtered
  ranking with mean-rank ties.
- **REINFORCE training takes ~46 s per fold** (target was 30 s); the full evaluation suite takes ~13 min on an M4.
- The parser understands a fixed set of question shapes (one per relation); anything else is `NO CARDS`.

## How this was built

Kiroween judges score how Kiro was used, so this section is kept exact; the authoritative ledger is
[`docs/arena/authorship.md`](docs/arena/authorship.md).

- **Kiro** — *in progress:* the `/.kiro` project (steering docs that mirror the card standard, agent hooks that lint the
  deck and run the tests on save, the MCP server that lets Kiro punch and query cards) and the web card reader. Kiro's
  commits carry Kiro's trailer; its tool-call transcript is in `docs/kiro/`.
- **Claude Code** (Anthropic) — the design arena and all review documents under `docs/arena/`, and, at the author's
  instruction, the Python core: encoder, deck, lint, CLI, evaluation protocol, walker, parser and narrator, with tests.
  Its commits carry a `Co-Authored-By: Claude` trailer.
- **Diya** — direction, arbitration, the Kiro sessions, and every commit.

License: MIT.
