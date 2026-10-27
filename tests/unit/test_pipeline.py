"""T-PIPE-01 to T-PIPE-13: the pipeline with fakes (C2d, C4, C5 `c5-pipeline` and `c5-stop`).

Contract: ARCHITECTURE.md sections 2.6, 2.7, and 4. Decisions: D-022, D-029, D-031, D-037,
D-042, D-054, D-059. Frame k arrives at (k + 1) x 0.032 s, so its start time is k x 0.032 s
(TESTS.md 2.4). Only the main thread and the worker call the fake clock. Thus the times are the
same in each run, and a clock call that the contract does not need makes the test fail.

T-PIPE-06 to T-PIPE-08 have two sources (C4). A fake source can wait for an event before its
first block, so that the sequence of the segments in the queue is always the same.

T-PIPE-09 and T-PIPE-10 (C5) give the "System" source a fake labeler (D-059). With a labeler and
a text, the worker calls the clock one more time, for the end of the speaker step.

T-PIPE-11 and T-PIPE-12 (C5, D-061) use a source with no end, as a live source: when `run()`
returns, the block iterator of the source must be closed and the threads of `run()` must have
ended. T-PIPE-11 and T-PIPE-13 stop with `_thread.interrupt_main()`, which has the effect of
Ctrl+C on the main thread (the test thread). Thus the stop path has a unit test. T-PIPE-13 has a
source that gives no more blocks: the stop must not wait for it with no message (R10).
"""

import _thread
import io
import threading
import time

import numpy as np
import pytest

from tir_asr.config import SAMPLE_RATE, VAD_FRAME, WARMUP_AUDIO_S, WARMUP_TEXT, Params
from tir_asr.errors import TirError
from tir_asr.pipeline import run, warm_up
from tir_asr.speakers.cluster import CentroidClusterer
from tir_asr.speakers.labeler import SpeakerLabeler
from tir_asr.types import AudioBlock

FRAME_S = VAD_FRAME / SAMPLE_RATE  # 0.032 s
SPEECH = 0.9
SILENCE = 0.1
LISTENING = "Listening. Press Ctrl+C to stop.\n"
WAIT_S = 5.0  # test only: a limit for each wait, so that a failed test does not hang
NOT_DONE_S = 0.3  # T-PIPE-07: run() must not return in this time after the end of Me
BLOCK_SLEEP_S = 0.001  # T-PIPE-11, T-PIPE-12: the time between two blocks of an endless source


def probabilities(count: int, regions: list[tuple[int, int]]) -> list[float]:
    """`count` frames at SILENCE, with SPEECH for each (first, last) frame region."""
    values = [SILENCE] * count
    for first, last in regions:
        values[first : last + 1] = [SPEECH] * (last - first + 1)
    return values


class FakeSource:
    """`count` blocks with the label. `after`: an event to wait for before the first block.

    `ended` is set after the last block. `error`: an exception that `blocks()` raises.
    """

    def __init__(
        self,
        count: int,
        label: str = "Me",
        after: threading.Event | None = None,
        error: BaseException | None = None,
    ):
        self.count = count
        self.label = label
        self.after = after
        self.error = error
        self.ended = threading.Event()

    def blocks(self):
        if self.error is not None:
            raise self.error
        if self.after is not None:
            assert self.after.wait(timeout=WAIT_S), f"{self.label}: no start event"
        for k in range(self.count):
            samples = np.zeros(VAD_FRAME, dtype=np.float32)
            yield AudioBlock(source=self.label, samples=samples, arrival=(k + 1) * FRAME_S)
        self.ended.set()


class EndlessSource:
    """Blocks with no end, as a live source (D-061).

    `first` is set after the first block. `closed` is set when the block iterator closes: a real
    source closes its audio stream at that time.
    """

    def __init__(self, label: str = "Me"):
        self.label = label
        self.first = threading.Event()
        self.closed = threading.Event()

    def blocks(self):
        k = 0
        try:
            while True:
                samples = np.zeros(VAD_FRAME, dtype=np.float32)
                yield AudioBlock(source=self.label, samples=samples, arrival=(k + 1) * FRAME_S)
                self.first.set()
                k += 1
                time.sleep(BLOCK_SLEEP_S)
        finally:
            self.closed.set()


class SilentSource:
    """One block, then no more blocks until `release` (T-PIPE-13): a source with no data."""

    def __init__(self, label: str = "Me"):
        self.label = label
        self.first = threading.Event()
        self.release = threading.Event()
        self.ended = threading.Event()

    def blocks(self):
        samples = np.zeros(VAD_FRAME, dtype=np.float32)
        yield AudioBlock(source=self.label, samples=samples, arrival=FRAME_S)
        self.first.set()
        self.release.wait(timeout=WAIT_S)
        self.ended.set()


class EndlessVad:
    """SPEECH in the frame regions, SILENCE for all other frames, with no end."""

    def __init__(self, regions: list[tuple[int, int]] | None = None):
        self.regions = list(regions or [])
        self.frame = 0

    def __call__(self, samples: np.ndarray) -> float:
        k, self.frame = self.frame, self.frame + 1
        return SPEECH if any(first <= k <= last for first, last in self.regions) else SILENCE


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


class FakeSpeakerError(TirError):
    """An error with the message format of SpeakerError."""


class FakeEmbedder:
    def __init__(self):
        self.calls = []

    def embed(self, audio: np.ndarray) -> np.ndarray:
        self.calls.append(audio)
        return np.ones(3)


class FakeLabeler:
    """Gives the labels in order and records the segments. `error`: raise it in `label`."""

    def __init__(self, labels: list[str], error: BaseException | None = None):
        self.labels = list(labels)
        self.error = error
        self.calls = []

    def label(self, segment) -> str:
        self.calls.append(segment)
        if self.error is not None:
            raise self.error
        return self.labels.pop(0)


def start(frames, regions, transcriber, translator, clock):
    """Run the pipeline with a fake source and a fake VAD. Return (code, output, errors)."""
    out, err = io.StringIO(), io.StringIO()
    code = run(
        [(FakeSource(frames), FakeVad(probabilities(frames, regions)))],
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
        [(FakeSource(10), FakeVad([1.2] * 10))],
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
    embedder = FakeEmbedder()
    clusterer = CentroidClusterer(threshold=0.5, min_new_s=1.0)
    SpeakerLabeler(embedder, clusterer)  # the program labeler holds the same embedder

    asr_s, mt_s, spk_s = warm_up(
        transcriber, translator, embedder, FakeClock([10.0, 10.4, 10.5, 10.53])
    )

    assert len(transcriber.calls) == 1
    audio = transcriber.calls[0]
    assert audio.shape == (int(WARMUP_AUDIO_S * SAMPLE_RATE),)
    assert audio.dtype == np.float32
    assert not audio.any()
    assert translator.calls == [WARMUP_TEXT]
    assert len(embedder.calls) == 1
    assert embedder.calls[0] is audio  # the same zeros as the ASR call
    assert clusterer.count == 0  # D-059 point 5: the warm-up does not change the clusterer
    assert (asr_s, mt_s, spk_s) == (pytest.approx(0.4), pytest.approx(0.1), pytest.approx(0.03))


def test_pipe_06_two_sources_give_labelled_blocks_and_summed_counts():
    me = FakeSource(50)
    system = FakeSource(100, label="System", after=me.ended)  # its segment comes after Me
    translator = FakeTranslator("hi")
    clock = FakeClock([0.0, 1.400, 1.500, 1.510, 3.200, 3.300, 3.310])
    out, err = io.StringIO(), io.StringIO()

    code = run(
        [
            (me, FakeVad(probabilities(50, [(5, 24)]))),
            (system, FakeVad(probabilities(100, [(30, 36), (60, 79)]))),  # 30-36: short
        ],
        FakeTranscriber(["բարև", "բարև"]),
        translator,
        Params(),
        clock,
        out,
        err,
    )

    assert out.getvalue() == (
        LISTENING + "[00:00:00] Me\n"
        " HY: բարև\n"
        " EN: hi\n"
        " [Latency: vad 0.51s, asr 0.09s, mt 0.10s, out 0.01s | Total 0.71s]\n"
        "\n"
        "[00:00:01] System\n"
        " HY: բարև\n"
        " EN: hi\n"
        " [Latency: vad 0.51s, asr 0.13s, mt 0.10s, out 0.01s | Total 0.75s]\n"
        "\n"
        "Stopped. Segments: 2, short segments: 1, empty texts: 0, not processed: 0.\n"
    )
    assert err.getvalue() == ""
    assert code == 0
    assert translator.calls == ["բարև", "բարև"]


def test_pipe_07_done_only_after_the_end_of_each_source():
    release = threading.Event()
    me = FakeSource(20)
    system = FakeSource(50, label="System", after=release)
    out, err = io.StringIO(), io.StringIO()
    result = {}

    def call_run() -> None:
        result["code"] = run(
            [
                (me, FakeVad([SILENCE] * 20)),
                (system, FakeVad(probabilities(50, [(5, 24)]))),
            ],
            FakeTranscriber(["բարև"]),
            FakeTranslator("hi"),
            Params(),
            FakeClock([0.0, 1.400, 1.500, 1.510]),
            out,
            err,
        )

    runner = threading.Thread(target=call_run, daemon=True)
    runner.start()
    assert me.ended.wait(timeout=WAIT_S), "Me did not end"
    time.sleep(NOT_DONE_S)
    running_after_me = runner.is_alive()
    release.set()
    runner.join(timeout=WAIT_S)

    assert running_after_me, "run() returned after the end of Me only"
    assert not runner.is_alive(), "run() did not return after the end of both sources"
    assert out.getvalue() == (
        LISTENING + "[00:00:00] System\n"
        " HY: բարև\n"
        " EN: hi\n"
        " [Latency: vad 0.51s, asr 0.09s, mt 0.10s, out 0.01s | Total 0.71s]\n"
        "\n"
        "Stopped. Segments: 1, short segments: 0, empty texts: 0, not processed: 0.\n"
    )
    assert err.getvalue() == ""
    assert result["code"] == 0


def test_pipe_08_error_line_names_the_capture_thread_of_the_source():
    system = FakeSource(10, label="System", error=KeyError("x"))
    out, err = io.StringIO(), io.StringIO()

    code = run(
        [(FakeSource(10), FakeVad([SILENCE] * 10)), (system, FakeVad([]))],
        FakeTranscriber([]),
        FakeTranslator(),
        Params(),
        FakeClock([0.0]),
        out,
        err,
    )

    assert err.getvalue().startswith("Traceback (most recent call last):\n"), err.getvalue()
    assert err.getvalue().endswith("tir-asr: capture System: KeyError: 'x'\n"), err.getvalue()
    assert out.getvalue() == LISTENING
    assert code == 1


def test_pipe_09_system_lines_get_the_speaker_label_and_the_spk_step():
    me = FakeSource(50)
    system = FakeSource(140, label="System", after=me.ended)  # its segments come after Me
    labeler = FakeLabeler(["Speaker 2"])
    # Me: ASR end, MT end, write. System, text: ASR end, MT end, speaker end, write.
    # System, empty text: ASR end, write (no MT call and no speaker step).
    clock = FakeClock([0.0, 1.400, 1.500, 1.510, 3.200, 3.300, 3.320, 3.330, 4.500, 4.510])
    out, err = io.StringIO(), io.StringIO()

    code = run(
        [
            (me, FakeVad(probabilities(50, [(5, 24)]))),
            (system, FakeVad(probabilities(140, [(30, 36), (60, 79), (100, 119)]))),
        ],
        FakeTranscriber(["բարև", "բարև", ""]),
        FakeTranslator("hi"),
        Params(),
        clock,
        out,
        err,
        labelers={"System": labeler},
    )

    assert out.getvalue() == (
        LISTENING + "[00:00:00] Me\n"
        " HY: բարև\n"
        " EN: hi\n"
        " [Latency: vad 0.51s, asr 0.09s, mt 0.10s, out 0.01s | Total 0.71s]\n"
        "\n"
        "[00:00:01] Speaker 2\n"
        " HY: բարև\n"
        " EN: hi\n"
        " [Latency: vad 0.51s, asr 0.13s, mt 0.10s, spk 0.02s, out 0.01s | Total 0.77s]\n"
        "\n"
        "[00:00:03] System\n"
        " HY: (no text)\n"
        " [Latency: vad 0.51s, asr 0.15s | Total 0.67s]\n"
        "\n"
        "Stopped. Segments: 3, short segments: 1, empty texts: 1, not processed: 0.\n"
    )
    assert err.getvalue() == ""
    assert code == 0
    assert len(labeler.calls) == 1  # only the System segment with a text
    assert labeler.calls[0].source == "System"
    assert labeler.calls[0].start == pytest.approx(60 * FRAME_S)


def test_pipe_10_error_in_the_labeler():
    labeler = FakeLabeler([], error=FakeSpeakerError("speakers: test"))
    out, err = io.StringIO(), io.StringIO()

    code = run(
        [(FakeSource(111, label="System"), FakeVad(probabilities(111, [(5, 24)])))],
        FakeTranscriber(["բարև"]),
        FakeTranslator("hi"),
        Params(),
        FakeClock([0.0, 1.400, 1.500]),
        out,
        err,
        labelers={"System": labeler},
    )

    assert err.getvalue() == "tir-asr: speakers: test\n"
    assert out.getvalue() == LISTENING  # no block and no shutdown line
    assert code == 1


def new_threads(before: set[threading.Thread]) -> list[str]:
    """The names of the threads that run now and did not run before."""
    return [thread.name for thread in threading.enumerate() if thread not in before]


def test_pipe_11_ctrl_c_closes_the_sources_and_ends_the_threads():
    source = EndlessSource()
    out, err = io.StringIO(), io.StringIO()

    def interrupt() -> None:
        if source.first.wait(timeout=WAIT_S):  # run() is in its main loop
            _thread.interrupt_main()  # as Ctrl+C: KeyboardInterrupt in the main thread

    helper = threading.Thread(target=interrupt, name="helper", daemon=True)
    before = set(threading.enumerate()) | {helper}
    helper.start()

    code = run(
        [(source, EndlessVad())],
        FakeTranscriber([]),
        FakeTranslator(),
        Params(),
        FakeClock([0.0]),
        out,
        err,
    )
    closed = source.closed.is_set()
    running = new_threads(before)

    assert source.first.is_set(), "the source gave no block"
    assert closed, "run() returned before the block iterator of the source closed"
    assert running == [], f"threads of run() still run: {running}"
    assert out.getvalue() == (
        LISTENING + "Stopped. Segments: 0, short segments: 0, empty texts: 0, not processed: 0.\n"
    )
    assert err.getvalue() == ""
    assert code == 0


def test_pipe_12_an_error_closes_the_sources_and_ends_the_threads():
    source = EndlessSource()
    transcriber = FakeTranscriber([], error=FakeAsrError("asr: test"))
    out, err = io.StringIO(), io.StringIO()
    before = set(threading.enumerate())

    code = run(
        [(source, EndlessVad([(5, 24)]))],
        transcriber,
        FakeTranslator(),
        Params(),
        FakeClock([0.0]),
        out,
        err,
    )
    closed = source.closed.is_set()
    running = new_threads(before)

    assert len(transcriber.calls) == 1
    assert closed, "run() returned before the block iterator of the source closed"
    assert running == [], f"threads of run() still run: {running}"
    assert err.getvalue() == "tir-asr: asr: test\n"
    assert out.getvalue() == LISTENING  # no block and no shutdown line
    assert code == 1


def test_pipe_13_a_thread_that_does_not_stop_gives_an_error_line(monkeypatch):
    monkeypatch.setattr("tir_asr.pipeline.STOP_JOIN_S", 0.1)
    source = SilentSource()
    out, err = io.StringIO(), io.StringIO()

    def interrupt() -> None:
        if source.first.wait(timeout=WAIT_S):  # the capture thread waits for a block now
            _thread.interrupt_main()

    threading.Thread(target=interrupt, name="helper", daemon=True).start()
    try:
        code = run(
            [(source, EndlessVad())],
            FakeTranscriber([]),
            FakeTranslator(),
            Params(),
            FakeClock([0.0]),
            out,
            err,
        )
    finally:
        source.release.set()  # the capture thread ends after the test
    assert source.ended.wait(timeout=WAIT_S), "the source did not end after the release"

    assert out.getvalue() == (
        LISTENING + "Stopped. Segments: 0, short segments: 0, empty texts: 0, not processed: 0.\n"
    )
    assert err.getvalue() == "tir-asr: stop: thread capture Me did not stop in 0.1 s\n"
    assert code == 0
