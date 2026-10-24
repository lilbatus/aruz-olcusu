import re
from html.parser import HTMLParser
from importlib.resources import files
from string import Formatter

import pytest

from aruz import strings
from aruz.normalize import asciify

PLACEHOLDER = re.compile(r"__[A-Z_]+__")
TEXT_ATTRIBUTES = {"placeholder", "aria-label", "title", "alt"}
WORD = re.compile(r"[^\W\d_]+(?:['’][^\W\d_]+)*")


def leaves(table, path=()):
    for key, value in table.items():
        if isinstance(value, dict):
            yield from leaves(value, path + (key,))
        else:
            yield path + (key,), value


def shape(table):
    return {key: shape(value) if isinstance(value, dict) else None for key, value in table.items()}


def fields(template):
    return {name for _, name, _, _ in Formatter().parse(template) if name is not None}


def lower(word, lang):
    return word.replace("I", "ı").replace("İ", "i").lower() if lang == "tr" else word.lower()


def skeleton(word):
    return asciify(word.replace("I", "i").replace("İ", "i")).lower().replace("'", "").replace("’", "")


def test_languages_have_the_same_keys():
    assert set(strings.LANGUAGES) == {"tr", "en"}
    assert shape(strings.TR) == shape(strings.EN)


@pytest.mark.parametrize("lang", sorted(strings.LANGUAGES))
def test_no_value_is_empty(lang):
    for path, value in leaves(strings.LANGUAGES[lang]):
        assert isinstance(value, str) and value.strip(), path


def test_templates_take_the_same_fields():
    english = dict(leaves(strings.EN))
    for path, value in leaves(strings.TR):
        assert fields(value) == fields(english[path]), path


@pytest.mark.parametrize("lang", sorted(strings.LANGUAGES))
def test_terms_follow_the_glossary(lang):
    terms = {skeleton(term): term for term in strings.GLOSSARY}
    for path, value in leaves(strings.LANGUAGES[lang]):
        for word in WORD.findall(re.sub(r"\{[^}]*\}", " ", value)):
            term = terms.get(skeleton(word))
            if term:
                assert lower(word, lang) == lower(term, lang), (path, word, term)


def test_glossary_catches_a_misspelled_term():
    terms = {skeleton(term): term for term in strings.GLOSSARY}
    assert terms[skeleton("imale")] == "imâle"
    assert lower("imale", "en") != lower(terms[skeleton("imale")], "en")


class Markup(HTMLParser):
    def __init__(self):
        super().__init__()
        self.depth = 0
        self.found = []

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.depth += 1
        self.found += [value for name, value in attrs if name in TEXT_ATTRIBUTES and value]

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.depth -= 1

    def handle_data(self, data):
        if not self.depth and data.strip():
            self.found.append(data.strip())


def test_markup_has_no_hardcoded_text():
    parser = Markup()
    parser.feed(files("aruz").joinpath("web/index.html").read_text("utf-8"))
    assert parser.found
    assert [text for text in parser.found if not PLACEHOLDER.fullmatch(text)] == []
