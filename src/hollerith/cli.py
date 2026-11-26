"""`hollerith` command line: lint, decode, punch, show, neighbours."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .code_table import LAYOUT
from .deck import Deck, DeckError
from .hollerith_code import Card, CardEncodingError, encode
from .lint import lint_file

DEFAULT_DECK = Path("data/cards.deck")


def _print_card(card: Card) -> None:
    print(card.text)
    print("-" * 80)
    for label, row in zip(("12", "11", " 0", " 1", " 2", " 3", " 4", " 5", " 6", " 7", " 8", " 9"), card.rows()):
        print(f"{label} {row}")
    print("-" * 80)
    for name in ("subject", "relation", "object", "source", "sequence"):
        a, b = LAYOUT[name]
        print(f"{name:9} cols {a:2}-{b:2}: {card.field(name)!r}")


def cmd_lint(args: argparse.Namespace) -> int:
    problems = lint_file(args.deck)
    for p in problems:
        print(p)
    print(f"{len(problems)} problem(s)" if problems else "deck is clean")
    return 1 if problems else 0


def cmd_decode(args: argparse.Namespace) -> int:
    try:
        card = Card(args.line) if len(args.line) == 80 else encode(args.line)
    except CardEncodingError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    _print_card(card)
    return 0


def cmd_punch(args: argparse.Namespace) -> int:
    deck = Deck.load(args.deck) if Path(args.deck).exists() else Deck()
    try:
        fwd, inv = deck.punch(args.subject, args.relation, args.object, args.source)
    except DeckError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    deck.save(args.deck)
    print(fwd.text)
    print(inv.text)
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    deck = Deck.load(args.deck)
    for card in deck.cards:
        if int(card.text[72:80]) == args.sequence:
            _print_card(card)
            return 0
    print(f"error: no card {args.sequence:08d}", file=sys.stderr)
    return 1


def cmd_neighbours(args: argparse.Namespace) -> int:
    deck = Deck.load(args.deck)
    facts = deck.neighbours(args.entity)
    if not facts:
        print("NO CARDS")
        return 1
    for f in facts:
        print(f"[{f.sequence:08d}] {f.subject} --{f.relation}--> {f.object}  ({f.source})")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="hollerith", description="Hollerith's Ghost card tools")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("lint", help="check a deck against the card standard")
    p.add_argument("deck", nargs="?", default=DEFAULT_DECK)
    p.set_defaults(fn=cmd_lint)

    p = sub.add_parser("decode", help="show the holes for an 80-column line or any short text")
    p.add_argument("line")
    p.set_defaults(fn=cmd_decode)

    p = sub.add_parser("punch", help="append a fact and its inverse to the deck")
    p.add_argument("subject")
    p.add_argument("relation")
    p.add_argument("object")
    p.add_argument("source")
    p.add_argument("--deck", default=DEFAULT_DECK)
    p.set_defaults(fn=cmd_punch)

    p = sub.add_parser("show", help="print one card by sequence number")
    p.add_argument("sequence", type=int)
    p.add_argument("--deck", default=DEFAULT_DECK)
    p.set_defaults(fn=cmd_show)

    p = sub.add_parser("neighbours", help="sorter pass: every card with the entity in columns 1-20")
    p.add_argument("entity")
    p.add_argument("--deck", default=DEFAULT_DECK)
    p.set_defaults(fn=cmd_neighbours)

    args = ap.parse_args(argv)
    try:
        return args.fn(args)
    except DeckError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
