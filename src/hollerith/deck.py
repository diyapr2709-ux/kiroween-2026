"""The deck is the database.

`data/cards.deck` holds one 80-column card per line and nothing else. Every query is a
pass over the card text — there is no separate index of facts built at import time.
`neighbours` is a simulated IBM 082 sorter pass: sort the deck on one field, then select
the run of cards whose field matches.
"""
from __future__ import annotations

import bisect
from dataclasses import dataclass
from pathlib import Path

from .code_table import INVERSE, RELATIONS, SOURCES, slice_of, width
from .hollerith_code import Card, CardEncodingError, punch_fields
from .lint import line_problems, read_lines


class DeckError(ValueError):
    """A deck file or operation that violates the card standard."""


@dataclass(frozen=True)
class Fact:
    subject: str
    relation: str
    object: str
    source: str
    sequence: int

    @classmethod
    def from_card(cls, card: Card) -> "Fact":
        seq = card.text[slice_of("sequence")]
        if not seq.isdigit():
            raise DeckError(f"sequence {seq!r} is not 8 digits")
        return cls(
            subject=card.field("subject"),
            relation=card.field("relation"),
            object=card.field("object"),
            source=card.field("source"),
            sequence=int(seq),
        )

    def triple(self) -> tuple[str, str, str]:
        return (self.subject, self.relation, self.object)


class Deck:
    def __init__(self, cards: list[Card] | None = None) -> None:
        self._cards: list[Card] = list(cards or [])

    # ---- persistence -------------------------------------------------------------
    @classmethod
    def load(cls, path: str | Path) -> "Deck":
        """Load a deck, enforcing the card-level layout rules on every line."""
        try:
            lines = read_lines(path)
        except ValueError as e:
            raise DeckError(f"{path}: {e}") from None
        cards = []
        for n, line in enumerate(lines, start=1):
            problems = line_problems(line)
            if problems:
                raise DeckError(f"{path}:{n}: " + "; ".join(problems))
            cards.append(Card(line))
        return cls(cards)

    def save(self, path: str | Path) -> None:
        Path(path).write_bytes("".join(c.text + "\n" for c in self._cards).encode("utf-8"))

    # ---- reading -----------------------------------------------------------------
    @property
    def cards(self) -> list[Card]:
        return list(self._cards)

    def __len__(self) -> int:
        return len(self._cards)

    def facts(self) -> list[Fact]:
        return [Fact.from_card(c) for c in self._cards]

    def triples(self) -> list[tuple[str, str, str]]:
        return [f.triple() for f in self.facts()]

    def entities(self) -> set[str]:
        ents = set()
        for c in self._cards:
            ents.add(c.field("subject"))
            ents.add(c.field("object"))
        ents.discard("")
        return ents

    def relations(self) -> set[str]:
        return {c.field("relation") for c in self._cards}

    def _sorter_pass(self, field: str, key: str) -> list[Card]:
        """Simulated IBM 082 sorter: order the deck on one field, pull the matching run."""
        sl = slice_of(field)
        padded = key.strip().upper().ljust(width(field))
        ordered = sorted(self._cards, key=lambda c: c.text[sl])
        keys = [c.text[sl] for c in ordered]
        lo = bisect.bisect_left(keys, padded)
        hi = bisect.bisect_right(keys, padded)
        return ordered[lo:hi]

    def neighbours(self, entity: str) -> list[Fact]:
        """Every card with `entity` in columns 1-20, in sequence order.

        Because every fact has its inverse card, this is the entity's full out-edge set.
        """
        run = self._sorter_pass("subject", entity)
        return sorted((Fact.from_card(c) for c in run), key=lambda f: f.sequence)

    def find(self, subject: str | None = None, relation: str | None = None, object: str | None = None) -> list[Fact]:
        want = {k: v.strip().upper() for k, v in (("subject", subject), ("relation", relation), ("object", object)) if v is not None}
        out = []
        for c in self._cards:
            if all(c.field(k) == v for k, v in want.items()):
                out.append(Fact.from_card(c))
        return out

    def has_entity(self, entity: str) -> bool:
        return bool(self._sorter_pass("subject", entity)) or bool(self._sorter_pass("object", entity))

    # ---- writing -----------------------------------------------------------------
    def next_sequence(self) -> int:
        if not self._cards:
            return 1
        return max(int(c.text[slice_of("sequence")]) for c in self._cards) + 1

    def punch(self, subject: str, relation: str, object: str, source: str) -> tuple[Card, Card]:
        """Append a forward fact and its inverse as two cards with consecutive sequence numbers."""
        s, o = subject.strip().upper(), object.strip().upper()
        rel, src = relation.strip().upper(), source.strip().upper()
        if not s or not o:
            raise DeckError("subject and object must not be empty")
        if rel in RELATIONS:
            pass
        elif rel in INVERSE:
            raise DeckError(
                f"{rel!r} is an inverse relation; punch the forward fact instead: ({o}, {INVERSE[rel]}, {s})"
            )
        else:
            raise DeckError(f"relation {relation!r} is not in the vocabulary: {sorted(RELATIONS)}")
        if src not in SOURCES:
            raise DeckError(f"source {source!r} is not an allowed code: {sorted(SOURCES)}")
        if s == o:
            raise DeckError("a fact cannot relate an entity to itself")
        if self.find(s, rel, o):
            raise DeckError(f"duplicate fact ({s}, {rel}, {o})")
        seq = self.next_sequence()
        try:
            fwd = punch_fields(s, rel, o, src, seq)
            inv = punch_fields(o, RELATIONS[rel], s, src, seq + 1)
        except CardEncodingError as e:
            raise DeckError(str(e)) from None
        self._cards.extend([fwd, inv])
        return fwd, inv
