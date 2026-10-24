from aruz.readings import is_med, readings
from aruz.syllables import syllabify


def shapes(line):
    return {"".join(u.weight for u in r.units) for r in readings(line)}


def texts(reading):
    return [s.text for s in reading.syllables]


def test_short_open_syllable_is_short():
    assert ".-" in shapes("beni")


def test_closed_syllable_is_long():
    assert "--" in shapes("candan")


def test_long_vowel_is_long():
    assert ".--" in shapes("cefâdan")


def test_last_syllable_is_always_long():
    assert all(s.endswith("-") for s in shapes("bu gece"))


def test_med_detection():
    assert is_med(syllabify("yâr")[0])
    assert is_med(syllabify("dost")[0])
    assert is_med(syllabify("kand")[0])
    assert not is_med(syllabify("can")[0])
    assert not is_med(syllabify("yâ")[0])


def test_med_branches():
    assert shapes("dost gelür") == {"-..-", "-.-"}


def test_med_after_long_vowel_and_n_is_discouraged():
    costs = {"".join(u.weight for u in r.units): r.cost for r in readings("cân gelür")}
    assert costs["-.-"] < costs["-..-"]


def test_med_license_reported():
    reading = next(r for r in readings("yâr gelür") if len(r.units) == 4)
    assert [(lic.kind, lic.text) for lic in reading.licenses] == [("med", "yâr")]


def test_ulama_is_optional():
    variants = {tuple(texts(r)) for r in readings("yâr usanmaz")}
    assert ("yâr", "u", "san", "maz") in variants
    assert ("yâ", "ru", "san", "maz") in variants


def test_ulama_license_names_the_join():
    reading = next(r for r in readings("yâr usanmaz") if texts(r)[:2] == ["yâ", "ru"])
    assert [(lic.kind, lic.syllable, lic.text) for lic in reading.licenses] == [("ulama", 0, "yâ-ru")]


def test_ulama_shortens_closed_syllable():
    reading = next(r for r in readings("gönül alır") if texts(r)[:3] == ["gö", "nü", "la"])
    assert "".join(u.weight for u in reading.units)[:3] == "..."


def test_ayn_blocks_ulama():
    variants = {tuple(texts(r)) for r in readings("dil 'aşk")}
    assert variants == {("dil", "'aşk")}


def test_izafet_always_links():
    variants = {tuple(texts(r)) for r in readings("gül-i ra'nâ")}
    assert variants == {("gü", "li", "ra'", "nâ")}


def test_izafet_can_be_short_or_long():
    found = shapes("gül-i ra'nâ")
    assert "..--" in found
    assert ".---" in found


def test_conjunction_can_be_short_or_long():
    assert shapes("şeb ü rûz") == {"..-", ".--"}


def test_readings_sorted_by_cost():
    costs = [r.cost for r in readings("dost u yâr-i dil")]
    assert costs == sorted(costs)
