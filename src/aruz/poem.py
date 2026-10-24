from dataclasses import dataclass

from aruz.match import Fit, best_fits, confidence
from aruz.meters import Meter, meters
from aruz.normalize import split_beyits
from aruz.readings import penalties


@dataclass
class Candidate:
    meter: Meter
    cost: float
    fits: list[Fit | None]


@dataclass
class Poem:
    beyits: list[list[str]]
    candidates: list[Candidate]
    confidence: float
    flagged: list[int]

    @property
    def best(self) -> Candidate:
        return self.candidates[0]

    @property
    def alternatives(self) -> list[Candidate]:
        return self.candidates[1:3]

    def beyit_fits(self, index: int) -> list[Fit | None]:
        start = sum(len(b) for b in self.beyits[:index])
        return self.best.fits[start:start + len(self.beyits[index])]


def scan(text: str) -> Poem:
    w = penalties()
    beyits = split_beyits(text)
    lines = [line for beyit in beyits for line in beyit]
    if not lines:
        raise ValueError("empty input")
    per_line = [best_fits(line) for line in lines]
    candidates = []
    for m in meters():
        fits = [found.get(m.id) for found in per_line]
        cost = sum(f.cost if f else w["unmatched"] for f in fits)
        candidates.append(Candidate(m, cost, fits))
    candidates.sort(key=lambda c: c.cost)
    average = [c.cost / len(lines) for c in candidates[:3]]
    poem = Poem(beyits, candidates, confidence(average, w["confidence_temperature"]), [])
    poem.flagged = [
        i for i in range(len(beyits))
        if any(f is None or f.cost > w["gazel_bad_fit"] for f in poem.beyit_fits(i))
    ]
    return poem
