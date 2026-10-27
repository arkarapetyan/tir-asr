"""T-SPK-06, T-SPK-08, T-SPK-09, T-SPK-10: the speaker eval core with fakes (D-057).

No model. The expected values come from the approved test table (TESTS.md section 2.7): the
streams from the label times, the sweep from vectors at known angles (the cosine of two vectors
is cos(a1 - a2)).
"""

import math
import re

import numpy as np
import pytest

from tir_asr.config import SAMPLE_RATE
from tir_asr.eval.data import DataError, Label, ScriptLine
from tir_asr.eval.nearest import NearestClusterer
from tir_asr.eval.spk_run import Embedded, SweepPoint, pairwise, pass_range, sweep, truth_of
from tir_asr.eval.streams import Stream, Turn, call_stream, cut, join, stream_d
from tir_asr.speakers.cluster import CentroidClusterer


def at(degrees: float) -> np.ndarray:
    radians = math.radians(degrees)
    return np.array([math.cos(radians), math.sin(radians)])


def numbered(seconds: float) -> np.ndarray:
    """Audio whose sample k has the value k, so a test can see which samples a cut keeps."""
    return np.arange(round(seconds * SAMPLE_RATE), dtype=np.float32)


def line(line_id: str, speaker: str) -> ScriptLine:
    return ScriptLine(line_id, speaker, "mic" if speaker == "Me" else "call", "", "")


def test_spk_06_call_stream_has_only_the_call_side_turns():
    lines = [line("s1-01", "Me"), line("s1-02", "Speaker 1"), line("s1-03", "Speaker 2")]
    labels = [Label("s1-03", 5.0, 7.0), Label("s1-01", 0.0, 0.5), Label("s1-02", 1.0, 3.0)]

    stream = call_stream("s1", numbered(10.0), lines, labels)

    assert stream.name == "s1"
    assert stream.turns == [Turn(1.0, 3.0, "s1/Speaker 1"), Turn(5.0, 7.0, "s1/Speaker 2")]


def test_spk_06_cut_and_join():
    s1 = Stream("s1", numbered(10.0), [Turn(1.0, 3.0, "a"), Turn(5.0, 7.0, "b")])

    first = cut(s1, 0.0, 4.0, "s1a")
    second = cut(s1, 4.0, None, "s1b")
    joined = join([second, first], "j")

    assert len(first.audio) == 4 * SAMPLE_RATE
    assert first.turns == [Turn(1.0, 3.0, "a")]
    assert second.audio[0] == 4 * SAMPLE_RATE
    assert len(second.audio) == 6 * SAMPLE_RATE
    assert second.turns == [Turn(1.0, 3.0, "b")]
    assert len(joined.audio) == 10 * SAMPLE_RATE
    assert joined.turns == [Turn(1.0, 3.0, "b"), Turn(7.0, 9.0, "a")]


def test_spk_06_cut_inside_a_turn():
    s1 = Stream("s1", numbered(10.0), [Turn(1.0, 3.0, "a")])

    message = "data: s1: the cut at 2.00 s is inside a turn (1.00–3.00 s)"
    with pytest.raises(DataError, match=f"^{re.escape(message)}$"):
        cut(s1, 2.0, None, "x")


def test_spk_06_stream_d():
    s1 = Stream("s1", numbered(40.0), [Turn(10.0, 12.0, "s1/A"), Turn(36.0, 38.0, "s1/B")])
    s2 = Stream("s2", numbered(5.0), [Turn(1.0, 2.0, "s2/A")])
    s3 = Stream("s3", numbered(5.0), [Turn(1.0, 2.0, "s3/A")])

    d = stream_d(s1, s2, s3)

    # S1 0-34 s, S2 (5 s) from 34 s, S1 34-40 s from 39 s, S3 from 45 s.
    assert d.name == "D"
    assert len(d.audio) == 50 * SAMPLE_RATE
    assert d.turns == [
        Turn(10.0, 12.0, "s1/A"),
        Turn(35.0, 36.0, "s2/A"),
        Turn(41.0, 43.0, "s1/B"),
        Turn(46.0, 47.0, "s3/A"),
    ]
    assert d.audio[39 * SAMPLE_RATE] == 34 * SAMPLE_RATE  # the S1 part after the cut


def test_spk_06_truth_of_a_segment():
    turns = [Turn(1.0, 3.0, "a"), Turn(3.5, 6.0, "b")]

    assert truth_of(2.5, 4.0, turns) == "a"  # 0.5 s with a, 0.5 s with b: the earlier turn
    assert truth_of(3.2, 5.0, turns) == "b"  # no overlap with a, 1.5 s with b
    assert truth_of(7.0, 8.0, turns) is None


def items() -> list[Embedded]:
    # A at 0 and 30 deg, B at 100 and 130 deg; then a segment with no turn at 200 deg.
    def item(angle, duration, truth):
        return Embedded(at(angle), 0.01, duration, truth)

    return [
        item(0, 4.0, "A"),
        item(30, 2.0, "A"),
        item(100, 3.0, "B"),
        item(130, 1.0, "B"),
        item(200, 3.0, None),
    ]


@pytest.mark.parametrize("rule", [CentroidClusterer, NearestClusterer])
def test_spk_08_sweep(rule):
    points = sweep(items(), rule, [0.5, 0.95], min_new_s=1.0)

    # 0.5: A A | B B, then the segment with no turn starts a third speaker (it is not scored).
    assert points[0] == SweepPoint(0.5, 1.0, 1.0, wrong=0, scored=4, speakers=3)
    # 0.95: every segment starts a speaker. Best mapping: S1 -> A (4 s), S3 -> B (3 s) of 10 s.
    assert points[1] == SweepPoint(0.95, 0.7, 0.5, wrong=2, scored=4, speakers=5)


def test_spk_09_pairwise():
    vectors = [
        Embedded(at(0), 0.0, 3.0, "A"),
        Embedded(2 * at(60), 0.0, 3.0, "A"),  # the length does not change the cosine
        Embedded(at(90), 0.0, 3.0, "B"),
        Embedded(at(0), 0.0, 3.0, None),  # not scored
    ]

    result = pairwise(vectors)

    assert result.same_pairs == 1
    assert result.same_min == pytest.approx(0.5)
    assert result.same_mean == pytest.approx(0.5)
    assert result.different_pairs == 2
    assert result.different_max == pytest.approx(math.cos(math.radians(30)))
    assert result.different_mean == pytest.approx(math.cos(math.radians(30)) / 2)


def test_spk_09_pairwise_with_one_speaker():
    result = pairwise([Embedded(at(0), 0.0, 3.0, "A"), Embedded(at(10), 0.0, 3.0, "A")])

    assert result.different_pairs == 0
    assert result.different_max is None
    assert result.different_mean is None


def column(wrong: list[int]) -> list[SweepPoint]:
    thresholds = [0.2, 0.25, 0.3, 0.35, 0.4]
    return [SweepPoint(t, 1.0, 1.0, w, 10, 2) for t, w in zip(thresholds, wrong, strict=True)]


def test_spk_10_pass_range():
    # Passing (each stream 1 or fewer wrong): 0.25, 0.3, 0.35.
    assert pass_range({"S": column([3, 1, 0, 0, 2]), "T": column([2, 0, 1, 0, 0])}) == (0.25, 0.35)
    # Two runs of equal length: the first run.
    assert pass_range({"S": column([0, 2, 0, 2, 0])}) == (0.2, 0.2)
    # No passing threshold.
    assert pass_range({"S": column([2, 2, 2, 2, 2])}) is None
