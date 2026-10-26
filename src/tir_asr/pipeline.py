"""Pipeline: the warm-up, the threads, the segment queue, and the stop (ARCHITECTURE.md 2.6, 4).

Decisions: D-022, D-029, D-031, D-037, D-042. This module is core: it gets the adapters as
arguments, and it imports no model and no audio-device package (D-021).

Threads (section 4): the capture thread reads the blocks, calls `Endpointer.push`, and puts each
segment in the segment queue. The worker thread does ASR, then MT (if the text is not empty),
then writes the block. The main thread waits for "done" (the end of the source) or for the first
error, or it gets Ctrl+C.
"""

import queue
import threading
import traceback
from collections.abc import Callable
from typing import TextIO

import numpy as np

from tir_asr.config import SAMPLE_RATE, WARMUP_AUDIO_S, WARMUP_TEXT, Params
from tir_asr.errors import TirError
from tir_asr.output import write_block
from tir_asr.segment.endpoint import Endpointer
from tir_asr.types import AudioSource, Line, SpeechProbability, Transcriber, Translator

PROGRAM = "tir-asr"
LISTENING = "Listening. Press Ctrl+C to stop."
END = None  # the end mark in the segment queue: the source has no more blocks

Clock = Callable[[], float]


def warm_up(transcriber: Transcriber, translator: Translator, clock: Clock) -> tuple[float, float]:
    """Call each GPU model one time with a synthetic input (D-022, D-037).

    Return the ASR time and the MT time in seconds. The caller prints them.
    """
    audio = np.zeros(int(WARMUP_AUDIO_S * SAMPLE_RATE), dtype=np.float32)
    start = clock()
    transcriber.transcribe(audio)
    asr_end = clock()
    translator.translate(WARMUP_TEXT)
    mt_end = clock()
    return asr_end - start, mt_end - asr_end


def run(
    source: AudioSource,
    vad: SpeechProbability,
    transcriber: Transcriber,
    translator: Translator,
    params: Params,
    clock: Clock,
    out: TextIO,
    err: TextIO,
) -> int:
    """Run until Ctrl+C, the end of the source, or the first error. Return the exit code.

    Ctrl+C or the end of the source: the shutdown line, then 0. An error: the error line on
    `err`, no shutdown line, then 1 (D-042).
    """
    endpointer = Endpointer(params, vad)
    segments: queue.Queue = queue.Queue()  # no size limit (D-029)
    events: queue.Queue = queue.Queue()  # ("done", None) or ("error", (thread name, error))
    output_lock = threading.Lock()  # the shutdown line is the last line (D-042)
    stopped = threading.Event()
    counts = {"queued": 0, "written": 0, "empty": 0}

    def capture() -> None:
        for block in source.blocks():
            segment = endpointer.push(block)
            if segment is not None:
                counts["queued"] += 1
                segments.put(segment)
        segments.put(END)  # only the tests and the WAV source end (D-025)

    def work() -> None:
        while (segment := segments.get()) is not END:
            hy = transcriber.transcribe(segment.audio)
            asr_end = clock()
            if hy:
                en = translator.translate(hy)
                mt_end = clock()
            else:  # D-031: no MT call for an empty text
                en = ""
                mt_end = asr_end
            with output_lock:
                if stopped.is_set():
                    return
                line = Line(
                    label=segment.source,
                    start=segment.start,
                    hy=hy,
                    en=en,
                    speech_end=segment.speech_end,
                    closed=segment.closed,
                    asr_end=asr_end,
                    mt_end=mt_end,
                    write=clock(),
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
        thread("capture", capture).start()
        kind, detail = events.get()
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
        not_processed = counts["queued"] - counts["written"]
        out.write(
            f"Stopped. Segments: {counts['written']}, short segments: {endpointer.short_segments}, "
            f"empty texts: {counts['empty']}, not processed: {not_processed}.\n"
        )
        out.flush()
    return 0
