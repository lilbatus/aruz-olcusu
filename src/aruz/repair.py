import re
import tomllib
import unicodedata
from dataclasses import dataclass
from functools import cache
from importlib.resources import files
from itertools import product

from turkish.deasciifier import Deasciifier

from aruz import lexicon
from aruz.match import best_fits
from aruz.meters import meters
from aruz.normalize import asciify, fold
from aruz.readings import penalties
from aruz.syllables import syllabify

LETTERS = "A-Za-zÇçĞğİıÖöŞşÜüÂâÎîÛûÊêÔôĀāĪīŪū"
APOSTROPHES = "'’ʿʾ‘"
WORD = re.compile(f"[{LETTERS}]+(?:[{APOSTROPHES}][{LETTERS}]+)*[{APOSTROPHES}]?")
PLAIN = re.compile(f"[A-Za-z{APOSTROPHES}]+")
NO_APOSTROPHES = str.maketrans("", "", APOSTROPHES)
BACK = set("aıouâû")
VOWELS = set("aeıioöuüâîû")
QUESTION_VOWELS = {"a": "ı", "ı": "ı", "â": "ı", "o": "u", "u": "u", "û": "u", "ö": "ü", "ü": "ü"}
SWAPS = {
    "ı": "i", "i": "ı", "yı": "yi", "yi": "yı", "u": "ü", "ü": "u", "vü": "vu", "vu": "vü",
    "mı": "mi", "mi": "mı", "mu": "mü", "mü": "mu",
}


@dataclass
class Form:
    text: str
    count: int = 0


@dataclass
class Spot:
    index: int
    misra: int
    start: int
    end: int
    original: str
    forms: list[Form]
    source: str
    fixed: bool = False
    choice: int = 0
    uncertain: bool = False
    by_meter: bool = False
    by_user: bool = False

    @property
    def text(self) -> str:
        return self.forms[self.choice].text


@dataclass
class Restoration:
    original: str
    spots: list[Spot]

    @property
    def text(self) -> str:
        return splice(self.original, 0, len(self.original), self.spots, {})


def key(word: str) -> str:
    return asciify(word).lower().translate(NO_APOSTROPHES)


def lower(ch: str) -> str:
    return {"I": "ı", "İ": "i"}.get(ch, ch.lower())


def upper(ch: str) -> str:
    return {"i": "İ", "ı": "I"}.get(ch, ch.upper())


def merge(form: str, typed: str) -> str:
    out = []
    i = j = 0
    while i < len(form) or j < len(typed):
        if j < len(typed) and typed[j] in APOSTROPHES:
            out.append(typed[j])
            j += 1
            i += i < len(form) and form[i] in APOSTROPHES
        elif i < len(form) and form[i] in APOSTROPHES:
            out.append(form[i])
            i += 1
        else:
            ch = lower(form[i])
            out.append(upper(ch) if typed[j].isupper() else ch)
            i += 1
            j += 1
    return "".join(out)


def splice(text: str, start: int, end: int, spots: list["Spot"], picks: dict[int, str]) -> str:
    parts = []
    last = start
    for spot in spots:
        if start <= spot.start and spot.end <= end:
            parts.append(text[last:spot.start])
            parts.append(picks.get(spot.index, spot.text))
            last = spot.end
    parts.append(text[last:end])
    return "".join(parts)


@cache
def phrases() -> dict[tuple[str, ...], tuple[str, ...]]:
    data = tomllib.loads(files("aruz").joinpath("data/phrases.toml").read_text("utf-8"))
    return {tuple(key(word) for word in entry["words"]): tuple(entry["words"]) for entry in data["phrase"]}


def misra_spans(text: str) -> list[tuple[int, int]]:
    spans = []
    for line in re.finditer(r"[^\n]+", text):
        for piece in re.finditer(r"[^/]+", line.group()):
            if piece.group().strip():
                spans.append((line.start() + piece.start(), line.start() + piece.end()))
    return spans


def last_vowel(word: str) -> str:
    vowels = [ch for ch in fold(word) if ch in VOWELS]
    return vowels[-1] if vowels else "e"


def izafet(suffix: str, previous: str) -> str:
    if suffix == "i" and fold(previous)[-1:] in ("a", "e"):
        return "i"
    vowel = "ı" if last_vowel(previous) in BACK else "i"
    return "y" + vowel if suffix == "yi" else vowel


def izafet_from_corpus(suffix: str, previous: "Spot") -> str:
    options = ("yı", "yi") if suffix == "yi" else ("ı", "i")
    seen = lexicon.izafets(key(previous.original))
    back, front = (seen.get(option, 0) for option in options)
    if back + front >= penalties()["repair_izafet_min"] and back != front:
        return options[0] if back > front else options[1]
    return izafet(suffix, previous.forms[0].text)


def conjunction(word: str, previous: str) -> str:
    if word == "vu":
        return "vü"
    return "u" if last_vowel(previous) in BACK else "ü"


def question(previous: str) -> str:
    return "m" + QUESTION_VOWELS.get(last_vowel(previous), "i")


def unique(forms: list[Form]) -> list[Form]:
    merged: dict[str, Form] = {}
    for form in forms:
        if form.text in merged:
            merged[form.text].count += form.count
        else:
            merged[form.text] = Form(form.text, form.count)
    return sorted(merged.values(), key=lambda form: -form.count)


def with_fallback(forms: list[Form], fallback: str) -> list[Form]:
    if all(form.text != fallback for form in forms):
        forms.append(Form(fallback, 0))
    return forms


def rule(result: str, typed: str) -> tuple[list[Form], str, bool]:
    return [Form(merge(result, typed)), Form(merge(SWAPS[result], typed))], "rule", True


def candidates(typed: str, guess: str, previous: "Spot | None", after_hyphen: bool, phrase: str | None) -> tuple[list[Form], str, bool]:
    if not PLAIN.fullmatch(typed):
        return [Form(typed)], "typed", True
    if phrase:
        return [Form(merge(phrase, typed))], "phrase", True
    k = key(typed)
    if previous and after_hyphen and k in ("i", "yi"):
        return rule(izafet_from_corpus(k, previous), typed)
    if previous and not after_hyphen and k in ("u", "vu"):
        return rule(conjunction(k, previous.forms[0].text), typed)
    if previous and not after_hyphen and k in ("mi", "mu"):
        return rule(question(previous.forms[0].text), typed)
    fallback = merge(guess, typed)
    entries = lexicon.lookup(k)
    if entries:
        forms = unique([Form(merge(form, typed), count) for form, count in entries])
        floor = penalties()["repair_min_share"] * forms[0].count
        return with_fallback([form for form in forms if form.count >= floor], fallback), "lexicon", False
    found = lexicon.stem(k) if typed.translate(NO_APOSTROPHES) == typed else None
    if found:
        end, form, count = found
        return with_fallback([Form(merge(form + guess[end:], typed), count)], fallback), "stem", False
    return [Form(fallback)], "deasciifier", False


def phrase_matches(text: str, tokens: list[re.Match]) -> dict[int, str]:
    keys = [key(token.group()) for token in tokens]
    found = {}
    for words_key, words in phrases().items():
        size = len(words_key)
        for i in range(len(tokens) - size + 1):
            window = tokens[i:i + size]
            if tuple(keys[i:i + size]) != words_key:
                continue
            if not all(PLAIN.fullmatch(t.group()) for t in window):
                continue
            if any(text[a.end():b.start()].strip() for a, b in zip(window, window[1:])):
                continue
            found.update({i + n: word for n, word in enumerate(words)})
    return found


def misra_spots(text: str, start: int, end: int, misra: int, first_index: int) -> list[Spot]:
    guess = Deasciifier(asciify(text[start:end])).convert_to_turkish()
    tokens = list(WORD.finditer(text, start, end))
    matched = phrase_matches(text, tokens)
    spots: list[Spot] = []
    for n, token in enumerate(tokens):
        previous = spots[-1] if spots else None
        after_hyphen = token.start() > 0 and text[token.start() - 1] == "-"
        forms, source, fixed = candidates(
            token.group(), guess[token.start() - start:token.end() - start], previous, after_hyphen, matched.get(n)
        )
        spots.append(Spot(first_index + n, misra, token.start(), token.end(), token.group(), forms, source, fixed))
    return spots


def contested(forms: list[Form]) -> bool:
    counts = sorted((form.count for form in forms), reverse=True)
    return len(counts) > 1 and counts[1] > 0 and counts[1] >= penalties()["repair_uncertain_ratio"] * counts[0]


def signature(text: str) -> tuple:
    return tuple((s.closed, s.long_vowel, len(s.coda) >= 2, bool(s.onset)) for s in syllabify(fold(text)))


def groups(spot: Spot) -> list[list[int]]:
    found: dict[tuple, list[int]] = {}
    for i, form in enumerate(spot.forms):
        found.setdefault(signature(form.text), []).append(i)
    return sorted(found.values(), key=lambda members: -max(spot.forms[i].count for i in members))


def choose_by_count(spots: list[Spot]) -> None:
    for spot in spots:
        if not spot.fixed:
            spot.uncertain = contested(spot.forms)


def misra_costs(text: str, span: tuple[int, int], spots: list[Spot]) -> tuple[list[Spot], list[list[list[int]]], dict[tuple, tuple[dict, float]]]:
    w = penalties()
    open_spots = [spot for spot in spots if not spot.fixed and len(groups(spot)) > 1]
    if len(open_spots) > w["repair_max_ambiguous"]:
        def closeness(spot: Spot) -> float:
            first, second = groups(spot)[:2]
            return max(spot.forms[i].count for i in second) / max(1, max(spot.forms[i].count for i in first))
        open_spots = sorted(open_spots, key=closeness, reverse=True)[: w["repair_max_ambiguous"]]
    options = [groups(spot) for spot in open_spots]
    results = {}
    for combo in product(*[range(len(o)) for o in options]):
        picks = {spot.index: spot.forms[option[g][0]].text for spot, option, g in zip(open_spots, options, combo)}
        line = splice(text, span[0], span[1], spots, picks)
        prior = w["repair_rare_form"] * sum(1 for g in combo if g)
        results[combo] = (best_fits(line), prior)
    return open_spots, options, results


def choose_by_meter(text: str, spots: list[Spot]) -> None:
    w = penalties()
    spans = misra_spans(text)
    tables = [misra_costs(text, span, [s for s in spots if s.misra == n]) for n, span in enumerate(spans)]

    def cost(fits: dict, meter_id: str) -> float:
        return fits[meter_id].cost if meter_id in fits else w["unmatched"]

    def total(meter_id: str) -> float:
        return sum(min(cost(fits, meter_id) + prior for fits, prior in results.values()) for _, _, results in tables)

    best = min((m.id for m in meters()), key=total)
    decided = set()
    for open_spots, options, results in tables:
        chosen = min(results, key=lambda combo: cost(results[combo][0], best) + results[combo][1])
        for j, (spot, option) in enumerate(zip(open_spots, options)):
            decided.add(spot.index)
            scores = []
            for g in range(len(option)):
                trial = chosen[:j] + (g,) + chosen[j + 1:]
                scores.append(cost(results[trial][0], best))
            winners = [g for g, score in enumerate(scores) if score <= min(scores) + 1e-9]
            group = option[chosen[j]]
            spot.choice = group[0]
            spot.by_meter = len(winners) == 1
            pool = [spot.forms[i] for g in winners for i in option[g]] if len(winners) > 1 else [spot.forms[i] for i in group]
            spot.uncertain = contested(pool)
    for spot in spots:
        if not spot.fixed and spot.index not in decided:
            spot.uncertain = contested(spot.forms)


def restore(text: str, use_meter: bool = True, choices: dict[int, int] | None = None) -> Restoration:
    text = unicodedata.normalize("NFC", text.replace("\r\n", "\n").replace("\r", "\n"))
    spots: list[Spot] = []
    for misra, (start, end) in enumerate(misra_spans(text)):
        spots.extend(misra_spots(text, start, end, misra, len(spots)))
    for spot in spots:
        pick = (choices or {}).get(spot.index)
        if pick is not None and 0 <= pick < len(spot.forms):
            spot.choice, spot.fixed, spot.by_user = pick, True, True
    if use_meter:
        choose_by_meter(text, spots)
    else:
        choose_by_count(spots)
    return Restoration(text, spots)
