"""The code table matches the published IBM 029 assignments and is internally consistent."""
import re
from pathlib import Path

import pytest

from hollerith import CODE, INVERSE, LAYOUT, RELATIONS, SOURCES
from hollerith.code_table import PATTERN_TO_CHAR, ROWS, width

REPO = Path(__file__).resolve().parents[1]

# Every one of the 61 characters, pinned independently of the generator in code_table.py.
KNOWN: dict[str, set[str]] = {str(d): {str(d)} for d in range(10)}
KNOWN.update({ch: {"12", str(i)} for i, ch in enumerate("ABCDEFGHI", start=1)})
KNOWN.update({ch: {"11", str(i)} for i, ch in enumerate("JKLMNOPQR", start=1)})
KNOWN.update({ch: {"0", str(i)} for i, ch in enumerate("STUVWXYZ", start=2)})
KNOWN.update({
    " ": set(), "&": {"12"}, "-": {"11"}, "/": {"0", "1"},
    ".": {"12", "8", "3"}, "<": {"12", "8", "4"}, "(": {"12", "8", "5"}, "+": {"12", "8", "6"}, "|": {"12", "8", "7"},
    "$": {"11", "8", "3"}, "*": {"11", "8", "4"}, ")": {"11", "8", "5"}, ";": {"11", "8", "6"}, "¬": {"11", "8", "7"},
    ",": {"0", "8", "3"}, "%": {"0", "8", "4"}, "_": {"0", "8", "5"}, ">": {"0", "8", "6"}, "?": {"0", "8", "7"},
    ":": {"8", "2"}, "#": {"8", "3"}, "@": {"8", "4"}, "'": {"8", "5"}, "=": {"8", "6"}, '"': {"8", "7"},
})


@pytest.mark.parametrize("ch,rows", sorted(KNOWN.items()))
def test_known_assignments(ch: str, rows: set[str]) -> None:
    assert CODE[ch] == frozenset(rows)


def test_known_table_is_complete() -> None:
    assert set(KNOWN) == set(CODE)


def test_alphabet_size() -> None:
    assert len(CODE) == 61  # 26 letters + 10 digits + space + 24 specials (incl. not-sign)


def test_no_two_characters_share_a_pattern() -> None:
    assert len(PATTERN_TO_CHAR) == len(CODE)


def test_every_pattern_uses_only_real_rows() -> None:
    for ch, pattern in CODE.items():
        assert pattern <= set(ROWS), ch


def test_at_most_one_zone_and_one_digit_punch_plus_8() -> None:
    zones = {"12", "11", "0"}
    for ch, pattern in CODE.items():
        if ch in "/STUVWXYZ" or ch in ",%_>?":  # 0 acts as a zone here
            continue
        assert len(pattern & zones) <= 1, ch
        digits = pattern - zones - {"8"}
        assert len(digits) <= 1, ch


def test_layout_covers_all_80_columns_without_overlap() -> None:
    spans = sorted(LAYOUT.values())
    assert spans[0][0] == 1 and spans[-1][1] == 80
    for (a1, b1), (a2, b2) in zip(spans, spans[1:]):
        assert b1 + 1 == a2, (a1, b1, a2, b2)


def test_relations_are_a_bijection_and_fit_the_field() -> None:
    assert len(set(RELATIONS.values())) == len(RELATIONS)
    assert not set(RELATIONS) & set(RELATIONS.values())
    for r in INVERSE:
        assert INVERSE[INVERSE[r]] == r
        assert len(r) <= width("relation")


def test_sources_fit_their_field() -> None:
    for code in SOURCES:
        assert len(code) <= width("source")
        assert re.fullmatch(r"[A-Z0-9]+", code)


def test_steering_doc_agrees_if_present() -> None:
    """If Kiro's steering doc exists, it must name every relation, source and hole pattern."""
    doc = REPO / ".kiro" / "steering" / "hollerith.md"
    if not doc.exists():
        pytest.skip("steering doc not written yet (Kiro's Loop 1 task)")
    text = doc.read_text(encoding="utf-8")
    for r in INVERSE:
        assert re.search(rf"(?<![A-Z]){re.escape(r)}(?![A-Z])", text), f"steering doc does not mention relation {r}"
    for s in SOURCES:
        assert re.search(rf"(?<![A-Z]){re.escape(s)}(?![A-Z])", text), f"steering doc does not mention source {s}"
    # Hole patterns: the doc must contain each character's rows in the form "12-8-3" (or "none").
    for ch, pattern in CODE.items():
        rows = "-".join(sorted(pattern, key=ROWS.index)) if pattern else "none"
        assert rows in text, f"steering doc lacks the hole pattern {rows} for {ch!r}"
