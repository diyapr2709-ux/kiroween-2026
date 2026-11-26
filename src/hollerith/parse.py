"""Question parser: natural language -> (entity, relation), deterministic, no LLM.

Two steps: (1) find the longest deck entity named in the question (case-insensitive, word
boundaries, abbreviations allowed via `ALIASES`); (2) match the question shape to a relation
with a small pattern table. Anything unmatched is reported, never guessed — an unknown entity
becomes a NO CARDS answer downstream, and an unrecognised question shape is `relation=None`.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .code_table import INVERSE

# question shape -> relation asked FROM the named entity. Order matters: first match wins.
PATTERNS: list[tuple[str, str]] = [
    (r"\bwho (founded|started|created|established)\b", "FOUNDED BY"),
    (r"\bwhat (company|companies|organi[sz]ations?)? ?did .* (found|start|establish)\b", "FOUNDED"),
    (r"\bwho (built|constructed|made)\b", "BUILT BY"),
    (r"\bwhat (machines?|computers?)? ?did .* build\b", "BUILT"),
    (r"\bwho invented\b", "INVENTED BY"),
    (r"\bwhat did .* invent\b", "INVENTED"),
    (r"\bwho (worked|was employed) (at|for)\b", "EMPLOYED"),
    (r"\bwhere did .* work\b", "WORKED AT"),
    (r"\bwho (did|does) .* employ\b", "EMPLOYED"),
    (r"\bwho (led|ran|headed|directed)\b", "LED BY"),
    (r"\bwhat did .* (lead|run|head|direct)\b", "LED"),
    (r"\bwhere was .* born\b", "BORN IN"),
    (r"\bwho was born in\b", "BIRTHPLACE OF"),
    (r"\bwhere (is|was) .* (located|based)\b", "LOCATED IN"),
    (r"\bwhat (is|was) (located|based) in\b", "LOCATION OF"),
    (r"\bwhat (did|does) .* (use|run on)\b", "USED"),
    (r"\bwho used\b|\bwhat used\b", "USED BY"),
    (r"\bwhat was .* renamed (to|as)\b|\bwhat did .* become\b", "RENAMED TO"),
    (r"\bwhat was .* (renamed from|called before|formerly)\b", "RENAMED FROM"),
    (r"\bwhat did .* merge into\b|\bwhat acquired\b", "MERGED INTO"),
    (r"\bwhat was .* formed from\b|\bwhat formed\b", "FORMED FROM"),
    (r"\bwhat (succeeded|replaced|came after)\b", "PRECEDED"),
    (r"\bwhat did .* (succeed|replace)\b|\bwhat (preceded|came before)\b", "SUCCEEDED"),
    (r"\bwho (did|does) .* influence\b|\bwhat did .* influence\b", "INFLUENCED"),
    (r"\bwho influenced\b|\bwhat influenced\b", "INFLUENCED BY"),
]

ALIASES: dict[str, str] = {
    "IBM": "IBM", "I.B.M.": "IBM",
    "TABULATING MACHINE COMPANY": "TABULATING MACH CO", "TABULATING MACHINE CO": "TABULATING MACH CO",
    "COMPUTING-TABULATING-RECORDING": "CTR", "C-T-R": "CTR",
    "ECKERT-MAUCHLY COMPUTER CORPORATION": "ECKERT-MAUCHLY CO", "ECKERT MAUCHLY": "ECKERT-MAUCHLY CO", "EMCC": "ECKERT-MAUCHLY CO",
    "HOLLERITH": "HERMAN HOLLERITH", "TURING": "ALAN TURING", "ZUSE": "KONRAD ZUSE", "HOPPER": "GRACE HOPPER",
    "VON NEUMANN": "JOHN VON NEUMANN", "AIKEN": "HOWARD AIKEN", "ECKERT": "J. PRESPER ECKERT", "MAUCHLY": "JOHN MAUCHLY",
    "WATSON SR": "THOMAS J. WATSON SR", "WATSON SENIOR": "THOMAS J. WATSON SR", "THOMAS WATSON": "THOMAS J. WATSON SR",
    "WATSON JR": "THOMAS J. WATSON JR", "WATSON JUNIOR": "THOMAS J. WATSON JR",
    "UNIVERSITY OF MANCHESTER": "UNIV OF MANCHESTER", "MANCHESTER UNIVERSITY": "UNIV OF MANCHESTER",
    "UNIVERSITY OF CAMBRIDGE": "UNIV OF CAMBRIDGE", "CAMBRIDGE UNIVERSITY": "UNIV OF CAMBRIDGE",
    "HARVARD": "HARVARD UNIVERSITY", "THE MOORE SCHOOL": "MOORE SCHOOL", "CENSUS BUREAU": "US CENSUS BUREAU",
    "THE TRANSISTOR": "TRANSISTOR", "THE INTEGRATED CIRCUIT": "INTEGRATED CIRCUIT", "MARK I": "HARVARD MARK I",
    "THE 1890 CENSUS": "1890 US CENSUS", "1890 CENSUS": "1890 US CENSUS",
}


@dataclass(frozen=True)
class Parse:
    question: str
    entity: str | None
    relation: str | None
    matched_text: str | None

    @property
    def ok(self) -> bool:
        return self.entity is not None and self.relation is not None


def _normalise(q: str) -> str:
    q = q.upper().replace("’", "'")
    q = re.sub(r"[^\w\s\.\-&']", " ", q)
    return re.sub(r"\s+", " ", q).strip()


def find_entity(question: str, entities: set[str]) -> tuple[str | None, str | None]:
    """Longest entity (or alias) mentioned in the question, by word boundaries."""
    q = " " + _normalise(question) + " "
    best: tuple[str | None, str | None] = (None, None)
    best_len = 0
    for text, canon in list(ALIASES.items()) + [(e, e) for e in entities]:
        if canon not in entities:
            continue
        pat = r"(?<![A-Z0-9])" + re.escape(text) + r"(?![A-Z0-9])"
        if re.search(pat, q) and len(text) > best_len:
            best, best_len = (canon, text), len(text)
    return best


def find_relation(question: str) -> str | None:
    q = question.lower()
    for pat, rel in PATTERNS:
        if re.search(pat, q):
            return rel
    return None


def parse(question: str, entities: set[str]) -> Parse:
    if not question or not question.strip():
        return Parse(question, None, None, None)
    entity, text = find_entity(question, entities)
    rel = find_relation(question)
    if rel is not None and rel not in INVERSE:  # defensive: pattern table must stay on-vocabulary
        rel = None
    return Parse(question, entity, rel, text)
