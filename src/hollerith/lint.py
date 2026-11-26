"""Card lint: every rule a deck must satisfy, reported one line per problem.

Works on raw lines so that a malformed file still gets a full report.
"""
from __future__ import annotations

from collections import defaultdict
from itertools import combinations
from pathlib import Path

from .code_table import CODE, COLUMNS, INVERSE, LAYOUT, SOURCES, slice_of

JACCARD_LIMIT = 0.5


def _field(line: str, name: str) -> str:
    return line[slice_of(name)].rstrip(" ")


def lint_lines(lines: list[str], jaccard_limit: float = JACCARD_LIMIT) -> list[str]:
    problems: list[str] = []
    if not lines:
        return ["deck is empty"]

    triples: list[tuple[str, str, str]] = []
    seqs: list[int] = []
    for n, line in enumerate(lines, start=1):
        if len(line) != COLUMNS:
            problems.append(f"line {n}: {len(line)} characters, a card has {COLUMNS} columns")
            continue
        bad = sorted({c for c in line if c not in CODE})
        if bad:
            problems.append(f"line {n}: characters outside the IBM 029 set: {bad}")
        s, r, o = _field(line, "subject"), _field(line, "relation"), _field(line, "object")
        for name, value in (("subject", s), ("relation", r), ("object", o)):
            if not value:
                problems.append(f"line {n}: empty {name}")
            a, b = LAYOUT[name]
            if line[b - 1] != " ":
                problems.append(f"line {n}: {name} fills every column of its field, check for truncation")
        if r and r not in INVERSE:
            problems.append(f"line {n}: relation {r!r} is not in the vocabulary")
        src = _field(line, "source")
        if src not in SOURCES:
            problems.append(f"line {n}: source code {src!r} is not one of {sorted(SOURCES)}")
        if line[slice_of("reserved")].strip():
            problems.append(f"line {n}: columns 64-72 must be blank")
        seq = line[slice_of("sequence")]
        if not seq.isdigit():
            problems.append(f"line {n}: sequence {seq!r} is not 8 digits")
        else:
            seqs.append(int(seq))
        if s and r and o:
            triples.append((s, r, o))

    if len(set(seqs)) != len(seqs):
        problems.append("sequence numbers are not unique")
    if seqs != sorted(seqs):
        problems.append("sequence numbers are not ascending")

    tset = set(triples)
    if len(tset) != len(triples):
        problems.append(f"{len(triples) - len(tset)} duplicate fact(s)")
    for s, r, o in sorted(tset):
        if r in INVERSE and (o, INVERSE[r], s) not in tset:
            problems.append(f"missing inverse card for ({s}, {r}, {o})")

    subjects = {s for s, _, _ in triples}
    objects = {o for _, _, o in triples}
    for e in sorted(objects - subjects):
        problems.append(f"dangling entity, never a subject: {e}")
    for e in sorted(subjects - objects):
        problems.append(f"dangling entity, never an object: {e}")

    pairs: dict[str, set[tuple[str, str]]] = defaultdict(set)
    for s, r, o in triples:
        pairs[r].add((s, o))
    for r1, r2 in combinations(sorted(pairs), 2):
        a, b = pairs[r1], pairs[r2]
        j = len(a & b) / len(a | b) if (a | b) else 0.0
        if j > jaccard_limit:
            problems.append(f"relations {r1} and {r2} look like synonyms (Jaccard {j:.2f})")

    return problems


def lint_file(path: str | Path) -> list[str]:
    lines = Path(path).read_text(encoding="utf-8").split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    return lint_lines(lines)
