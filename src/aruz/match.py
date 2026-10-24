import math
from dataclasses import dataclass
from functools import lru_cache

from aruz.meters import Pattern, patterns
from aruz.readings import License, Reading, Unit, penalties, readings


@dataclass
class Fit:
    pattern: Pattern
    reading: Reading
    cost: float
    licenses: list[License]

    def feet(self) -> list[tuple[str, str, list[Unit]]]:
        result = []
        start = 0
        for name, shape in zip(self.pattern.feet, self.pattern.shapes):
            result.append((name, shape, self.reading.units[start:start + len(shape)]))
            start += len(shape)
        return result


def word_final(reading: Reading, index: int) -> bool:
    syllables = reading.syllables
    return index + 1 == len(syllables) or syllables[index + 1].word != syllables[index].word


def foreign(reading: Reading, index: int) -> bool:
    text = reading.words[reading.syllables[index].word].text
    return any(ch in text for ch in "âîû'")


def unit_cost(reading: Reading, unit: Unit, want: str, w: dict) -> tuple[float, str | None]:
    if unit.weight == want:
        return 0.0, None
    if unit.fixed:
        return math.inf, None
    if want == "-":
        if foreign(reading, unit.syllable):
            return w["imale_foreign"], "imale"
        if word_final(reading, unit.syllable):
            return w["imale_word_final"], "imale"
        return w["imale"], "imale"
    if reading.syllables[unit.syllable].closed:
        return w["zihaf_closed"], "zihaf"
    return w["zihaf"], "zihaf"


def fit(reading: Reading, pattern: Pattern, w: dict) -> Fit | None:
    weights = pattern.weights
    if len(reading.units) != len(weights):
        return None
    cost = reading.cost
    licenses = list(reading.licenses)
    for unit, want in zip(reading.units[:-1], weights[:-1]):
        extra, kind = unit_cost(reading, unit, want, w)
        if extra == math.inf:
            return None
        cost += extra
        if kind:
            licenses.append(License(kind, unit.syllable, reading.syllables[unit.syllable].text))
    licenses.sort(key=lambda lic: lic.syllable)
    return Fit(pattern, reading, cost, licenses)


@lru_cache(maxsize=4096)
def best_fits(line: str) -> dict[str, Fit]:
    w = penalties()
    options = readings(line)
    best: dict[str, Fit] = {}
    for pattern in patterns():
        for reading in options:
            result = fit(reading, pattern, w)
            if result and (pattern.meter.id not in best or result.cost < best[pattern.meter.id].cost):
                best[pattern.meter.id] = result
    return best


def confidence(costs: list[float], temperature: float) -> float:
    if not costs:
        return 0.0
    scores = [math.exp(-(c - costs[0]) / temperature) for c in costs]
    return scores[0] / sum(scores)
