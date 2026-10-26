"""Armenian text normalization for WER and CER (D-047).

The eval normalizes the reference text and the ASR text before it compares them.
The program output and the MT input do not change.

Rules, in this order:

1. Unicode NFKC. This also opens the Armenian ligatures U+FB13 to U+FB17.
2. Lowercase.
3. Delete the marks that go inside a word, with no space: U+055C, U+055B, U+055F, U+055A.
   Keep the question mark U+055E (D-047, option P1).
4. Change "\u0565\u0582" to "\u0565\u057e". After rule 1, this also covers "\u0587".
5. Put one space in place of each other punctuation mark or symbol (Unicode categories P and S).
6. One space between words. No space at the start or at the end.

Digits do not change (D-047, option N1).
"""

import unicodedata

QUESTION_MARK = "\u055e"
IN_WORD_MARKS = "\u055c\u055b\u055f\u055a"
EV_CLASSICAL = "\u0565\u0582"
EV_REFORMED = "\u0565\u057e"

_DELETE_IN_WORD_MARKS = str.maketrans("", "", IN_WORD_MARKS)


def normalize_hy(text: str) -> str:
    """Return the normalized form of an Armenian text (D-047, rules 1 to 6)."""
    text = unicodedata.normalize("NFKC", text)
    text = text.lower()
    text = text.translate(_DELETE_IN_WORD_MARKS)
    text = text.replace(EV_CLASSICAL, EV_REFORMED)
    text = "".join(" " if _is_mark(char) else char for char in text)
    return " ".join(text.split())


def _is_mark(char: str) -> bool:
    """True for a punctuation mark or a symbol (rule 5), except the question mark."""
    return char != QUESTION_MARK and unicodedata.category(char)[0] in "PS"
