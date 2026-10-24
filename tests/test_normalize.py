from aruz.normalize import Word, fold, parse_misra, split_beyits


def test_fold_turkish_case():
    assert fold("IŞIK İçin") == "ışık için"


def test_fold_macron_becomes_circumflex():
    assert fold("cefā") == fold("cefâ") == "cefâ"
    assert fold("dīn ū") == "dîn û"


def test_fold_decomposed_circumflex():
    assert fold("cân") == "cân"


def test_fold_drops_scholarly_dots():
    assert fold("ḥüsn ṣabr żulm") == "hüsn sabr zulm"


def test_fold_ayn_marks():
    assert fold("maʿnâ") == fold("ma’nâ") == fold("maʾnâ") == "ma'nâ"


def test_fold_keeps_turkish_letters():
    assert fold("çeşm-i gönül ağlar") == "çeşm-i gönül ağlar"


def test_parse_misra_plain():
    words = parse_misra("Beni candan usandırdı, cefâdan yâr usanmaz mı?")
    assert [w.text for w in words] == ["beni", "candan", "usandırdı", "cefâdan", "yâr", "usanmaz", "mı"]
    assert all(w.kind == "plain" for w in words)


def test_parse_misra_izafet():
    words = parse_misra("dil-i şeydâ bâde-yi gül-gûn")
    assert words == [
        Word("dil"),
        Word("i", "izafet"),
        Word("şeydâ"),
        Word("bâde"),
        Word("yi", "izafet"),
        Word("gül"),
        Word("gûn"),
    ]


def test_parse_misra_conjunction():
    words = parse_misra("şeb ü rûz gonca vü gül")
    kinds = [(w.text, w.kind) for w in words]
    assert ("ü", "conjunction") in kinds
    assert ("vü", "conjunction") in kinds


def test_split_beyits_lines():
    text = "a b\nc d\n\ne f\ng h"
    assert split_beyits(text) == [["a b", "c d"], ["e f", "g h"]]


def test_split_beyits_slash():
    assert split_beyits("a b / c d") == [["a b", "c d"]]


def test_split_beyits_without_blank_lines():
    assert split_beyits("a\nb\nc\nd") == [["a", "b"], ["c", "d"]]
