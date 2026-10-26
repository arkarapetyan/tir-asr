"""T-MET-01 to T-MET-08: WER, CER, chrF, and the digit count for the bake-off (D-047, D-049).

The expected values are written out here from the definitions. They do not come from the code.
"""

import pytest

from tir_asr.eval.metrics import MetricError, cer, chrf, digit_words, edit_distance, wer


@pytest.mark.parametrize(
    ("ref", "hyp", "expected"),
    [
        (["a", "b", "c"], ["a", "b", "c"], 0),
        (["a", "b", "c"], ["a", "x", "c"], 1),
        (["a", "b", "c"], ["a", "c"], 1),
        (["a", "b"], ["a", "b", "c"], 1),
        ([], ["a", "b"], 2),
        (["a", "b"], [], 2),
        ([], [], 0),
        ("kitten", "sitting", 3),
    ],
)
def test_met_01_edit_distance(ref, hyp, expected):
    assert edit_distance(ref, hyp) == expected


def test_met_02_wer_uses_the_normalization():
    assert wer(["Բարև, տղերք։"], ["բարև տղերք"]) == 0.0


def test_met_03_wer_is_for_the_full_list_not_a_mean_of_the_lines():
    assert wer(["ա բ", "գ դ ե զ"], ["ա", "գ դ ե զ"]) == pytest.approx(1 / 6)


def test_met_04_wer_keeps_the_question_mark():
    assert wer(["Լսո՞ւմ եք"], ["լսում եք"]) == 0.5


def test_met_05_cer_counts_the_spaces():
    assert cer(["աբ գդ"], ["աբ գե"]) == pytest.approx(1 / 5)


def test_met_06_chrf_same_text_gives_100():
    assert chrf(["The cat sat on the mat."], ["The cat sat on the mat."]) == pytest.approx(100.0)


def test_met_06_chrf_no_common_character_gives_0():
    assert chrf(["abc"], ["xyz"]) == 0.0


def test_met_06_chrf_does_not_lowercase():
    assert chrf(["Hello there"], ["hello there"]) < 100.0


def test_met_07_digit_words():
    assert digit_words(["ժամը 8-ին", "15 000 դրամ"]) == 3


@pytest.mark.parametrize("metric", [wer, cer, chrf])
def test_met_08_lists_with_different_lengths(metric):
    with pytest.raises(MetricError, match="^metrics: 2 references and 1 hypotheses$"):
        metric(["ա", "բ"], ["ա"])


@pytest.mark.parametrize("metric", [wer, cer])
def test_met_08_references_with_no_words(metric):
    with pytest.raises(MetricError, match="^metrics: the references have no words$"):
        metric(["։ ,"], ["ա"])
