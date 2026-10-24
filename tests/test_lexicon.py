import tomllib
from pathlib import Path

from aruz import lexicon
from aruz.normalize import asciify
from aruz.repair import restore

CORPUS = tomllib.loads((Path(__file__).parent / "data" / "corpus.toml").read_text("utf-8"))


def test_tables_load_every_kind():
    tables = lexicon.tables()
    assert set(tables) == {"form", "lemma", "izafet"}
    assert all(tables.values())


def test_lookup_is_ranked_by_count():
    entries = lexicon.lookup("mana")
    assert "ma'nâ" in [form for form, _ in entries]
    counts = [count for _, count in entries]
    assert counts == sorted(counts, reverse=True)


def test_unknown_key():
    assert lexicon.lookup("qqqq") == []
    assert lexicon.izafets("qqqq") == {}


def test_stem_uses_marked_lemmas():
    end, form, count = lexicon.stem("cananina")
    assert (end, form) == (5, "cânân")
    assert count > 0
    assert lexicon.stem("abc") is None


def test_missing_source_is_skipped():
    assert lexicon.read("data/no-such-lexicon.tsv.gz") == ""


def words(text):
    return text.split()


def accuracy(beyits, use_meter):
    hits = total = 0
    for original in beyits:
        restored = restore(asciify(original), use_meter=use_meter).text
        for want, got in zip(words(original), words(restored), strict=True):
            hits += want == got
            total += 1
    return hits / total


def test_meter_does_not_hurt_restoration():
    beyits = ["\n".join(item["lines"]) for item in CORPUS["beyit"][::5]]
    with_meter = accuracy(beyits, True)
    without = accuracy(beyits, False)
    assert with_meter >= without
    assert with_meter > 0.6
