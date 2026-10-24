import json
import sys

import pytest

from aruz import cli, strings

TASK = "Haddeden gecmis nezaket yal u bal olmus sana"
FUZULI = "Beni candan usandırdı cefâdan yâr usanmaz mı"


def run(monkeypatch, capsys, *args):
    monkeypatch.setattr(sys, "argv", ["aruz", *args])
    cli.main()
    return capsys.readouterr().out


def test_plain_scan_has_no_explanations(monkeypatch, capsys):
    out = run(monkeypatch, capsys, FUZULI)
    assert "Mefâîlün" in out
    assert strings.TR["REASON_NAMES"]["open_short_vowel"] not in out
    assert strings.TR["REPAIR_LABEL"] not in out


def test_explain_lists_reasons(monkeypatch, capsys):
    out = run(monkeypatch, capsys, "--explain", FUZULI)
    assert strings.TR["REASON_NAMES"]["final_syllable_rule"] in out
    assert strings.TR["REASON_NAMES"]["imale"] in out
    assert strings.TR["REASON_NAMES"]["ulama"] in out
    assert "“mı” ünlüyle bittiği için" in out


def test_repair_prints_the_restored_line(monkeypatch, capsys):
    out = run(monkeypatch, capsys, "--repair", TASK)
    assert strings.TR["REPAIR_LABEL"] in out
    assert out.index("nezâket") < out.index(strings.TR["METER"])
    assert "Fâilâtün" in out


def test_json_with_repair(monkeypatch, capsys):
    data = json.loads(run(monkeypatch, capsys, "--json", "--repair", TASK))
    assert data["repair"]["text"] == "Haddeden geçmiş nezâket yâl ü bâl olmuş sana"
    assert data["beyits"][0]["misras"][0]["fit"]["syllables"]


def test_json_without_repair(monkeypatch, capsys):
    data = json.loads(run(monkeypatch, capsys, "--json", FUZULI))
    assert "repair" not in data


def test_empty_input_exits(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["aruz", "   "])
    with pytest.raises(SystemExit) as stop:
        cli.main()
    assert stop.value.code == strings.TR["EMPTY"]
