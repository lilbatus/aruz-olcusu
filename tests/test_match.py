import pytest

from aruz.match import best_fits, confidence
from aruz.meters import meters, patterns
from aruz.poem import scan

FUZULI = "Beni candan usandırdı cefâdan yâr usanmaz mı / Felekler yandı âhımdan murâdım şem'i yanmaz mı"


def test_every_meter_has_a_pattern():
    ids = {p.meter.id for p in patterns()}
    assert ids == {m.id for m in meters()}


def test_variants_expand():
    labels = {p.label for p in patterns() if p.meter.id == "remel-8-mahbun"}
    assert labels == {
        "Fe'ilâtün Fe'ilâtün Fe'ilâtün Fe'ilün",
        "Fe'ilâtün Fe'ilâtün Fe'ilâtün Fa'lün",
        "Fâilâtün Fe'ilâtün Fe'ilâtün Fe'ilün",
        "Fâilâtün Fe'ilâtün Fe'ilâtün Fa'lün",
    }


@pytest.mark.parametrize("meter", meters(), ids=lambda m: m.id)
def test_clean_pattern_matches_its_meter(meter):
    pattern = next(p for p in patterns() if p.meter == meter)
    syllables = {".": "ta", "-": "tan"}
    line = " ".join(syllables[w] for w in pattern.weights)
    fits = best_fits(line)
    assert fits[meter.id].cost == 0


def test_fuzuli_example():
    poem = scan(FUZULI)
    assert poem.best.meter.id == "hezec-8-salim"
    first = poem.best.fits[0]
    licenses = [(lic.kind, lic.text) for lic in first.licenses]
    assert ("imale", "ni") in licenses
    assert ("imale", "dı") in licenses
    assert ("ulama", "yâ-ru") in licenses
    assert poem.best.fits[1].cost == 0


def test_fuzuli_feet_alignment():
    first = scan(FUZULI).best.fits[0]
    feet = [[first.reading.syllables[u.syllable].text for u in units] for _, _, units in first.feet()]
    assert feet == [["be", "ni", "can", "dan"], ["u", "san", "dır", "dı"], ["ce", "fâ", "dan", "yâ"], ["ru", "san", "maz", "mı"]]


def test_alternatives_and_confidence():
    poem = scan(FUZULI)
    assert len(poem.alternatives) == 2
    assert all(a.cost >= poem.best.cost for a in poem.alternatives)
    assert 0.5 < poem.confidence <= 1


def test_confidence_is_softmax_of_best():
    assert confidence([1.0, 1.0], 1.0) == pytest.approx(0.5)
    assert confidence([0.0, 5.0, 5.0], 1.0) > 0.95
    assert confidence([], 1.0) == 0.0


def test_gazel_flags_bad_beyit():
    text = "\n\n".join([
        FUZULI.replace(" / ", "\n"),
        "Perîşân halk-ı âlem âh u efgân etdügümdendür\nPerîşân oldugum halkı perîşân etdügümdendür",
        "Âşık oldur kim kılur cânın fedâ cânânına\nMeyl-i cânân etmesün her kim ki kıymaz cânına",
    ])
    poem = scan(text)
    assert poem.best.meter.id == "hezec-8-salim"
    assert poem.flagged == [2]


def test_empty_input():
    with pytest.raises(ValueError):
        scan("  \n ")
