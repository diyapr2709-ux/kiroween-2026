"""`hollerith` command line: lint, decode, punch, show, neighbours.

Exit codes: 0 ok · 1 the deck/query has a problem (lint failures, NO CARDS, bad input)
· 2 the deck could not be read at all. Hooks rely on these.
"""
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
        card = encode(args.line)
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


def cmd_split(args: argparse.Namespace) -> int:
    from .split import make_folds, write_folds
    deck = Deck.load(args.deck)
    folds = make_folds(deck, k=args.folds, seed=args.split_seed, hops=args.hops, universe=args.universe)
    meta = write_folds(folds, args.out, deck, args.split_seed, args.hops, args.universe)
    print(f"universe={meta['universe']} ({meta['facts_testable']}/{meta['facts_total']} facts) "
          f"folds={meta['k']} queries={meta['total_queries']} reachable={meta['reachable_rate']:.3f} "
          f"answerable={meta['answerable_rate']:.3f} excluded_facts={meta['excluded_total']} -> {args.out}/")
    return 0


def cmd_eval(args: argparse.Namespace) -> int:
    from .baselines import BASELINES
    from .evaluate import format_table, run
    from .policy import Policy
    systems = {}
    for name in args.systems.split(","):
        if name in BASELINES:
            systems[name] = BASELINES[name](args.hops) if name == "random_walk" else BASELINES[name]()
        elif name in ("policy_rl", "policy_sl", "policy_rl_simple", "policy_sl_simple"):
            systems[name] = Policy(mode=name.split("_")[1], hops=args.hops, epochs=args.epochs, verbose=args.verbose,
                                   simple_paths=name.endswith("_simple"))
        else:
            print(f"error: unknown system {name!r}; known: {sorted(BASELINES) + ['policy_rl', 'policy_sl']}", file=sys.stderr)
            return 1
    seeds = [int(s) for s in args.seeds.split(",")]
    summary = run(args.deck, systems, args.out, seeds, args.folds, args.split_seed, args.hops, args.universe)
    print(format_table(summary))
    print(f"-> {args.out}/hits1.csv, {args.out}/summary.json")
    return 0


def cmd_train(args: argparse.Namespace) -> int:
    from .trace import save_model, train_full
    deck = Deck.load(args.deck)
    p = train_full(deck, mode=args.mode, seed=args.seed, epochs=args.epochs, hops=args.hops)
    save_model(p, args.out)
    print(f"trained policy_{args.mode} on {len(deck)} cards ({args.epochs} epochs, seed {args.seed}) -> {args.out}")
    return 0


def cmd_ask(args: argparse.Namespace) -> int:
    from .trace import ask, load_model
    deck = Deck.load(args.deck)
    policy = load_model(args.model, deck) if Path(args.model).exists() else None
    pulled = [int(x) for x in args.pull.split(",") if x] if args.pull else []
    t = ask(args.question, deck, policy, pulled=pulled)
    if args.json:
        print(t.to_json())
    else:
        print(f"Q: {t.question}")
        print(f"   parsed: {t.entity} / {t.relation}   status: {t.status}" + (f"   confidence: {t.confidence:.2f}" if t.confidence is not None else ""))
        for c in t.path:
            print(f"   {c['line']}")
        print(t.narration)
    return 0 if t.status == "answered" else 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="hollerith", description="Hollerith's Ghost card tools")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("lint", help="check a deck against the card standard")
    p.add_argument("deck", nargs="?", default=DEFAULT_DECK)
    p.set_defaults(fn=cmd_lint)

    p = sub.add_parser("decode", help="show the holes for up to 80 characters of text")
    p.add_argument("line")
    p.set_defaults(fn=cmd_decode)

    p = sub.add_parser("punch", help="append a forward fact and its inverse to the deck")
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

    p = sub.add_parser("split", help="write k-fold evaluation splits with the leakage gate")
    p.add_argument("--deck", default=DEFAULT_DECK)
    p.add_argument("--out", default="splits")
    p.add_argument("--folds", type=int, default=5)
    p.add_argument("--split-seed", type=int, default=0)
    p.add_argument("--hops", type=int, default=4)
    p.add_argument("--universe", choices=["testable", "all"], default="testable",
                   help="testable = pre-registered facts whose endpoints both have >=2 neighbours (default); all = every fact")
    p.set_defaults(fn=cmd_split)

    p = sub.add_parser("eval", help="evaluate systems with filtered Hits@k / MRR over the folds")
    p.add_argument("--systems", default="random_walk,frequency")
    p.add_argument("--seeds", default="0,1,2")
    p.add_argument("--deck", default=DEFAULT_DECK)
    p.add_argument("--out", default="results")
    p.add_argument("--folds", type=int, default=5)
    p.add_argument("--split-seed", type=int, default=0)
    p.add_argument("--hops", type=int, default=4)
    p.add_argument("--universe", choices=["testable", "all"], default="testable")
    p.add_argument("--epochs", type=int, default=40)
    p.add_argument("--verbose", action="store_true")
    p.set_defaults(fn=cmd_eval)

    p = sub.add_parser("train", help="train the product walker on the full deck and save it")
    p.add_argument("--mode", choices=["rl", "sl"], default="sl")
    p.add_argument("--deck", default=DEFAULT_DECK)
    p.add_argument("--out", default="models/walker.npz")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--epochs", type=int, default=40)
    p.add_argument("--hops", type=int, default=4)
    p.set_defaults(fn=cmd_train)

    p = sub.add_parser("ask", help="answer a question from the cards; emits a trace")
    p.add_argument("question")
    p.add_argument("--deck", default=DEFAULT_DECK)
    p.add_argument("--model", default="models/walker.npz")
    p.add_argument("--pull", default="", help="comma-separated card sequence numbers to pull before walking")
    p.add_argument("--json", action="store_true")
    p.set_defaults(fn=cmd_ask)

    args = ap.parse_args(argv)
    try:
        return args.fn(args)
    except (DeckError, OSError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
