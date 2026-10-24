from dataclasses import dataclass

from aruz import strings
from aruz.match import Fit
from aruz.readings import LINKED_KINDS, is_med
from aruz.repair import Spot
from aruz.syllables import Syllable

CODES = (
    "open_short_vowel",
    "closed_consonant",
    "long_vowel",
    "final_syllable_rule",
    "med",
    "med_skipped",
    "izafet",
    "conjunction",
    "ulama",
    "imale",
    "zihaf",
)


@dataclass(frozen=True)
class Reason:
    code: str
    syllable: str
    word: str
    position: int
    before: str | None
    after: str
    detail: str = ""


def describe(reason: Reason, lang: str = strings.DEFAULT) -> dict:
    words = strings.LANGUAGES[lang]
    text = words["REASON_TEXTS"][reason.code].format(
        syllable=reason.syllable,
        word=reason.word,
        position=reason.position,
        before=words["WEIGHT_NAMES"].get(reason.before, ""),
        after=words["WEIGHT_NAMES"][reason.after],
        detail=reason.detail,
        cause=words["MED_CAUSES"].get(reason.detail, ""),
    )
    return {"name": words["REASON_NAMES"][reason.code], "text": text}


def describe_spot(spot: Spot, lang: str = strings.DEFAULT) -> list[dict]:
    words = strings.LANGUAGES[lang]
    if spot.text != spot.original:
        sentences = [words["REPAIR_CHANGED"].format(original=spot.original, restored=spot.text)]
    else:
        sentences = [words["REPAIR_KEPT"].format(original=spot.original)]
    sentences.append(words["REPAIR_SOURCES"][spot.source])
    if spot.by_user:
        sentences.append(words["REPAIR_USER"])
    elif spot.by_meter:
        sentences.append(words["REPAIR_METER"])
    elif spot.uncertain:
        sentences.append(words["REPAIR_UNCERTAIN"])
    if len(spot.forms) > 1:
        sentences.append(words["REPAIR_CYCLE"].format(n=spot.choice + 1, count=len(spot.forms)))
    return [{"name": words["REPAIR_NAME"], "text": " ".join(sentences)}]


def natural(s: Syllable) -> str:
    return "-" if s.closed or s.long_vowel else "."


def classify(s: Syllable, kind: str, weight: str, last: bool) -> tuple[str, str | None, str, str]:
    if last:
        if not s.closed and not s.long_vowel:
            return "final_syllable_rule", ".", "-", ""
        if not s.closed:
            return "long_vowel", None, "-", ""
        return "closed_consonant", None, "-", ""
    if kind in LINKED_KINDS and not s.closed and not s.long_vowel:
        return kind, ".", weight, ""
    if is_med(s):
        cause = "long_vowel" if s.long_vowel else "two_consonants"
        if weight == "-.":
            return "med", "-", "-.", cause
        if s.long_vowel and s.coda == "n":
            return "closed_consonant", None, "-", ""
        return "med_skipped", "-.", "-", cause
    if s.long_vowel:
        return "long_vowel", None, "-", ""
    if s.closed:
        return "closed_consonant", None, "-", ""
    return "open_short_vowel", None, ".", ""


def reasons(fit: Fit) -> list[list[Reason]]:
    reading = fit.reading
    weights: dict[int, str] = {}
    for unit in reading.units:
        weights[unit.syllable] = weights.get(unit.syllable, "") + unit.weight
    licenses: dict[int, list[tuple[str, str]]] = {}
    for lic in fit.licenses:
        licenses.setdefault(lic.syllable, []).append((lic.kind, lic.text))
    last = len(reading.syllables) - 1
    result = []
    for i, s in enumerate(reading.syllables):
        word = reading.words[s.word]
        here = licenses.get(i, [])
        items = [
            Reason("ulama", s.text, word.text, i + 1, "-", natural(s), text)
            for kind, text in here if kind == "ulama"
        ]
        code, before, after, detail = classify(s, word.kind, weights[i], i == last)
        items.append(Reason(code, s.text, word.text, i + 1, before, after, detail))
        for kind, _ in here:
            if kind == "imale":
                items.append(Reason("imale", s.text, word.text, i + 1, ".", "-"))
            elif kind == "zihaf":
                items.append(Reason("zihaf", s.text, word.text, i + 1, "-", "."))
        result.append(items)
    return result
