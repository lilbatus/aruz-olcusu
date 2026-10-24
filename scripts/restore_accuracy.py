import tomllib
from pathlib import Path

from turkish.deasciifier import Deasciifier

from aruz.normalize import asciify
from aruz.repair import restore

CORPUS = Path(__file__).resolve().parent.parent / "tests" / "data" / "corpus.toml"

MODES = {
    "deasciifier only": lambda text: "\n".join(Deasciifier(line).convert_to_turkish() for line in text.split("\n")),
    "lexicon, no meter": lambda text: restore(text, use_meter=False).text,
    "lexicon + meter": lambda text: restore(text, use_meter=True).text,
}


def load() -> list[str]:
    corpus = tomllib.loads(CORPUS.read_text("utf-8"))
    return ["\n".join(item["lines"]) for item in corpus["beyit"]]


def score(originals: list[str], run) -> tuple[int, int, int, int]:
    hits = total = marked_hits = marked_total = 0
    for original in originals:
        restored = run(asciify(original))
        for want, got in zip(original.split(), restored.split(), strict=True):
            hit = want == got
            hits += hit
            total += 1
            if asciify(want) != want:
                marked_hits += hit
                marked_total += 1
    return hits, total, marked_hits, marked_total


def main() -> None:
    originals = load()
    print(f"{'mode':<20} {'all words':>18} {'words with marks':>22}")
    for name, run in MODES.items():
        hits, total, marked_hits, marked_total = score(originals, run)
        print(f"{name:<20} {hits:>5}/{total:<5} {hits / total:6.1%} {marked_hits:>8}/{marked_total:<5} {marked_hits / marked_total:6.1%}")


if __name__ == "__main__":
    main()
