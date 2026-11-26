"""Templated narrator: a green-bar listing built ONLY from the cards on the path.

Every sentence names only entities that appear on a path card and cites that card's sequence
number as [00000012]. Faithfulness is therefore 100 % by construction; the check in
docs/arena/checks/check_faithfulness.py verifies it on the emitted trace anyway.
"""
from __future__ import annotations

from .deck import Fact

VERBS: dict[str, str] = {
    "FOUNDED": "founded", "FOUNDED BY": "was founded by",
    "BUILT": "built", "BUILT BY": "was built by",
    "WORKED AT": "worked at", "EMPLOYED": "employed",
    "RENAMED TO": "was renamed", "RENAMED FROM": "was formerly",
    "INFLUENCED": "influenced", "INFLUENCED BY": "was influenced by",
    "USED": "used", "USED BY": "was used by",
    "MERGED INTO": "merged into", "FORMED FROM": "was formed from",
    "LED": "led", "LED BY": "was led by",
    "BORN IN": "was born in", "BIRTHPLACE OF": "is the birthplace of",
    "INVENTED": "invented", "INVENTED BY": "was invented by",
    "SUCCEEDED": "succeeded", "PRECEDED": "preceded",
    "LOCATED IN": "was located in", "LOCATION OF": "was the location of",
}


def cite(f: Fact) -> str:
    return f"[{f.sequence:08d}]"


def sentence(f: Fact) -> str:
    return f"{f.subject} {VERBS.get(f.relation, f.relation.lower())} {f.object} {cite(f)}."


def narrate_answer(question: str, subject: str, relation: str, answer: str, path: list[Fact], direct: bool = True) -> str:
    lines = [sentence(f) for f in path]
    hops = len(path)
    rel = VERBS.get(relation, relation.lower())
    cites = " ".join(cite(f) for f in path)
    chain = " -> ".join(f.relation for f in path)
    if direct and hops == 1:
        lines.append(f"ANSWER: {answer} — {subject} {rel} {answer}, read directly from card {cite(path[0])}.")
    elif hops == 1:
        lines.append(f"ANSWER: {answer} — inferred, not read directly: card {cites} says {path[0].relation}, "
                     f"from which the reader concludes {subject} {rel} {answer}.")
    else:
        lines.append(f"ANSWER: {answer} — inferred over {hops} cards {cites} ({chain}): {subject} {rel} {answer}.")
    return "\n".join(lines)


def narrate_jam(subject: str, relation: str, path: list[Fact], reason: str = "") -> str:
    lines = [sentence(f) for f in path]
    where = path[-1].object if path else subject
    why = f" ({reason})" if reason else ""
    lines.append(f"JAM: NO {relation} FROM {where}{why}. The reader found no card that completes this path; no answer is given.")
    return "\n".join(lines)


def narrate_no_cards(entity: str | None, relation: str | None) -> str:
    if entity is None:
        return "NO CARDS, NO ANSWER. No card in the deck names that entity."
    if relation is None:
        return f"NO CARDS, NO ANSWER. The question about {entity} does not match any relation punched on the cards."
    return f"NO CARDS, NO ANSWER. No card leaves {entity} and no path was found."
