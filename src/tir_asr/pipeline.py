"""Pipeline: the warm-up, the threads, the segment queue, and the stop (ARCHITECTURE.md 2.6, 4).

Decisions: D-022, D-029, D-031, D-037, D-042, D-054, D-059. This module is core: it gets the
adapters as arguments, and it imports no model and no audio-device package (D-021).

Threads (section 4): one capture thread for each audio source reads the blocks of its source,
calls the `Endpointer.push` of its source, and puts each segment in the one segment queue. The
worker thread does ASR, then MT (if the text is not empty), then the speaker step (a source with
a labeler, and a text that is not empty), then writes the block. The main thread waits for
"done" (the end of all sources) or for the first error, or it gets Ctrl+C.
"""

import queue
import threading
import traceback
from collections.abc import Callable, Mapping, Sequence
from typing import TextIO

import numpy as np

from tir_asr.config import SAMPLE_RATE, WARMUP_AUDIO_S, WARMUP_TEXT, Params
from tir_asr.errors import TirError
from tir_asr.output import write_block
from tir_asr.segment.endpoint import Endpointer
from tir_asr.types import (
    AudioSource,
    Labeler,
    Line,
    SpeakerEmbedder,
    SpeechProbability,
    Transcriber,
    Translator,
)

PROGRAM = "tir-asr"
LISTENING = "Listening. Press Ctrl+C to stop."
END = None  # the end mark in the segment queue: one source has no more blocks
# D-044: the main thread waits for an event with this time limit, in a loop. The limit only wakes
# the main thread, so that Python can handle a waiting Ctrl+C. With no limit, Ctrl+C did nothing
# when another thread received the signal (L-02, probe C, T-E2E-02).
STOP_POLL_S = 0.5

Clock = Callable[[], float]


def warm_up(
    transcriber: Transcriber, translator: Translator, embedder: SpeakerEmbedder, clock: Clock
) -> tuple[float, float, float]:
    """Call each GPU model one time with a synthetic input (D-022, D-037, D-059).

    The speaker model gets the same zeros as the ASR model. The warm-up gets the embedder, not
    the labeler, so it cannot change a clusterer. Return the ASR time, the MT time, and the
    speaker time in seconds. The caller prints them.
    """
    audio = np.zeros(int(WARMUP_AUDIO_S * SAMPLE_RATE), dtype=np.float32)
    start = clock()
    transcriber.transcribe(audio)
    asr_end = clock()
    translator.translate(WARMUP_TEXT)
    mt_end = clock()
    embedder.embed(audio)
    spk_end = clock()
    return asr_end - start, mt_end - asr_end, spk_end - mt_end


def run(
    sources: Sequence[tuple[AudioSource, SpeechProbability]],
    transcriber: Transcriber,
    translator: Translator,
    params: Params,
    clock: Clock,
    out: TextIO,
    err: TextIO,
    labelers: Mapping[str, Labeler] | None = None,
) -> int:
    """Run until Ctrl+C, the end of all sources, or the first error. Return the exit code.

    `sources` has one (source, VAD) pair for each audio source. Each pair gets its own
    Endpointer and its own capture thread, with the name `capture <label>` (D-054). All
    capture threads put their segments in one queue, and one worker takes them in that order.
    Ctrl+C or the end of all sources: the shutdown line, then 0. An error: the error line on
    `err`, no shutdown line, then 1 (D-042).

    `labelers` has a labeler for each source label that needs speaker labels (the program:
    "System"). A source with no labeler keeps its source label. A segment with an empty text
    gets no labeler call and keeps its source label (D-059 point 3).
    """
    labelers = dict(labelers or {})
    endpointers = [Endpointer(params, vad) for _, vad in sources]
    segments: queue.Queue = queue.Queue()  # one queue for all sources, no size limit (D-029)
    events: queue.Queue = queue.Queue()  # ("done", None) or ("error", (thread name, error))
    output_lock = threading.Lock()  # the shutdown line is the last line (D-042)
    stopped = threading.Event()
    queued = [0] * len(sources)  # one count for each capture thread, so no lock is necessary
    counts = {"written": 0, "empty": 0}  # the worker writes them

    def capture(index: int) -> Callable[[], None]:
        source, endpointer = sources[index][0], endpointers[index]

        def read() -> None:
            for block in source.blocks():
                segment = endpointer.push(block)
                if segment is not None:
                    queued[index] += 1
                    segments.put(segment)
            segments.put(END)  # only the tests and the WAV source end (D-025)

        return read

    def work() -> None:
        ends = 0
        while ends < len(sources):  # "done" only after the end mark of each source (D-054)
            segment = segments.get()
            if segment is END:
                ends += 1
                continue
            hy = transcriber.transcribe(segment.audio)
            asr_end = clock()
            if hy:
                en = translator.translate(hy)
                mt_end = clock()
            else:  # D-031: no MT call for an empty text
                en = ""
                mt_end = asr_end
            labeler = labelers.get(segment.source)
            if labeler is not None and hy:  # D-059 point 3: no speaker step for an empty text
                label = labeler.label(segment)
                spk_end = clock()
            else:
                label = segment.source
                spk_end = None
            with output_lock:
                if stopped.is_set():
                    return
                line = Line(
                    label=label,
                    start=segment.start,
                    hy=hy,
                    en=en,
                    speech_end=segment.speech_end,
                    closed=segment.closed,
                    asr_end=asr_end,
                    mt_end=mt_end,
                    write=clock(),
                    spk_end=spk_end,
                )
                write_block(line, session_start, out)
                counts["written"] += 1
                if not hy:
                    counts["empty"] += 1
        events.put(("done", None))

    def thread(name: str, target: Callable[[], None]) -> threading.Thread:
        def body() -> None:
            try:
                target()
            except Exception as error:  # the main thread stops the program (section 2.6)
                events.put(("error", (name, error)))

        return threading.Thread(target=body, name=name, daemon=True)

    # D-042 point 5: the session start comes before the capture starts.
    session_start = clock()
    out.write(f"{LISTENING}\n")
    out.flush()
    try:
        thread("worker", work).start()
        for index, (source, _) in enumerate(sources):
            thread(f"capture {source.label}", capture(index)).start()
        while True:
            try:
                kind, detail = events.get(timeout=STOP_POLL_S)
                break
            except queue.Empty:
                continue  # D-044: a wake-up only
    except KeyboardInterrupt:
        kind, detail = "stop", None

    if kind == "error":
        name, error = detail
        if not isinstance(error, TirError):
            err.write("".join(traceback.format_exception(error)))
            err.write(f"{PROGRAM}: {name}: {type(error).__name__}: {error}\n")
        else:
            err.write(f"{PROGRAM}: {error}\n")
        err.flush()
        return 1

    with output_lock:
        stopped.set()
        not_processed = sum(queued) - counts["written"]  # in the queue, in ASR, or in MT
        short = sum(endpointer.short_segments for endpointer in endpointers)
        out.write(
            f"Stopped. Segments: {counts['written']}, short segments: {short}, "
            f"empty texts: {counts['empty']}, not processed: {not_processed}.\n"
        )
        out.flush()
    return 0
