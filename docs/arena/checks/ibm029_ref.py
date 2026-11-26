"""Independent IBM 029 keypunch code table — Claude Code's validation reference.

This file is NOT application code. It exists so that Kiro's encoder in `src/hollerith/`
can be checked against a table written separately, from the published 029 (EBCDIC card
code) assignments. If the two disagree, one of them is wrong and the finding is logged.

Rows on an 80-column card, top to bottom: 12, 11, 0, 1, 2, ..., 9.
A character is a set of punched rows. Space is the empty set.
"""
from __future__ import annotations

ROWS: tuple[str, ...] = ("12", "11", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9")
ROW_INDEX: dict[str, int] = {r: i for i, r in enumerate(ROWS)}

CODE: dict[str, frozenset[str]] = {}

# Digits: single punch in the digit row.
for _d in "0123456789":
    CODE[_d] = frozenset({_d})

# Letters: zone punch + digit punch.
for _i, _ch in enumerate("ABCDEFGHI", start=1):
    CODE[_ch] = frozenset({"12", str(_i)})
for _i, _ch in enumerate("JKLMNOPQR", start=1):
    CODE[_ch] = frozenset({"11", str(_i)})
for _i, _ch in enumerate("STUVWXYZ", start=2):
    CODE[_ch] = frozenset({"0", str(_i)})

# Space and the three single-zone / zone-1 specials.
CODE[" "] = frozenset()
CODE["&"] = frozenset({"12"})
CODE["-"] = frozenset({"11"})
CODE["/"] = frozenset({"0", "1"})

# 029 specials: zone + 8 + digit, or 8 + digit.
_SPECIALS: dict[str, tuple[str, ...]] = {
    ".": ("12", "8", "3"),
    "<": ("12", "8", "4"),
    "(": ("12", "8", "5"),
    "+": ("12", "8", "6"),
    "|": ("12", "8", "7"),
    "$": ("11", "8", "3"),
    "*": ("11", "8", "4"),
    ")": ("11", "8", "5"),
    ";": ("11", "8", "6"),
    "¬": ("11", "8", "7"),  # ¬ logical NOT
    ",": ("0", "8", "3"),
    "%": ("0", "8", "4"),
    "_": ("0", "8", "5"),
    ">": ("0", "8", "6"),
    "?": ("0", "8", "7"),
    ":": ("8", "2"),
    "#": ("8", "3"),
    "@": ("8", "4"),
    "'": ("8", "5"),
    "=": ("8", "6"),
    '"': ("8", "7"),
}
for _ch, _rows in _SPECIALS.items():
    CODE[_ch] = frozenset(_rows)

ALPHABET: str = "".join(sorted(CODE))
ASCII_ALPHABET: str = "".join(c for c in ALPHABET if ord(c) < 128)

# Inverse table; also proves no two characters share a pattern.
PATTERN_TO_CHAR: dict[frozenset[str], str] = {}
for _ch, _p in CODE.items():
    assert _p not in PATTERN_TO_CHAR, f"duplicate pattern {_p} for {_ch!r} and {PATTERN_TO_CHAR[_p]!r}"
    PATTERN_TO_CHAR[_p] = _ch


def encode_char(ch: str) -> frozenset[str]:
    """Rows punched for one character; upper-cases letters; rejects anything else."""
    if len(ch) != 1:
        raise ValueError("encode_char takes exactly one character")
    up = ch.upper()
    if up not in CODE:
        raise ValueError(f"character {ch!r} is not in the IBM 029 set")
    return CODE[up]


def encode(text: str) -> list[list[bool]]:
    """12 x 80 hole matrix (True = hole) for a string of at most 80 029 characters."""
    if len(text) > 80:
        raise ValueError(f"text is {len(text)} characters; a card has 80 columns")
    padded = text.ljust(80)
    matrix = [[False] * 80 for _ in ROWS]
    for col, ch in enumerate(padded):
        for row in encode_char(ch):
            matrix[ROW_INDEX[row]][col] = True
    return matrix


def decode(matrix: list[list[bool]]) -> str:
    """Inverse of `encode`; trailing spaces are stripped (a card has no end-of-text mark)."""
    if len(matrix) != 12 or any(len(r) != 80 for r in matrix):
        raise ValueError("matrix must be 12 rows x 80 columns")
    chars = []
    for col in range(80):
        pattern = frozenset(ROWS[i] for i in range(12) if matrix[i][col])
        if pattern not in PATTERN_TO_CHAR:
            raise ValueError(f"column {col + 1}: hole pattern {sorted(pattern)} is not a 029 character")
        chars.append(PATTERN_TO_CHAR[pattern])
    return "".join(chars).rstrip(" ")


if __name__ == "__main__":
    print(f"{len(CODE)} characters ({len(ASCII_ALPHABET)} ASCII); all patterns unique")
    for ch in sorted(CODE, key=lambda c: (len(CODE[c]), sorted(CODE[c], key=ROW_INDEX.get))):
        print(f"  {ch!r:6} {'-'.join(sorted(CODE[ch], key=ROW_INDEX.get)) or '(none)'}")
