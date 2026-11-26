"""CLI exit codes and output — the save hooks depend on these."""
from pathlib import Path

import pytest

from hollerith import Deck
from hollerith.cli import main


@pytest.fixture
def deck_path(tmp_path: Path) -> Path:
    d = Deck()
    d.punch("HERMAN HOLLERITH", "FOUNDED", "TABULATING MACH CO", "WIKI")
    d.punch("TABULATING MACH CO", "MERGED INTO", "CTR", "IBMARCH")
    p = tmp_path / "cards.deck"
    d.save(p)
    return p


def test_lint_clean_exits_0(deck_path: Path, capsys) -> None:
    assert main(["lint", str(deck_path)]) == 0
    assert "deck is clean" in capsys.readouterr().out


def test_lint_problem_exits_1(deck_path: Path, capsys) -> None:
    raw = bytearray(deck_path.read_bytes())
    raw[63] = ord("X")  # column 64 of card 1 is reserved and must be blank
    deck_path.write_bytes(bytes(raw))
    assert main(["lint", str(deck_path)]) == 1
    out = capsys.readouterr().out
    assert "line 1: columns 64-72 must be blank" in out and "1 problem(s)" in out


def test_lint_truncated_card_cascades_to_its_pair(deck_path: Path, capsys) -> None:
    deck_path.write_bytes(deck_path.read_bytes()[:-2] + b"\n")  # last card now 79 columns
    assert main(["lint", str(deck_path)]) == 1
    out = capsys.readouterr().out
    assert "79 characters" in out and "missing inverse" in out and "3 problem(s)" in out


def test_lint_missing_file_exits_2(tmp_path: Path, capsys) -> None:
    assert main(["lint", str(tmp_path / "nope.deck")]) == 2
    assert "error:" in capsys.readouterr().err


def test_neighbours_prints_cards_in_sequence_order(deck_path: Path, capsys) -> None:
    assert main(["neighbours", "tabulating mach co", "--deck", str(deck_path)]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines[0].startswith("[00000002] TABULATING MACH CO --FOUNDED BY-->")
    assert lines[1].startswith("[00000003] TABULATING MACH CO --MERGED INTO-->")


def test_neighbours_unknown_entity_is_no_cards_exit_1(deck_path: Path, capsys) -> None:
    assert main(["neighbours", "ADA LOVELACE", "--deck", str(deck_path)]) == 1
    assert capsys.readouterr().out.strip() == "NO CARDS"


def test_punch_appends_two_cards_and_prints_them(deck_path: Path, capsys) -> None:
    assert main(["punch", "CTR", "RENAMED TO", "IBM", "IBMARCH", "--deck", str(deck_path)]) == 0
    out = capsys.readouterr().out.splitlines()
    assert len(out) == 2 and out[0].endswith("00000005") and out[1].endswith("00000006")
    assert len(Deck.load(deck_path)) == 6


def test_punch_bad_relation_exits_1_and_leaves_deck_unchanged(deck_path: Path, capsys) -> None:
    before = deck_path.read_bytes()
    assert main(["punch", "CTR", "KNOWS", "IBM", "WIKI", "--deck", str(deck_path)]) == 1
    assert "error:" in capsys.readouterr().err
    assert deck_path.read_bytes() == before


def test_show_prints_holes_and_fields(deck_path: Path, capsys) -> None:
    assert main(["show", "1", "--deck", str(deck_path)]) == 0
    out = capsys.readouterr().out
    assert out.splitlines()[0].startswith("HERMAN HOLLERITH")
    assert "12 " in out and "subject   cols  1-20: 'HERMAN HOLLERITH'" in out


def test_show_missing_sequence_exits_1(deck_path: Path) -> None:
    assert main(["show", "99", "--deck", str(deck_path)]) == 1


def test_decode_uppercases_and_rejects(capsys) -> None:
    assert main(["decode", "hollerith"]) == 0
    assert capsys.readouterr().out.startswith("HOLLERITH")
    assert main(["decode", "a" * 80]) == 0
    assert main(["decode", "a" * 81]) == 1
    assert main(["decode", "café"]) == 1


def test_corrupt_deck_exits_2(tmp_path: Path, capsys) -> None:
    p = tmp_path / "bad.deck"
    p.write_text("HERMAN HOLLERITH".ljust(72) + "ABCDEFGH\n")
    assert main(["neighbours", "HERMAN HOLLERITH", "--deck", str(p)]) == 2
    assert "sequence" in capsys.readouterr().err
