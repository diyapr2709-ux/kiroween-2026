"""Loop 3 validation: the narrator may name only entities on the path and may cite only
cards on the path. Deterministic — no LLM judge.

Trace JSON (one file per question, or a JSON list), the schema Kiro's CLI must emit:
{
  "question": "...",
  "status": "answered" | "jam" | "no_cards",
  "path": [{"seq": "00000012", "subject": "HOLLERITH", "relation": "FOUNDED", "object": "TABULATING MACHINE CO"}, ...],
  "answer": "IBM",
  "narration": "... [00000012] ..."
}
Entity vocabulary comes from the deck so that mentions of ANY known entity off the path are caught.

Usage:  python -I docs/arena/checks/check_faithfulness.py traces/*.json --deck data/cards.deck
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def deck_entities(deck: Path) -> set[str]:
    ents = set()
    for line in deck.read_text(encoding="utf-8").splitlines():
        if len(line) == 80:
            ents.add(line[0:20].rstrip())
            ents.add(line[35:55].rstrip())
    ents.discard("")
    return ents


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("traces", nargs="+")
    ap.add_argument("--deck", required=True)
    ap.add_argument("--threshold", type=float, default=0.95)
    args = ap.parse_args()
    vocab = deck_entities(Path(args.deck))

    traces = []
    for t in args.traces:
        data = json.loads(Path(t).read_text(encoding="utf-8"))
        traces.extend(data if isinstance(data, list) else [data])

    faithful = 0
    total = 0
    for tr in traces:
        if tr.get("status") != "answered":
            continue  # jams and NO CARDS have no narration to check; counted separately
        total += 1
        path = tr.get("path", [])
        on_path = {c["subject"] for c in path} | {c["object"] for c in path}
        seqs = {c["seq"] for c in path}
        text = tr.get("narration", "").upper()
        problems = []
        # Blank out on-path entity names (longest first) so that a city named inside a longer
        # on-path entity ("MANCHESTER" in "MANCHESTER MARK 1") is not a false positive.
        scrubbed = text
        for e in sorted(on_path, key=len, reverse=True):
            scrubbed = re.sub(r"(?<![A-Z0-9])" + re.escape(e) + r"(?![A-Z0-9])", " ", scrubbed)
        for e in sorted(vocab - on_path, key=len, reverse=True):
            if re.search(r"(?<![A-Z0-9])" + re.escape(e) + r"(?![A-Z0-9])", scrubbed):
                problems.append(f"names off-path entity {e!r}")
        for cited in re.findall(r"\[(\d{8})\]", text):
            if cited not in seqs:
                problems.append(f"cites card {cited} not on path")
        if not re.findall(r"\[(\d{8})\]", text):
            problems.append("cites no card at all")
        if tr.get("answer") and tr["answer"] not in on_path:
            problems.append(f"answer {tr['answer']!r} is not on the path")
        if problems:
            print(f"UNFAITHFUL  {tr.get('question','?')[:60]!r}")
            for p in problems:
                print("    ", p)
        else:
            faithful += 1

    n_jam = sum(1 for t in traces if t.get("status") == "jam")
    n_none = sum(1 for t in traces if t.get("status") == "no_cards")
    rate = faithful / total if total else 0.0
    print(f"answered: {total}  faithful: {faithful}  rate: {rate:.3f}  jams: {n_jam}  no_cards: {n_none}")
    ok = total >= 50 and rate >= args.threshold
    print("FAITHFULNESS:", "PASS" if ok else f"FAIL (need ≥50 answered and rate ≥ {args.threshold})")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
