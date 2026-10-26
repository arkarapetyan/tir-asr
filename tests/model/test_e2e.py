"""T-E2E-01, T-E2E-02: the full program with the real models (C2d, branch c2d-cli).

Requirements: K1 (each total < 5 s), F2, F3, F5. Decisions: D-022, D-025, D-032, D-043. The test
loads the models with the function of the program (`app.load_models`), does the warm-up, and
runs the pipeline with the test WAV source: clip 1, then clip 2, at real-time speed. The gap
between the clips is 152 + 480 = 632 ms of silence, so both segments close (D-032).

T-E2E-02 is the automatic form of L-02 (D-044). It starts the installed command `tir-asr` in a
new process, with the real models and the real default microphone, waits for "Listening", and
sends SIGINT, as Ctrl+C does. The time limits are in this test only, not in the program.

Run the tests with `env -u LD_LIBRARY_PATH` (D-030). The test runs on Aren's laptop only. It imports
the program modules inside the test function, so that CI can collect this file (D-021).

Input files (local only, data/ and models/ are in .gitignore):
  data/eval/c2-check{1,2}.16k.wav                16 kHz mono PCM
  models/nllb-200-distilled-600M-ct2-float16/    the converted CTranslate2 model
"""

import importlib.util
import io
import os
import queue
import re
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

from tir_asr.config import Params

pytestmark = pytest.mark.model

ROOT = Path(__file__).resolve().parents[2]
CLIPS = [ROOT / "data" / "eval" / f"c2-check{n}.16k.wav" for n in (1, 2)]
SUPPORT = ROOT / "tests" / "support" / "wav_source.py"
K1_S = 5.0
HEAD = re.compile(r"^\[(\d\d):(\d\d):(\d\d)\] (.+)$")
TOTAL = re.compile(r"\| Total (\d+\.\d\d)s\]$")
LISTENING = "Listening. Press Ctrl+C to stop."
STARTUP_LIMIT_S = 120.0  # T-E2E-02, test only: the time for the startup
AFTER_LISTENING_S = 2.0  # T-E2E-02: the program listens for this time before the SIGINT
STOP_LIMIT_S = 10.0  # T-E2E-02, test only: the time from the SIGINT to the end of the process


def report(line: str) -> None:
    print(f"RESULT {line}", flush=True)


def load_wav_source():
    """Load tests/support/wav_source.py by its path (pytest uses --import-mode=importlib)."""
    spec = importlib.util.spec_from_file_location("wav_source", SUPPORT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_e2e_01_full_pipeline_with_the_real_models():
    from tir_asr.app import load_models
    from tir_asr.pipeline import run, warm_up

    wav_source = load_wav_source()
    params = Params()
    log = io.StringIO()
    vad, transcriber, translator = load_models(params, log)
    for line in log.getvalue().splitlines():
        report(line)
    asr_s, mt_s = warm_up(transcriber, translator, time.monotonic)
    report(f"warm-up ASR {asr_s:.3f} s, MT {mt_s:.3f} s")

    out, err = io.StringIO(), io.StringIO()
    code = run(
        wav_source.WavSource(CLIPS), vad, transcriber, translator, params, time.monotonic, out, err
    )

    lines = out.getvalue().splitlines()
    for line in lines:
        report(line)
    assert code == 0, err.getvalue()
    assert err.getvalue() == ""

    heads = [HEAD.match(line) for line in lines if HEAD.match(line)]
    assert len(heads) >= 2, "a clip ends with less than 512 ms of silence (D-032)"
    assert len(heads) == 2, f"{len(heads)} blocks, expected 2"
    assert [head.group(4) for head in heads] == ["Me", "Me"]
    seconds = [int(h.group(1)) * 3600 + int(h.group(2)) * 60 + int(h.group(3)) for h in heads]
    assert seconds == sorted(seconds), f"the blocks are not in time order: {seconds}"
    assert "(no text)" not in out.getvalue()

    totals = [float(match.group(1)) for line in lines if (match := TOTAL.search(line))]
    report(f"totals {totals} s; K1 limit {K1_S} s")
    assert len(totals) == 2
    assert all(total < K1_S for total in totals), f"a total is not under {K1_S} s: {totals}"


def test_e2e_02_ctrl_c_stops_the_program():
    command = Path(sys.executable).with_name("tir-asr")
    assert command.exists(), f"{command} does not exist; run `uv sync` one time (D-043)"
    process = subprocess.Popen(
        [str(command)],
        cwd=ROOT,  # the MT model folder is relative to the project folder (section 2.4)
        env=dict(os.environ, HF_HUB_OFFLINE="1"),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,  # one pipe: NeMo writes its load lines to stderr
        text=True,
        encoding="utf-8",
    )
    lines: queue.Queue = queue.Queue()

    def read() -> None:
        for line in process.stdout:
            lines.put(line.rstrip("\n"))
        lines.put(None)  # the end of the output

    threading.Thread(target=read, daemon=True).start()
    output = []
    try:
        deadline = time.monotonic() + STARTUP_LIMIT_S
        while not output or output[-1] != LISTENING:
            try:
                line = lines.get(timeout=max(0.1, deadline - time.monotonic()))
            except queue.Empty:
                pytest.fail(f"no {LISTENING!r} line within {STARTUP_LIMIT_S:.0f} s")
            assert line is not None, f"the program ended before {LISTENING!r}: {output[-5:]}"
            output.append(line)
        time.sleep(AFTER_LISTENING_S)
        sent = time.monotonic()
        process.send_signal(signal.SIGINT)
        try:
            code = process.wait(timeout=STOP_LIMIT_S)
        except subprocess.TimeoutExpired:
            pytest.fail(f"the program did not stop within {STOP_LIMIT_S:.0f} s after SIGINT (L-02)")
        stopped_s = time.monotonic() - sent
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()

    while (line := lines.get(timeout=STOP_LIMIT_S)) is not None:
        output.append(line)
    program = [line for line in output if not line.startswith(("[NeMo", " ", "\t")) and line]
    for line in program[-12:]:
        report(line)
    report(f"exit code {code}, {stopped_s:.2f} s after SIGINT")
    assert code == 0
    # The last line of the program (not a NeMo line, not indented, not empty).
    assert program[-1].startswith("Stopped. Segments: "), program[-3:]
