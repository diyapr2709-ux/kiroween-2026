"""Encode text to IBM 029 hole patterns and back.

A `Card` is exactly 80 characters of text over the 029 set; its holes are derived, never
stored. `encode` upper-cases letters and rejects anything outside the set or longer than
80 columns. `decode` is exact on the card (every column) and strips trailing blanks when
returning a string, because a card has no end-of-text mark.
"""
from __future__ import annotations

from dataclasses import dataclass

from .code_table import ALPHABET, CODE, COLUMNS, LAYOUT, PATTERN_TO_CHAR, ROWS, ROW_INDEX, slice_of


class CardEncodingError(ValueError):
    """Raised for text that cannot be punched, or holes that are not a 029 character."""


Holes = list[list[bool]]


@dataclass(frozen=True)
class Card:
    text: str  # exactly 80 characters, all in the 029 set

    def __post_init__(self) -> None:
        if len(self.text) != COLUMNS:
            raise CardEncodingError(f"a card has {COLUMNS} columns; got {len(self.text)} characters")
        bad = sorted({c for c in self.text if c not in CODE})
        if bad:
            raise CardEncodingError(f"characters not in the IBM 029 set: {bad}")

    @property
    def holes(self) -> Holes:
        """12 x 80 matrix, True where a hole is punched."""
        m = [[False] * COLUMNS for _ in ROWS]
        for col, ch in enumerate(self.text):
            for row in CODE[ch]:
                m[ROW_INDEX[row]][col] = True
        return m

    def rows(self, hole: str = "O", blank: str = ".") -> list[str]:
        """The card as 12 printable rows, top (12) to bottom (9)."""
        return ["".join(hole if h else blank for h in row) for row in self.holes]

    def field(self, name: str) -> str:
        """A layout field's text with trailing blanks removed."""
        return self.text[slice_of(name)].rstrip(" ")

    @classmethod
    def from_holes(cls, holes: Holes) -> "Card":
        return cls(holes_to_text(holes))


def normalise(text: str) -> str:
    """Upper-case letters; raise on anything the 029 cannot punch or that is too long."""
    if len(text) > COLUMNS:
        raise CardEncodingError(f"text is {len(text)} characters; a card has {COLUMNS} columns")
    up = text.upper()
    bad = sorted({c for c in up if c not in CODE})
    if bad:
        raise CardEncodingError(f"characters not in the IBM 029 set: {bad}")
    return up


def encode(text: str) -> Card:
    """Punch up to 80 characters onto a card, right-padded with blanks."""
    return Card(normalise(text).ljust(COLUMNS))


def holes_to_text(holes: Holes) -> str:
    """Exact 80-character text for a 12 x 80 hole matrix."""
    if len(holes) != len(ROWS) or any(len(r) != COLUMNS for r in holes):
        raise CardEncodingError(f"hole matrix must be {len(ROWS)} rows x {COLUMNS} columns")
    out = []
    for col in range(COLUMNS):
        pattern = frozenset(ROWS[i] for i in range(len(ROWS)) if holes[i][col])
        try:
            out.append(PATTERN_TO_CHAR[pattern])
        except KeyError:
            raise CardEncodingError(
                f"column {col + 1}: holes {sorted(pattern, key=ROW_INDEX.get)} are not a 029 character"
            ) from None
    return "".join(out)


def decode(card: Card | Holes) -> str:
    """Read a card (or a raw hole matrix) back to text, trailing blanks removed."""
    text = card.text if isinstance(card, Card) else holes_to_text(card)
    return text.rstrip(" ")


def punch_fields(subject: str, relation: str, object_: str, source: str, sequence: int) -> Card:
    """Lay out one fact on a card according to `LAYOUT`; raise if any field overflows."""
    parts = {"subject": subject, "relation": relation, "object": object_, "source": source}
    text = ""
    for name in ("subject", "relation", "object", "source", "reserved", "sequence"):
        a, b = LAYOUT[name]
        w = b - a + 1
        if name == "reserved":
            value = ""
        elif name == "sequence":
            if not 0 <= sequence <= 10**w - 1:
                raise CardEncodingError(f"sequence {sequence} does not fit in {w} digits")
            value = f"{sequence:0{w}d}"
        else:
            value = normalise(parts[name].strip())
            if not value:
                raise CardEncodingError(f"{name} must not be empty")
            if len(value) > w:
                raise CardEncodingError(f"{name} {value!r} is {len(value)} characters; field is {w} columns")
        text += value.ljust(w)
    return Card(text)


__all__ = ["ALPHABET", "Card", "CardEncodingError", "Holes", "decode", "encode", "holes_to_text", "normalise", "punch_fields"]
