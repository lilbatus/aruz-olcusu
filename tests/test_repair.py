import pytest

from aruz.normalize import asciify, split_beyits
from aruz.repair import (
    Form,
    conjunction,
    contested,
    izafet,
    key,
    merge,
    misra_spans,
    restore,
    signature,
)


def texts(restoration):
    return [spot.text for spot in restoration.spots]


def test_asciify_is_one_to_one():
    text = "Perîşân halk-ı âlem ÂH u İŞK çeşm-i Ğ Ö Ü ı"
    assert len(asciify(text)) == len(text)
    assert asciify(text) == "Perisan halk-i alem AH u ISK cesm-i G O U i"


def test_key_drops_marks_case_and_apostrophes():
    assert key("Ma'nâ") == "mana"
    assert key("İŞK") == "isk"


def test_merge_keeps_case_and_typed_apostrophes():
    assert merge("nezâket", "Nezaket") == "Nezâket"
    assert merge("ma'nâ", "mana") == "ma'nâ"
    assert merge("şem", "sem'") == "şem'"
    assert merge("ışk", "ISK") == "IŞK"
    assert merge("işk", "Isk") == "İşk"


def test_misra_spans_follow_split_beyits():
    text = "a b / c d\n\n  e f\ng h /  \n"
    spans = misra_spans(text)
    assert [text[s:e].strip() for s, e in spans] == [m for beyit in split_beyits(text) for m in beyit]


@pytest.mark.parametrize("suffix, previous, expected", [
    ("i", "dil", "i"),
    ("i", "cân", "ı"),
    ("i", "gonca", "i"),
    ("i", "nâle", "i"),
    ("yi", "sahrâ", "yı"),
    ("yi", "rû", "yı"),
    ("yi", "bâde", "yi"),
    ("i", "şem'", "i"),
])
def test_izafet_rule(suffix, previous, expected):
    assert izafet(suffix, previous) == expected


@pytest.mark.parametrize("word, previous, expected", [
    ("u", "âh", "u"),
    ("u", "derd", "ü"),
    ("u", "sîm", "ü"),
    ("u", "sabr", "u"),
    ("vu", "Leylâ", "vü"),
    ("vu", "bende", "vü"),
])
def test_conjunction_rule(word, previous, expected):
    assert conjunction(word, previous) == expected


def test_signature_separates_weights():
    assert signature("nezaket") != signature("nezâket")
    assert signature("ma'na")[0] == signature("ma'nâ")[0]
    assert signature("ma'na") != signature("ma'nâ")
    assert signature("dâğ") == signature("dâg")


def test_contested():
    assert not contested([Form("cân", 10), Form("can", 0)])
    assert contested([Form("yâr", 10), Form("yar", 5)])
    assert not contested([Form("yâr", 10), Form("yar", 1)])


def test_typed_words_are_kept():
    restored = restore("Perîşân halk-ı âlem", use_meter=False)
    assert restored.text == "Perîşân halk-ı âlem"
    assert all(spot.source in {"typed", "rule"} or spot.text == spot.original for spot in restored.spots)


def test_deasciifier_restores_turkish_letters():
    restored = restore("gecmis olmus", use_meter=False)
    assert texts(restored) == ["geçmiş", "olmuş"]


def test_phrase():
    restored = restore("yal u bal", use_meter=False)
    assert restored.text == "yâl ü bâl"
    assert {spot.source for spot in restored.spots} == {"phrase"}


def test_izafet_and_conjunction_in_text():
    restored = restore("dil-i sahra-yi ah u efgan", use_meter=False)
    assert restored.text.startswith("dil-i ")
    assert "-yı " in restored.text
    assert " u " in restored.text


def test_layout_is_preserved():
    text = "Beni candan / usandirdi\n\nfelekler yandi"
    restored = restore(text, use_meter=False)
    assert restored.text.count("\n") == 2
    assert " / " in restored.text


def test_choices_override():
    restored = restore("dil-i", use_meter=False)
    chosen = restore("dil-i", use_meter=False, choices={1: 1})
    assert restored.spots[1].text == "i"
    assert chosen.spots[1].text == "ı"
    assert chosen.spots[1].by_user


def test_task_example_with_meter():
    restored = restore("Haddeden gecmis nezaket yal u bal olmus sana")
    assert restored.text == "Haddeden geçmiş nezâket yâl ü bâl olmuş sana"


def test_meter_overrides_the_most_common_form():
    without = restore("Haddeden gecmis nezaket yal u bal olmus sana", use_meter=False)
    assert without.spots[2].text == "nezaket"
    spot = restore("Haddeden gecmis nezaket yal u bal olmus sana").spots[2]
    assert spot.text == "nezâket"
    assert spot.by_meter
    assert not spot.uncertain


def test_candidates_are_unique():
    for spot in restore("Nice mumkin ki tahalluf ide te'sir-i du'a").spots:
        texts_ = [form.text for form in spot.forms]
        assert len(texts_) == len(set(texts_))


def test_tie_at_line_end_is_uncertain():
    spot = restore("Haddeden gecmis nezaket yal u bal olmus yar").spots[-1]
    assert not spot.by_meter
    assert spot.uncertain


def test_user_choice_survives_meter_search():
    spot = restore("Haddeden gecmis nezaket yal u bal olmus sana").spots[2]
    plain = [form.text for form in spot.forms].index("nezaket")
    restored = restore("Haddeden gecmis nezaket yal u bal olmus sana", choices={2: plain})
    assert restored.spots[2].text == "nezaket"
    assert restored.spots[2].by_user


@pytest.mark.parametrize("text, expected", [
    ("usanmaz mi", "mı"),
    ("gelir mi", "mi"),
    ("gelur mi", "mü"),
    ("olur mu", "mu"),
    ("gordun mu", "mü"),
])
def test_question_particle_follows_harmony(text, expected):
    assert restore(text, use_meter=False).spots[1].text == expected


def test_izafet_vowel_comes_from_the_corpus():
    assert restore("hal-i dil", use_meter=False).spots[1].text == "i"
    assert restore("dag-i hicran", use_meter=False).spots[1].text == "ı"


def test_invalid_choice_is_ignored():
    restored = restore("yal u bal", use_meter=False, choices={1: 5})
    assert restored.text == "yâl ü bâl"
    assert not restored.spots[1].by_user
