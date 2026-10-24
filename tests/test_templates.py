import pytest

from aruz import strings
from aruz.explain import CODES, Reason, describe, describe_spot, reasons
from aruz.poem import scan
from aruz.repair import Form, Spot
from aruz.report import poem_dict

SAMPLES = {
    "open_short_vowel": Reason("open_short_vowel", "be", "beni", 1, None, "."),
    "closed_consonant": Reason("closed_consonant", "can", "candan", 3, None, "-"),
    "long_vowel": Reason("long_vowel", "fâ", "cefâdan", 10, None, "-"),
    "final_syllable_rule": Reason("final_syllable_rule", "na", "sana", 15, ".", "-"),
    "med": Reason("med", "aşk", "aşk", 1, "-", "-.", "two_consonants"),
    "med_skipped": Reason("med_skipped", "yâr", "yâr", 1, "-.", "-", "long_vowel"),
    "izafet": Reason("izafet", "ni", "i", 2, ".", "-"),
    "conjunction": Reason("conjunction", "hu", "u", 9, ".", "."),
    "ulama": Reason("ulama", "yâ", "yâr", 12, "-", "-", "yâ-ru"),
    "imale": Reason("imale", "ni", "beni", 2, ".", "-"),
    "zihaf": Reason("zihaf", "tan", "tan", 2, "-", "."),
}


def test_every_code_has_a_name_and_a_template():
    assert set(strings.TR["REASON_NAMES"]) == set(CODES)
    assert set(strings.TR["REASON_TEXTS"]) == set(CODES)
    assert set(SAMPLES) == set(CODES)


@pytest.mark.parametrize("code", CODES)
def test_template_fills_completely(code):
    reason = SAMPLES[code]
    tip = describe(reason)
    assert tip["name"] == strings.TR["REASON_NAMES"][code]
    assert "{" not in tip["text"] and "}" not in tip["text"]
    assert reason.syllable in tip["text"] or reason.word in tip["text"] or code == "med"
    assert len(tip["text"].split(". ")) <= 3


def test_final_syllable_example():
    assert describe(SAMPLES["final_syllable_rule"])["text"] == (
        "“na” ünlüyle bittiği için normalde açıktır (.), ama mısranın son hecesi. "
        "Aruzda son hece her zaman kapalı (-) sayılır."
    )


def test_med_example_for_two_consonants():
    assert describe(SAMPLES["med"])["text"] == (
        "İki ünsüzle biten heceler (aşk, meşk, çeşm) aruzda bir buçuk hece sayılır: kapalı + açık (- .)."
    )


def test_med_example_for_long_vowel():
    reason = Reason("med", "yâr", "yâr", 1, "-", "-.", "long_vowel")
    assert describe(reason)["text"].startswith("Uzun ünlüden sonra ünsüzle biten heceler (yâr")


def test_weight_names_cover_every_weight():
    for reason in SAMPLES.values():
        assert reason.after in strings.TR["WEIGHT_NAMES"]
        assert reason.before is None or reason.before in strings.TR["WEIGHT_NAMES"]
    assert set(strings.TR["MED_CAUSES"]) == {"two_consonants", "long_vowel"}


def test_izafet_template_names_the_chosen_weight():
    assert describe(SAMPLES["izafet"])["text"].endswith("Burada kapalı (-) sayıldı.")
    short = Reason("izafet", "li", "i", 9, ".", ".")
    assert describe(short)["text"].endswith("Burada açık (.) sayıldı.")


def test_ulama_template_shows_the_join():
    assert "(yâ-ru)" in describe(SAMPLES["ulama"])["text"]


def test_real_scan_fills_every_reason():
    poem = scan("Gamdan öldüm demedüm hâl-i dil-i zârı sana\nEy gül-i tâze revâ görmedüm âzârı sana")
    for result in poem.best.fits:
        for group in reasons(result):
            for reason in group:
                text = describe(reason)["text"]
                assert "{" not in text and text


@pytest.mark.parametrize("source", sorted(strings.TR["REPAIR_SOURCES"]))
def test_repair_tip_for_every_source(source):
    spot = Spot(0, 0, 0, 7, "nezaket", [Form("nezâket", 22), Form("nezaket", 131)], source)
    text = describe_spot(spot)[0]["text"]
    assert "{" not in text and "}" not in text
    assert "“nezaket” → “nezâket”." in text
    assert strings.TR["REPAIR_SOURCES"][source] in text
    assert "(1/2)" in text


@pytest.mark.parametrize("flags, sentence", [
    ({"by_user": True}, strings.TR["REPAIR_USER"]),
    ({"by_meter": True}, strings.TR["REPAIR_METER"]),
    ({"uncertain": True}, strings.TR["REPAIR_UNCERTAIN"]),
])
def test_repair_tip_explains_the_decision(flags, sentence):
    spot = Spot(0, 0, 0, 3, "yar", [Form("yâr", 420), Form("yar", 978)], "lexicon", **flags)
    assert sentence in describe_spot(spot)[0]["text"]


def test_repair_tip_for_an_untouched_word():
    spot = Spot(0, 0, 0, 3, "dil", [Form("dil", 10)], "lexicon")
    tip = describe_spot(spot)[0]
    assert tip["name"] == strings.TR["REPAIR_NAME"]
    assert tip["text"].startswith("“dil” olduğu gibi bırakıldı.")
    assert "/" not in tip["text"]


def test_report_carries_tooltip_texts():
    report = poem_dict(scan("Gamdan öldüm demedüm hâl-i dil-i zârı sana"))
    result = report["beyits"][0]["misras"][0]["fit"]
    last = result["syllables"][-1]["reasons"][0]
    assert last["code"] == "final_syllable_rule"
    assert last["name"] == "son hece"
    assert last["text"] == describe(SAMPLES["final_syllable_rule"])["text"]
    for lic in result["licenses"]:
        assert lic["tip"]["name"] == strings.TR["REASON_NAMES"][lic["kind"]]
        assert lic["tip"]["text"]
