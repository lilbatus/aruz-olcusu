import tomllib
from dataclasses import dataclass, field, replace
from functools import cache
from importlib.resources import files
from itertools import product

from aruz.normalize import Word, parse_misra
from aruz.syllables import Syllable, syllabify_words

LINKED_KINDS = {"izafet", "conjunction"}


@dataclass(frozen=True)
class Unit:
    weight: str
    syllable: int
    fixed: bool = False


@dataclass(frozen=True)
class License:
    kind: str
    syllable: int
    text: str


@dataclass
class Reading:
    words: list[Word]
    syllables: list[Syllable]
    units: list[Unit] = field(default_factory=list)
    cost: float = 0.0
    licenses: list[License] = field(default_factory=list)


@cache
def penalties() -> dict:
    return tomllib.loads(files("aruz").joinpath("data/penalties.toml").read_text("utf-8"))


def is_med(s: Syllable) -> bool:
    return (s.long_vowel and s.closed) or len(s.coda) >= 2


def ulama_points(groups: list[list[Syllable]]) -> list[int]:
    return [
        i for i in range(len(groups) - 1)
        if groups[i][-1].closed and not groups[i + 1][0].onset
    ]


def link(groups: list[list[Syllable]], joins: set[int]) -> tuple[list[Syllable], list[int]]:
    groups = [list(g) for g in groups]
    joined_at = []
    for i in sorted(joins):
        left, right = groups[i][-1], groups[i + 1][0]
        groups[i][-1] = replace(left, coda=left.coda[:-1])
        groups[i + 1][0] = replace(right, onset=left.coda[-1])
        joined_at.append(sum(len(g) for g in groups[:i + 1]) - 1)
    return [s for g in groups for s in g], joined_at


def choices(s: Syllable, kind: str, last: bool, w: dict) -> list[tuple[tuple[str, ...], float, str | None]]:
    if last:
        return [(("-",), 0.0, None)]
    if kind in LINKED_KINDS and not s.closed and not s.long_vowel:
        return [((".",), 0.0, None), (("-",), w[f"{kind}_long"], kind)]
    if is_med(s) and s.long_vowel and s.coda == "n":
        return [(("-", "."), w["med_after_n"], "med"), (("-",), 0.0, None)]
    if is_med(s):
        return [(("-", "."), 0.0, "med"), (("-",), w["med_skipped"], None)]
    if s.long_vowel or s.closed:
        return [(("-",), 0.0, None)]
    return [((".",), 0.0, None)]


def expand(words: list[Word], syllables: list[Syllable], base: float, base_licenses: list[License], w: dict) -> list[Reading]:
    partial = [Reading(words, syllables, [], base, list(base_licenses))]
    for i, s in enumerate(syllables):
        last = i == len(syllables) - 1
        grown = []
        for r in partial:
            for weights, cost, kind in choices(s, words[s.word].kind, last, w):
                units = r.units + [Unit(x, i, fixed=len(weights) > 1) for x in weights]
                licenses = r.licenses + ([License(kind, i, s.text)] if kind else [])
                grown.append(Reading(words, syllables, units, r.cost + cost, licenses))
        grown.sort(key=lambda r: r.cost)
        partial = grown[: w["beam_width"]]
    return partial


def readings(line: str) -> list[Reading]:
    w = penalties()
    parsed = parse_misra(line)
    pairs = [(word, group) for word, group in zip(parsed, syllabify_words(parsed)) if group]
    if not pairs:
        return []
    words = [word for word, _ in pairs]
    groups = [[replace(s, word=i) for s in group] for i, (_, group) in enumerate(pairs)]
    points = ulama_points(groups)
    forced = {i for i in points if words[i + 1].kind in LINKED_KINDS}
    optional = [i for i in points if i not in forced]
    result = []
    for picks in product((False, True), repeat=len(optional)):
        joins = forced | {i for i, on in zip(optional, picks) if on}
        syllables, joined_at = link(groups, joins)
        licenses = [
            License("ulama", at, f"{syllables[at].text}-{syllables[at + 1].text}")
            for at, i in zip(joined_at, sorted(joins)) if i not in forced
        ]
        cost = w["ulama"] * len(licenses)
        result.extend(expand(words, syllables, cost, licenses, w))
    result.sort(key=lambda r: r.cost)
    return result[: w["beam_width"]]
