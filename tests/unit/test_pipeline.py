"""T-PIPE-01 to T-PIPE-05: the pipeline with fakes (C2d, branch c2d-pipeline).

Contract: ARCHITECTURE.md sections 2.6, 2.7, and 4. Decisions: D-022, D-029, D-031, D-037,
D-042. Frame k arrives at (k + 1) x 0.032 s, so its start time is k x 0.032 s (TESTS.md 2.4).
Only the main thread and the worker call the fake clock. Thus the times are the same in each
run, and a clock call that the contract does not need makes the test fail.
"""

import io

import numpy as np
import pytest

from tir_asr.config import SAMPLE_RATE, VAD_FRAME, WARMUP_AUDIO_S, WARMUP_TEXT, Params
from tir_asr.errors import TirError
from tir_asr.pipeline import run, warm_up
from tir_asr.types import AudioBlock

FRAME_S = VAD_FRAME / SAMPLE_RATE  # 0.032 s
SPEECH = 0.9
SILENCE = 0.1
LISTENING = "Listening. Press Ctrl+C to stop.\n"


def probabilities(count: int, regions: list[tuple[int, int]]) -> list[float]:
    """`count` frames at SILENCE, with SPEECH for each (first, last) frame region."""
    values = [SILENCE] * count
    for first, last in regions:
        values[first : last + 1] = [SPEECH] * (last - first + 1)
    return values


class FakeSource:
    def __init__(self, count: int):
        self.count = count

    def blocks(self):
        for k in range(self.count):
            samples = np.zeros(VAD_FRAME, dtype=np.float32)
            yield AudioBlock(source="Me", samples=samples, arrival=(k + 1) * FRAME_S)


class FakeVad:
    def __init__(self, values: list[float]):
        self.values = list(values)

    def __call__(self, samples: np.ndarray) -> float:
        return self.values.pop(0)


class FakeTranscriber:
    def __init__(self, texts: list[str], error: BaseException | None = None):
        self.texts = list(texts)
        self.error = error
        self.calls = []

    def transcribe(self, audio: np.ndarray) -> str:
        self.calls.append(audio)
        if self.error is not None:
            raise self.error
        return self.texts.pop(0)


class FakeTranslator:
    def __init__(self, text: str = "hi", error: BaseException | None = None):
        self.text = text
        self.error = error
        self.calls = []

    def translate(self, text: str) -> str:
        self.calls.append(text)
        if self.error is not None:
            raise self.error
        return self.text


class FakeClock:
    def __init__(self, values: list[float]):
        self.values = list(values)

    def __call__(self) -> float:
        assert self.values, "the fake clock has no more values"
        return self.values.pop(0)


class FakeAsrError(TirError):
    """An error with the message format of AsrError (the real class needs `torch`)."""


def start(frames, regions, transcriber, translator, clock):
    """Run the pipeline with a fake source and a fake VAD. Return (code, output, errors)."""
    out, err = io.StringIO(), io.StringIO()
    code = run(
        FakeSource(frames),
        FakeVad(probabilities(frames, regions)),
        transcriber,
        translator,
        Params(),
        clock,
        out,
        err,
    )
    return code, out.getvalue(), err.getvalue()


def test_pipe_01_two_segments_end_to_end_with_fakes():
    transcriber = FakeTranscriber(["բարև", "բարև"])
    translator = FakeTranslator("hi")
    clock = FakeClock([0.0, 1.400, 1.500, 1.510, 3.200, 3.300, 3.310])

    code, out, err = start(111, [(5, 24), (60, 79)], transcriber, translator, clock)

    assert out == (
        LISTENING + "[00:00:00] Me\n"
        " HY: բարև\n"
        " EN: hi\n"
        " [Latency: vad 0.51s, asr 0.09s, mt 0.10s, out 0.01s | Total 0.71s]\n"
        "\n"
        "[00:00:01] Me\n"
        " HY: բարև\n"
        " EN: hi\n"
        " [Latency: vad 0.51s, asr 0.13s, mt 0.10s, out 0.01s | Total 0.75s]\n"
        "\n"
        "Stopped. Segments: 2, short segments: 0, empty texts: 0, not processed: 0.\n"
    )
    assert err == ""
    assert code == 0
    assert len(transcriber.calls) == 2
    assert translator.calls == ["բարև", "բարև"]


def test_pipe_02_tir_error_in_the_worker():
    transcriber = FakeTranscriber([], error=FakeAsrError("asr: test"))

    code, out, err = start(111, [(5, 24)], transcriber, FakeTranslator(), FakeClock([0.0]))

    assert err == "tir-asr: asr: test\n"
    assert out == LISTENING  # no block and no shutdown line
    assert code == 1


def test_pipe_02_other_exception_in_the_worker():
    translator = FakeTranslator(error=KeyError("x"))
    clock = FakeClock([0.0, 1.400])

    code, out, err = start(111, [(5, 24)], FakeTranscriber(["բարև"]), translator, clock)

    assert err.startswith("Traceback (most recent call last):\n"), err
    assert err.endswith("tir-asr: worker: KeyError: 'x'\n"), err
    assert out == LISTENING
    assert code == 1


def test_pipe_02_error_in_the_capture_thread():
    out, err = io.StringIO(), io.StringIO()

    code = run(
        FakeSource(10),
        FakeVad([1.2] * 10),
        FakeTranscriber([]),
        FakeTranslator(),
        Params(),
        FakeClock([0.0]),
        out,
        err,
    )

    assert err.getvalue() == "tir-asr: segment: probability 1.2 is not in [0, 1]\n"
    assert out.getvalue() == LISTENING
    assert code == 1


def test_pipe_03_empty_text_gets_no_mt_call():
    translator = FakeTranslator()
    clock = FakeClock([0.0, 1.400, 1.410])

    code, out, err = start(111, [(5, 24)], FakeTranscriber([""]), translator, clock)

    assert translator.calls == []
    assert out == (
        LISTENING + "[00:00:00] Me\n"
        " HY: (no text)\n"
        " [Latency: vad 0.51s, asr 0.09s | Total 0.61s]\n"
        "\n"
        "Stopped. Segments: 1, short segments: 0, empty texts: 1, not processed: 0.\n"
    )
    assert err == ""
    assert code == 0


def test_pipe_04_shutdown_line_counts_the_segments():
    # Regions: normal (5-24), short (60-66: 7 frames = 224 ms), empty text (100-119).
    transcriber = FakeTranscriber(["բարև", ""])
    clock = FakeClock([0.0, 1.400, 1.500, 1.510, 4.500, 4.510])

    code, out, err = start(
        150, [(5, 24), (60, 66), (100, 119)], transcriber, FakeTranslator(), clock
    )

    assert out.splitlines()[-1] == (
        "Stopped. Segments: 2, short segments: 1, empty texts: 1, not processed: 0."
    )
    assert err == ""
    assert code == 0


def test_pipe_05_warm_up_calls_each_model_once():
    transcriber = FakeTranscriber([""])
    translator = FakeTranslator()

    asr_s, mt_s = warm_up(transcriber, translator, FakeClock([10.0, 10.4, 10.5]))

    assert len(transcriber.calls) == 1
    audio = transcriber.calls[0]
    assert audio.shape == (int(WARMUP_AUDIO_S * SAMPLE_RATE),)
    assert audio.dtype == np.float32
    assert not audio.any()
    assert translator.calls == [WARMUP_TEXT]
    assert (asr_s, mt_s) == (pytest.approx(0.4), pytest.approx(0.1))
