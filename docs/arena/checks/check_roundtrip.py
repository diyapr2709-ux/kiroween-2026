"""Loop 1 validation: encode->decode round trip, run independently of the app's own tests.

Two targets, both exercised with the same generated cases:
  1. this directory's reference table (`ibm029_ref`) — must be perfect, or the reference is wrong;
  2. the app encoder in `src/hollerith/`, if importable — every case must round-trip AND every
     character's hole pattern must equal the reference pattern.

Usage (from the repo root):
  uv run --with hypothesis python -I docs/arena/checks/check_roundtrip.py --cases 20000 --seed 7
"""
from __future__ import annotations

import argparse
import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ibm029_ref as ref  # noqa: E402

from hypothesis import HealthCheck, given, settings, strategies as st  # noqa: E402

ALPHA = ref.ALPHABET
INVALID = ["a\tb", "\x00", "café", "⌑", "~", "^", "`", "{", "}", "[", "]", "\\", "x" * 81]


def load_kiro():
    """Return (encode, decode, error_type) from the app package, or None if not present."""
    sys.path.insert(0, str(Path.cwd() / "src"))
    try:
        mod = importlib.import_module("hollerith.hollerith_code")
    except ModuleNotFoundError:
        return None
    err = getattr(mod, "CardEncodingError", Exception)
    return mod.encode, mod.decode, err


def to_matrix(card) -> list[list[bool]]:
    """Normalise whatever the app returns into a 12x80 list of bools."""
    if hasattr(card, "holes"):
        card = card.holes
    if hasattr(card, "tolist"):
        card = card.tolist()
    return [[bool(x) for x in row] for row in card]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", type=int, default=10_000)
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()

    failures: list[str] = []
    kiro = load_kiro()
    print(f"reference alphabet: {len(ALPHA)} chars; app encoder: {'found' if kiro else 'NOT FOUND (reference only)'}")

    @settings(max_examples=args.cases, deadline=None, derandomize=False, database=None,
              suppress_health_check=list(HealthCheck))
    @given(st.text(alphabet=ALPHA, min_size=0, max_size=80))
    def prop(s: str) -> None:
        m = ref.encode(s)
        back = ref.decode(m)
        if back != s.rstrip(" "):
            failures.append(f"REF round-trip failed: {s!r} -> {back!r}")
        if kiro:
            k_enc, k_dec, _ = kiro
            km = to_matrix(k_enc(s))
            if km != m:
                failures.append(f"APP hole pattern differs from reference for {s!r}")
            kb = k_dec(k_enc(s))
            if kb.rstrip(" ") != s.rstrip(" "):
                failures.append(f"APP round-trip failed: {s!r} -> {kb!r}")

    import random
    random.seed(args.seed)
    prop()

    # Explicit edge cases.
    for s in ["", " " * 80, ALPHA[:80], ref.ASCII_ALPHABET[:80], "HOLLERITH" + " " * 71]:
        if ref.decode(ref.encode(s)) != s.rstrip(" "):
            failures.append(f"REF edge case failed: {s!r}")
    # Lower-case must be accepted and upper-cased by the reference.
    if ref.decode(ref.encode("hollerith")) != "HOLLERITH":
        failures.append("REF did not upper-case lowercase input")
    # Invalid input must be rejected.
    for s in INVALID:
        try:
            ref.encode(s)
            failures.append(f"REF accepted invalid input {s!r}")
        except ValueError:
            pass
        if kiro:
            k_enc, _, k_err = kiro
            try:
                k_enc(s)
                failures.append(f"APP accepted invalid input {s!r}")
            except k_err:
                pass
            except Exception as e:  # wrong exception type is a minor finding
                failures.append(f"APP rejected {s!r} with {type(e).__name__}, not CardEncodingError")

    if kiro:
        k_enc, _, _ = kiro
        for ch in ALPHA:
            km = to_matrix(k_enc(ch))
            if km != ref.encode(ch):
                failures.append(f"APP code table differs from reference at {ch!r}")

    uniq = sorted(set(failures))
    print(f"generated cases: {args.cases}; failures: {len(uniq)}")
    for f in uniq[:40]:
        print("  FAIL", f)
    return 1 if uniq else 0


if __name__ == "__main__":
    raise SystemExit(main())
