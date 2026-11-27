"""The `ask` pipeline and its trace JSON — the contract between the CLI and the web reader.

    question -> parse -> (entity, relation)
             -> direct card?  yes: answered, path = [card]
             -> else walk (policy) -> answered if the best path's probability >= threshold
                                    else jam, path = the walk up to the dead end
             -> unknown entity / shape: no_cards

Trace schema (one object per question; a list when several):
{
  "question": str, "status": "answered" | "jam" | "no_cards",
  "entity": str|null, "relation": str|null, "answer": str|null,
  "path": [{"seq": "00000012", "subject", "relation", "object", "source", "line", "prob"}],
  "confidence": float|null, "pulled": ["00000012", ...], "narration": str, "mode": "direct" | "walk" | null
}
`--pull SEQ` masks those cards (and their inverses) before walking: pull-a-card.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np

from .code_table import INVERSE
from .deck import Deck, Fact
from .graph import Graph
from .narrate import narrate_answer, narrate_jam, narrate_no_cards
from .parse import parse
from .policy import Policy

DEFAULT_MODEL = Path("models/walker.npz")
JAM_THRESHOLD = 0.10  # product rule: a walk whose best path has probability below this is a jam


@dataclass
class Trace:
    question: str
    status: str
    entity: str | None
    relation: str | None
    answer: str | None
    path: list[dict] = field(default_factory=list)
    confidence: float | None = None
    pulled: list[str] = field(default_factory=list)
    narration: str = ""
    mode: str | None = None

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)


def card_dict(f: Fact, deck_lines: dict[int, str], prob: float | None = None) -> dict:
    return {"seq": f"{f.sequence:08d}", "subject": f.subject, "relation": f.relation, "object": f.object,
            "source": f.source, "line": deck_lines.get(f.sequence, ""), "prob": prob}


# ---- model persistence -------------------------------------------------------------------
def train_full(deck: Deck, mode: str = "sl", seed: int = 0, epochs: int = 40, hops: int = 4) -> Policy:
    """Train the product walker on every card of the deck (no held-out facts)."""
    from .graph import forward_facts
    g = Graph.from_deck(deck)
    p = Policy(mode=mode, hops=hops, epochs=epochs, simple_paths=True)  # product walker: no oscillation
    p.chain_prune = True  # product walker: jam where the path shape stops being known, do not wander
    p.fit(g, forward_facts(deck), [], seed)
    return p


def save_model(p: Policy, path: str | Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    chains = {r: sorted(list(c) for c in cs) for r, cs in p.known_chains.items()}
    np.savez(path, R=p.R, E=p.E, rels=np.array(p.rels), ents=np.array(p.ents),
             meta=np.array(json.dumps({"mode": p.mode, "hops": p.hops, "dim": p.dim, "beam": p.beam, "chains": chains, "simple_paths": p.simple_paths, "chain_prune": p.chain_prune})))


def load_model(path: str | Path, deck: Deck) -> Policy:
    z = np.load(path, allow_pickle=False)
    meta = json.loads(str(z["meta"]))
    p = Policy(mode=meta["mode"], hops=meta["hops"], dim=meta["dim"], beam=meta["beam"], epochs=0,
               simple_paths=meta.get("simple_paths", False))
    p._init(Graph.from_deck(deck), [str(e) for e in z["ents"]], seed=0)
    p.rels = [str(r) for r in z["rels"]]
    p.ridx = {r: i for i, r in enumerate(p.rels)}
    p.ents = [str(e) for e in z["ents"]]
    p.eidx = {e: i for i, e in enumerate(p.ents)}
    p.R, p.E = z["R"], z["E"]
    p.known_chains = {r: {tuple(c) for c in cs} for r, cs in meta.get("chains", {}).items()}
    p.chain_prune = bool(meta.get("chain_prune", False))
    return p


# ---- the pipeline -----------------------------------------------------------------------
def ask(question: str, deck: Deck, policy: Policy | None, pulled: list[int] | None = None,
        threshold: float = JAM_THRESHOLD) -> Trace:
    pulled = pulled or []
    lines = {int(c.text[72:80]): c.text for c in deck.cards}
    facts_by_seq = {f.sequence: f for f in deck.facts()}
    masked: set[tuple[str, str, str]] = set()
    for s in pulled:
        f = facts_by_seq.get(s)
        if f:
            masked.add(f.triple())
            masked.add((f.object, INVERSE[f.relation], f.subject))
    pulled_str = [f"{s:08d}" for s in pulled]

    p = parse(question, deck.entities())
    if p.ambiguous:
        names = ", ".join((p.entity,) + p.ambiguous)
        return Trace(question, "no_cards", None, p.relation, None, [], None, pulled_str,
                     f"NO CARDS, NO ANSWER. AMBIGUOUS: the question names {names}. Ask about one entity at a time.", None)
    if not p.ok:
        return Trace(question, "no_cards", p.entity, p.relation, None, [], None, pulled_str,
                     narrate_no_cards(p.entity, p.relation), None)

    direct = [f for f in deck.find(subject=p.entity, relation=p.relation) if f.triple() not in masked]
    if direct:
        f = direct[0]
        return Trace(question, "answered", p.entity, p.relation, f.object, [card_dict(f, lines, 1.0)], 1.0,
                     pulled_str, narrate_answer(question, p.entity, p.relation, f.object, [f]), "direct")

    if policy is None:
        return Trace(question, "no_cards", p.entity, p.relation, None, [], None, pulled_str,
                     narrate_no_cards(p.entity, p.relation), None)

    if masked:
        policy.g = Graph([f for f in deck.facts() if f.triple() not in masked])
    else:
        policy.g = Graph.from_deck(deck)
    res = policy.walk(p.entity, p.relation)
    if res.answer is None or not res.path:
        return Trace(question, "no_cards", p.entity, p.relation, None, [], None, pulled_str,
                     narrate_no_cards(p.entity, p.relation), "walk")
    conf = float(np.exp(res.log_prob))
    cards = [card_dict(f, lines, pr) for f, pr in zip(res.path, res.step_probs)]
    chain = tuple(f.relation for f in res.path)
    if conf < threshold:
        return Trace(question, "jam", p.entity, p.relation, None, cards, conf, pulled_str,
                     narrate_jam(p.entity, p.relation, res.path, reason="low confidence"), "walk")
    if not policy.chain_known(p.relation, chain):
        # Product rule: a path shape that never explained this relation during training is not
        # an answer. The cards are still shown — that is the receipt for "I don't know".
        return Trace(question, "jam", p.entity, p.relation, None, cards, conf, pulled_str,
                     narrate_jam(p.entity, p.relation, res.path, reason="unknown path shape " + " -> ".join(chain)), "walk")
    return Trace(question, "answered", p.entity, p.relation, res.answer, cards, conf, pulled_str,
                 narrate_answer(question, p.entity, p.relation, res.answer, res.path, direct=False), "walk")
