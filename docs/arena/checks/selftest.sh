#!/usr/bin/env bash
# Self-test of the validation harness on synthetic inputs. Requires uv (for hypothesis).
set -euo pipefail
cd "$(dirname "$0")/../../.."
T="${TMPDIR:-/tmp}/hollerith-selftest"
rm -rf "$T"; mkdir -p "$T/splits" "$T/traces"

echo "== 1. reference table =="
python3 -I docs/arena/checks/ibm029_ref.py | head -1

echo "== 2. round trip (reference only, 3000 cases) =="
uv run --quiet --with hypothesis python -I docs/arena/checks/check_roundtrip.py --cases 3000 --seed 7

echo "== 3. deck lint on a good 4-card deck, then a broken one =="
python3 - "$T" <<'PY'
import sys
t = sys.argv[1]
def card(s, r, o, src, seq):
    return f"{s:<20}{r:<15}{o:<20}{src:<8}{'':9}{seq:08d}"
good = [
    card("HOLLERITH", "FOUNDED", "TABULATING MACH CO", "IBMARCH", 1),
    card("TABULATING MACH CO", "FOUNDED BY", "HOLLERITH", "IBMARCH", 2),
    card("TABULATING MACH CO", "RENAMED TO", "IBM", "CHM", 3),
    card("IBM", "RENAMED FROM", "TABULATING MACH CO", "CHM", 4),
]
open(f"{t}/good.deck", "w").write("\n".join(good) + "\n")
bad = good[:3] + [card("IBM", "RENAMED FROM", "TABULATING MACH CO", "WIKI?", 4)[:79] + "x"]
open(f"{t}/bad.deck", "w").write("\n".join(bad) + "\n")
PY
python3 -I docs/arena/checks/check_deck.py "$T/good.deck" --sources IBMARCH,CHM
if python3 -I docs/arena/checks/check_deck.py "$T/bad.deck" --sources IBMARCH,CHM >/dev/null; then
  echo "FAIL: broken deck passed"; exit 1; else echo "broken deck correctly rejected"; fi

echo "== 4. leakage gate: clean fold passes, leaky fold fails =="
printf '{"s":"A","r":"R","o":"B"}\n{"s":"B","r":"R","o":"C"}\n' > "$T/splits/fold0.train.jsonl"
printf '{"s":"C","r":"R","o":"D"}\n' > "$T/splits/fold0.test.jsonl"
python3 -I docs/arena/checks/check_leakage.py --train "$T/splits/fold0.train.jsonl" --test "$T/splits/fold0.test.jsonl"
printf '{"s":"B","r":"RINV","o":"A"}\n' > "$T/splits/fold1.test.jsonl"
cp "$T/splits/fold0.train.jsonl" "$T/splits/fold1.train.jsonl"
if python3 -I docs/arena/checks/check_leakage.py --train "$T/splits/fold1.train.jsonl" --test "$T/splits/fold1.test.jsonl" >/dev/null; then
  echo "FAIL: inverse leak not caught"; exit 1; else echo "inverse leak correctly caught"; fi

echo "== 5. stats on synthetic results (policy clearly better) =="
python3 - "$T" <<'PY'
import sys, random
t = sys.argv[1]; rng = random.Random(1)
with open(f"{t}/hits1.csv", "w") as f:
    f.write("seed,query,policy_rl,random_walk,frequency\n")
    for seed in range(3):
        for q in range(200):
            f.write(f"{seed},Q{q:03d},{int(rng.random()<0.55)},{int(rng.random()<0.15)},{int(rng.random()<0.30)}\n")
PY
python3 -I docs/arena/checks/stats.py "$T/hits1.csv" --system policy_rl --baselines random_walk,frequency --boot 2000

echo "== 6. faithfulness: 50 faithful traces pass, one unfaithful is reported =="
python3 - "$T" <<'PY'
import sys, json
t = sys.argv[1]
path = [{"seq":"00000001","subject":"HOLLERITH","relation":"FOUNDED","object":"TABULATING MACH CO"},
        {"seq":"00000003","subject":"TABULATING MACH CO","relation":"RENAMED TO","object":"IBM"}]
traces = [{"question":f"q{i}","status":"answered","path":path,"answer":"IBM",
           "narration":"HOLLERITH founded TABULATING MACH CO [00000001], later renamed IBM [00000003]."} for i in range(50)]
traces.append({"question":"bad","status":"answered","path":path,"answer":"IBM",
               "narration":"HOLLERITH and TURING built IBM [00000099]."})
traces.append({"question":"unknown","status":"no_cards","path":[],"answer":"","narration":""})
json.dump(traces, open(f"{t}/traces/all.json","w"))
PY
python3 -I docs/arena/checks/check_faithfulness.py "$T/traces/all.json" --deck "$T/good.deck" || true
echo "== selftest complete =="
