"""Property-based round trip: every string over the 029 set survives encode -> decode."""
import pytest
from hypothesis import HealthCheck, given, settings, strategies as st

from hollerith import ALPHABET, Card, CardEncodingError, decode, encode
from hollerith.hollerith_code import holes_to_text

CASES = 10_000


@settings(max_examples=CASES, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(st.text(alphabet=ALPHABET, min_size=0, max_size=80))
def test_text_round_trip(s: str) -> None:
    assert decode(encode(s)) == s.rstrip(" ")


@settings(max_examples=CASES, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(st.text(alphabet=ALPHABET, min_size=0, max_size=80))
def test_card_round_trip_is_exact_on_all_80_columns(s: str) -> None:
    card = encode(s)
    assert holes_to_text(card.holes) == card.text
    assert Card.from_holes(card.holes) == card


@pytest.mark.parametrize("s", ["", " " * 80, "A" * 80, ALPHABET[:80], "HOLLERITH"])
def test_edge_cases(s: str) -> None:
    assert decode(encode(s)) == s.rstrip(" ")


def test_lowercase_is_uppercased() -> None:
    assert decode(encode("hollerith's ghost")) == "HOLLERITH'S GHOST"


@pytest.mark.parametrize("s", ["x" * 81, "A" * 200])
def test_too_long_is_rejected(s: str) -> None:
    with pytest.raises(CardEncodingError):
        encode(s)


@pytest.mark.parametrize("s", ["a\tb", "\x00", "café", "~", "^", "`", "{", "}", "[", "]", "\\", "⌑", "\n"])
def test_invalid_characters_are_rejected(s: str) -> None:
    with pytest.raises(CardEncodingError):
        encode(s)


def test_bad_holes_are_rejected() -> None:
    card = encode("A")
    holes = card.holes
    holes[0][0] = True  # row 12
    holes[1][0] = True  # row 11 -> 12-11-1 is not a character
    with pytest.raises(CardEncodingError):
        holes_to_text(holes)


def test_wrong_shape_is_rejected() -> None:
    with pytest.raises(CardEncodingError):
        holes_to_text([[False] * 80] * 11)
