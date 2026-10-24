import json
import re

from fastapi.testclient import TestClient

from aruz import strings
from aruz.web.app import app

client = TestClient(app)


def test_page_has_turkish_strings_and_no_placeholders():
    html = client.get("/").text
    assert strings.TR["WEB_BUTTON"] in html
    assert "__" not in html.replace("__proto__", "")


def test_scan_endpoint():
    response = client.post("/api/scan", json={"text": "Beni candan usandırdı cefâdan yâr usanmaz mı"})
    assert response.status_code == 200
    report = response.json()
    assert report["meter"]["id"] == "hezec-8-salim"
    misra = report["beyits"][0]["misras"][0]
    assert [f["name"] for f in misra["fit"]["feet"]] == ["Mefâîlün"] * 4
    assert {lic["kind"] for lic in misra["fit"]["licenses"]} == {"imale", "ulama"}
    assert len(report["alternatives"]) == 2


def test_page_has_a_single_tooltip_element():
    html = client.get("/").text
    assert html.count('id="tip"') == 1
    assert 'role="tooltip"' in html


def test_scan_carries_tooltip_texts():
    report = client.post("/api/scan", json={"text": "Beni candan usandırdı cefâdan yâr usanmaz mı"}).json()
    fit = report["beyits"][0]["misras"][0]["fit"]
    assert all(u["syllable"] >= 1 for foot in fit["feet"] for u in foot["units"])
    assert all(r["name"] and r["text"] for s in fit["syllables"] for r in s["reasons"])
    assert {lic["tip"]["name"] for lic in fit["licenses"]} == {"imâle", "ulama"}


TASK = "Haddeden gecmis nezaket yal u bal olmus sana"


def test_page_has_the_repair_switch():
    html = client.get("/").text
    assert 'id="repair"' in html and 'role="switch"' in html
    assert strings.TR["WEB_REPAIR"] in html
    assert strings.TR["REPAIR_LABEL"] in html


def test_scan_without_repair_has_no_repair_block():
    report = client.post("/api/scan", json={"text": TASK}).json()
    assert "repair" not in report
    assert set(report) == {"meter", "confidence", "alternatives", "beyits", "tips"}


def test_scan_with_repair():
    report = client.post("/api/scan", json={"text": TASK, "repair": True}).json()
    repair = report["repair"]
    assert repair["text"] == "Haddeden geçmiş nezâket yâl ü bâl olmuş sana"
    assert "".join(segment["text"] for segment in repair["segments"]) == repair["text"]
    assert report["beyits"][0]["misras"][0]["text"] == repair["text"]
    word = next(w for w in repair["words"] if w["index"] == 2)
    assert word["original"] == "nezaket"
    assert word["restored"] == "nezâket"
    assert word["changed"] == [3]
    assert word["by_meter"]
    assert word["tips"][0]["name"] == strings.TR["REPAIR_NAME"]


def test_choices_cycle_a_word():
    first = client.post("/api/scan", json={"text": TASK, "repair": True}).json()
    word = next(w for w in first["repair"]["words"] if w["index"] == 2)
    other = (word["choice"] + 1) % len(word["candidates"])
    second = client.post("/api/scan", json={"text": TASK, "repair": True, "choices": {"2": other}}).json()
    chosen = next(w for w in second["repair"]["words"] if w["index"] == 2)
    assert chosen["restored"] == word["candidates"][other]
    assert chosen["by_user"]


def test_page_carries_both_languages():
    html = client.get("/").text
    data = json.loads(re.search(r'<script id="strings" type="application/json">(.*?)</script>', html, re.S).group(1))
    assert set(data) == {"tr", "en"}
    assert data["en"]["WEB_BUTTON"] == strings.EN["WEB_BUTTON"]
    assert set(data["tr"]) == set(data["en"])
    assert 'data-lang="tr"' in html and 'data-lang="en"' in html


def test_scan_carries_english_texts():
    report = client.post("/api/scan", json={"text": "Beni candan usandırdı cefâdan yâr usanmaz mı"}).json()
    fit = report["beyits"][0]["misras"][0]["fit"]
    reason = fit["syllables"][1]["reasons"][1]
    assert reason["i18n"]["en"]["name"] == "imâle"
    assert reason["i18n"]["tr"]["text"] == reason["text"]
    lic = fit["licenses"][0]
    assert lic["i18n"]["en"]["tip"]["text"]
    assert lic["i18n"]["tr"]["name"] == lic["name"]


def test_scan_rejects_empty_text():
    response = client.post("/api/scan", json={"text": "   "})
    assert response.status_code == 400
    assert response.json()["detail"] == strings.TR["EMPTY"]
