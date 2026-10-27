"""SIGINT probe for L-02 (C2d): why Ctrl+C did not stop tir-asr. Not part of the package.

The probe does the startup steps of `app.py` one at a time. After each step, it prints the
SIGINT handler, whether the main thread blocks SIGINT, and the number of threads. Then it waits
for Ctrl+C in two ways:
  test 1: `queue.Queue.get(timeout=0.5)` in a loop;
  test 2: `queue.Queue.get()` with no time limit, as `pipeline.run` does now.
Press Ctrl+C one time in each test.

Run it in the project folder, in the same way as the live run (no `uv run`):
  .venv/bin/python scripts/probe_sigint.py 2>&1 | tee -i test-results/c2d-probe-sigint.txt

Caution: if test 2 does not react in 10 s, close the terminal. The output up to that point is
in the result file.
"""

import os
import queue
import signal
import threading
import time

TEST_1_LIMIT_S = 30.0  # test 1 ends after this time with no Ctrl+C


def state(step: str) -> None:
    handler = signal.getsignal(signal.SIGINT)
    owner = getattr(handler, "__module__", None)
    blocked = signal.SIGINT in signal.pthread_sigmask(signal.SIG_BLOCK, [])  # no change
    native = len(os.listdir("/proc/self/task"))
    print(
        f"{step}: SIGINT handler {handler!r} (module {owner}); blocked in the main thread: "
        f"{blocked}; Python threads {threading.active_count()}, native threads {native}",
        flush=True,
    )


def main() -> None:
    state("start")
    import torch  # noqa: F401  (the import is the step)

    state("import torch")
    from tir_asr.asr.nemo_rnnt import NemoRnntTranscriber
    from tir_asr.config import Params
    from tir_asr.pipeline import warm_up

    transcriber = NemoRnntTranscriber()
    state("ASR loaded")
    from tir_asr.mt.ct2_nllb import Ct2NllbTranslator

    translator = Ct2NllbTranslator(Params())
    state("MT loaded")
    from tir_asr.segment.silero import SileroSpeechProbability

    SileroSpeechProbability()
    state("VAD loaded")
    from tir_asr.speakers.titanet import TitanetEmbedder  # C5: the startup loads it last

    embedder = TitanetEmbedder()
    state("speaker model loaded")
    warm_up(transcriber, translator, embedder, time.monotonic)
    state("warm-up done")
    from tir_asr.audio.soundcard_source import SoundcardSource, default_microphone_id

    microphone = SoundcardSource("Me", default_microphone_id())
    state("microphone selected")

    count = [0]

    def capture() -> None:
        for _ in microphone.blocks():
            count[0] += 1

    threading.Thread(target=capture, name="capture", daemon=True).start()
    time.sleep(1.0)
    state(f"capture thread running ({count[0]} blocks in 1 s)")

    events: queue.Queue = queue.Queue()
    print("test 1: press Ctrl+C one time now.", flush=True)
    start = time.monotonic()
    try:
        while time.monotonic() - start < TEST_1_LIMIT_S:
            try:
                events.get(timeout=0.5)
            except queue.Empty:
                pass
        print(f"test 1: no KeyboardInterrupt in {TEST_1_LIMIT_S:.0f} s", flush=True)
    except KeyboardInterrupt:
        print(f"test 1: KeyboardInterrupt after {time.monotonic() - start:.1f} s", flush=True)
    state("after test 1")

    # flush=True: the output goes into a pipe (tee). C2d run 1 had no flush here.
    print(
        "test 2: press Ctrl+C one time now. If nothing happens in 10 s, close the terminal.",
        flush=True,
    )
    start = time.monotonic()
    try:
        events.get()
    except KeyboardInterrupt:
        print(f"test 2: KeyboardInterrupt after {time.monotonic() - start:.1f} s", flush=True)
    print("probe C: done", flush=True)


if __name__ == "__main__":
    main()
