"""T-AUDIO-01 to T-AUDIO-04: the soundcard source adapter (C2d `c2d-audio`, C4 `c4-audio`).

Contract: ARCHITECTURE.md sections 2.1 and 7. Decisions: D-020, D-041, D-054. The limits come
from probe B (`scripts/probe_audio.py`; TESTS.md, "C2d audio probes").

T-AUDIO-01, T-AUDIO-03, and T-AUDIO-04 load a null sink with `pactl` and unload it after the
test. T-AUDIO-01 plays a tone into the sink with `pw-play`, and the adapter records the monitor
of the sink. T-AUDIO-02 starts a new Python process with no PulseAudio server. T-AUDIO-04
compares the device list and the two default ids with the values that `pactl` gives.

Caution: the tests change the audio server for a few seconds. Do not run them during a call.
If a test stops and the sink stays, run `pactl list short modules | grep null-sink`, then
`pactl unload-module <number>`.

The tests run on Aren's laptop only (marker `sim`). They import `soundcard` and the adapter
inside the test functions, so that CI can collect this file without the `laptop` group (D-021).
"""

import os
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
