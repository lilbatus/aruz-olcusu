import tomllib
from pathlib import Path

from aruz.explain import CODES, Reason, reasons
from aruz.match import fit
from aruz.meters import Pattern, meters
from aruz.poem import scan
from aruz.readings import penalties, readings
from aruz.report import poem_dict

FUZULI = "Beni candan usandırdı cefâdan yâr usanmaz mı"


def first_fit(text):
    return scan(text).best.fits[0]


def at(items, position):
    return items[position - 1]


def codes(items, position):
    return [r.code for r in at(items, position)]


def test_basic_codes_on_fuzuli():
    items = reasons(first_fit(FUZULI))
    assert at(items, 1) == [Reason("open_short_vowel", "be", "beni", 1, None, ".")]
    assert at(items, 3) == [Reason("closed_consonant", "can", "candan", 3, None, "-")]
    assert at(items, 10) == [Reason("long_vowel", "fâ", "cefâdan", 10, None, "-")]


def test_imale_follows_the_base_reason():
    items = reasons(first_fit(FUZULI))
    assert at(items, 2) == [
        Reason("open_short_vowel", "ni", "beni", 2, None, "."),
        Reason("imale", "ni", "beni", 2, ".", "-"),
    ]
    assert codes(items, 8) == ["open_short_vowel", "imale"]


def test_ulama_comes_first_and_names_the_join():
    items = reasons(first_fit(FUZULI))
    assert at(items, 12) == [
        Reason("ulama", "yâ", "yâr", 12, "-", "-", "yâ-ru"),
        Reason("long_vowel", "yâ", "yâr", 12, None, "-"),
    ]


def test_ulama_can_open_a_short_syllable():
    items = reasons(first_fit("Gamdan öldüm demedüm hâl-i dil-i zârı sana"))
    assert at(items, 2)[0] == Reason("ulama", "da", "gamdan", 2, "-", ".", "da-nöl")


def test_final_syllable_rule():
    items = reasons(first_fit("Gamdan öldüm demedüm hâl-i dil-i zârı sana"))
    assert at(items, 15) == [Reason("final_syllable_rule", "na", "sana", 15, ".", "-")]


def test_final_closed_syllable_keeps_its_own_reason():
    items = reasons(first_fit("Dem-â-dem cevrlerdür çekdügüm bî-rahm bütlerden"))
    assert codes(items, 14) == ["closed_consonant"]


def test_med_two_consonants():
    items = reasons(first_fit("Dem-â-dem cevrlerdür çekdügüm bî-rahm bütlerden"))
    assert at(items, 4) == [Reason("med", "cevr", "cevrlerdür", 4, "-", "-.", "two_consonants")]


def test_med_skipped():
    reading = next(r for r in readings("yâr gelür") if len(r.units) == 3)
    result = fit(reading, Pattern(meters()[0], ("Fâilün",), ("-.-",)), penalties())
    items = reasons(result)
    assert at(items, 1) == [Reason("med_skipped", "yâr", "yâr", 1, "-.", "-", "long_vowel")]


def test_long_vowel_and_n_reads_as_closed():
    items = reasons(first_fit("Ten-i mecrûha cândan câna cânândan haber verdün"))
    assert codes(items, 6) == ["closed_consonant"]
    assert codes(items, 11) == ["closed_consonant"]


def test_izafet():
    items = reasons(first_fit("Ten-i mecrûha cândan câna cânândan haber verdün"))
    assert at(items, 2) == [Reason("izafet", "ni", "i", 2, ".", "-")]


def test_conjunction():
    items = reasons(first_fit("Perîşân halk-ı âlem âh u efgân etdügümdendür"))
    assert at(items, 9) == [Reason("conjunction", "hu", "u", 9, ".", ".")]


def test_zihaf():
    reading = readings("tan tan tan")[0]
    result = fit(reading, Pattern(meters()[0], ("X",), ("-.-",)), penalties())
    items = reasons(result)
    assert at(items, 2) == [
        Reason("closed_consonant", "tan", "tan", 2, None, "-"),
        Reason("zihaf", "tan", "tan", 2, "-", "."),
    ]


def test_every_syllable_has_a_reason_and_every_license_is_explained():
    corpus = tomllib.loads((Path(__file__).parent / "data" / "corpus.toml").read_text("utf-8"))
    seen = set()
    for item in corpus["beyit"]:
        for result in scan("\n".join(item["lines"])).best.fits:
            if result is None:
                continue
            items = reasons(result)
            assert len(items) == len(result.reading.syllables)
            assert all(items)
            for lic in result.licenses:
                assert lic.kind in {r.code for r in items[lic.syllable]}
            seen.update(r.code for group in items for r in group)
    seen.update({"med_skipped", "zihaf"})
    assert seen == set(CODES)


def test_report_adds_reasons_without_touching_existing_fields():
    report = poem_dict(scan(FUZULI))
    result = report["beyits"][0]["misras"][0]["fit"]
    assert set(result) == {"pattern", "penalty", "feet", "licenses", "syllables"}
    unit = result["feet"][0]["units"][1]
    assert set(unit) == {"text", "mark", "license", "tail", "syllable"}
    assert unit["syllable"] == 2
    syllable = result["syllables"][1]
    assert syllable["position"] == 2
    assert syllable["text"] == "ni"
    assert syllable["word"] == "beni"
    assert syllable["mark"] == "-"
    assert [r["code"] for r in syllable["reasons"]] == ["open_short_vowel", "imale"]
    reason = dict(syllable["reasons"][1])
    translations = reason.pop("i18n")
    assert reason == {
        "code": "imale", "syllable": "ni", "word": "beni", "position": 2,
        "before": ".", "after": "-", "detail": "",
        "name": "imâle",
        "text": "“ni” normalde açıktır (.), ama vezin burada kapalı (-) bir hece istiyor. Kısa hece uzatılarak okunur.",
    }
    assert translations["tr"] == {"name": reason["name"], "text": reason["text"]}
    assert translations["en"]["name"] == "imâle"
    assert translations["en"]["text"].startswith("“ni” is normally open (.)")


def test_med_tail_units_point_to_the_same_syllable():
    report = poem_dict(scan("Dem-â-dem cevrlerdür çekdügüm bî-rahm bütlerden"))
    units = [u for foot in report["beyits"][0]["misras"][0]["fit"]["feet"] for u in foot["units"]]
    tails = [u for u in units if u["tail"]]
    assert tails
    assert all(u["syllable"] in {4, 11} for u in tails)
