"""Card lint: every rule a deck must satisfy, reported one line per problem.

Works on raw lines so that a malformed file still gets a full report. `line_problems` is the
per-card contract and is also what `Deck.load` enforces, so a deck that loads is a deck that
lints clean at the card level.
"""
from __future__ import annotations

from collections import defaultdict
from itertools import combinations
from pathlib import Path

from .code_table import CODE, COLUMNS, INVERSE, LAYOUT, RELATIONS, SOURCES, slice_of

JACCARD_LIMIT = 0.5


def _field(line: str, name: str) -> str:
    return line[slice_of(name)].rstrip(" ")


def read_lines(path: str | Path) -> list[str]:
    """Read a deck file strictly: UTF-8, LF only, no trailing-newline ambiguity."""
    text = Path(path).read_bytes().decode("utf-8")
    if "\r" in text:
        raise ValueError("deck file contains carriage returns; cards must be LF-terminated")
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    return lines


def line_problems(line: str) -> list[str]:
    """Card-level rules for one 80-column line (no cross-card checks)."""
    problems: list[str] = []
    if len(line) != COLUMNS:
        return [f"{len(line)} characters, a card has {COLUMNS} columns"]
    bad = sorted({c for c in line if c not in CODE})
    if bad:
        problems.append(f"characters outside the IBM 029 set: {bad}")
    s, r, o = _field(line, "subject"), _field(line, "relation"), _field(line, "object")
    for name, value in (("subject", s), ("relation", r), ("object", o)):
        a, b = LAYOUT[name]
        if not value:
            problems.append(f"empty {name}")
        elif line[a - 1] == " ":
            problems.append(f"{name} starts with a blank column")
        if line[b - 1] != " ":
            problems.append(f"{name} fills every column of its field, check for truncation")
    if s and o and s == o:
        problems.append(f"card relates {s} to itself")
    if r and r not in INVERSE:
        problems.append(f"relation {r!r} is not in the vocabulary")
    src = _field(line, "source")
    if src not in SOURCES:
        problems.append(f"source code {src!r} is not one of {sorted(SOURCES)}")
    if line[slice_of("reserved")].strip():
        problems.append("columns 64-72 must be blank")
    seq = line[slice_of("sequence")]
    if not seq.isdigit():
        problems.append(f"sequence {seq!r} is not 8 digits")
    return problems


def lint_lines(lines: list[str], jaccard_limit: float = JACCARD_LIMIT) -> list[str]:
    problems: list[str] = []
    if not lines:
        return ["deck is empty"]

    triples: list[tuple[str, str, str]] = []
    seqs: list[int] = []
    good: list[tuple[int, str]] = []
    for n, line in enumerate(lines, start=1):
        ps = line_problems(line)
        problems.extend(f"line {n}: {p}" for p in ps)
        if len(line) != COLUMNS:
            continue
        s, r, o = _field(line, "subject"), _field(line, "relation"), _field(line, "object")
        seq = line[slice_of("sequence")]
        if seq.isdigit():
            seqs.append(int(seq))
        if s and r and o:
            triples.append((s, r, o))
        if not ps:
            good.append((n, line))

    if len(set(seqs)) != len(seqs):
        problems.append("sequence numbers are not unique")
    if seqs != sorted(seqs):
        problems.append("sequence numbers are not ascending")

    # Pairing: card 2k-1 is a forward fact, card 2k is its mirror with the next sequence number.
    if len(lines) % 2:
        problems.append("odd number of cards: every fact needs its inverse card")
    for i in range(0, len(lines) - 1, 2):
        a, b = lines[i], lines[i + 1]
        if len(a) != COLUMNS or len(b) != COLUMNS:
            continue
        ra = _field(a, "relation")
        if ra and ra not in RELATIONS:
            problems.append(f"line {i + 1}: forward card carries inverse relation {ra!r}")
            continue
        if ra in RELATIONS:
            expect = (_field(a, "object"), RELATIONS[ra], _field(a, "subject"), _field(a, "source"))
            got = (_field(b, "subject"), _field(b, "relation"), _field(b, "object"), _field(b, "source"))
            if expect != got:
                problems.append(f"line {i + 2}: not the mirror of line {i + 1}")
            sa, sb = a[slice_of("sequence")], b[slice_of("sequence")]
            if sa.isdigit() and sb.isdigit() and int(sb) != int(sa) + 1:
                problems.append(f"line {i + 2}: sequence should be {int(sa) + 1:08d}")

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
    try:
        lines = read_lines(path)
    except ValueError as e:
        return [str(e)]
    return lint_lines(lines)
