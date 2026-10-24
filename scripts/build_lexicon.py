import gzip
import json
import re
import tempfile
import tomllib
import unicodedata
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path

from aruz.normalize import asciify, fold

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "src" / "aruz" / "data"
CORPUS = ROOT / "tests" / "data" / "corpus.toml"
CACHE = Path(tempfile.gettempdir()) / "aruz-lexicon"

UD = {
    "UD_Ottoman_Turkish-BOUN": "7252f055d59356bd216af0551cdae45e4c7940bb",
    "UD_Ottoman_Turkish-DUDU": "dd23a14215f5e3042d3d91bf997bf92327fc8fcc",
}
OTC = "BUCOLIN/OTC-Corpus"
OTC_REVISION = "c8a8e82c6fc46aaadde130f4e39d0cb6488268e8"
OTC_SKIP = {"whole_corpus.txt", "metadata.txt", "stats.txt"}
OTC_MIN_COUNT = 3

VOWELS = "aeıioöuüâîû"
TOKEN = re.compile(r"[a-zçğıöşüâîû'\-]+")
NOT_LETTER = re.compile(r"[^a-z]+")
IZAFET = {"i", "ı", "u", "ü", "yi", "yı", "yu", "yü"}
IZAFET_VOWELS = {"ı", "i", "yı", "yi"}
NAME_SUFFIX = re.compile(r"(?<![^\W\d_])([A-ZÇĞİÖŞÜÂÎÛ][^\W\d_]*)['’‘ʿʾ`´ʼ]([^\W\d_]+)")
SUFFIXES = {
    "a", "e", "ya", "ye", "ı", "i", "u", "ü", "yı", "yi", "yu", "yü",
    "da", "de", "ta", "te", "dan", "den", "tan", "ten", "ın", "in", "un", "ün",
    "nın", "nin", "nun", "nün", "la", "le", "yla", "yle", "ca", "ce", "ça", "çe",
    "dır", "dir", "dur", "dür", "tır", "tir", "tur", "tür", "dı", "di", "du", "dü",
    "lar", "ler", "ları", "leri", "na", "ne", "nı", "ni", "nu", "nü", "nda", "nde", "ndan", "nden",
}


def download(url: str, name: str) -> Path:
    path = CACHE / name
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        request = urllib.request.Request(url, headers={"User-Agent": "aruz-lexicon-builder"})
        with urllib.request.urlopen(request) as response:
            path.write_bytes(response.read())
    return path


def split_name(match: re.Match) -> str:
    suffix = fold(match.group(2))
    return f"{match.group(1)} {match.group(2)}" if suffix in SUFFIXES else match.group(0)


def clean(text: str) -> str:
    text = NAME_SUFFIX.sub(split_name, unicodedata.normalize("NFC", text))
    text = text.replace("I", "ı").replace("İ", "i").lower()
    text = re.sub(r"(?<=[aeıioöuüâîûāīūēō])ġ", "ğ", text)
    return fold(text)


def skeleton(folded: str) -> str:
    return NOT_LETTER.sub(" ", asciify(folded)).strip()


def split_words(folded: str):
    for token in TOKEN.findall(folded):
        for i, part in enumerate(token.split("-")):
            part = re.sub("'+", "'", part).strip("'")
            if not part or part == "y" or (i > 0 and part in IZAFET):
                continue
            if any(ch in VOWELS for ch in part):
                yield part


def izafets(folded: str):
    for token in TOKEN.findall(folded):
        parts = [re.sub("'+", "'", part).strip("'") for part in token.split("-")]
        for stem, suffix in zip(parts, parts[1:]):
            if suffix in IZAFET_VOWELS and any(ch in VOWELS for ch in stem):
                yield stem, suffix


def key(form: str) -> str:
    return asciify(form).replace("'", "")


def leak_pattern() -> re.Pattern:
    corpus = tomllib.loads(CORPUS.read_text("utf-8"))
    lines = {skeleton(clean(line)) for item in corpus["beyit"] for line in item["lines"]}
    return re.compile("|".join(re.escape(line) for line in sorted(lines, key=len, reverse=True)))


def count(folded: str, counts: dict[str, Counter]) -> None:
    counts["form"].update(split_words(folded))
    counts["izafet"].update((key(stem), suffix) for stem, suffix in izafets(folded))


def read_conllu(path: Path, leak: re.Pattern, counts: dict[str, Counter]) -> int:
    skipped = 0
    keep = True
    for line in path.read_text("utf-8").splitlines():
        if line.startswith("# text ="):
            folded = clean(line.split("=", 1)[1])
            keep = not leak.search(skeleton(folded))
            skipped += not keep
            if keep:
                count(folded, counts)
        elif keep and line and line[0].isdigit():
            columns = line.split("\t")
            if columns[0].isdigit() and columns[2] != "_":
                counts["lemma"].update(split_words(clean(columns[2])))
    return skipped


def read_otc(path: Path, leak: re.Pattern, counts: dict[str, Counter]) -> int:
    skipped = 0
    for folded in clean(path.read_text("utf-8", errors="replace")).splitlines():
        if leak.search(skeleton(folded)):
            skipped += 1
            continue
        count(folded, counts)
    return skipped


def empty() -> dict[str, Counter]:
    return {"form": Counter(), "lemma": Counter(), "izafet": Counter()}


def ud_sources(leak: re.Pattern) -> tuple[dict[str, Counter], int]:
    counts, skipped = empty(), 0
    for repo, sha in UD.items():
        tree = json.loads(download(f"https://api.github.com/repos/UniversalDependencies/{repo}/git/trees/{sha}", f"{repo}-{sha[:8]}.json").read_text("utf-8"))
        for entry in tree["tree"]:
            if entry["path"].endswith(".conllu"):
                url = f"https://raw.githubusercontent.com/UniversalDependencies/{repo}/{sha}/{entry['path']}"
                path = download(url, f"{repo}-{sha[:8]}-{entry['path']}")
                skipped += read_conllu(path, leak, counts)
                print(f"  {repo}/{entry['path']}")
    return counts, skipped


def otc_source(leak: re.Pattern) -> tuple[dict[str, Counter], int]:
    counts, skipped = empty(), 0
    listing = json.loads(download(f"https://huggingface.co/api/datasets/{OTC}/tree/{OTC_REVISION}", f"otc-{OTC_REVISION[:8]}.json").read_text("utf-8"))
    for entry in listing:
        name = entry["path"]
        if not name.endswith(".txt") or name in OTC_SKIP:
            continue
        url = f"https://huggingface.co/datasets/{OTC}/resolve/{OTC_REVISION}/{urllib.parse.quote(name)}"
        skipped += read_otc(download(url, f"otc-{OTC_REVISION[:8]}-{name}"), leak, counts)
        print(f"  {OTC}/{name}")
    return counts, skipped


def rows(counts: dict[str, Counter], minimum: int = 1) -> list[tuple[str, str, int, str]]:
    table = [(key(form), form, n, kind) for kind in ("form", "lemma") for form, n in counts[kind].items() if n >= minimum]
    table += [(stem, suffix, n, "izafet") for (stem, suffix), n in counts["izafet"].items() if n >= minimum]
    return sorted(table, key=lambda row: (row[3], row[0], -row[2], row[1]))


def write(path: Path, table: list[tuple[str, str, int, str]]) -> None:
    lines = ["key\tform\tcount\tkind"] + [f"{k}\t{form}\t{count}\t{kind}" for k, form, count, kind in table]
    data = ("\n".join(lines) + "\n").encode("utf-8")
    with path.open("wb") as raw, gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as out:
        out.write(data)


def main() -> None:
    leak = leak_pattern()
    print("UD treebanks")
    ud, ud_skipped = ud_sources(leak)
    ud_table = rows(ud)
    write(DATA / "lexicon-ud.tsv.gz", ud_table)
    print(f"  {sum(ud['form'].values())} tokens, {len(ud_table)} rows, {ud_skipped} sentences dropped as test quotes")
    print("OTC corpus")
    otc, otc_skipped = otc_source(leak)
    otc_table = rows(otc, OTC_MIN_COUNT)
    write(DATA / "lexicon-otc.tsv.gz", otc_table)
    print(f"  {sum(otc['form'].values())} tokens, {len(otc_table)} rows, {otc_skipped} lines dropped as test quotes")


if __name__ == "__main__":
    main()
