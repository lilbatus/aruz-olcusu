import math
from collections import Counter
from dataclasses import asdict

from aruz import strings
from aruz.explain import Reason, describe, describe_spot, reasons
from aruz.match import Fit
from aruz.poem import Candidate, Poem
from aruz.readings import License, penalties
from aruz.repair import APOSTROPHES, Restoration


def number(value: float, lang: str = strings.DEFAULT, digits: int | None = None) -> str:
    text = f"{value:g}" if digits is None else f"{value:.{digits}f}"
    return text.replace(".", strings.LANGUAGES[lang]["DECIMAL"])


def changed(original: str, restored: str) -> list[int]:
    marks = []
    i = 0
    for j, ch in enumerate(restored):
        if i < len(original) and original[i] == ch:
            i += 1
        elif i < len(original) and not (ch in APOSTROPHES and original[i] not in APOSTROPHES):
            marks.append(j)
            i += 1
        else:
            marks.append(j)
    return marks


def repair_dict(restoration: Restoration) -> dict:
    words, segments, last = [], [], 0
    for spot in restoration.spots:
        marks = changed(spot.original, spot.text)
        if not marks and len(spot.forms) == 1:
            continue
        segments.append({"text": restoration.original[last:spot.start], "word": None})
        segments.append({"text": spot.text, "word": spot.index})
        last = spot.end
        words.append({
            "index": spot.index,
            "original": spot.original,
            "restored": spot.text,
            "candidates": [form.text for form in spot.forms],
            "choice": spot.choice,
            "changed": marks,
            "uncertain": spot.uncertain,
            "source": spot.source,
            "by_meter": spot.by_meter,
            "by_user": spot.by_user,
            "tips": describe_spot(spot),
            "i18n": {lang: {"tips": describe_spot(spot, lang)} for lang in strings.LANGUAGES},
        })
    segments.append({"text": restoration.original[last:], "word": None})
    return {"text": restoration.text, "segments": [s for s in segments if s["text"]], "words": words}


def reason_dict(reason: Reason) -> dict:
    return asdict(reason) | describe(reason) | {"i18n": {lang: describe(reason, lang) for lang in strings.LANGUAGES}}


def syllables_dict(fit: Fit, explained: list[list[Reason]]) -> list[dict]:
    marks: dict[int, str] = {}
    for unit, mark in zip(fit.reading.units, fit.pattern.weights):
        marks[unit.syllable] = marks.get(unit.syllable, "") + mark
    return [
        {
            "position": i + 1,
            "text": s.text,
            "word": fit.reading.words[s.word].text,
            "mark": marks[i],
            "reasons": [reason_dict(reason) for reason in items],
        }
        for i, (s, items) in enumerate(zip(fit.reading.syllables, explained))
    ]


def license_tip(explained: list[list[Reason]], syllable: int, kind: str, lang: str = strings.DEFAULT) -> dict:
    return describe(next(r for r in explained[syllable] if r.code == kind), lang)


def license_dict(lic: License, explained: list[list[Reason]]) -> dict:
    return {
        "kind": lic.kind,
        "name": strings.TR["LICENSES"][lic.kind],
        "syllable": lic.syllable + 1,
        "text": lic.text,
        "tip": license_tip(explained, lic.syllable, lic.kind),
        "i18n": {
            lang: {"name": words["LICENSES"][lic.kind], "tip": license_tip(explained, lic.syllable, lic.kind, lang)}
            for lang, words in strings.LANGUAGES.items()
        },
    }


def misra_dict(text: str, fit: Fit | None) -> dict:
    if fit is None:
        return {"text": text, "fit": None}
    explained = reasons(fit)
    licensed = {lic.syllable: lic.kind for lic in fit.licenses}
    feet = []
    previous = None
    for name, shape, units in fit.feet():
        cells = []
        for unit, mark in zip(units, shape):
            first = unit.syllable != previous
            previous = unit.syllable
            cells.append({
                "text": fit.reading.syllables[unit.syllable].text if first else "~",
                "mark": mark,
                "license": licensed.get(unit.syllable),
                "tail": not first,
                "syllable": unit.syllable + 1,
            })
        feet.append({"name": name, "units": cells})
    return {
        "text": text,
        "fit": {
            "pattern": fit.pattern.label,
            "penalty": round(fit.cost, 2),
            "feet": feet,
            "licenses": [license_dict(lic, explained) for lic in fit.licenses],
            "syllables": syllables_dict(fit, explained),
        },
    }


def span(values: list[float], lang: str) -> str:
    low, high = min(values), max(values)
    if low == high:
        return number(low, lang)
    return strings.LANGUAGES[lang]["RANGE"].format(low=number(low, lang), high=number(high, lang))


def license_counts(poem: Poem, lang: str) -> str:
    words = strings.LANGUAGES[lang]
    found = Counter(lic.kind for fit in poem.best.fits if fit for lic in fit.licenses)
    items = [words["COUNT"].format(name=name, n=found[kind]) for kind, name in words["LICENSES"].items() if found[kind]]
    unmatched = sum(fit is None for fit in poem.best.fits)
    if unmatched:
        items.append(words["COUNT"].format(name=words["PENALTY_UNMATCHED"], n=unmatched))
    return ", ".join(items) if items else words["PENALTY_NONE"]


def alternative_tip(poem: Poem, candidate: Candidate, lang: str) -> dict:
    words = strings.LANGUAGES[lang]
    diff = candidate.cost - poem.best.cost
    unmatched = sum(fit is None for fit in candidate.fits)
    if diff < 0.005:
        text = words["ALT_TIE"]
    elif unmatched:
        text = words["ALT_UNMATCHED"].format(diff=number(round(diff, 2), lang), unmatched=unmatched, total=len(candidate.fits))
    else:
        text = words["ALT_FITS"].format(diff=number(round(diff, 2), lang))
    return {"name": candidate.meter.name, "text": text}


def tips_dict(poem: Poem) -> dict:
    w = penalties()
    total = len(poem.best.fits)
    averages = [candidate.cost / total for candidate in poem.candidates[:3]]
    found = {}
    for lang, words in strings.LANGUAGES.items():
        penalty = words["PENALTY_TIP"].format(
            imale=span([w["imale_word_final"], w["imale"], w["imale_foreign"]], lang),
            zihaf=span([w["zihaf"], w["zihaf_closed"]], lang),
            unmatched=number(w["unmatched"], lang),
            counts=license_counts(poem, lang),
        )
        confidence = words["CONFIDENCE_TIP"].format(
            factor=number(math.exp(1 / w["confidence_temperature"]), lang, 1),
            best=number(round(averages[0], 1), lang),
            second=number(round(averages[1], 1), lang),
            third=number(round(averages[2], 1), lang),
        )
        meter = words["METER_TIP"].format(fitting=sum(fit is not None for fit in poem.best.fits), total=total)
        found[lang] = {
            "penalty": {"name": words["PENALTY"], "text": penalty},
            "confidence": {"name": words["CONFIDENCE"], "text": confidence},
            "meter": {"name": words["METER"], "text": meter},
            "alternatives": [alternative_tip(poem, candidate, lang) for candidate in poem.alternatives],
        }
    return found


def candidate_dict(candidate: Candidate) -> dict:
    return {
        "id": candidate.meter.id,
        "name": candidate.meter.name,
        "feet": candidate.meter.label,
        "penalty": round(candidate.cost, 2),
    }


def poem_dict(poem: Poem) -> dict:
    return {
        "meter": candidate_dict(poem.best),
        "confidence": round(poem.confidence, 3),
        "alternatives": [candidate_dict(c) for c in poem.alternatives],
        "beyits": [
            {
                "index": i + 1,
                "flagged": i in poem.flagged,
                "misras": [misra_dict(text, fit) for text, fit in zip(beyit, poem.beyit_fits(i))],
            }
            for i, beyit in enumerate(poem.beyits)
        ],
        "tips": tips_dict(poem),
    }
