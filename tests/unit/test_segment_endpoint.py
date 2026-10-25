"""T-SEG-01 to T-SEG-09: the Endpointer state machine (ARCHITECTURE.md section 2.2).

Frame `k` arrives at (k + 1) x 0.032 s, so its start time is k x 0.032 s (TESTS.md 2.4).
The fake SpeechProbability returns the next number of a list. The audio of frame `k` is a
ramp: sample `n` of the stream has the value `n`, so a test can see which samples a
segment holds.
"""

import numpy as np
import pytest

from tir_asr.config import Params
from tir_asr.segment.endpoint import Endpointer, SegmentError
from tir_asr.types import AudioBlock

FRAME = 512
FRAME_S = 0.032
PAD = 480  # vad_speech_pad_ms = 30 at 16 kHz

SPEECH = 0.9
SILENT = 0.1
MID = 0.4  # between vad_end_threshold (0.35) and vad_threshold (0.5)


class FakeVad:
    """SpeechProbability fake: each call returns the next number of the list."""

    def __init__(self, probabilities):
        self._numbers = iter(probabilities)

    def __call__(self, samples):
        return next(self._numbers)


def block(k: int) -> AudioBlock:
    samples = np.arange(k * FRAME, (k + 1) * FRAME, dtype=np.float32)
    return AudioBlock(source="Me", samples=samples, arrival=(k + 1) * FRAME_S)


def run(probabilities):
    """Push one block for each probability. Return the Endpointer and [(frame, Segment)]."""
    endpointer = Endpointer(Params(), FakeVad(probabilities))
    found = []
    for k in range(len(probabilities)):
        segment = endpointer.push(block(k))
        if segment is not None:
            found.append((k, segment))
    return endpointer, found


# frames 0-4 silent, frames 5-24 speech, then 20 silent frames (the input of T-SEG-01)
BASE = [SILENT] * 5 + [SPEECH] * 20 + [SILENT] * 20


def test_seg_01_start_is_the_start_of_the_first_speech_frame():
    _, found = run(BASE)

    assert len(found) == 1
    segment = found[0][1]
    assert segment.start == pytest.approx(0.160)
    assert segment.source == "Me"
    assert segment.cut is False


def test_seg_02_true_end_and_close_after_16_silent_frames():
    _, found = run(BASE)

    # Frame 25 is the first silent frame. Frame 40 is the 16th silent frame.
    assert [k for k, _ in found] == [40]
    segment = found[0][1]
    assert segment.speech_end == pytest.approx(0.800)
    assert segment.closed == pytest.approx(1.312)


def test_seg_03_speech_after_a_short_silence_is_one_segment():
    # frames 25-34: 10 silent frames (under 16). Speech again in frames 35-54.
    probabilities = [SILENT] * 5 + [SPEECH] * 20 + [SILENT] * 10 + [SPEECH] * 20 + [SILENT] * 20
    _, found = run(probabilities)

    assert len(found) == 1
    segment = found[0][1]
    assert segment.start == pytest.approx(0.160)
    assert segment.speech_end == pytest.approx(55 * FRAME_S)  # start of the second silence
    assert found[0][0] == 55 + 15  # the 16th frame of the second silence


def test_seg_04_frame_between_the_thresholds_inside_speech_does_not_start_a_silence():
    # Frames 10-12 and 18-19 are at 0.4. The first frame under 0.35 is frame 20.
    probabilities = (
        [SILENT] * 5 + [SPEECH] * 5 + [MID] * 3 + [SPEECH] * 5 + [MID] * 2 + [SILENT] * 20
    )
    _, found = run(probabilities)

    assert [k for k, _ in found] == [20 + 15]
    assert found[0][1].speech_end == pytest.approx(20 * FRAME_S)


def test_seg_04_frame_between_the_thresholds_inside_a_silence_counts_as_silence():
    # Speech in frames 0-7. Silence from frame 8: 1 silent, 5 at 0.4, 10 silent = 16 frames.
    probabilities = [SPEECH] * 8 + [SILENT] + [MID] * 5 + [SILENT] * 10 + [SILENT] * 4
    _, found = run(probabilities)

    assert [k for k, _ in found] == [8 + 15]  # the 16th frame that is not >= 0.5
    assert found[0][1].speech_end == pytest.approx(8 * FRAME_S)


def test_seg_05_segment_under_the_minimum_length_gives_no_output():
    short, found_short = run([SILENT] * 3 + [SPEECH] * 7 + [SILENT] * 20)  # 224 ms
    long, found_long = run([SILENT] * 3 + [SPEECH] * 8 + [SILENT] * 20)  # 256 ms

    assert found_short == []
    assert short.short_segments == 1
    assert len(found_long) == 1
    assert long.short_segments == 0


def test_seg_06_hard_cut_at_the_maximum_length():
    # 11 s of speech is 344 frames (0-343). Then 20 silent frames.
    probabilities = [SPEECH] * 344 + [SILENT] * 20
    _, found = run(probabilities)

    assert [k for k, _ in found] == [312, 344 + 15]
    first = found[0][1]
    assert first.cut is True
    assert first.closed == pytest.approx(10.016)
    assert first.speech_end == first.closed
    assert first.start == pytest.approx(0.0)
    # No end pad: the audio ends with the last sample of frame 312.
    assert first.audio[0] == 0
    assert first.audio[-1] == 313 * FRAME - 1
    # A second segment starts at frame 313.
    second = found[1][1]
    assert second.cut is False
    assert second.start == pytest.approx(313 * FRAME_S)


def test_seg_07_maximum_length_during_an_open_silence_ends_at_the_true_end():
    # Speech in frames 0-308 (9.888 s). The silence starts at frame 309.
    # The 10 s limit comes at frame 312, the 4th silent frame.
    probabilities = [SPEECH] * 309 + [SILENT] * 20
    _, found = run(probabilities)

    assert [k for k, _ in found] == [312]
    segment = found[0][1]
    assert segment.cut is False
    assert segment.speech_end == pytest.approx(309 * FRAME_S)
    assert segment.closed == pytest.approx(313 * FRAME_S)
    assert segment.audio[-1] == 309 * FRAME + PAD - 1  # true end + end pad


def test_seg_08_audio_has_the_pads():
    _, found = run(BASE)

    audio = found[0][1].audio
    assert np.array_equal(audio, np.arange(2080, 13280))  # (5 x 512 - 480) to (25 x 512 + 480)


def test_seg_08_start_at_frame_0_has_no_start_pad():
    _, found = run([SPEECH] * 20 + [SILENT] * 20)

    audio = found[0][1].audio
    assert np.array_equal(audio, np.arange(0, 20 * FRAME + PAD))


def test_seg_08_pad_longer_than_one_frame_is_limited_to_the_samples_that_exist():
    # vad_speech_pad_ms = 100 is 1600 samples (3.125 frames). Speech starts at frame 2,
    # so only 1024 samples exist before it. The second segment has the full pad.
    params = Params(vad_speech_pad_ms=100)
    probabilities = [SILENT] * 2 + [SPEECH] * 10 + [SILENT] * 16 + [SPEECH] * 10 + [SILENT] * 20
    endpointer = Endpointer(params, FakeVad(probabilities))
    found = [
        segment
        for k in range(len(probabilities))
        if (segment := endpointer.push(block(k))) is not None
    ]

    assert len(found) == 2
    assert np.array_equal(found[0].audio, np.arange(0, 12 * FRAME + 1600))
    # The second segment: speech in frames 28-37, so the pad runs from sample 28 x 512 - 1600.
    assert np.array_equal(found[1].audio, np.arange(28 * FRAME - 1600, 38 * FRAME + 1600))


def test_seg_08_start_pad_of_a_segment_that_starts_right_after_a_close():
    # The first segment closes at frame 25 (speech 0-9, silent frames 10-25).
    # Speech starts again at frame 26, so the start pad comes from frame 25.
    probabilities = [SPEECH] * 10 + [SILENT] * 16 + [SPEECH] * 10 + [SILENT] * 20
    _, found = run(probabilities)

    assert [k for k, _ in found] == [25, 36 + 15]
    second = found[1][1]
    assert second.start == pytest.approx(26 * FRAME_S)
    assert np.array_equal(second.audio, np.arange(26 * FRAME - PAD, 36 * FRAME + PAD))


def test_seg_09_wrong_frame_length_fails_before_the_vad_is_called():
    endpointer = Endpointer(Params(), FakeVad([]))  # a call to the fake would fail
    bad = AudioBlock(source="Me", samples=np.zeros(500, dtype=np.float32), arrival=0.032)

    with pytest.raises(SegmentError) as error:
        endpointer.push(bad)

    assert str(error.value) == "segment: frame has 500 samples, expected 512"


def test_seg_09_probability_outside_0_to_1_fails():
    endpointer = Endpointer(Params(), FakeVad([1.2]))

    with pytest.raises(SegmentError) as error:
        endpointer.push(block(0))

    assert str(error.value) == "segment: probability 1.2 is not in [0, 1]"
