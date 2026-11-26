"""The encoding standard: IBM 029 code table, card layout, relation vocabulary, sources.

Everything that defines what a valid card *is* lives here, so the encoder, the deck, the
lint and the UI cannot drift apart. `.kiro/steering/hollerith.md` documents the same table
in prose; `tests/test_code_table.py` checks the two agree.

Card rows, top to bottom: 12, 11, 0, 1, 2, ..., 9. A character is the set of rows punched.
"""
from __future__ import annotations

ROWS: tuple[str, ...] = ("12", "11", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9")
ROW_INDEX: dict[str, int] = {r: i for i, r in enumerate(ROWS)}
COLUMNS = 80


def _build_code() -> dict[str, frozenset[str]]:
    code: dict[str, frozenset[str]] = {}
    for d in "0123456789":
        code[d] = frozenset({d})
    for i, ch in enumerate("ABCDEFGHI", start=1):
        code[ch] = frozenset({"12", str(i)})
    for i, ch in enumerate("JKLMNOPQR", start=1):
        code[ch] = frozenset({"11", str(i)})
    for i, ch in enumerate("STUVWXYZ", start=2):
        code[ch] = frozenset({"0", str(i)})
    code[" "] = frozenset()
    code["&"] = frozenset({"12"})
    code["-"] = frozenset({"11"})
    code["/"] = frozenset({"0", "1"})
    specials = {
        ".": ("12", "8", "3"), "<": ("12", "8", "4"), "(": ("12", "8", "5"),
        "+": ("12", "8", "6"), "|": ("12", "8", "7"),
        "$": ("11", "8", "3"), "*": ("11", "8", "4"), ")": ("11", "8", "5"),
        ";": ("11", "8", "6"), "¬": ("11", "8", "7"),
        ",": ("0", "8", "3"), "%": ("0", "8", "4"), "_": ("0", "8", "5"),
        ">": ("0", "8", "6"), "?": ("0", "8", "7"),
        ":": ("8", "2"), "#": ("8", "3"), "@": ("8", "4"),
        "'": ("8", "5"), "=": ("8", "6"), '"': ("8", "7"),
    }
    for ch, rows in specials.items():
        code[ch] = frozenset(rows)
    return code


CODE: dict[str, frozenset[str]] = _build_code()
ALPHABET: str = "".join(sorted(CODE))
PATTERN_TO_CHAR: dict[frozenset[str], str] = {p: c for c, p in CODE.items()}
assert len(PATTERN_TO_CHAR) == len(CODE), "two characters share a hole pattern"

# Column layout, 1-based inclusive, as printed on the card form.
LAYOUT: dict[str, tuple[int, int]] = {
    "subject": (1, 20),
    "relation": (21, 35),
    "object": (36, 55),
    "source": (56, 63),
    "reserved": (64, 72),
    "sequence": (73, 80),
}


def width(field: str) -> int:
    a, b = LAYOUT[field]
    return b - a + 1


def slice_of(field: str) -> slice:
    a, b = LAYOUT[field]
    return slice(a - 1, b)


# Relation vocabulary: forward -> inverse. Twelve pairs, no synonyms.
RELATIONS: dict[str, str] = {
    "FOUNDED": "FOUNDED BY",
    "BUILT": "BUILT BY",
    "WORKED AT": "EMPLOYED",
    "RENAMED TO": "RENAMED FROM",
    "INFLUENCED": "INFLUENCED BY",
    "USED": "USED BY",
    "MERGED INTO": "FORMED FROM",
    "LED": "LED BY",
    "BORN IN": "BIRTHPLACE OF",
    "INVENTED": "INVENTED BY",
    "SUCCEEDED": "PRECEDED",
    "LOCATED IN": "LOCATION OF",
}
INVERSE: dict[str, str] = {**RELATIONS, **{v: k for k, v in RELATIONS.items()}}
assert all(len(r) <= width("relation") for r in INVERSE), "relation name wider than its field"

# Source codes allowed in columns 56-63. These name the reference family consulted when a
# card was authored; they are not page-level citations (see README > Limitations).
SOURCES: dict[str, str] = {
    "WIKI": "Wikipedia article(s) on the named entities",
    "IBMARCH": "IBM Archives, ibm.com/history",
    "CHM": "Computer History Museum timeline",
}
