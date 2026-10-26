"""WER, CER, and chrF for the bake-off (D-047, D-049).

WER and CER compare the normalized Armenian texts (`normalize_hy`, D-047).
chrF compares the English texts with no normalization (sacrebleu default values).
Each score is for the full list: the total edits divided by the total reference length.
"""

from collections.abc import Callable, Sequence

from sacrebleu.metrics import CHRF

from tir_asr.errors import TirError
from tir_asr.eval.normalize import normalize_hy


class MetricError(TirError):
    """An input that gives no valid score."""


def edit_distance(ref: Sequence, hyp: Sequence) -> int:
    """Minimum number of substitutions, deletions, and insertions (each costs 1)."""
    previous = list(range(len(hyp) + 1))
    for i, ref_item in enumerate(ref, start=1):
        current = [i]
        for j, hyp_item in enumerate(hyp, start=1):
            current.append(
                min(
                    previous[j] + 1,  # deletion
                    current[j - 1] + 1,  # insertion
                    previous[j - 1] + (ref_item != hyp_item),  # substitution or match
                )
            )
        previous = current
    return previous[-1]


def wer(refs: Sequence[str], hyps: Sequence[str]) -> float:
    """Word error rate of the normalized Armenian texts, for the full list."""
    return _error_rate(refs, hyps, str.split)


def cer(refs: Sequence[str], hyps: Sequence[str]) -> float:
    """Character error rate of the normalized Armenian texts (spaces count), for the full list."""
    return _error_rate(refs, hyps, list)


def chrf(refs: Sequence[str], hyps: Sequence[str]) -> float:
    """chrF (0 to 100) of the English texts, for the full list."""
    _check_lengths(refs, hyps)
    return CHRF().corpus_score(list(hyps), [list(refs)]).score


def digit_words(texts: Sequence[str]) -> int:
    """Number of normalized words that contain a digit (D-047, N1)."""
    return sum(
        any(char.isdigit() for char in word)
        for text in texts
        for word in normalize_hy(text).split()
    )


def _check_lengths(refs: Sequence[str], hyps: Sequence[str]) -> None:
    if len(refs) != len(hyps):
        raise MetricError(f"metrics: {len(refs)} references and {len(hyps)} hypotheses")


def _error_rate(
    refs: Sequence[str], hyps: Sequence[str], units: Callable[[str], Sequence[str]]
) -> float:
    _check_lengths(refs, hyps)
    edits = 0
    total = 0
    for ref, hyp in zip(refs, hyps, strict=True):
        ref_units = units(normalize_hy(ref))
        edits += edit_distance(ref_units, units(normalize_hy(hyp)))
        total += len(ref_units)
    if total == 0:
        raise MetricError("metrics: the references have no words")
    return edits / total
