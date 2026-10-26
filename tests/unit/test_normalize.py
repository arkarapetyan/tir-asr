"""T-NORM-01 to T-NORM-09: Armenian text normalization for WER and CER (D-047).

The expected texts are written out here from the D-047 rules. They do not come from the code.
D-047: rule 3 keeps the question mark U+055E (option P1). Digits do not change (option N1).
Marks that are hard to see are written as escapes, for example "\\u055e" for the question mark.
"""

import re
from pathlib import Path

import pytest

from tir_asr.eval.normalize import normalize_hy

SCRIPTS = Path(__file__).resolve().parents[2] / "docs" / "eval" / "scripts.md"

UPPER_OR_LOWER_LETTER = re.compile("[\u0531-\u0556\u0561-\u0587]")
NORMALIZED_LINE = re.compile("[\u0561-\u0586\u055e]+( [\u0561-\u0586\u055e]+)*")


def script_lines() -> list[str]:
    """The Armenian column of each script line in docs/eval/scripts.md (S1 to S4)."""
    rows = [
        line
        for line in SCRIPTS.read_text(encoding="utf-8").splitlines()
        if re.match(r"\| s\d-\d\d", line)
    ]
    return [row.split("|")[3].strip() for row in rows]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("\ufb13ա", "մնա"),
        ("\ufb14", "մե"),
        ("\ufb15", "մի"),
        ("\ufb16", "վն"),
        ("\ufb17", "մխ"),
    ],
)
def test_norm_01_nfkc_opens_the_armenian_ligatures(text, expected):
    assert normalize_hy(text) == expected


def test_norm_02_lowercase():
    assert normalize_hy("Բարև ԵՐԵՎԱՆ OK") == "բարեվ երեվան ok"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("\u0587", "եվ"),
        ("եւ", "եվ"),
        ("Եվ", "եվ"),
        ("ԵՎ", "եվ"),
        ("ԵՒ", "եվ"),
        ("Երևան", "երեվան"),
        ("Երեւան", "երեվան"),
        ("Երեվան", "երեվան"),
        ("ուր", "ուր"),
        ("Լսում", "լսում"),
    ],
)
def test_norm_03_three_spellings_of_ev_give_one_form(text, expected):
    assert normalize_hy(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Լսո\u055eւմ", "լսո\u055eւմ"),
        ("ԼՍՈ\u055eՒՄ", "լսո\u055eւմ"),
        ("Վա\u055cյ", "վայ"),
        ("ե\u055bս", "ես"),
        ("ա\u055fբ", "աբ"),
        ("ա\u055aբ", "աբ"),
        ("լսում \u055e", "լսում \u055e"),
    ],
)
def test_norm_04_marks_inside_a_word_go_except_the_question_mark(text, expected):
    assert normalize_hy(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Բարև, տղերք\u0589 Լսո\u055eւմ եք ինձ\u0589", "բարեվ տղերք լսո\u055eւմ եք ինձ"),
        ("այսօր\u055d մինչև", "այսօր մինչեվ"),
        ("երկու-մեկ", "երկու մեկ"),
        ("երկու\u058aմեկ", "երկու մեկ"),
        ("\u00abՆռնենի\u00bb", "նռնենի"),
    ],
)
def test_norm_05_punctuation_becomes_a_space(text, expected):
    assert normalize_hy(text) == expected


@pytest.mark.parametrize(
    "mark",
    [".", ",", ":", ";", "?", "!", '"', "\u2026", "\u2014", "\u0589", "\u055d", "\u00ab", "\u00bb"],
)
def test_norm_05_each_mark_becomes_one_space(mark):
    assert normalize_hy(f"ա{mark}բ") == "ա բ"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("  ա\tբ\n\nգ  ", "ա բ գ"),
        ("\u0589 ,", ""),
        ("", ""),
    ],
)
def test_norm_06_one_space_between_words_and_none_at_the_ends(text, expected):
    assert normalize_hy(text) == expected


def test_norm_07_digits_do_not_change():
    assert normalize_hy("ժամը 8-ին") == "ժամը 8 ին"


def test_norm_08_each_script_word_stays_one_word():
    lines = script_lines()
    assert len(lines) == 44, "docs/eval/scripts.md: expected 44 lines in S1 to S4"

    for line in lines:
        words_with_a_letter = [w for w in line.split() if UPPER_OR_LOWER_LETTER.search(w)]

        result = normalize_hy(line)

        assert NORMALIZED_LINE.fullmatch(result), f"{line!r} -> {result!r}"
        assert len(result.split()) == len(words_with_a_letter), f"{line!r} -> {result!r}"


def test_norm_09_a_second_run_changes_nothing():
    for line in script_lines():
        once = normalize_hy(line)

        assert normalize_hy(once) == once, f"{line!r}"
