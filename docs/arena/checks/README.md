# Claude Code validation harness

**Authorship:** written by Claude Code (the project's independent reviewer). This is *not*
application code — nothing here is imported by `src/`, and the app runs without this directory.
Each script re-derives a standard independently of Kiro's implementation so that the two can
disagree. The repo's own tests under `tests/` are Kiro's.

| Script | Loop | Checks | Command |
|---|---|---|---|
| `ibm029_ref.py` | 1 | independent IBM 029 code table, 61 chars (60 ASCII + ¬), unique patterns | `python -I docs/arena/checks/ibm029_ref.py` |
| `check_roundtrip.py` | 1 | encode→decode on N generated strings; Kiro's hole patterns vs reference; invalid input rejected | `uv run --with hypothesis python -I docs/arena/checks/check_roundtrip.py --cases 20000 --seed 7` |
| `check_deck.py` | 1 | 80 cols, layout, 029 charset, seq, inverses, dangling entities, source codes, relation Jaccard | `python -I docs/arena/checks/check_deck.py data/cards.deck --sources IBMARCH,CHM` |
| `check_leakage.py` | 2 | no test fact / inverse / same-pair edge in train; counts unanswerable queries; exit 2 on leak | `python -I docs/arena/checks/check_leakage.py --folds splits/` |
| `stats.py` | 2 | paired bootstrap CI, McNemar exact, sign over seeds → PASS/FAIL of the §4 exit criterion | `python -I docs/arena/checks/stats.py results/hits1.csv --system policy_rl --baselines random_walk,frequency --alpha 0.025` |
| `check_faithfulness.py` | 3 | narrator names only on-path entities, cites only on-path cards, ≥50 answered, rate ≥ 0.95 | `python -I docs/arena/checks/check_faithfulness.py traces/*.json --deck data/cards.deck` |

Input formats these scripts expect (and that Kiro's spec must therefore produce):
- `data/cards.deck` — 80-char lines, layout 1–20 / 21–35 / 36–55 / 56–63 source / 64–72 blank / 73–80 seq.
- `splits/fold{k}.train.jsonl`, `splits/fold{k}.test.jsonl` — one `{"s","r","o"}` per line.
- `results/hits1.csv` — `seed,query,<system>,<system>,...` with 0/1 cells.
- `traces/*.json` — see docstring of `check_faithfulness.py`.

Self-test (no Kiro code needed): `bash docs/arena/checks/selftest.sh`
