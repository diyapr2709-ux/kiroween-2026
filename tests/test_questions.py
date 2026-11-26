"""Every generated question parses back to its card's (subject, relation)."""
from collections import Counter
from pathlib import Path

import pytest

from hollerith import Deck
from hollerith.code_table import INVERSE
from hollerith.parse import parse
from hollerith.questions import TEMPLATES, question_for, questions

REPO = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def deck() -> Deck:
    return Deck.load(REPO / "data" / "cards.deck")


def test_every_relation_has_a_template() -> None:
    assert set(TEMPLATES) == set(INVERSE)


def test_every_card_question_round_trips_through_the_parser(deck) -> None:
    ents = deck.entities()
    failures = Counter()
    for q, f in questions(deck):
        p = parse(q, ents)
        if (p.entity, p.relation) != (f.subject, f.relation):
            failures[(f.relation, p.entity == f.subject, p.relation == f.relation)] += 1
    assert not failures, dict(failures)


def test_title_case_keeps_acronyms_and_suffixes(deck) -> None:
    f = deck.find(subject="THOMAS J. WATSON SR", relation="LED")[0]
    assert question_for(f) == "What did Thomas J. Watson SR lead?"
    f = deck.find(subject="IBM", relation="BUILT")[0]
    assert question_for(f) == "What did IBM build?"
    f = deck.find(subject="UNIV OF MANCHESTER", relation="BUILT")[0]
    assert question_for(f) == "What did Univ of Manchester build?"
