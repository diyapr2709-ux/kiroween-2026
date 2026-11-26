"""The arena statistics script must not be fooled by pooling seeds."""
import csv
import random
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
STATS = REPO / "docs" / "arena" / "checks" / "stats.py"


def write_csv(path: Path, rows) -> None:
    with path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["seed", "query", "policy", "baseline"])
        w.writerows(rows)


def run(path: Path) -> tuple[int, str]:
    r = subprocess.run([sys.executable, "-I", str(STATS), str(path), "--system", "policy", "--baselines", "baseline",
                        "--alpha", "0.025", "--boot", "500", "--seed", "0"], capture_output=True, text=True)
    return r.returncode, r.stdout


def test_identical_rows_across_seeds_do_not_inflate_significance(tmp_path: Path) -> None:
    """A borderline single-seed effect copied to 3 seeds must stay borderline (no pooling)."""
    rng = random.Random(0)
    rows = []
    base = {f"f0-{i:08d}-fwd": (int(rng.random() < 0.08), int(rng.random() < 0.05)) for i in range(120)}
    for seed in range(3):
        for q, (p, b) in base.items():
            rows.append([seed, q, p, b])
    rc, out = run(tmp_path / "a.csv")
    write_csv(tmp_path / "a.csv", rows)
    rc, out = run(tmp_path / "a.csv")
    assert "seed 0:" in out and "seed 1:" in out and "seed 2:" in out
    p_lines = [l for l in out.splitlines() if l.startswith("McNemar exact, seed")]
    ps = {float(l.split("p=")[1].split()[0]) for l in p_lines}
    assert len(ps) == 1  # identical seeds -> identical per-seed tests, not a pooled n=360 test


def test_clear_effect_passes_and_null_effect_fails(tmp_path: Path) -> None:
    rng = random.Random(1)
    good = [[s, f"f0-{i:08d}-{d}", int(rng.random() < 0.6), int(rng.random() < 0.1)]
            for s in range(3) for i in range(100) for d in ("fwd", "inv")]
    write_csv(tmp_path / "good.csv", good)
    rc, out = run(tmp_path / "good.csv")
    assert rc == 0 and "EXIT CRITERION: PASS" in out
    null = [[s, f"f0-{i:08d}-{d}", int(rng.random() < 0.2), int(rng.random() < 0.2)]
            for s in range(3) for i in range(100) for d in ("fwd", "inv")]
    write_csv(tmp_path / "null.csv", null)
    rc, out = run(tmp_path / "null.csv")
    assert rc == 1 and "EXIT CRITERION: FAIL" in out
