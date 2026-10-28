"""Output rules for the two texts of each segment (ARCHITECTURE.md section 2.9, D-066).

The template `TextStep.process` applies these rules for P1 and P4, so that the HY line has only
Armenian text and the EN line has only English text (D-066 part 3, Aren: "ALWAYS").

Rule 1, hesitation marks (D-066 part 1). [RUN, C7, script S5, the P4 call] For the interjection
«Հը» of s5-43, the Seamless model wrote "#err" in the Armenian text and "#Hmm" in the English
text; P1 wrote «հը». The model writes the mark with normal tokens of its vocabulary ("▁#",
"err"), so the mark comes from the model, not from the decode or the terminal.

- Armenian: delete each "#" with the Latin letters after it, the spaces before it, and one comma
  directly after it. A text that has only marks becomes empty (then D-031 applies).
- English: delete each "#" directly before a Latin letter. The word stays: "#Hmm" gives "Hmm".

Rule 2, scripts (D-066 part 3). A word is a part of the text between two spaces. A word with a
character that is not allowed for its line is not shown: each run of such words becomes one mark
`FOREIGN`, so that the line shows that the program removed a part of the model text (R10).

- Armenian line: the letters and the marks of the Armenian block (U+0531 to U+0556, U+0559 to
  U+055F, U+0561 to U+0587, U+0589, U+058A), the Armenian ligatures (U+FB13 to U+FB17), the
  digits 0 to 9, and the punctuation in `ARMENIAN_PUNCTUATION`.
- English line: the printable ASCII characters (U+0020 to U+007E) and the punctuation in
  `ENGLISH_PUNCTUATION`. A letter with an accent (for example "é") is not allowed.

A text that no rule changes stays the same, also its spaces. A text that a rule changes has one
space between words, and no space at the start or at the end.

This module is core: it imports no model package (D-021).
"""

import re
from collections.abc import Callable

FOREIGN = "[?]"
ARMENIAN_PUNCTUATION = frozenset(",.:;!?-()«»\"'…–—%")
ENGLISH_PUNCTUATION = frozenset("’‘“”–—…")
_ARMENIAN_RANGES = ((0x0531, 0x0556), (0x0559, 0x055F), (0x0561, 0x0587), (0x0589, 0x058A))
_LIGATURES = (0xFB13, 0xFB17)
_HY_MARK = re.compile(r"\s*#[A-Za-z]+,?")
_EN_MARK = re.compile(r"#(?=[A-Za-z])")


def armenian_char(char: str) -> bool:
    """True for a character that the Armenian line allows (rule 2)."""
    code = ord(char)
    if any(low <= code <= high for low, high in _ARMENIAN_RANGES):
        return True
    if _LIGATURES[0] <= code <= _LIGATURES[1]:
        return True
    return "0" <= char <= "9" or char in ARMENIAN_PUNCTUATION


def english_char(char: str) -> bool:
    """True for a character that the English line allows (rule 2)."""
    return " " <= char <= "~" or char in ENGLISH_PUNCTUATION


def clean_armenian(text: str) -> str:
    """The Armenian text after rule 1 and rule 2."""
    if "#" in text:
        text = _HY_MARK.sub("", text).strip()
    return _only(text, armenian_char)


def clean_english(text: str) -> str:
    """The English text after rule 1 and rule 2."""
    if "#" in text:
        text = _EN_MARK.sub("", text)
    return _only(text, english_char)


def _only(text: str, allowed: Callable[[str], bool]) -> str:
    """Rule 2: each run of words with a character that is not allowed becomes one `FOREIGN`."""
    words = text.split()
    if all(allowed(char) for word in words for char in word):
        return text
    kept: list[str] = []
    for word in words:
        if all(allowed(char) for char in word):
            kept.append(word)
        elif not kept or kept[-1] != FOREIGN:
            kept.append(FOREIGN)
    return " ".join(kept)
