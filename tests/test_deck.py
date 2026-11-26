"""The deck file is the database: layout, inverses, sorter pass, punch, strict load."""
from pathlib import Path

import pytest

from hollerith import Deck, DeckError, Fact, LAYOUT
from hollerith.hollerith_code import CardEncodingError, punch_fields


@pytest.fixture
def deck() -> Deck:
    d = Deck()
    d.punch("Herman Hollerith", "founded", "Tabulating Mach Co", "wiki")
    d.punch("TABULATING MACH CO", "MERGED INTO", "CTR", "IBMARCH")
    d.punch("CTR", "RENAMED TO", "IBM", "IBMARCH")
    return d


def test_punch_writes_fact_and_inverse_with_consecutive_sequence(deck: Deck) -> None:
    cards = deck.cards
    assert len(cards) == 6
    f0, f1 = Fact.from_card(cards[0]), Fact.from_card(cards[1])
    assert f0.triple() == ("HERMAN HOLLERITH", "FOUNDED", "TABULATING MACH CO")
    assert f1.triple() == ("TABULATING MACH CO", "FOUNDED BY", "HERMAN HOLLERITH")
    assert (f0.sequence, f1.sequence) == (1, 2)
    assert f0.source == f1.source == "WIKI"


def test_layout_columns(deck: Deck) -> None:
    line = deck.cards[0].text
    assert len(line) == 80
    for name, expect in (("subject", "HERMAN HOLLERITH"), ("relation", "FOUNDED"),
                         ("object", "TABULATING MACH CO"), ("source", "WIKI"), ("sequence", "00000001")):
        a, b = LAYOUT[name]
        assert line[a - 1:b].rstrip() == expect
    a, b = LAYOUT["reserved"]
    assert line[a - 1:b] == " " * 9


def test_neighbours_is_a_sorter_pass_in_sequence_order(deck: Deck) -> None:
    facts = deck.neighbours("  tabulating mach co ")
    assert [f.relation for f in facts] == ["FOUNDED BY", "MERGED INTO"]
    assert [f.sequence for f in facts] == sorted(f.sequence for f in facts)
    assert deck.neighbours("NOBODY") == []


def test_neighbours_sequence_order_is_not_insertion_order() -> None:
    d = Deck()
    d.punch("B", "FOUNDED", "A", "WIKI")      # seq 1-2: A FOUNDED BY B is card 2
    d.punch("A", "RENAMED TO", "C", "WIKI")   # seq 3-4
    d.punch("A", "LED", "D", "WIKI")          # seq 5-6
    assert [f.sequence for f in d.neighbours("A")] == [2, 3, 5]


def test_find_filters(deck: Deck) -> None:
    assert len(deck.find(relation="renamed to")) == 1
    assert deck.find(subject="IBM", relation="RENAMED FROM")[0].object == "CTR"
    assert deck.find(subject="IBM", relation="FOUNDED") == []


def test_entities_and_has_entity(deck: Deck) -> None:
    assert deck.entities() == {"HERMAN HOLLERITH", "TABULATING MACH CO", "CTR", "IBM"}
    assert deck.has_entity("ibm") and not deck.has_entity("ENIAC")


def test_save_and_load_round_trip(tmp_path: Path, deck: Deck) -> None:
    p = tmp_path / "cards.deck"
    deck.save(p)
    raw = p.read_bytes()
    assert b"\r" not in raw and raw.endswith(b"\n")
    assert all(len(line) == 80 for line in raw.decode().rstrip("\n").split("\n"))
    assert Deck.load(p).triples() == deck.triples()


@pytest.mark.parametrize("line,why", [
    ("HOLLERITH" + " " * 70, "79 columns"),
    ("hollerith".ljust(80), "lowercase"),
    ("HERMAN HOLLERITH".ljust(72) + "ABCDEFGH", "alphabetic sequence"),
    ("HERMAN HOLLERITH".ljust(63) + "GARBAGE  " + "00000001", "garbage in reserved columns"),
    (punch_fields("A", "FOUNDED", "B", "WIKI", 1).text[:55] + "BLOG    " + " " * 9 + "00000001", "bad source"),
    (" HOLLERITH".ljust(20) + "FOUNDED".ljust(15) + "X".ljust(20) + "WIKI".ljust(8) + " " * 9 + "00000001", "leading blank"),
    ("X".ljust(20) + "FOUNDED".ljust(15) + "X".ljust(20) + "WIKI".ljust(8) + " " * 9 + "00000001", "self loop"),
    ("X".ljust(20) + "KNOWS".ljust(15) + "Y".ljust(20) + "WIKI".ljust(8) + " " * 9 + "00000001", "unknown relation"),
])
def test_load_rejects_layout_violations(tmp_path: Path, line: str, why: str) -> None:
    p = tmp_path / "bad.deck"
    p.write_bytes((line + "\n").encode())
    with pytest.raises(DeckError):
        Deck.load(p)


def test_load_rejects_crlf(tmp_path: Path, deck: Deck) -> None:
    p = tmp_path / "crlf.deck"
    p.write_bytes("".join(c.text + "\r\n" for c in deck.cards).encode())
    with pytest.raises(DeckError):
        Deck.load(p)


def test_load_rejects_blank_line_in_middle(tmp_path: Path, deck: Deck) -> None:
    p = tmp_path / "gap.deck"
    cards = deck.cards
    p.write_bytes((cards[0].text + "\n\n" + cards[1].text + "\n").encode())
    with pytest.raises(DeckError):
        Deck.load(p)


def test_load_empty_file_is_an_empty_deck(tmp_path: Path) -> None:
    p = tmp_path / "empty.deck"
    p.write_bytes(b"")
    assert len(Deck.load(p)) == 0


@pytest.mark.parametrize("args", [
    ("A", "KNOWS", "B", "WIKI"),                 # unknown relation
    ("A", "FOUNDED BY", "B", "WIKI"),            # inverse relation on a forward card
    ("A", "FOUNDED", "B", "BLOG"),               # unknown source
    ("A" * 21, "FOUNDED", "B", "WIKI"),          # subject overflow
    ("A", "FOUNDED", "A", "WIKI"),               # self loop
    ("IBM", "FOUNDED", "IBM ", "WIKI"),          # self loop hidden by whitespace
    ("", "FOUNDED", "B", "WIKI"),                # empty subject
    ("   ", "FOUNDED", "B", "WIKI"),             # blank subject
    ("A", "FOUNDED", "", "WIKI"),                # empty object
    ("HERMAN HOLLERITH ", "FOUNDED", "TABULATING MACH CO", "WIKI"),  # duplicate hidden by whitespace
])
def test_punch_rejects(deck: Deck, args: tuple[str, str, str, str]) -> None:
    before = len(deck)
    with pytest.raises(DeckError):
        deck.punch(*args)
    assert len(deck) == before


def test_punch_strips_and_uppercases() -> None:
    d = Deck()
    fwd, inv = d.punch("  grace hopper ", " worked at", " bell labs  ", " wiki ")
    assert Fact.from_card(fwd).triple() == ("GRACE HOPPER", "WORKED AT", "BELL LABS")
    assert Fact.from_card(inv).triple() == ("BELL LABS", "EMPLOYED", "GRACE HOPPER")
    assert fwd.text[0] != " " and inv.text[0] != " "


def test_punch_inverse_error_names_the_forward_form(deck: Deck) -> None:
    with pytest.raises(DeckError, match=r"\(B, FOUNDED, A\)"):
        deck.punch("A", "FOUNDED BY", "B", "WIKI")


def test_punch_fields_sequence_width() -> None:
    card = punch_fields("A", "FOUNDED", "B", "WIKI", 99_999_999)
    assert card.text[72:80] == "99999999"
    with pytest.raises(CardEncodingError):
        punch_fields("A", "FOUNDED", "B", "WIKI", 100_000_000)
    with pytest.raises(CardEncodingError):
        punch_fields("", "FOUNDED", "B", "WIKI", 1)


def test_empty_deck_has_no_facts_and_sequence_starts_at_one() -> None:
    d = Deck()
    assert d.facts() == [] and d.next_sequence() == 1 and d.entities() == set()


def test_fact_from_card_rejects_non_numeric_sequence() -> None:
    from hollerith.hollerith_code import Card
    with pytest.raises(DeckError):
        Fact.from_card(Card("A".ljust(72) + "ABCDEFGH"))
