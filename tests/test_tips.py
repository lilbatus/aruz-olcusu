import math

import pytest

from aruz import strings
from aruz.poem import Candidate, scan
from aruz.readings import penalties
from aruz.report import alternative_tip, number, poem_dict, tips_dict

FUZULI = "Beni candan usandırdı cefâdan yâr usanmaz mı\nFelekler yandı âhımdan murâdım şem'i yanmaz mı"


def test_tips_exist_in_both_languages():
    tips = poem_dict(scan(FUZULI))["tips"]
    assert set(tips) == {"tr", "en"}
    for lang in tips:
        assert set(tips[lang]) == {"penalty", "confidence", "meter", "alternatives"}
        for tip in [tips[lang]["penalty"], tips[lang]["confidence"], tips[lang]["meter"], *tips[lang]["alternatives"]]:
            assert tip["name"] and tip["text"]
            assert "{" not in tip["text"] and "}" not in tip["text"]


def test_penalty_tip_matches_the_code():
    tips = tips_dict(scan(FUZULI))
    assert tips["tr"]["penalty"]["text"] == (
        "Her mısranın bu vezindeki en ucuz okumasının cezaları toplanır: imâle 0,6–1,6; zihaf 2,5–4; "
        "kalıba hiç oturmayan mısra 8 puan. Bu sonuçta: imâle ×2, ulama ×1."
    )
    assert tips["en"]["penalty"]["text"].endswith("In this result: imâle ×2, ulama ×1.")
    w = penalties()
    text = tips["en"]["penalty"]["text"]
    assert f"{number(min(w['imale_word_final'], w['imale'], w['imale_foreign']), 'en')}–" in text
    assert f"{number(w['unmatched'], 'en')} points" in text


def test_penalty_tip_counts_unmatched_misras():
    poem = scan("Bu şehr-i Sıtanbul ki bî-misl ü bahâdır\nBir sengine yek-pâre Acem mülkü fedâdır")
    assert sum(fit is None for fit in poem.best.fits) == 1
    assert tips_dict(poem)["tr"]["penalty"]["text"].endswith("Bu sonuçta: kalıba oturmayan mısra ×1.")


def test_penalty_tip_without_licenses():
    tips = tips_dict(scan("Felekler yandı âhımdan murâdım şem'i yanmaz mı"))
    assert tips["tr"]["penalty"]["text"].endswith("Bu sonuçta: hiç ruhsat yok.")
    assert tips["en"]["penalty"]["text"].endswith("In this result: no licenses.")


def test_confidence_tip_matches_the_code():
    poem = scan(FUZULI)
    averages = [candidate.cost / len(poem.best.fits) for candidate in poem.candidates[:3]]
    factor = math.exp(1 / penalties()["confidence_temperature"])
    text = tips_dict(poem)["en"]["confidence"]["text"]
    assert f"about {number(factor, 'en', 1)} times" in text
    expected = [number(round(value, 1), "en") for value in averages]
    assert text.endswith(f"averages {expected[0]} and its rivals {expected[1]} and {expected[2]}.")


def test_meter_tip_counts_fitting_misras():
    tips = tips_dict(scan(FUZULI))
    assert tips["tr"]["meter"]["text"].endswith("Burada 2/2 mısra bu kalıba oturuyor.")
    assert tips["en"]["meter"]["text"].endswith("Here 2 of 2 mısras fit its pattern.")


def test_alternative_tips():
    poem = scan("Gamdan öldüm demedüm hâl-i dil-i zârı sana\nEy gül-i tâze revâ görmedüm âzârı sana")
    first = poem.alternatives[0]
    tip = alternative_tip(poem, first, "tr")
    assert tip["name"] == first.meter.name
    assert tip["text"] == strings.TR["ALT_FITS"].format(diff=number(round(first.cost - poem.best.cost, 2), "tr"))
    unmatched = scan(FUZULI)
    tip = alternative_tip(unmatched, unmatched.alternatives[0], "en")
    assert tip["text"].endswith("2 of 2 mısras do not fit this pattern at all.")


@pytest.mark.parametrize("lang", ["tr", "en"])
def test_alternative_tie(lang):
    poem = scan(FUZULI)
    twin = Candidate(poem.alternatives[0].meter, poem.best.cost, poem.best.fits)
    assert alternative_tip(poem, twin, lang)["text"] == strings.LANGUAGES[lang]["ALT_TIE"]


def test_numbers_follow_the_language():
    assert number(1.2, "tr") == "1,2"
    assert number(1.2, "en") == "1.2"
    assert number(99.94, "tr", 1) == "99,9"
    assert number(16.0, "en") == "16"
