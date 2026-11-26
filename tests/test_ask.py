"""Parser, narrator faithfulness, the ask pipeline and its trace schema, model save/load."""
import json
import re
from pathlib import Path

import pytest

from hollerith import Deck
from hollerith.narrate import narrate_answer
from hollerith.parse import find_relation, parse
from hollerith.trace import ask, load_model, save_model, train_full

REPO = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def deck() -> Deck:
    return Deck.load(REPO / "data" / "cards.deck")


@pytest.fixture(scope="module")
def policy(deck):
    return train_full(deck, mode="sl", seed=0, epochs=15)


@pytest.mark.parametrize("q,ent,rel", [
    ("Who founded the Tabulating Machine Company?", "TABULATING MACH CO", "FOUNDED BY"),
    ("who founded IBM", "IBM", "FOUNDED BY"),
    ("Where was Herman Hollerith born?", "HERMAN HOLLERITH", "BORN IN"),
    ("Where did Grace Hopper work?", "GRACE HOPPER", "WORKED AT"),
    ("What did Konrad Zuse build?", "KONRAD ZUSE", "BUILT"),
    ("Who built ENIAC?", "ENIAC", "BUILT BY"),
    ("What was CTR renamed to?", "CTR", "RENAMED TO"),
    ("What did Hollerith invent?", "HERMAN HOLLERITH", "INVENTED"),
    ("What succeeded the IBM 701?", "IBM 701", "PRECEDED"),
    ("Who led IBM?", "IBM", "LED BY"),
    ("Where is Bell Labs located?", "BELL LABS", "LOCATED IN"),
    ("What did ENIAC use?", "ENIAC", "USED"),
    ("Who influenced Howard Aiken?", "HOWARD AIKEN", "INFLUENCED BY"),
])
def test_parse_known_shapes(deck, q, ent, rel) -> None:
    p = parse(q, deck.entities())
    assert (p.entity, p.relation) == (ent, rel), p


def test_parse_prefers_longest_entity(deck) -> None:
    p = parse("Who led Thomas J. Watson Sr?", deck.entities())  # contains 'WATSON SR' alias and full name
    assert p.entity == "THOMAS J. WATSON SR"
    p = parse("What did IBM 701 use?", deck.entities())  # 'IBM' is a prefix of 'IBM 701'
    assert p.entity == "IBM 701"


def test_parse_unknown_entity_and_shape(deck) -> None:
    assert parse("Where was Ada Lovelace born?", deck.entities()).entity is None
    assert parse("Is IBM a good company?", deck.entities()).relation is None
    assert not parse("", deck.entities()).ok
    assert find_relation("tell me everything") is None


def test_narration_cites_every_card_and_names_only_path_entities(deck) -> None:
    f = deck.find(subject="HERMAN HOLLERITH", relation="FOUNDED")[0]
    text = narrate_answer("q", f.subject, f.relation, f.object, [f])
    assert f"[{f.sequence:08d}]" in text
    for e in deck.entities() - {f.subject, f.object}:
        assert not re.search(r"(?<![A-Z0-9])" + re.escape(e) + r"(?![A-Z0-9])", text.upper()), e


def test_ask_direct_card(deck, policy) -> None:
    t = ask("Who founded the Tabulating Machine Company?", deck, policy)
    assert t.status == "answered" and t.mode == "direct" and t.answer == "HERMAN HOLLERITH"
    assert len(t.path) == 1 and t.path[0]["seq"] == "00000002" and t.confidence == 1.0
    assert "[00000002]" in t.narration


def test_ask_unknown_entity_is_no_cards(deck, policy) -> None:
    t = ask("Where was Ada Lovelace born?", deck, policy)
    assert t.status == "no_cards" and t.answer is None and t.path == []
    assert t.narration.startswith("NO CARDS, NO ANSWER")


def test_ask_unparseable_is_no_cards_with_entity(deck, policy) -> None:
    t = ask("Is IBM a good company?", deck, policy)
    assert t.status == "no_cards" and t.entity == "IBM" and "IBM" in t.narration


def test_pull_a_card_forces_the_walker(deck, policy) -> None:
    direct = ask("Who founded the Tabulating Machine Company?", deck, policy)
    pulled = ask("Who founded the Tabulating Machine Company?", deck, policy, pulled=[int(direct.path[0]["seq"])])
    assert pulled.pulled == ["00000002"]
    assert pulled.mode == "walk"
    assert pulled.status in ("answered", "jam")
    assert all(c["seq"] not in ("00000001", "00000002") for c in pulled.path)
    if pulled.status == "answered":
        assert pulled.path[-1]["object"] == pulled.answer
        for c in pulled.path:
            assert f"[{c['seq']}]" in pulled.narration
    else:
        assert pulled.answer is None and pulled.narration.startswith(("JAM", "TABULATING", "HERMAN")) and "JAM:" in pulled.narration


def test_trace_json_schema(deck, policy) -> None:
    t = ask("Where did Grace Hopper work?", deck, policy)
    d = json.loads(t.to_json())
    assert set(d) == {"question", "status", "entity", "relation", "answer", "path", "confidence", "pulled", "narration", "mode"}
    for c in d["path"]:
        assert set(c) == {"seq", "subject", "relation", "object", "source", "line", "prob"} and len(c["line"]) == 80


def test_every_answered_trace_is_faithful(deck, policy) -> None:
    """Narration names only on-path entities and cites only on-path cards, over many questions."""
    from hollerith.questions import questions
    pairs = questions(deck)[:120]
    vocab = deck.entities()
    checked = 0
    for q, gold in pairs:
        t = ask(q, deck, policy, pulled=[gold.sequence])  # pull the gold card so the walker must work
        if t.status != "answered":
            continue
        on_path = {c["subject"] for c in t.path} | {c["object"] for c in t.path}
        seqs = {c["seq"] for c in t.path}
        up = t.narration.upper()
        for e in sorted(on_path, key=len, reverse=True):  # blank out on-path names, longest first
            up = re.sub(r"(?<![A-Z0-9])" + re.escape(e) + r"(?![A-Z0-9])", " ", up)
        for e in vocab - on_path:
            assert not re.search(r"(?<![A-Z0-9])" + re.escape(e) + r"(?![A-Z0-9])", up), (q, e)
        for s in re.findall(r"\[(\d{8})\]", t.narration):
            assert s in seqs
        checked += 1
    assert checked >= 20


def test_model_save_load_round_trip(tmp_path, deck, policy) -> None:
    p = tmp_path / "walker.npz"
    save_model(policy, p)
    again = load_model(p, deck)
    q = "Where did Grace Hopper work?"
    a = ask(q, deck, policy, pulled=[])
    b = ask(q, deck, again, pulled=[])
    assert a.answer == b.answer and a.path == b.path


def test_unknown_path_shape_is_a_jam_not_an_answer(deck, policy) -> None:
    """A path whose relation chain never explained the asked relation in training is a jam."""
    assert policy.known_chains  # SL training recorded chains
    t = ask("Who founded Ferranti?", deck, policy)  # FERRANTI has no FOUNDED BY card
    assert t.status in ("jam", "no_cards")
    if t.status == "jam":
        assert t.answer is None and "JAM:" in t.narration and t.path  # the receipt is still shown


def test_pulled_one_card_answer_is_narrated_as_inferred(deck, policy) -> None:
    t = ask("Who founded the Tabulating Machine Company?", deck, policy, pulled=[2])
    assert t.mode == "walk"
    if t.status == "answered":
        assert "read directly" not in t.narration and "inferred" in t.narration
    else:
        assert "JAM:" in t.narration


def test_chains_survive_save_load(tmp_path, deck, policy) -> None:
    from hollerith.trace import load_model, save_model
    p = tmp_path / "w.npz"
    save_model(policy, p)
    again = load_model(p, deck)
    assert again.known_chains == policy.known_chains
