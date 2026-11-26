"""Natural-language questions generated from cards — one template per relation.

`question_for(fact)` asks (fact.subject, fact.relation, ?). Every template parses back to the same
(entity, relation) through `parse.py`; `tests/test_questions.py` checks that for every card.
Used for the suggested-questions hopper, the faithfulness report, and the LLM-only baseline.
"""
from __future__ import annotations

from .deck import Deck, Fact

TEMPLATES: dict[str, str] = {
    "FOUNDED": "What did {s} found?",
    "FOUNDED BY": "Who founded {s}?",
    "BUILT": "What did {s} build?",
    "BUILT BY": "Who built {s}?",
    "WORKED AT": "Where did {s} work?",
    "EMPLOYED": "Who worked at {s}?",
    "RENAMED TO": "What was {s} renamed to?",
    "RENAMED FROM": "What was {s} formerly called?",
    "INFLUENCED": "What did {s} influence?",
    "INFLUENCED BY": "Who influenced {s}?",
    "USED": "What did {s} use?",
    "USED BY": "Who used {s}?",
    "MERGED INTO": "What did {s} merge into?",
    "FORMED FROM": "What was {s} formed from?",
    "LED": "What did {s} lead?",
    "LED BY": "Who led {s}?",
    "BORN IN": "Where was {s} born?",
    "BIRTHPLACE OF": "Who was born in {s}?",
    "INVENTED": "What did {s} invent?",
    "INVENTED BY": "Who invented {s}?",
    "SUCCEEDED": "What did {s} succeed?",
    "PRECEDED": "What succeeded {s}?",
    "LOCATED IN": "Where was {s} located?",
    "LOCATION OF": "What was located in {s}?",
}


def _title(name: str) -> str:
    """Card text is upper case; questions read better in title case, and the parser is case-blind."""
    small = {"OF", "AND", "THE", "DE"}
    words = []
    for w in name.split(" "):
        if w in small:
            words.append(w.lower())
        elif len(w) <= 3 and w.isalpha() and w not in ("SR", "JR"):
            words.append(w)  # acronyms: IBM, CTR, MIT, NPL, DEC, CDC, NCR
        else:
            words.append(w[:1] + w[1:].lower())
    return " ".join(words)


def question_for(fact: Fact, title_case: bool = True) -> str:
    s = _title(fact.subject) if title_case else fact.subject
    return TEMPLATES[fact.relation].format(s=s)


def questions(deck: Deck, title_case: bool = True) -> list[tuple[str, Fact]]:
    """(question, gold card) for every card in the deck, in sequence order."""
    return [(question_for(f, title_case), f) for f in deck.facts()]
