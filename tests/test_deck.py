"""The deck file is the database: layout, inverses, sorter pass, punch."""
from pathlib import Path

import pytest

from hollerith import Deck, DeckError, Fact, LAYOUT
from hollerith.hollerith_code import punch_fields


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
    a, b = LAYOUT["subject"]
    assert line[a - 1:b].rstrip() == "HERMAN HOLLERITH"
    a, b = LAYOUT["relation"]
    assert line[a - 1:b].rstrip() == "FOUNDED"
    a, b = LAYOUT["object"]
    assert line[a - 1:b].rstrip() == "TABULATING MACH CO"
    a, b = LAYOUT["source"]
    assert line[a - 1:b].rstrip() == "WIKI"
    a, b = LAYOUT["reserved"]
    assert line[a - 1:b] == " " * 9
    a, b = LAYOUT["sequence"]
    assert line[a - 1:b] == "00000001"


def test_neighbours_is_a_sorter_pass_over_subject_column(deck: Deck) -> None:
    facts = deck.neighbours("tabulating mach co")
    assert [f.relation for f in facts] == ["FOUNDED BY", "MERGED INTO"]
    assert deck.neighbours("NOBODY") == []


def test_find_filters(deck: Deck) -> None:
    assert len(deck.find(relation="RENAMED TO")) == 1
    assert deck.find(subject="IBM", relation="RENAMED FROM")[0].object == "CTR"
    assert deck.find(subject="IBM", relation="FOUNDED") == []


def test_entities_and_has_entity(deck: Deck) -> None:
    assert deck.entities() == {"HERMAN HOLLERITH", "TABULATING MACH CO", "CTR", "IBM"}
    assert deck.has_entity("ibm") and not deck.has_entity("ENIAC")


def test_save_and_load_round_trip(tmp_path: Path, deck: Deck) -> None:
    p = tmp_path / "cards.deck"
    deck.save(p)
    text = p.read_text()
    assert all(len(line) == 80 for line in text.rstrip("\n").split("\n"))
    again = Deck.load(p)
    assert again.triples() == deck.triples()


def test_load_rejects_short_line(tmp_path: Path) -> None:
    p = tmp_path / "bad.deck"
    p.write_text("HOLLERITH" + " " * 70 + "\n")  # 79 columns
    with pytest.raises(DeckError):
        Deck.load(p)


def test_load_rejects_bad_character(tmp_path: Path) -> None:
    p = tmp_path / "bad.deck"
    p.write_text("hollerith".ljust(80) + "\n")  # lowercase is not in the punched set
    with pytest.raises(DeckError):
        Deck.load(p)


def test_punch_rejects_bad_relation_source_overflow_and_duplicates(deck: Deck) -> None:
    with pytest.raises(DeckError):
        deck.punch("A", "KNOWS", "B", "WIKI")
    with pytest.raises(DeckError):
        deck.punch("A", "FOUNDED", "B", "BLOG")
    with pytest.raises(DeckError):
        deck.punch("A" * 21, "FOUNDED", "B", "WIKI")
    with pytest.raises(DeckError):
        deck.punch("A", "FOUNDED", "A", "WIKI")
    with pytest.raises(DeckError):
        deck.punch("HERMAN HOLLERITH", "FOUNDED", "TABULATING MACH CO", "WIKI")


def test_punch_fields_sequence_width() -> None:
    card = punch_fields("A", "FOUNDED", "B", "WIKI", 99_999_999)
    assert card.text[72:80] == "99999999"
    with pytest.raises(Exception):
        punch_fields("A", "FOUNDED", "B", "WIKI", 100_000_000)


def test_empty_deck_has_no_facts_and_sequence_starts_at_one() -> None:
    d = Deck()
    assert d.facts() == [] and d.next_sequence() == 1 and d.entities() == set()
