import tomllib
from dataclasses import dataclass
from functools import cache
from importlib.resources import files
from itertools import product


@dataclass(frozen=True)
class Meter:
    id: str
    name: str
    feet: tuple[str, ...]
    sources: tuple[str, ...]

    @property
    def label(self) -> str:
        return " ".join(self.feet)


@dataclass(frozen=True)
class Pattern:
    meter: Meter
    feet: tuple[str, ...]
    shapes: tuple[str, ...]

    @property
    def weights(self) -> str:
        return "".join(self.shapes)

    @property
    def label(self) -> str:
        return " ".join(self.feet)


@cache
def library() -> dict:
    return tomllib.loads(files("aruz").joinpath("data/meters.toml").read_text("utf-8"))


@cache
def meters() -> tuple[Meter, ...]:
    data = library()
    return tuple(
        Meter(m["id"], m["name"], tuple(m["feet"]), tuple(data["sources"][s] for s in m["sources"]))
        for m in data["meter"]
    )


def meter(meter_id: str) -> Meter:
    return next(m for m in meters() if m.id == meter_id)


@cache
def patterns() -> tuple[Pattern, ...]:
    data = library()
    feet = data["feet"]
    result = []
    for entry, m in zip(data["meter"], meters()):
        firsts = [m.feet[0], *entry.get("first", [])]
        lasts = [m.feet[-1], *entry.get("last", [])]
        for first, last in product(firsts, lasts):
            names = (first, *m.feet[1:-1], last) if len(m.feet) > 1 else (first,)
            result.append(Pattern(m, names, tuple(feet[n] for n in names)))
    return tuple(result)
