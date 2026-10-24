import re
import unicodedata
from dataclasses import dataclass

CIRCUMFLEX = "̂"
MACRON = "̄"
KEPT_MARKS = {CIRCUMFLEX, "̧", "̆", "̈"}
AYN_MARKS = set("'’‘ʿʾʼ`´")
IZAFET = {"i", "ı", "u", "ü", "yi", "yı", "yu", "yü"}
CONJUNCTIONS = {"u", "ü", "vu", "vü"}
FLAT_VOWELS = str.maketrans({"ô": "o", "ê": "e"})
ASCII = str.maketrans("çÇğĞıİöÖşŞüÜâÂîÎûÛêÊôÔāĀīĪūŪ", "cCgGiIoOsSuUaAiIuUeEoOaAiIuU")


@dataclass(frozen=True)
class Word:
    text: str
    kind: str = "plain"


def fold(text: str) -> str:
    text = text.replace("I", "ı").replace("İ", "i").lower()
    chars = []
    for ch in unicodedata.normalize("NFD", text):
        if ch == MACRON:
            chars.append(CIRCUMFLEX)
        elif ch in AYN_MARKS:
            chars.append("'")
        elif unicodedata.combining(ch) and ch not in KEPT_MARKS:
            continue
        else:
            chars.append(ch)
    return unicodedata.normalize("NFC", "".join(chars)).translate(FLAT_VOWELS)


def asciify(text: str) -> str:
    return text.translate(ASCII)


def clean(text: str) -> str:
    return re.sub(r"[^\w'\-\s]|[\d_]", " ", text)


def parse_misra(line: str) -> list[Word]:
    words = []
    for token in clean(fold(line)).split():
        parts = [part for part in token.split("-") if part]
        for i, part in enumerate(parts):
            if i > 0 and part in IZAFET:
                words.append(Word(part, "izafet"))
            elif len(parts) == 1 and part in CONJUNCTIONS and words:
                words.append(Word(part, "conjunction"))
            else:
                words.append(Word(part))
    return words


def split_beyits(text: str) -> list[list[str]]:
    beyits = []
    for block in re.split(r"\n\s*\n", text.strip()):
        misras = [m.strip() for line in block.splitlines() for m in line.split("/") if m.strip()]
        beyits.extend(misras[i:i + 2] for i in range(0, len(misras), 2))
    return beyits
