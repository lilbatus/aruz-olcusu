from aruz.normalize import parse_misra
from aruz.syllables import syllabify, syllabify_words


def split(word):
    return [s.text for s in syllabify(word)]


def test_single_consonant_goes_to_next_syllable():
    assert split("beni") == ["be", "ni"]
    assert split("cefâdan") == ["ce", "fâ", "dan"]


def test_two_consonants_split():
    assert split("candan") == ["can", "dan"]
    assert split("usandırdı") == ["u", "san", "dır", "dı"]


def test_three_consonants_keep_two():
    assert split("dostlar") == ["dost", "lar"]


def test_final_cluster_stays():
    assert split("dost") == ["dost"]
    assert split("kand") == ["kand"]


def test_hiatus():
    assert split("şâir") == ["şâ", "ir"]


def test_ayn_is_a_consonant():
    assert split("ma'nâ") == ["ma'", "nâ"]
    assert split("nef'î") == ["nef", "'î"]
    assert split("'aşk") == ["'aşk"]


def test_long_vowel_and_closed():
    yar = syllabify("yâr")[0]
    assert yar.long_vowel and yar.closed
    ni = syllabify("beni")[1]
    assert not ni.long_vowel and not ni.closed


def test_no_vowel():
    assert syllabify("'") == []


def test_words_keep_index():
    words = parse_misra("Beni candan usandırdı cefâdan yâr usanmaz mı")
    groups = syllabify_words(words)
    flat = [s.text for group in groups for s in group]
    assert flat == ["be", "ni", "can", "dan", "u", "san", "dır", "dı", "ce", "fâ", "dan", "yâr", "u", "san", "maz", "mı"]
    assert [s.word for s in groups[4]] == [4]
