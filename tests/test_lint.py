"""One failing fixture per lint rule, and the shipped deck must be clean."""
from pathlib import Path

import pytest

from hollerith import lint_file, lint_lines
from hollerith.hollerith_code import punch_fields


def card(s: str, r: str, o: str, src: str = "WIKI", seq: int = 1) -> str:
    return punch_fields(s, r, o, src, seq).text


GOOD = [
    card("HOLLERITH", "FOUNDED", "TABULATING MACH CO", "WIKI", 1),
    card("TABULATING MACH CO", "FOUNDED BY", "HOLLERITH", "WIKI", 2),
    card("TABULATING MACH CO", "MERGED INTO", "CTR", "IBMARCH", 3),
    card("CTR", "FORMED FROM", "TABULATING MACH CO", "IBMARCH", 4),
]


def test_good_deck_is_clean() -> None:
    assert lint_lines(GOOD) == []


def test_empty_deck() -> None:
    assert lint_lines([]) == ["deck is empty"]


def test_short_line() -> None:
    assert any("80 columns" in p for p in lint_lines(GOOD + [GOOD[0][:79]]))


def test_bad_character() -> None:
    bad = "h" + GOOD[0][1:]
    assert any("029" in p for p in lint_lines([bad] + GOOD[1:]))


def test_reserved_columns_must_be_blank() -> None:
    bad = GOOD[0][:63] + "X" + GOOD[0][64:]
    assert any("64-72" in p for p in lint_lines([bad] + GOOD[1:]))


def test_bad_source_code() -> None:
    bad = GOOD[0][:55] + "BLOG    " + GOOD[0][63:]
    assert any("source code" in p for p in lint_lines([bad] + GOOD[1:]))


def test_unknown_relation() -> None:
    bad = card("HOLLERITH", "KNOWS", "CTR", "WIKI", 5)
    assert any("not in the vocabulary" in p for p in lint_lines(GOOD + [bad]))


def test_missing_inverse() -> None:
    assert any("missing inverse" in p for p in lint_lines(GOOD[:3]))


def test_duplicate_and_unordered_sequence() -> None:
    dup = GOOD + [GOOD[0]]
    probs = lint_lines(dup)
    assert any("not unique" in p for p in probs)
    assert any("not ascending" in p for p in probs)
    assert any("duplicate fact" in p for p in probs)


def test_dangling_entity() -> None:
    probs = lint_lines([GOOD[0]])
    assert any("dangling" in p for p in probs)


def test_relation_synonyms_are_flagged() -> None:
    lines = GOOD + [
        card("HOLLERITH", "LED", "TABULATING MACH CO", "WIKI", 5),
        card("TABULATING MACH CO", "LED BY", "HOLLERITH", "WIKI", 6),
    ]
    # FOUNDED and LED share their only (s,o) pair -> Jaccard 1.0
    assert any("synonyms" in p and "FOUNDED" in p and "LED" in p for p in lint_lines(lines))


def test_full_field_is_flagged_for_truncation() -> None:
    lines = [card("A" * 20, "FOUNDED", "B", "WIKI", 1), card("B", "FOUNDED BY", "A" * 20, "WIKI", 2)]
    assert any("truncation" in p for p in lint_lines(lines))


def test_shipped_deck_is_clean() -> None:
    deck = Path("data/cards.deck")
    if not deck.exists():
        pytest.skip("deck not authored yet")
    assert lint_file(deck) == []
