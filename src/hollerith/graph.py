"""In-memory view of a set of cards for walking and evaluation.

A `Graph` is built from `Fact`s (usually a training subset of the deck). It is a *view* for
computation, never a second store of truth: it is rebuilt from cards every time and is never
saved. Every forward fact in the deck already has its inverse card, so edges here are exactly
the cards given.
"""
from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field

from .code_table import RELATIONS
from .deck import Deck, Fact

NO_OP = "NO_OP"


@dataclass
class Graph:
    facts: list[Fact]
    out: dict[str, list[Fact]] = field(default_factory=lambda: defaultdict(list), repr=False)
    entities: list[str] = field(default_factory=list)
    relations: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.out = defaultdict(list)
        ents: set[str] = set()
        rels: set[str] = set()
        for f in self.facts:
            self.out[f.subject].append(f)
            ents.update((f.subject, f.object))
            rels.add(f.relation)
        self.entities = sorted(ents)
        self.relations = sorted(rels)
        self.index = {e: i for i, e in enumerate(self.entities)}

    @classmethod
    def from_deck(cls, deck: Deck) -> "Graph":
        return cls(deck.facts())

    def __len__(self) -> int:
        return len(self.facts)

    def has(self, entity: str) -> bool:
        return entity in self.index

    def edges(self, entity: str) -> list[Fact]:
        return self.out.get(entity, [])

    def triples(self) -> set[tuple[str, str, str]]:
        return {f.triple() for f in self.facts}

    def reachable_within(self, start: str, hops: int) -> set[str]:
        """Entities reachable from `start` in <= hops steps following any card."""
        if start not in self.index:
            return set()
        seen = {start}
        frontier = deque([(start, 0)])
        while frontier:
            e, d = frontier.popleft()
            if d == hops:
                continue
            for f in self.out.get(e, ()):
                if f.object not in seen:
                    seen.add(f.object)
                    frontier.append((f.object, d + 1))
        return seen

    def shortest_path(self, start: str, goal: str, hops: int) -> list[Fact] | None:
        """BFS path of cards from start to goal within `hops`, or None."""
        if start not in self.index or goal not in self.index:
            return None
        if start == goal:
            return []
        prev: dict[str, Fact] = {}
        seen = {start}
        frontier = deque([(start, 0)])
        while frontier:
            e, d = frontier.popleft()
            if d == hops:
                continue
            for f in self.out.get(e, ()):
                if f.object in seen:
                    continue
                seen.add(f.object)
                prev[f.object] = f
                if f.object == goal:
                    path = []
                    cur = goal
                    while cur != start:
                        path.append(prev[cur])
                        cur = prev[cur].subject
                    return path[::-1]
                frontier.append((f.object, d + 1))
        return None


def forward_facts(deck: Deck) -> list[Fact]:
    """The deck's forward cards (one per fact), i.e. cards whose relation is a forward relation."""
    return [f for f in deck.facts() if f.relation in RELATIONS]


def with_inverses(facts: list[Fact], deck: Deck) -> list[Fact]:
    """Given forward facts, return them plus their inverse cards as they exist in the deck."""
    want = {f.triple() for f in facts}
    inv = {(f.object, RELATIONS[f.relation], f.subject) for f in facts}
    return [f for f in deck.facts() if f.triple() in want or f.triple() in inv]
