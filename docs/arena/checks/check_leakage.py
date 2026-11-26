"""Loop 2 gate: assert that no test fact, its inverse, or ANY edge between the same two
entities is present in the training graph. Fails loudly (exit 2) on the first violation.

Expected inputs (one fact per line, JSON: {"s": ..., "r": ..., "o": ...}) — the format
Kiro's split writer must produce; if Kiro chooses another format the spec is revised, not this gate.

Usage:  python -I docs/arena/checks/check_leakage.py --train splits/fold0.train.jsonl --test splits/fold0.test.jsonl
        (repeat per fold, or pass --folds splits/ to check every fold*.train/test pair)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def load(path: Path) -> list[tuple[str, str, str]]:
    out = []
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        d = json.loads(line)
        out.append((d["s"], d["r"], d["o"]))
    return out


def check(train: Path, test: Path) -> list[str]:
    tr = load(train)
    te = load(test)
    train_set = set(tr)
    train_pairs = {(s, o) for s, _, o in tr} | {(o, s) for s, _, o in tr}
    train_entities = {s for s, _, _ in tr} | {o for _, _, o in tr}
    problems = []
    for s, r, o in te:
        if (s, r, o) in train_set:
            problems.append(f"test fact present in train: ({s}, {r}, {o})")
        if (s, o) in train_pairs:
            problems.append(f"edge between test pair {{{s}, {o}}} present in train (inverse/synonym leak)")
        if s not in train_entities:
            problems.append(f"NOTE test subject not in train (query is unanswerable, must be counted): {s}")
    overlap = set(tr) & set(te)
    if overlap:
        problems.append(f"{len(overlap)} facts appear in both files")
    return problems


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--train")
    ap.add_argument("--test")
    ap.add_argument("--folds", help="directory containing fold*.train.jsonl / fold*.test.jsonl")
    args = ap.parse_args()

    pairs: list[tuple[Path, Path]] = []
    if args.folds:
        d = Path(args.folds)
        for tr in sorted(d.glob("fold*.train.jsonl")):
            val = d / tr.name.replace(".train.", ".val.")
            if val.exists():  # the walking graph is train ∪ val, so val must be gated too
                merged = d / tr.name.replace(".train.", ".walk.")
                merged.write_text(tr.read_text() + val.read_text())
                tr = merged
            pairs.append((tr, d / tr.name.replace(".walk.", ".test.").replace(".train.", ".test.")))
    elif args.train and args.test:
        pairs.append((Path(args.train), Path(args.test)))
    else:
        ap.error("give --train and --test, or --folds DIR")

    hard = 0
    for tr, te in pairs:
        probs = check(tr, te)
        fails = [p for p in probs if not p.startswith("NOTE")]
        notes = [p for p in probs if p.startswith("NOTE")]
        print(f"{tr.name} / {te.name}: {len(fails)} leaks, {len(notes)} unanswerable test queries")
        for p in fails[:20]:
            print("  LEAK", p)
        hard += len(fails)
    if hard:
        print(f"LEAKAGE GATE FAILED: {hard} violations")
        return 2
    print("leakage gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
