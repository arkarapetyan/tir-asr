"""Pipeline: the warm-up, the threads, the segment queue, and the stop (ARCHITECTURE.md 2.6, 4).

Decisions: D-022, D-029, D-031, D-037, D-042, D-054, D-059, D-061, D-062, D-067. This module is
core: it gets the adapters as arguments, and it imports no model and no audio-device package
(D-021).

Threads (section 4): one capture thread for each audio source reads the blocks of its source,
calls the `Endpointer.push` of its source, and puts each segment in the one segment queue. The
worker thread does the text step (the Armenian text, then the English text if the Armenian text
is not empty; P1 or P4, D-062), then the speaker step (a source with a labeler), then writes the
block. A segment with an empty text gives no block; the shutdown line counts it (D-031, C7).
The main thread waits for "done" (the end of all sources) or for the first error, or it gets
Ctrl+C.

The stop (D-061): at each end, the main thread sets the stop event and waits for all threads
before `run()` returns. Each capture thread stops at its next block and closes its block
iterator, so that the audio stream closes. Thus no thread uses the audio library or a model
while Python runs its exit functions: the exit function of `soundcard` frees the PulseAudio
main loop, and a capture thread that still records then stops the process (L-02, exit code 134).

The GIL (D-067): while `run()` runs, a thread that waits for the interpreter lock gets it after
`GIL_SWITCH_S`, not after the Python default of 5 ms. `run()` sets the old value back at its end.
"""

import queue
import sys
import threading
import time
import traceback
from collections.abc import Callable, Mapping, Sequence
from typing import TextIO

import numpy as np

from tir_asr.config import SAMPLE_RATE, WARMUP_AUDIO_S, Params
from tir_asr.errors import TirError
from tir_asr.output import write_block
from tir_asr.segment.endpoint import Endpointer
from tir_asr.text.step import TextStep
from tir_asr.types import AudioSource, Labeler, Line, SpeakerEmbedder, SpeechProbability

PROGRAM = "tir-asr"
LISTENING = "Listening. Press Ctrl+C to stop."
END = None  # the end mark in the segment queue: one source has no more blocks
# D-044: the main thread waits for an event with this time limit, in a loop. The limit only wakes
# the main thread, so that Python can handle a waiting Ctrl+C. With no limit, Ctrl+C did nothing
# when another thread received the signal (L-02, probe C, T-E2E-02).
STOP_POLL_S = 0.5
# D-061: at the end of run(), the main thread waits this time in total for all threads. A thread
# that does not stop in this time stays a daemon thread, and `err` gets a line for it (R10).
STOP_JOIN_S = 2.0
# D-067: the interpreter switch interval while run() runs (the Python default is 0.005 s).
# [RUN, C7, T-SIM-03 with P4] Each arrival gap over 64 ms came during a text step call, and no
# full GC pass came in a gap. Probable mechanism [UNVERIFIED]: the P4 worker runs the Python code
# of the decode loop, and a capture thread waits up to the switch interval for the GIL at each of
# its handoffs in a block.
GIL_SWITCH_S = 0.001

Clock = Callable[[], float]


def warm_up(
    text_step: TextStep, embedder: SpeakerEmbedder, clock: Clock
) -> tuple[float, float, float]:
    """Call each GPU model one time with a synthetic input (D-022, D-037, D-059, D-062).

    The text step gets `WARMUP_AUDIO_S` of zeros (`TextStep.warm_up`: P1 also translates
    `WARMUP_TEXT`). The speaker model gets the same zeros. The warm-up gets the embedder, not
    the labeler, so it cannot change a clusterer. Return the time of the Armenian step, of the
    English step, and of the speaker model in seconds. The caller prints them.
    """
    audio = np.zeros(int(WARMUP_AUDIO_S * SAMPLE_RATE), dtype=np.float32)
    start = clock()
    text = text_step.warm_up(audio, clock)
    embedder.embed(audio)
    spk_end = clock()
    return text.asr_end - start, text.mt_end - text.asr_end, spk_end - text.mt_end


def run(
    sources: Sequence[tuple[AudioSource, SpeechProbability]],
    text_step: TextStep,
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
    The worker gives the audio of each segment to `text_step` (P1 or P4, D-062).
    Ctrl+C or the end of all sources: the shutdown line, then 0. An error: the error line on
    `err`, no shutdown line, then 1 (D-042). In each case, `run()` returns only after the
    threads have stopped, or after `STOP_JOIN_S` (D-061).

    `labelers` has a labeler for each source label that needs speaker labels (the program:
    "System"). A source with no labeler keeps its source label. A segment with an empty text
    gets no labeler call (D-059 point 3) and no block (D-031, C7); the shutdown line counts it.

    While `run()` runs, the interpreter switch interval is `GIL_SWITCH_S` (D-067). At each end,
    `run()` sets the old value back.
    """
    previous = sys.getswitchinterval()
    sys.setswitchinterval(GIL_SWITCH_S)
    try:
        return _run(sources, text_step, params, clock, out, err, labelers)
    finally:
        sys.setswitchinterval(previous)


def _run(
    sources: Sequence[tuple[AudioSource, SpeechProbability]],
    text_step: TextStep,
    params: Params,
    clock: Clock,
    out: TextIO,
    err: TextIO,
    labelers: Mapping[str, Labeler] | None,
) -> int:
    """The body of `run()`."""
    labelers = dict(labelers or {})
    endpointers = [Endpointer(params, vad) for _, vad in sources]
    segments: queue.Queue = queue.Queue()  # one queue for all sources, no size limit (D-029)
    events: queue.Queue = queue.Queue()  # ("done", None) or ("error", (thread name, error))
    output_lock = threading.Lock()  # the shutdown line is the last line (D-042)
    stopped = threading.Event()
    queued = [0] * len(sources)  # one count for each capture thread, so no lock is necessary
    counts = {"written": 0, "empty": 0}  # the worker writes them
    threads: list[threading.Thread] = []

    def capture(index: int) -> Callable[[], None]:
        source, endpointer = sources[index][0], endpointers[index]

        def read() -> None:
            blocks = source.blocks()
            try:
                for block in blocks:
                    if stopped.is_set():
                        return  # D-061: the stream closes below
                    segment = endpointer.push(block)
                    if segment is not None:
                        queued[index] += 1
                        segments.put(segment)
                segments.put(END)  # only the tests and the WAV source end (D-025)
            finally:
                close = getattr(blocks, "close", None)
                if close is not None:
                    close()  # a generator: its `with` blocks close the audio stream (D-061)

        return read

    def work() -> None:
        ends = 0
        while ends < len(sources):  # "done" only after the end mark of each source (D-054)
            segment = segments.get()
            if stopped.is_set():
                return  # D-061: the main thread stops the program
            if segment is END:
                ends += 1
                continue
            text = text_step.process(segment.audio, clock)  # D-031 is in the text step
            hy = text.hy
            if not hy:  # D-031 (C7): no block and no speaker step; the shutdown line counts it
                with output_lock:
                    counts["empty"] += 1
                continue
            labeler = labelers.get(segment.source)
            if labeler is not None:
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
                    en=text.en,
                    speech_end=segment.speech_end,
                    closed=segment.closed,
                    asr_end=text.asr_end,
                    mt_end=text.mt_end,
                    write=clock(),
                    spk_end=spk_end,
                    steps=text_step.STEPS,  # D-063 part 2
                )
                write_block(line, session_start, out)
                counts["written"] += 1
        events.put(("done", None))

    def thread(name: str, target: Callable[[], None]) -> threading.Thread:
        def body() -> None:
            try:
                target()
            except Exception as error:  # the main thread stops the program (section 2.6)
                events.put(("error", (name, error)))

        new = threading.Thread(target=body, name=name, daemon=True)
        threads.append(new)
        return new

    def finish() -> None:
        """D-061: wake the worker, then wait for all threads, with one time limit for all."""
        segments.put(END)  # the worker can wait for a segment; it sees the stop event
        deadline = time.monotonic() + STOP_JOIN_S
        try:
            for each in threads:
                if each.is_alive():  # a thread that did not start cannot be joined
                    each.join(timeout=max(0.0, deadline - time.monotonic()))
        except KeyboardInterrupt:
            return  # a second Ctrl+C: return now
        for each in threads:
            if each.is_alive():  # R10: the time limit is not silent
                err.write(f"{PROGRAM}: stop: thread {each.name} did not stop in {STOP_JOIN_S} s\n")
        err.flush()

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
        with output_lock:
            stopped.set()  # no block after the error line
        name, error = detail
        if not isinstance(error, TirError):
            err.write("".join(traceback.format_exception(error)))
            err.write(f"{PROGRAM}: {name}: {type(error).__name__}: {error}\n")
        else:
            err.write(f"{PROGRAM}: {error}\n")
        err.flush()
        finish()
        return 1

    with output_lock:
        stopped.set()
        # in the queue or in the worker; an empty text is processed, but it has no block
        not_processed = sum(queued) - counts["written"] - counts["empty"]
        short = sum(endpointer.short_segments for endpointer in endpointers)
        out.write(
            f"Stopped. Segments: {counts['written']}, short segments: {short}, "
            f"empty texts: {counts['empty']}, not processed: {not_processed}.\n"
        )
        out.flush()
    finish()
    return 0
