"""One failing fixture per lint rule, boundary cases, and the shipped deck must be clean."""
from pathlib import Path

import pytest

from hollerith import lint_file, lint_lines
from hollerith.hollerith_code import punch_fields

REPO = Path(__file__).resolve().parents[1]


def card(s: str, r: str, o: str, src: str = "WIKI", seq: int = 1) -> str:
    return punch_fields(s, r, o, src, seq).text


GOOD = [
    card("HOLLERITH", "FOUNDED", "TABULATING MACH CO", "WIKI", 1),
    card("TABULATING MACH CO", "FOUNDED BY", "HOLLERITH", "WIKI", 2),
    card("TABULATING MACH CO", "MERGED INTO", "CTR", "IBMARCH", 3),
    card("CTR", "FORMED FROM", "TABULATING MACH CO", "IBMARCH", 4),
]


def has(problems: list[str], *needles: str) -> bool:
    return any(all(n in p for n in needles) for p in problems)


def test_good_deck_is_clean() -> None:
    assert lint_lines(GOOD) == []


def test_empty_deck() -> None:
    assert lint_lines([]) == ["deck is empty"]


def test_short_line() -> None:
    assert has(lint_lines(GOOD + [GOOD[0][:79]]), "80 columns")


def test_bad_character() -> None:
    assert has(lint_lines(["h" + GOOD[0][1:]] + GOOD[1:]), "029")


def test_reserved_columns_must_be_blank() -> None:
    bad = GOOD[0][:63] + "X" + GOOD[0][64:]
    assert has(lint_lines([bad] + GOOD[1:]), "64-72")


def test_bad_source_code() -> None:
    bad = GOOD[0][:55] + "BLOG    " + GOOD[0][63:]
    assert has(lint_lines([bad] + GOOD[1:]), "source code")


def test_unknown_relation() -> None:
    bad = card("HOLLERITH", "KNOWS", "CTR", "WIKI", 5)
    assert has(lint_lines(GOOD + [bad, card("CTR", "KNOWS", "HOLLERITH", "WIKI", 6)]), "not in the vocabulary")


def test_self_loop() -> None:
    bad = "IBM".ljust(20) + "FOUNDED".ljust(15) + "IBM".ljust(20) + "WIKI".ljust(8) + " " * 9 + "00000005"
    assert has(lint_lines(GOOD + [bad, bad[:72] + "00000006"]), "to itself")


def test_leading_blank_in_field() -> None:
    bad = " HOLLERITH".ljust(20) + "LED".ljust(15) + "CTR".ljust(20) + "WIKI".ljust(8) + " " * 9 + "00000005"
    assert has(lint_lines(GOOD + [bad, card("CTR", "LED BY", "HOLLERITH", "WIKI", 6)]), "starts with a blank")


def test_missing_inverse() -> None:
    assert has(lint_lines(GOOD[:3]), "missing inverse")


def test_odd_card_count() -> None:
    assert has(lint_lines(GOOD[:3]), "odd number of cards")


def test_forward_card_with_inverse_relation() -> None:
    lines = [card("TABULATING MACH CO", "FOUNDED BY", "HOLLERITH", "WIKI", 1),
             card("HOLLERITH", "FOUNDED", "TABULATING MACH CO", "WIKI", 2)]
    assert has(lint_lines(lines), "forward card carries inverse relation")


def test_second_card_must_mirror_first() -> None:
    lines = [GOOD[0], card("CTR", "FOUNDED BY", "HOLLERITH", "WIKI", 2)]
    probs = lint_lines(lines)
    assert has(probs, "not the mirror of line 1")


def test_pair_sequence_must_be_consecutive() -> None:
    lines = [GOOD[0], GOOD[1][:72] + "00000009"]
    assert has(lint_lines(lines), "sequence should be 00000002")


def test_duplicate_and_unordered_sequence() -> None:
    probs = lint_lines(GOOD + GOOD[:2])
    assert has(probs, "not unique")
    assert has(probs, "not ascending")
    assert has(probs, "duplicate fact")


def test_dangling_entity_never_subject_and_never_object() -> None:
    probs = lint_lines([GOOD[0], GOOD[0][:72] + "00000002"])
    assert has(probs, "dangling", "never a subject", "TABULATING MACH CO")
    assert has(probs, "dangling", "never an object", "HOLLERITH")


def test_relation_synonyms_are_flagged_above_half() -> None:
    lines = GOOD + [
        card("HOLLERITH", "LED", "TABULATING MACH CO", "WIKI", 5),
        card("TABULATING MACH CO", "LED BY", "HOLLERITH", "WIKI", 6),
    ]
    assert has(lint_lines(lines), "synonyms", "FOUNDED", "LED")


def test_jaccard_exactly_half_is_allowed() -> None:
    lines = GOOD + [
        card("HOLLERITH", "LED", "TABULATING MACH CO", "WIKI", 5),
        card("TABULATING MACH CO", "LED BY", "HOLLERITH", "WIKI", 6),
        card("WATSON", "LED", "IBM", "WIKI", 7),
        card("IBM", "LED BY", "WATSON", "WIKI", 8),
        card("WATSON", "WORKED AT", "IBM", "WIKI", 9),
        card("IBM", "EMPLOYED", "WATSON", "WIKI", 10),
    ]
    # FOUNDED {(H,T)} vs LED {(H,T),(W,I)} -> Jaccard 0.5 -> allowed
    assert not has(lint_lines(lines), "synonyms", "FOUNDED", "LED")


def test_full_field_is_flagged_for_truncation() -> None:
    lines = [card("A" * 20, "FOUNDED", "B", "WIKI", 1), card("B", "FOUNDED BY", "A" * 20, "WIKI", 2)]
    assert has(lint_lines(lines), "truncation")


def test_crlf_file_is_reported(tmp_path: Path) -> None:
    p = tmp_path / "crlf.deck"
    p.write_bytes("".join(l + "\r\n" for l in GOOD).encode())
    assert has(lint_file(p), "carriage return")


def test_shipped_deck_is_clean() -> None:
    deck = REPO / "data" / "cards.deck"
    assert deck.exists(), "data/cards.deck must ship with the repo"
    assert lint_file(deck) == []
