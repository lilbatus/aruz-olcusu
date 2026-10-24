import tomllib
from collections import Counter
from pathlib import Path

from aruz.meters import meters
from aruz.poem import scan

CORPUS = tomllib.loads((Path(__file__).parent / "data" / "corpus.toml").read_text("utf-8"))


def test_corpus_is_well_formed():
    known = {m.id for m in meters()}
    for item in CORPUS["beyit"]:
        assert item["meter"] in known
        assert item["source"] in CORPUS["sources"]
        assert len(item["lines"]) == 2


def test_corpus_size_and_poets():
    poets = Counter(item["poet"] for item in CORPUS["beyit"])
    assert sum(poets.values()) >= 30
    assert set(poets) >= {"Fuzûlî", "Bâkî", "Nedîm", "Nef'î", "Şeyh Gâlib", "Nâbî"}


def test_corpus_accuracy():
    items = CORPUS["beyit"]
    hits = sum(scan("\n".join(item["lines"])).best.meter.id == item["meter"] for item in items)
    assert hits / len(items) >= 0.9
