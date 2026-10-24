from dataclasses import dataclass

from aruz.normalize import Word

VOWELS = set("aeıioöuüâîû")
LONG_VOWELS = set("âîû")


@dataclass(frozen=True)
class Syllable:
    onset: str
    vowel: str
    coda: str
    word: int

    @property
    def text(self) -> str:
        return self.onset + self.vowel + self.coda

    @property
    def long_vowel(self) -> bool:
        return self.vowel in LONG_VOWELS

    @property
    def closed(self) -> bool:
        return bool(self.coda)


def syllabify(word: str, index: int = 0) -> list[Syllable]:
    nuclei = [i for i, ch in enumerate(word) if ch in VOWELS]
    syllables = []
    start = 0
    for n, pos in enumerate(nuclei):
        if n + 1 < len(nuclei):
            gap = nuclei[n + 1] - pos - 1
            end = pos + 1 + max(gap - 1, 0)
        else:
            end = len(word)
        syllables.append(Syllable(word[start:pos], word[pos], word[pos + 1:end], index))
        start = end
    return syllables


def syllabify_words(words: list[Word]) -> list[list[Syllable]]:
    return [syllabify(word.text, i) for i, word in enumerate(words)]
