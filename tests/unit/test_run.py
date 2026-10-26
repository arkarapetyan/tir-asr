"""T-RUN-01 to T-RUN-05: the bake-off core with fakes (D-046, D-048, D-051).

No model and no audio device. The expected values come from the approved test table
(TESTS.md section 2.5), not from the code.
"""

import numpy as np
import pytest

from tir_asr.config import SAMPLE_RATE, VAD_FRAME, Params
from tir_asr.eval.data import Label, ScriptLine
from tir_asr.eval.run import score_side, segment_file, transcribe_all, translate_all
from tir_asr.types import Segment


def loud_frame_vad(samples: np.ndarray) -> float:
    return 1.0 if float(np.max(np.abs(samples))) > 0.1 else 0.0


def segment(start: float, end: float, audio_s: float = 1.0) -> Segment:
    return Segment(
        source="eval",
        audio=np.zeros(int(audio_s * SAMPLE_RATE), dtype=np.float32),
        start=start,
        speech_end=end,
        closed=end + 0.5,
        cut=False,
    )


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


class FakeTranscriber:
    def __init__(self, texts: list[str], clock: FakeClock) -> None:
        self.texts = iter(texts)
        self.clock = clock

    def transcribe(self, audio: np.ndarray) -> str:
        self.clock.now += 0.1
        return next(self.texts)


class FakeTranslator:
    def __init__(self, clock: FakeClock) -> None:
        self.clock = clock
        self.calls: list[str] = []

    def translate(self, text: str) -> str:
        self.clock.now += 0.1
        self.calls.append(text)
        return "A"


LINES = [
    ScriptLine("s1-01", "Me", "mic", "ա բ", "a b"),
    ScriptLine("s1-03", "Me", "mic", "գ դ", "c d"),
]
LABELS = [Label("s1-01", 0.0, 2.0), Label("s1-03", 3.0, 5.0)]


def test_run_01_segments_in_audio_time_with_the_end_rule():
    audio = np.zeros(3 * SAMPLE_RATE, dtype=np.float32)
    audio[10 * VAD_FRAME : 40 * VAD_FRAME] = 0.5
    audio[80 * VAD_FRAME :] = 0.5  # loud to the last sample of the file

    segments = segment_file(audio, loud_frame_vad, Params())

    assert len(segments) == 2
    assert segments[0].start == pytest.approx(0.320)
    assert segments[0].speech_end == pytest.approx(1.280)
    assert segments[1].start == pytest.approx(80 * 0.032)


def test_run_02_asr_and_mt_calls():
    clock = FakeClock()
    segments = [segment(0, 1), segment(2, 3), segment(4, 5)]
    translator = FakeTranslator(clock)

    hy = transcribe_all(segments, FakeTranscriber(["ա", "", "բ"], clock), clock)
    en = translate_all([t.text for t in hy], translator, clock)

    assert [t.text for t in hy] == ["ա", "", "բ"]
    assert [t.seconds for t in hy] == pytest.approx([0.1, 0.1, 0.1])
    assert [t.text for t in en] == ["A", "", "A"]
    assert [t.seconds for t in en] == pytest.approx([0.1, 0.0, 0.1])
    assert translator.calls == ["ա", "բ"]


def test_run_03_main_numbers_use_the_joined_text():
    segments = [segment(0.0, 3.5), segment(4.0, 5.0)]

    score = score_side(LINES, LABELS, segments, ["ա բ գ", "դ"], ["a b c", "d"], [0, 0], [0, 0])

    assert score.wer == 0.0
    assert [(line.id, line.wer) for line in score.lines] == [("s1-01", 0.5), ("s1-03", 0.5)]


def test_run_04_segment_outside_each_label():
    segments = [segment(0.0, 2.0), segment(3.0, 5.0), segment(6.0, 7.0)]

    score = score_side(
        LINES, LABELS, segments, ["ա բ", "գ դ", "ե"], ["a b", "c d", "e"], [0, 0, 0], [0, 0, 0]
    )

    assert score.outside == 1
    assert score.wer == pytest.approx(1 / 4)


def test_run_05_time_numbers():
    segments = [segment(0.0, 2.0, audio_s=2.0), segment(3.0, 5.0, audio_s=3.0)]

    score = score_side(
        LINES, LABELS, segments, ["ա բ", "գ դ"], ["a b", "c d"], [0.1, 0.3], [0.2, 0.4]
    )

    assert score.audio_s == pytest.approx(5.0)
    assert score.asr_rtf == pytest.approx(0.08)
    assert score.asr_mean_s == pytest.approx(0.2)
    assert score.asr_max_s == pytest.approx(0.3)
    assert score.mt_mean_s == pytest.approx(0.3)
    assert score.mt_max_s == pytest.approx(0.4)
