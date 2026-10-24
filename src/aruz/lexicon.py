import gzip
from functools import cache
from importlib.resources import files

SOURCES = ("data/lexicon-ud.tsv.gz", "data/lexicon-otc.tsv.gz")
MARKED = set("âîû'")
MIN_STEM = 4

Table = dict[str, dict[str, int]]


def read(name: str) -> str:
    resource = files("aruz").joinpath(name)
    if not resource.is_file():
        return ""
    return gzip.decompress(resource.read_bytes()).decode("utf-8")


@cache
def tables() -> dict[str, Table]:
    found: dict[str, Table] = {"form": {}, "lemma": {}, "izafet": {}}
    for name in SOURCES:
        for line in read(name).splitlines()[1:]:
            key, form, count, kind = line.split("\t")
            bucket = found[kind].setdefault(key, {})
            bucket[form] = bucket.get(form, 0) + int(count)
    return found


def ranked(bucket: dict[str, int]) -> list[tuple[str, int]]:
    return sorted(bucket.items(), key=lambda item: (-item[1], item[0]))


def lookup(key: str) -> list[tuple[str, int]]:
    return ranked(tables()["form"].get(key, {}))


def izafets(key: str) -> dict[str, int]:
    return tables()["izafet"].get(key, {})


def stem(key: str) -> tuple[int, str, int] | None:
    lemmas = tables()["lemma"]
    for end in range(len(key) - 1, MIN_STEM - 1, -1):
        marked = [(form, count) for form, count in ranked(lemmas.get(key[:end], {})) if MARKED & set(form)]
        if marked:
            return end, marked[0][0], marked[0][1]
    return None
