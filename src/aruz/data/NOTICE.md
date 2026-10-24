# Third-party data

## lexicon-ud.tsv.gz

License: [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/)

Word, lemma and izafet counts derived from two Universal Dependencies treebanks, release r2.18:

- UD_Ottoman_Turkish-BOUN, Özateş et al. 2024, commit `7252f055d59356bd216af0551cdae45e4c7940bb`,
  https://github.com/UniversalDependencies/UD_Ottoman_Turkish-BOUN
- UD_Ottoman_Turkish-DUDU, Enes Yılandiloğlu, commit `dd23a14215f5e3042d3d91bf997bf92327fc8fcc`,
  https://github.com/UniversalDependencies/UD_Ottoman_Turkish-DUDU

Changes: sentences were tokenized and counted. Scholarly letters were mapped to the
transcription used by aruz (ā ī ū to â î û, ḫ ḥ to h, ḳ to k, ṣ to s, ṭ to t, ẓ ż to z, ḍ to d,
ñ to n, ġ to ğ or g, ʿ ʾ to '). Sentences that quote a line of the aruz test set were dropped.
This file is shared under the same license.

## lexicon-otc.tsv.gz

License: [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/). Non-commercial use only.

Word and izafet counts derived from OTC-Corpus by BUCOLIN, revision
`c8a8e82c6fc46aaadde130f4e39d0cb6488268e8`, https://huggingface.co/datasets/BUCOLIN/OTC-Corpus

Changes: the 64 text files were tokenized and counted; only forms seen at least three times were
kept. Lines that quote a line of the aruz test set were dropped, and apostrophes that separate a
suffix from a capitalized name were removed. Delete this file for commercial use; aruz then works
with the UD lexicon alone.

## Regenerating

Both files are produced by `scripts/build_lexicon.py` from the pinned revisions above.
