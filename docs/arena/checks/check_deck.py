"""Loop 1 validation: independent lint of `data/cards.deck` — reads the file, imports nothing of Kiro's.

Checks (ADR-001 §3 / spec-input-1 R3):
  - every line is exactly 80 characters, all in the IBM 029 set
  - layout: 1-20 subject, 21-35 relation, 36-55 object, 56-63 source code, 64-72 blank, 73-80 seq
  - sequence numbers are 8 digits, unique, strictly ascending
  - every (s, r, o) has an inverse (o, r', s) and r -> r' is a consistent bijection
  - no dangling entity (after inverses, every entity appears as a subject)
  - source codes come from an allowed list (--sources A,B,...) when given
  - relation-synonym check: Jaccard overlap of (s,o)-pair sets > 0.5 between two relations fails

Usage:  python -I docs/arena/checks/check_deck.py data/cards.deck [--sources IBMARCH,CHM,...]
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ibm029_ref as ref  # noqa: E402

FIELDS = {"subject": (0, 20), "relation": (20, 35), "object": (35, 55),
          "source": (55, 63), "reserved": (63, 72), "seq": (72, 80)}


def field(line: str, name: str) -> str:
    a, b = FIELDS[name]
    return line[a:b].rstrip(" ")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("deck")
    ap.add_argument("--sources", default="", help="comma-separated allowed source codes")
    ap.add_argument("--jaccard", type=float, default=0.5)
    args = ap.parse_args()
    allowed_sources = {s for s in args.sources.split(",") if s}

    problems: list[str] = []
    lines = Path(args.deck).read_text(encoding="utf-8").split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    if not lines:
        print("FAIL: deck is empty")
        return 1

    triples: list[tuple[str, str, str]] = []
    seqs: list[int] = []
    for n, line in enumerate(lines, start=1):
        if len(line) != 80:
            problems.append(f"line {n}: length {len(line)} != 80")
            continue
        bad = sorted({c for c in line if c not in ref.CODE})
        if bad:
            problems.append(f"line {n}: characters outside the 029 set: {bad}")
        s, r, o = field(line, "subject"), field(line, "relation"), field(line, "object")
        if not (s and r and o):
            problems.append(f"line {n}: empty subject/relation/object")
        if line[63:72].strip():
            problems.append(f"line {n}: columns 64-72 must be blank")
        src = field(line, "source")
        if allowed_sources and src not in allowed_sources:
            problems.append(f"line {n}: source code {src!r} not in allowed list")
        if not src:
            problems.append(f"line {n}: empty source code (cols 56-63)")
        seq = line[72:80]
        if not seq.isdigit():
            problems.append(f"line {n}: seq {seq!r} is not 8 digits")
        else:
            seqs.append(int(seq))
        # Field overflow heuristic: a field whose last column is non-blank while the
        # following field starts without a boundary is undetectable in fixed layout, so we
        # flag fields that are full to the last column as "check for truncation".
        for name in ("subject", "relation", "object"):
            a, b = FIELDS[name]
            if line[b - 1] != " ":
                problems.append(f"line {n}: {name} fills all {b - a} columns — check for truncation")
        triples.append((s, r, o))

    if seqs != sorted(seqs) or len(set(seqs)) != len(seqs):
        problems.append("sequence numbers are not unique and strictly ascending")

    # Inverses, inferred without the app's vocabulary: r' is the inverse of r only if EVERY
    # (s, r, o) has (o, r', s). Two entities may share several relations (X FOUNDED and LED Y),
    # so co-occurrence alone is not enough.
    tset = set(triples)
    by_rel: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for s, r, o in triples:
        by_rel[r].append((s, o))
    back: dict[tuple[str, str], set[str]] = defaultdict(set)
    for s, r, o in triples:
        back[(o, s)].add(r)
    rel_to_inv: dict[str, str] = {}
    for r, pairs in by_rel.items():
        candidates = None
        for s, o in pairs:
            cs = back.get((s, o), set())
            candidates = set(cs) if candidates is None else candidates & cs
        candidates = candidates or set()
        if not candidates:
            missing = [(s, o) for s, o in pairs if not back.get((s, o))]
            for s, o in missing[:5]:
                problems.append(f"missing inverse for ({s}, {r}, {o})")
            if not missing:
                problems.append(f"relation {r} has no single inverse covering all its cards")
        elif len(candidates) > 1:
            problems.append(f"relation {r} has several full-coverage inverses (synonyms?): {sorted(candidates)}")
        else:
            rel_to_inv[r] = next(iter(candidates))
    for r, r2 in rel_to_inv.items():
        if rel_to_inv.get(r2) != r:
            problems.append(f"inverse mapping not symmetric: {r} -> {r2} but {r2} -> {rel_to_inv.get(r2)}")

    # Dangling entities.
    subjects = {s for s, _, _ in triples}
    objects = {o for _, _, o in triples}
    for e in sorted(objects - subjects):
        problems.append(f"dangling entity (never a subject): {e}")
    for e in sorted(subjects - objects):
        problems.append(f"dangling entity (never an object): {e}")

    # Relation-synonym Jaccard.
    pairs_by_rel: dict[str, set[tuple[str, str]]] = defaultdict(set)
    for s, r, o in triples:
        pairs_by_rel[r].add((s, o))
    for r1, r2 in combinations(sorted(pairs_by_rel), 2):
        a, b = pairs_by_rel[r1], pairs_by_rel[r2]
        j = len(a & b) / len(a | b) if (a | b) else 0.0
        if j > args.jaccard:
            problems.append(f"relations {r1} and {r2} overlap (Jaccard {j:.2f} > {args.jaccard})")

    rels = Counter(r for _, r, _ in triples)
    print(f"cards: {len(lines)}  facts (incl. inverses): {len(triples)}  entities: {len(subjects | objects)}  relations: {len(rels)}")
    for r, c in rels.most_common():
        print(f"  {r:16} {c}")
    uniq = sorted(set(problems))
    print(f"problems: {len(uniq)}")
    for p in uniq[:60]:
        print("  FAIL", p)
    return 1 if uniq else 0


if __name__ == "__main__":
    raise SystemExit(main())
