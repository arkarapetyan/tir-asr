"""T-E2E-01 to T-E2E-03: the full program with the real models (C2d, branch c2d-cli; C6).

Requirements: K1 (each total < 5 s), F2, F3, F5. Decisions: D-022, D-025, D-032, D-043, D-054,
D-059 (C5: `load_models` also loads the speaker model, and the warm-up calls it), D-062 (C6:
`load_models` gives the text step, and `run()` and `warm_up()` get it).
The test loads the models with the functions of the program (`app.log_versions`,
`app.load_models`), does the warm-up, and runs the pipeline with the test WAV source as the one
source "Me": clip 1, then clip 2, at real-time speed. The gap between the clips is
152 + 480 = 632 ms of silence, so both segments close (D-032).

T-E2E-02 is the automatic form of L-02 (D-044). It starts the installed command `tir-asr` in a
new process, with the real models, the default microphone, and the monitor of the default
output (no flags, D-054), waits for "Listening", and sends SIGINT, as Ctrl+C does. The time
limits are in this test only, not in the program. D-061 (C5): the output must have no abort line
after the stop (L-02: `Aborting.` or `terminate called`, exit code 134).

T-E2E-03 (C6, D-062 parts 4 and 5, D-063 part 2) is T-E2E-01 and T-E2E-02 with the P4 text step:
(a) `load_models(…, seamless=True)` and the WAV source; (b) the installed command with
`--seamless`. With P4, NeMo ASR and NLLB do not load, and the latency line has the step `s2t`.

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


def wav_run(seamless: bool) -> tuple[list[str], list[str]]:
    """T-E2E-01 and T-E2E-03 (a): the WAV source as "Me". Return (startup lines, output lines)."""
    from tir_asr.app import load_models, log_versions
    from tir_asr.pipeline import run, warm_up

    wav_source = load_wav_source()
    params = Params()
    log = io.StringIO()
    log_versions(params, log)
    vads, text_step, embedder = load_models(params, log, ["Me"], seamless=seamless)
    startup = log.getvalue().splitlines()
    for line in startup:
        report(line)
    assert any(line.startswith("startup: speaker model loaded in ") for line in startup)
    asr_s, mt_s, spk_s = warm_up(text_step, embedder, time.monotonic)
    report(f"warm-up ASR {asr_s:.3f} s, MT {mt_s:.3f} s, speaker {spk_s:.3f} s")

    out, err = io.StringIO(), io.StringIO()
    source = wav_source.WavSource(CLIPS)
    code = run([(source, vads[0])], text_step, params, time.monotonic, out, err)

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
    return startup, lines


def test_e2e_01_full_pipeline_with_the_real_models():
    startup, lines = wav_run(seamless=False)

    assert any(line.startswith("startup: text step cascade (P1)") for line in startup)
    latency = [line for line in lines if line.startswith(" [Latency: ")]
    assert all(" asr " in line and " mt " in line for line in latency), latency


def test_e2e_03_a_full_pipeline_with_p4():
    startup, lines = wav_run(seamless=True)

    assert any(line.startswith("startup: text step seamless (P4)") for line in startup)
    assert any(line.startswith("startup: Seamless loaded in ") for line in startup)
    loaded = [line for line in startup if line.startswith(("startup: ASR ", "startup: MT "))]
    assert loaded == [], f"P1 models loaded with P4: {loaded}"
    latency = [line for line in lines if line.startswith(" [Latency: ")]
    assert all(" s2t " in line and " asr " not in line for line in latency), latency


def ctrl_c_run(args: list[str]) -> list[str]:
    """T-E2E-02 and T-E2E-03 (b): SIGINT after "Listening". Return the lines before it."""
    command = Path(sys.executable).with_name("tir-asr")
    assert command.exists(), f"{command} does not exist; run `uv sync` one time (D-043)"
    process = subprocess.Popen(
        [str(command), *args],
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
    aborts = [line for line in output if "Aborting" in line or "terminate called" in line]
    assert aborts == [], f"the program aborted at the stop (D-061): {aborts}"
    assert code == 0
    # D-054: the two sources come before "Listening", one line for each label.
    before = program[: program.index(LISTENING)]
    for label in ("Me", "System"):
        found = [line for line in before if line.startswith(f"startup: source {label}: ")]
        assert len(found) == 1, f"no single 'startup: source {label}' line: {before[-8:]}"
    # The last line of the program (not a NeMo line, not indented, not empty).
    assert program[-1].startswith("Stopped. Segments: "), program[-3:]
    return before


def test_e2e_02_ctrl_c_stops_the_program():
    before = ctrl_c_run([])

    assert any(line.startswith("startup: text step cascade (P1)") for line in before)


def test_e2e_03_b_ctrl_c_stops_the_program_with_p4():
    before = ctrl_c_run(["--seamless"])

    assert any(line.startswith("startup: text step seamless (P4)") for line in before)
    assert any(line.startswith("startup: warm-up s2t ") for line in before), before[-4:]
