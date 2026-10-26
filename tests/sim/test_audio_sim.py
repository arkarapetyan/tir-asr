"""T-AUDIO-01 to T-AUDIO-04, T-SIM-01: the audio sources (C2d `c2d-audio`; C4 `c4-audio`, `c4-cli`).

Contract: ARCHITECTURE.md sections 2.1 and 7. Decisions: D-020, D-041, D-054. The limits come
from probe B (`scripts/probe_audio.py`; TESTS.md, "C2d audio probes").

T-AUDIO-01, T-AUDIO-03, and T-AUDIO-04 load a null sink with `pactl` and unload it after the
test. T-AUDIO-01 plays a tone into the sink with `pw-play`, and the adapter records the monitor
of the sink. T-AUDIO-02 starts a new Python process with no PulseAudio server. T-AUDIO-04
compares the device list and the two default ids with the values that `pactl` gives.

T-SIM-01 (C4, D-054) loads two null sinks and runs the program functions with the real models
and two sources at the same time: `pw-play` plays the two sides of eval script S1 into the two
sinks, and the program captures their monitors. It is also a model test: run it with
`env -u LD_LIBRARY_PATH HF_HUB_OFFLINE=1` (D-030). Its input files are local only (data/).

Caution: the tests change the audio server for a few seconds. Do not run them during a call.
If a test stops and the sink stays, run `pactl list short modules | grep null-sink`, then
`pactl unload-module <number>`.

The tests run on Aren's laptop only (marker `sim`). They import `soundcard` and the adapter
inside the test functions, so that CI can collect this file without the `laptop` group (D-021).
"""

import io
import math
import os
import re
import subprocess
import sys
import threading
import time
import wave
from pathlib import Path

import numpy as np
import pytest

from tir_asr.config import SAMPLE_RATE, VAD_FRAME

pytestmark = pytest.mark.sim

SINK = "tir_t_audio"
MONITOR = f"{SINK}.monitor"

BLOCKS = 200  # 6.4 s in all
SILENT_BLOCKS = 30  # blocks 0-29: no audio; the tone starts after block 29
TONE_HZ = 440.0
TONE_AMPLITUDE = 0.25  # peak, -12 dBFS
TONE_S = 4.0
TONE_FILE_RATE = 48_000  # Hz, the rate of the sink (probe A)

BLOCK_S = VAD_FRAME / SAMPLE_RATE  # 0.032 s
MEAN_GAP_TOLERANCE_S = 0.0005  # span / (n - 1) = 32 ms +- 0.5 ms (D-041)
MAX_GAP_S = 2 * BLOCK_S  # 64 ms (D-041)
SILENCE_LIMIT = 1e-6  # max |x| in blocks 0-29
FREQUENCY_TOLERANCE_HZ = 1.0
RMS_TOLERANCE = 0.10  # +- 10 % of the played RMS
HOLE_SAMPLES = 16  # a run of this many exact zeros inside the tone is a hole
ROUTING_CHECK_S = 0.5  # the routing check runs this time after the player starts
PROCESS_TIMEOUT_S = 30  # test only: T-AUDIO-02 must not wait with no limit

# T-SIM-01 (D-054)
ROOT = Path(__file__).resolve().parents[2]
SIM_SINKS = {"Me": "tir_t_me", "System": "tir_t_system"}
S1_FILES = {
    "Me": ROOT / "data" / "eval" / "raw" / "s1.mic.wav",
    "System": ROOT / "data" / "eval" / "raw" / "s1.call.wav",
}
SCRIPTS_MD = ROOT / "docs" / "eval" / "scripts.md"
AFTER_PLAY_S = 2.0  # each source stops this time after the length of S1
START_LIMIT_S = 30.0  # test only: the time for the first block of each source
K1_S = 5.0
HEAD = re.compile(r"^\[(\d\d):(\d\d):(\d\d)\] (.+)$")
TOTAL = re.compile(r"\| Total (\d+\.\d\d)s\]$")


def report(line: str) -> None:
    print(f"RESULT {line}", flush=True)


def pactl(*args: str) -> str:
    result = subprocess.run(["pactl", *args], capture_output=True, text=True)
    assert result.returncode == 0, f"pactl {' '.join(args)} failed: {result.stderr}"
    return result.stdout.strip()


def pactl_rows(kind: str) -> list[list[str]]:
    return [line.split("\t") for line in pactl("list", "short", kind).splitlines() if line]


def defaults() -> tuple[str, str]:
    return pactl("get-default-sink"), pactl("get-default-source")


@pytest.fixture
def null_sink():
    """Load a null sink. Unload it after the test. The defaults must not change (D-041)."""
    assert SINK not in [row[1] for row in pactl_rows("sinks")], (
        f"a sink {SINK!r} is already there; unload it first (see the module docstring)"
    )
    before = defaults()
    module = pactl("load-module", "module-null-sink", f"sink_name={SINK}")
    try:
        yield SINK
    finally:
        pactl("unload-module", module)
    assert defaults() == before, f"the defaults changed: {before} -> {defaults()}"


def write_tone(path: Path) -> None:
    """A mono 16-bit WAV file with the tone, at the rate of the sink."""
    t = np.arange(int(TONE_S * TONE_FILE_RATE)) / TONE_FILE_RATE
    samples = np.round(TONE_AMPLITUDE * 32767 * np.sin(2 * np.pi * TONE_HZ * t)).astype("<i2")
    with wave.open(str(path), "wb") as file:
        file.setnchannels(1)
        file.setsampwidth(2)
        file.setframerate(TONE_FILE_RATE)
        file.writeframes(samples.tobytes())


class RoutingCheck(threading.Thread):
    """After ROUTING_CHECK_S, the new playback streams must be on the probe sink.

    Else the check stops the player, so that the tone does not play on the speakers. The check
    runs in a thread, so that it does not delay the reads of the adapter.
    """

    def __init__(self, player: subprocess.Popen, sink_index: str, inputs_before: set[str]):
        super().__init__(daemon=True)
        self.player = player
        self.sink_index = sink_index
        self.inputs_before = inputs_before
        self.new: dict[str, str] = {}
        self.error: BaseException | None = None

    def run(self) -> None:
        try:
            time.sleep(ROUTING_CHECK_S)
            rows = pactl_rows("sink-inputs")
            self.new = {row[0]: row[1] for row in rows if row[0] not in self.inputs_before}
            if not self.new or any(sink != self.sink_index for sink in self.new.values()):
                self.player.kill()
        except BaseException as error:  # the main thread reports it in an assert
            self.player.kill()
            self.error = error


def runs(mask: np.ndarray) -> list[tuple[int, int]]:
    """The (start, end) index pairs of the runs of True values; `end` is exclusive."""
    edges = np.diff(np.concatenate([[0], mask.astype(np.int8), [0]]))
    return list(zip(np.flatnonzero(edges == 1), np.flatnonzero(edges == -1), strict=True))


def test_audio_01_monitor_blocks_have_the_contract_format_and_content(null_sink, tmp_path):
    from tir_asr.audio.soundcard_source import SoundcardSource

    tone = tmp_path / "tone.wav"
    write_tone(tone)
    sink_index = next(row[0] for row in pactl_rows("sinks") if row[1] == SINK)

    source = SoundcardSource("System", MONITOR)
    report(f"audio device name: {source.name}")
    blocks = []
    player = None
    check = None
    stream = source.blocks()
    try:
        for block in stream:
            blocks.append(block)
            if len(blocks) == SILENT_BLOCKS:
                inputs_before = {row[0] for row in pactl_rows("sink-inputs")}
                play_start = time.monotonic()
                player = subprocess.Popen(
                    ["pw-play", "--target", SINK, str(tone)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                check = RoutingCheck(player, sink_index, inputs_before)
                check.start()
            if len(blocks) == BLOCKS:
                break
    finally:
        stream.close()
        if player is not None and player.poll() is None:
            player.kill()

    assert check is not None, "the player did not start"
    check.join()
    _, player_errors = player.communicate()
    report(f"routing: new playback streams (stream: sink) {check.new}, probe sink {sink_index}")
    report(f"pw-play exit code {player.returncode}, stderr {player_errors.strip()!r}")
    assert check.error is None, f"the routing check failed: {check.error!r}"
    assert check.new, "no new playback stream"
    assert all(sink == sink_index for sink in check.new.values()), "the tone went to another sink"
    assert player.returncode == 0, f"pw-play exit code {player.returncode}: {player_errors}"

    # Format of each block.
    assert len(blocks) == BLOCKS
    assert {block.source for block in blocks} == {"System"}
    assert {(block.samples.shape, block.samples.dtype) for block in blocks} == {
        ((VAD_FRAME,), np.dtype(np.float32))
    }

    # Arrival times.
    arrivals = np.array([block.arrival for block in blocks])
    gaps = np.diff(arrivals)
    mean_gap = (arrivals[-1] - arrivals[0]) / (BLOCKS - 1)
    report(
        f"gaps (ms): min {gaps.min() * 1000:.1f}, median {np.median(gaps) * 1000:.1f}, "
        f"max {gaps.max() * 1000:.1f}; span / (n - 1) {mean_gap * 1000:.3f} ms"
    )
    assert np.all(gaps > 0), "the arrival times do not increase"
    assert abs(mean_gap - BLOCK_S) <= MEAN_GAP_TOLERANCE_S, f"mean gap {mean_gap * 1000:.3f} ms"
    assert gaps.max() <= MAX_GAP_S, f"a gap of {gaps.max() * 1000:.1f} ms"

    # Silent phase.
    silent = np.concatenate([block.samples for block in blocks[:SILENT_BLOCKS]])
    report(f"silent phase: max |x| {np.abs(silent).max():.2e}")
    assert np.abs(silent).max() < SILENCE_LIMIT

    # Tone: the longest run of blocks with the tone, without its first and last block.
    rms = np.array([np.sqrt(np.mean(block.samples.astype(np.float64) ** 2)) for block in blocks])
    tone_runs = runs(rms > TONE_AMPLITUDE / 10)
    assert tone_runs, "no block has the tone"
    start, end = max(tone_runs, key=lambda run: run[1] - run[0])
    report(f"tone: blocks {start} to {end - 1}, first block {(arrivals[start] - play_start):.3f} s")
    x = np.concatenate([block.samples for block in blocks[start + 1 : end - 1]]).astype(np.float64)
    spectrum = np.abs(np.fft.rfft(x * np.hanning(len(x))))
    peak_hz = int(np.argmax(spectrum)) * SAMPLE_RATE / len(x)
    level = np.sqrt(np.mean(x**2))
    expected = TONE_AMPLITUDE / np.sqrt(2)
    holes = [run for run in runs(x == 0.0) if run[1] - run[0] >= HOLE_SAMPLES]
    report(f"tone: {peak_hz:.2f} Hz, RMS {level:.4f} (played {expected:.4f}), holes {len(holes)}")
    assert abs(peak_hz - TONE_HZ) <= FREQUENCY_TOLERANCE_HZ
    assert abs(level - expected) <= RMS_TOLERANCE * expected
    assert not holes, f"{len(holes)} run(s) of {HOLE_SAMPLES} or more zeros inside the tone"


NO_SERVER_SCRIPT = """
from tir_asr.audio.soundcard_source import AudioError, SoundcardSource, list_sources

for name, call in [("constructor", lambda: SoundcardSource("Me", "x")), ("list", list_sources)]:
    try:
        call()
    except AudioError as error:
        print(f"{name}: AudioError: {error}")
    else:
        print(f"{name}: no error")
"""
NO_SERVER = "AudioError: audio: cannot connect to the PulseAudio server"


def test_audio_02_no_pulseaudio_server(tmp_path):
    # A script file, not `python -c`: soundcard reads sys.argv at import.
    script = tmp_path / "no_server.py"
    script.write_text(NO_SERVER_SCRIPT, encoding="utf-8")
    environment = dict(os.environ, PULSE_SERVER=f"unix:{tmp_path / 'no-such-socket'}")

    result = subprocess.run(
        [sys.executable, "-I", str(script)],
        env=environment,
        capture_output=True,
        text=True,
        timeout=PROCESS_TIMEOUT_S,
    )

    report(f"no server: stdout {result.stdout.strip()!r}, exit code {result.returncode}")
    # [RUN] in the workspace: a second `import soundcard` in the same process fails again with
    # an AssertionError, so each call gives the same error.
    assert result.stdout.splitlines() == [f"constructor: {NO_SERVER}", f"list: {NO_SERVER}"], (
        result.stderr
    )


def test_audio_03_device_id_must_match_exactly(null_sink):
    import soundcard

    from tir_asr.audio.soundcard_source import AudioError, SoundcardSource

    # The risk is real: soundcard selects the monitor from a part of its name.
    fuzzy = soundcard.get_microphone(SINK, include_loopback=True)
    report(f"soundcard.get_microphone({SINK!r}) gives {fuzzy.id!r}")
    assert fuzzy.id == MONITOR

    with pytest.raises(AudioError) as raised:
        SoundcardSource("Me", SINK)

    report(f"audio error message: {raised.value}")
    assert str(raised.value) == f"audio: no source with the exact id {SINK}"


def test_audio_04_device_list_and_default_ids(null_sink):
    from tir_asr.audio.soundcard_source import (
        default_microphone_id,
        default_system_id,
        list_sources,
    )

    sources = list_sources()
    for source in sources:
        report(f"source: monitor={source.monitor} {source.id} ({source.name})")
    default_sink, default_source = defaults()
    mic, system = default_microphone_id(), default_system_id()
    report(f"pactl defaults: sink {default_sink}, source {default_source}")
    report(f"adapter defaults: mic {mic}, system {system}")

    ids = [source.id for source in sources]
    assert len(ids) == len(set(ids)), f"an id occurs two times: {ids}"
    kinds = {source.id: source.monitor for source in sources}
    assert kinds.get(MONITOR) is True, f"{MONITOR} is not in the list as a monitor"
    assert mic == default_source
    assert system == f"{default_sink}.monitor"
    assert kinds.get(system) is True, f"{system} is not in the list as a monitor"


@pytest.fixture
def two_null_sinks():
    """Load the two null sinks of T-SIM-01. Unload them after the test. The defaults must not
    change."""
    existing = [row[1] for row in pactl_rows("sinks")]
    for sink in SIM_SINKS.values():
        assert sink not in existing, f"a sink {sink!r} is already there; unload it first"
    before = defaults()
    modules = []
    try:
        for sink in SIM_SINKS.values():
            modules.append(pactl("load-module", "module-null-sink", f"sink_name={sink}"))
        yield SIM_SINKS
    finally:
        for module in reversed(modules):
            pactl("unload-module", module)
    assert defaults() == before, f"the defaults changed: {before} -> {defaults()}"


def write_pcm16(source: Path, target: Path) -> float:
    """Copy a mono float32 WAV file to a 16-bit WAV file at the same rate. Return its length."""
    from scipy.io import wavfile

    rate, audio = wavfile.read(source)
    assert audio.ndim == 1 and audio.dtype == np.float32, f"{source}: not mono float32"
    samples = np.round(np.clip(audio, -1.0, 1.0) * 32767).astype("<i2")
    with wave.open(str(target), "wb") as file:
        file.setnchannels(1)
        file.setsampwidth(2)
        file.setframerate(rate)
        file.writeframes(samples.tobytes())
    return len(samples) / rate


class Recorded:
    """Test wrapper of an AudioSource: it records the arrival times, sets `started` at the first
    block, and stops the source after `count` blocks."""

    def __init__(self, source, count: int):
        self.source = source
        self.label = source.label
        self.count = count
        self.arrivals: list[float] = []
        self.started = threading.Event()

    def blocks(self):
        stream = self.source.blocks()
        try:
            for block in stream:
                self.arrivals.append(block.arrival)
                self.started.set()
                yield block
                if len(self.arrivals) >= self.count:
                    break
        finally:
            stream.close()


class Players(threading.Thread):
    """At the first block of each source, play each file into its sink with `pw-play`.

    After ROUTING_CHECK_S, the two new playback streams must be on the two test sinks. Else the
    thread stops the players, so that the audio does not play on the speakers.
    """

    def __init__(self, files: dict[str, Path], sinks: dict[str, str], events, indexes: set):
        super().__init__(daemon=True)
        self.files, self.sinks, self.events, self.indexes = files, sinks, events, indexes
        self.processes: list[subprocess.Popen] = []
        self.new: dict[str, str] = {}
        self.error: BaseException | None = None

    def kill(self) -> None:
        for process in self.processes:
            if process.poll() is None:
                process.kill()

    def run(self) -> None:
        try:
            for event in self.events:
                assert event.wait(timeout=START_LIMIT_S), "a source gave no block"
            before = {row[0] for row in pactl_rows("sink-inputs")}
            for label, path in self.files.items():
                command = ["pw-play", "--target", self.sinks[label], str(path)]
                self.processes.append(
                    subprocess.Popen(
                        command, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True
                    )
                )
            time.sleep(ROUTING_CHECK_S)
            rows = pactl_rows("sink-inputs")
            self.new = {row[0]: row[1] for row in rows if row[0] not in before}
            if len(self.new) != len(self.files) or set(self.new.values()) != self.indexes:
                self.kill()
        except BaseException as error:  # the main thread reports it in an assert
            self.kill()
            self.error = error


def parse_blocks(text: str) -> list[tuple[str, int, str, float]]:
    """(label, seconds, Armenian text, total) for each block of the program output."""
    blocks = []
    head = None
    hy = ""
    for line in text.splitlines():
        if match := HEAD.match(line):
            head = match
        elif line.startswith(" HY: "):
            hy = line.removeprefix(" HY: ")
        elif head is not None and (total := TOTAL.search(line)):
            hours, minutes, seconds = (int(head.group(n)) for n in (1, 2, 3))
            seconds = hours * 3600 + minutes * 60 + seconds
            blocks.append((head.group(4), seconds, hy, float(total.group(1))))
            head, hy = None, ""
    return blocks


@pytest.mark.model
def test_sim_01_two_sources_at_the_same_time(two_null_sinks, tmp_path):
    from tir_asr.app import load_models, log_versions
    from tir_asr.audio.soundcard_source import SoundcardSource
    from tir_asr.config import Params
    from tir_asr.eval.data import read_references
    from tir_asr.eval.metrics import wer
    from tir_asr.pipeline import run, warm_up

    for path in [*S1_FILES.values(), SCRIPTS_MD]:
        assert path.exists(), f"{path} is missing (local eval data, D-046)"
    copies = {label: tmp_path / f"{label}.wav" for label in S1_FILES}
    lengths = [write_pcm16(S1_FILES[label], copies[label]) for label in S1_FILES]
    count = math.ceil((max(lengths) + AFTER_PLAY_S) / BLOCK_S)
    report(f"S1 lengths {lengths} s; each source stops after {count} blocks")

    params = Params()
    log = io.StringIO()
    log_versions(params, log)
    sources = [SoundcardSource(label, f"{sink}.monitor") for label, sink in SIM_SINKS.items()]
    vads, transcriber, translator = load_models(params, log, list(SIM_SINKS))
    for line in log.getvalue().splitlines():
        report(line)
    asr_s, mt_s = warm_up(transcriber, translator, time.monotonic)
    report(f"warm-up ASR {asr_s:.3f} s, MT {mt_s:.3f} s")

    recorded = [Recorded(source, count) for source in sources]
    indexes = {row[0] for row in pactl_rows("sinks") if row[1] in SIM_SINKS.values()}
    players = Players(copies, SIM_SINKS, [r.started for r in recorded], indexes)
    players.start()
    out, err = io.StringIO(), io.StringIO()
    try:
        code = run(
            list(zip(recorded, vads, strict=True)),
            transcriber,
            translator,
            params,
            time.monotonic,
            out,
            err,
        )
    finally:
        players.join(timeout=START_LIMIT_S)
        players.kill()

    for line in out.getvalue().splitlines():
        report(line)
    report(f"routing: new playback streams (stream: sink) {players.new}, test sinks {indexes}")
    for process in players.processes:
        _, errors = process.communicate()
        report(f"pw-play exit code {process.returncode}, stderr {errors.strip()!r}")
    assert players.error is None, f"the players failed: {players.error!r}"
    assert set(players.new.values()) == indexes, "the audio went to another sink"
    assert all(process.returncode == 0 for process in players.processes)

    # (1) Exit code and errors.
    assert code == 0, err.getvalue()
    assert err.getvalue() == ""

    # (2) Labels and time order.
    blocks = parse_blocks(out.getvalue())
    labels = [block[0] for block in blocks]
    report(f"blocks: {labels.count('Me')} Me, {labels.count('System')} System")
    assert set(labels) == set(SIM_SINKS), f"labels {sorted(set(labels))}"
    for label in SIM_SINKS:
        times = [block[1] for block in blocks if block[0] == label]
        assert times == sorted(times), f"{label}: the block times go back: {times}"

    # (3) Each label has the text of its own side (D-054: the source of each label).
    references = read_references(SCRIPTS_MD, "s1")
    sides = {"Me": "mic", "System": "call"}
    refs = {
        side: " ".join(line.hy for line in references if line.side == side)
        for side in sides.values()
    }
    rates = {}
    for label in SIM_SINKS:
        texts = [block[2] for block in blocks if block[0] == label and block[2] != "(no text)"]
        hyp = " ".join(texts)
        for side, ref in refs.items():
            rates[(label, side)] = wer([ref], [hyp])
        mic_wer, call_wer = rates[(label, "mic")], rates[(label, "call")]
        report(f"{label}: WER {mic_wer:.3f} (mic references), {call_wer:.3f} (call references)")
    assert rates[("Me", "mic")] < rates[("Me", "call")]
    assert rates[("System", "call")] < rates[("System", "mic")]

    # (4) K1.
    totals = [block[3] for block in blocks]
    report(f"totals: max {max(totals):.2f} s, mean {sum(totals) / len(totals):.2f} s")
    assert all(total < K1_S for total in totals), f"a total is not under {K1_S} s: {totals}"

    # (5) Arrival gaps of each source (Q-10), with the drift numbers (D-020).
    for source in recorded:
        arrivals = np.array(source.arrivals)
        gaps = np.diff(arrivals)
        mean_gap = (arrivals[-1] - arrivals[0]) / (len(arrivals) - 1)
        report(
            f"{source.label}: {len(arrivals)} blocks; gaps (ms) min {gaps.min() * 1000:.1f}, "
            f"max {gaps.max() * 1000:.1f}; span / (n - 1) {mean_gap * 1000:.3f} ms; "
            f"span / real time {mean_gap / BLOCK_S:.4f}"
        )
        assert gaps.max() <= MAX_GAP_S, f"{source.label}: a gap of {gaps.max() * 1000:.1f} ms"
