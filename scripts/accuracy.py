import tomllib
from collections import Counter
from pathlib import Path

from aruz.poem import scan

CORPUS = Path(__file__).resolve().parent.parent / "tests" / "data" / "corpus.toml"


def load() -> list[dict]:
    return tomllib.loads(CORPUS.read_text("utf-8"))["beyit"]


def evaluate() -> list[tuple[dict, str, float, float]]:
    rows = []
    for item in load():
        poem = scan("\n".join(item["lines"]))
        rows.append((item, poem.best.meter.id, poem.best.cost, poem.confidence))
    return rows


def main() -> None:
    rows = evaluate()
    hits = 0
    misses = Counter()
    for item, guess, cost, conf in rows:
        ok = guess == item["meter"]
        hits += ok
        if not ok:
            misses[(item["meter"], guess)] += 1
        mark = "ok  " if ok else "MISS"
        print(f"{mark} {item['poet']:<11} {item['meter']:<22} {guess:<22} {cost:5.2f} {conf:4.2f}  {item['lines'][0]}")
    print()
    print(f"beyit accuracy: {hits}/{len(rows)} = {hits / len(rows):.1%}")
    for (want, got), n in misses.most_common():
        print(f"  {want} -> {got}: {n}")
    lines = [(line, item["meter"]) for item, *_ in rows for line in item["lines"]]
    line_hits = sum(scan(line).best.meter.id == want for line, want in lines)
    print(f"misra accuracy: {line_hits}/{len(lines)} = {line_hits / len(lines):.1%}")


if __name__ == "__main__":
    main()
