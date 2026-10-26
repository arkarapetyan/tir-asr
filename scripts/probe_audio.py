"""Audio probes for T-AUDIO-01 (C2d). Not part of the package. The program does not use them.

Probe A: load a null sink, list the sources, find the exact id of its monitor, unload the
sink, and check that the default sink and the default source did not change.

Probe B: record blocks from the monitor of a null sink in the same way as the adapter
(16 kHz, 1 channel, 512 samples). First with no audio, then while `pw-play` plays a 440 Hz
tone into the sink. Then record blocks from the default microphone. Print the shape, the type,
the range, the gaps between the arrival times, the stream latency, the tone frequency, and the
level. No audio goes to disk, except the generated tone in a temporary folder.

Run this file as a script, not with `python -c`: `soundcard` reads `sys.argv` at import.

Caution: a probe changes the audio server for a few seconds. Do not run it during a call.
Probe B plays the tone into the null sink only. If you hear a tone, the routing failed: the
probe then stops the player and reports a problem.
If a probe stops with an error, run `pactl list short modules | grep null-sink`, then
`pactl unload-module <number>`.
"""

import argparse
import importlib.metadata
import platform
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import wave
from pathlib import Path

import numpy as np

SINK = "tir_probe"
MONITOR = f"{SINK}.monitor"

RATE = 16_000  # Hz, as the adapter (ARCHITECTURE.md section 2.1)
BLOCK = 512  # samples, as the adapter: 32 ms
TONE_HZ = 440.0
TONE_AMPLITUDE = 0.25  # peak, -12 dBFS
TONE_S = 4.0
TONE_FILE_RATE = 48_000  # Hz, the rate of the sink (probe A)
SILENT_BLOCKS = 30  # 0.96 s with no audio before the tone
SIM_BLOCKS = 200  # 6.4 s in all: the tone (4 s) ends before the last block
MIC_BLOCKS = 100  # 3.2 s from the default microphone
STALL_S = 3.0  # the watchdog prints a warning after this time with no block
ROUTING_CHECK_S = 0.5  # the routing check runs this time after the player starts


def run(*args: str) -> str:
    """Run a command and return its output. Stop with its error output if it fails."""
    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode != 0:
        sys.exit(f"probe_audio: {' '.join(args)} failed ({result.returncode}): {result.stderr}")
    return result.stdout.strip()


def defaults() -> tuple[str, str]:
    return run("pactl", "get-default-sink"), run("pactl", "get-default-source")


def print_tools() -> None:
    soundcard_version = importlib.metadata.version("soundcard")
    print(f"python {platform.python_version()}, soundcard {soundcard_version}")
    for tool in ("pactl", "pw-play"):
        path = shutil.which(tool)
        version = " | ".join(run(tool, "--version").splitlines()) if path else "NOT FOUND"
        print(f"{tool}: {path}: {version}")
    keys = ("Server Name", "Server Version", "Default Sample Specification")
    for line in run("pactl", "info").splitlines():
        if line.startswith(keys):
            print(f"pactl info: {line}")


def print_devices(soundcard) -> list[str]:
    """Print the sources and the sinks. Return the soundcard ids of all microphones."""
    print("pactl sources:")
    for line in run("pactl", "list", "short", "sources").splitlines():
        print(f"  {line}")
    print("soundcard microphones (include_loopback=True):")
    mics = soundcard.all_microphones(include_loopback=True)
    for mic in mics:
        print(f"  id={mic.id!r} name={mic.name!r} channels={mic.channels}", end="")
        print(f" loopback={mic.isloopback}")
    print("soundcard speakers:")
    for speaker in soundcard.all_speakers():
        print(f"  id={speaker.id!r} name={speaker.name!r} channels={speaker.channels}")
    return [mic.id for mic in mics]


def probe_a() -> int:
    print_tools()
    import soundcard  # the import fails with no PulseAudio server

    errors = []
    before = defaults()
    print(f"defaults before: sink={before[0]!r} source={before[1]!r}")

    t0 = time.monotonic()
    module = run("pactl", "load-module", "module-null-sink", f"sink_name={SINK}")
    print(f"loaded module-null-sink: module {module} ({time.monotonic() - t0:.3f} s)")
    try:
        loaded = defaults()
        print(f"defaults with the null sink: sink={loaded[0]!r} source={loaded[1]!r}")
        if loaded != before:
            errors.append("the defaults changed when the null sink loaded")

        ids = print_devices(soundcard)
        if MONITOR in ids:
            print(f"the monitor has the exact id {MONITOR!r}")
        else:
            errors.append(f"no microphone has the exact id {MONITOR!r}")

        mic = soundcard.default_microphone()
        print(f"soundcard default_microphone: id={mic.id!r} name={mic.name!r}")
        if mic.id != before[1]:
            errors.append(f"default_microphone id {mic.id!r} is not the default source")
    finally:
        run("pactl", "unload-module", module)
        print(f"unloaded module {module}")

    after = defaults()
    print(f"defaults after: sink={after[0]!r} source={after[1]!r}")
    if after != before:
        errors.append("the defaults after the unload are not the defaults before the load")
    if SINK in run("pactl", "list", "short", "sinks"):
        errors.append(f"the sink {SINK!r} is still there after the unload")

    for error in errors:
        print(f"PROBLEM: {error}")
    print("probe A: OK" if not errors else f"probe A: {len(errors)} problem(s)")
    return 1 if errors else 0


class Watchdog:
    """Prints a warning when a recording gets no block for STALL_S seconds.

    `record()` waits with no time limit (soundcard 0.4.6). The warning tells the user to press
    Ctrl+C. The `finally` block then unloads the null sink.
    """

    def __init__(self):
        self.last = None  # the time of the last block; None when no recording runs
        threading.Thread(target=self._watch, daemon=True).start()

    def _watch(self):
        while True:
            time.sleep(0.5)
            last = self.last
            if last is not None and time.monotonic() - last > STALL_S:
                print(f"probe_audio: no block for {STALL_S} s. Press Ctrl+C.", file=sys.stderr)
                self.last = None


def record_blocks(recorder, count: int, watchdog: Watchdog) -> tuple[list, list]:
    """Record `count` blocks as the adapter does. The arrival time is taken after `record`."""
    blocks, arrivals = [], []
    for _ in range(count):
        data = recorder.record(numframes=BLOCK)
        now = time.monotonic()
        watchdog.last = now
        blocks.append(data)
        arrivals.append(now)
    return blocks, arrivals


def describe(name: str, blocks: list, arrivals: list, opened: float) -> list[str]:
    """Print the shape, type, range, and gap numbers. Return the problems."""
    problems = []
    shapes = sorted({block.shape for block in blocks})
    dtypes = sorted({str(block.dtype) for block in blocks})
    print(f"{name}: {len(blocks)} blocks, shapes {shapes}, dtypes {dtypes}")
    if shapes != [(BLOCK, 1)] or dtypes != ["float32"]:
        problems.append(f"{name}: shape or dtype is not ({BLOCK}, 1) float32")
    x = np.concatenate([block.reshape(-1) for block in blocks]).astype(np.float64)
    outside = int(np.sum(np.abs(x) > 1.0))
    print(f"{name}: all finite {bool(np.isfinite(x).all())}, min {x.min():.4f}, max {x.max():.4f}")
    print(f"{name}: samples outside [-1, 1]: {outside}")
    if not np.isfinite(x).all():
        problems.append(f"{name}: samples are not finite")

    gaps = np.diff(np.array(arrivals)) * 1000
    first = (arrivals[0] - opened) * 1000
    span = (arrivals[-1] - arrivals[0]) * 1000
    expected = (len(arrivals) - 1) * BLOCK / RATE * 1000
    print(f"{name}: first block {first:.1f} ms after the recorder opened")
    print(
        f"{name}: gaps (ms) min {gaps.min():.1f}, p05 {np.percentile(gaps, 5):.1f}, "
        f"median {np.median(gaps):.1f}, mean {gaps.mean():.2f}, p95 {np.percentile(gaps, 95):.1f}, "
        f"max {gaps.max():.1f}"
    )
    print(
        f"{name}: gaps under 16 ms: {int(np.sum(gaps < 16))}, over 48 ms: {int(np.sum(gaps > 48))}"
    )
    print(f"{name}: span {span:.1f} ms for {len(gaps)} gaps; real time is {expected:.1f} ms")
    return problems


def runs(mask: np.ndarray) -> list[tuple[int, int]]:
    """The (start, end) index pairs of the runs of True values; `end` is exclusive."""
    edges = np.diff(np.concatenate([[0], mask.astype(np.int8), [0]]))
    return list(zip(np.flatnonzero(edges == 1), np.flatnonzero(edges == -1), strict=True))


def tone_report(blocks: list, arrivals: list, play_start: float) -> list[str]:
    """Print the silent phase, the tone delay, frequency, level, and holes. Return problems."""
    problems = []
    rms = np.array([np.sqrt(np.mean(block.astype(np.float64) ** 2)) for block in blocks])
    silent = np.concatenate([block.reshape(-1) for block in blocks[:SILENT_BLOCKS]])
    print(f"tone: silent phase max |x| {np.abs(silent).max():.6f}")

    tone_runs = runs(rms > TONE_AMPLITUDE / 10)
    if not tone_runs:
        problems.append("tone: no block has the tone")
        return problems
    start, end = max(tone_runs, key=lambda run: run[1] - run[0])
    print(
        f"tone: {len(tone_runs)} run(s) of tone blocks; the longest is blocks {start} to {end - 1}"
    )
    delay = (arrivals[start] - play_start) * 1000
    print(f"tone: first tone block arrived {delay:.0f} ms after the player started")

    x = np.concatenate([block.reshape(-1) for block in blocks[start + 1 : end - 1]])
    x = x.astype(np.float64)
    spectrum = np.abs(np.fft.rfft(x * np.hanning(len(x))))
    peak_hz = int(np.argmax(spectrum)) * RATE / len(x)
    level = np.sqrt(np.mean(x**2))
    expected = TONE_AMPLITUDE / np.sqrt(2)
    print(
        f"tone: peak frequency {peak_hz:.2f} Hz (played {TONE_HZ} Hz, bin {RATE / len(x):.2f} Hz)"
    )
    print(f"tone: RMS {level:.4f} (played {expected:.4f}), peak |x| {np.abs(x).max():.4f}")
    holes = [run for run in runs(x == 0.0) if run[1] - run[0] >= 16]
    print(f"tone: runs of 16 or more exact zeros inside the tone: {len(holes)}")
    return problems


def write_tone(path: Path) -> None:
    """A mono 16-bit WAV file with the tone, at the rate of the sink."""
    t = np.arange(int(TONE_S * TONE_FILE_RATE)) / TONE_FILE_RATE
    samples = np.round(TONE_AMPLITUDE * 32767 * np.sin(2 * np.pi * TONE_HZ * t)).astype("<i2")
    with wave.open(str(path), "wb") as file:
        file.setnchannels(1)
        file.setsampwidth(2)
        file.setframerate(TONE_FILE_RATE)
        file.writeframes(samples.tobytes())


def pactl_rows(*args: str) -> list[list[str]]:
    return [line.split("\t") for line in run("pactl", "list", "short", *args).splitlines() if line]


def sink_index(name: str) -> str:
    for row in pactl_rows("sinks"):
        if row[1] == name:
            return row[0]
    sys.exit(f"probe_audio: no sink with the name {name!r}")


class RoutingCheck(threading.Thread):
    """After ROUTING_CHECK_S, each new sink input must be on the probe sink. Else stop the player.

    It uses `subprocess` directly, because `run()` calls `sys.exit`, which does not stop the
    program from a thread.
    """

    def __init__(self, player, probe_sink: str, inputs_before: set[str]):
        super().__init__()
        self.player = player
        self.probe_sink = probe_sink
        self.inputs_before = inputs_before
        self.result = "not run"
        self.ok = False

    def run(self):
        time.sleep(ROUTING_CHECK_S)
        listed = subprocess.run(
            ["pactl", "list", "short", "sink-inputs"], capture_output=True, text=True
        )
        if listed.returncode != 0:
            self.player.kill()
            self.result = f"pactl failed: {listed.stderr}"
            return
        rows = [line.split("\t") for line in listed.stdout.splitlines() if line]
        new = {row[0]: row[1] for row in rows if row[0] not in self.inputs_before}
        if not new:
            self.player.kill()
            self.result = "no new sink input"
        elif any(sink != self.probe_sink for sink in new.values()):
            self.player.kill()
            self.result = f"new sink input on another sink (input: sink) {new}; player stopped"
        else:
            self.ok = True
            self.result = f"OK: new sink input on the probe sink (input: sink) {new}"


def probe_b() -> int:
    if shutil.which("pw-play") is None:
        sys.exit("probe_audio: pw-play not found")
    import soundcard  # the import fails with no PulseAudio server

    problems = []
    before = defaults()
    print(f"defaults before: sink={before[0]!r} source={before[1]!r}")
    watchdog = Watchdog()

    with tempfile.TemporaryDirectory() as folder:
        tone = Path(folder) / "tone.wav"
        write_tone(tone)
        module = run("pactl", "load-module", "module-null-sink", f"sink_name={SINK}")
        print(f"loaded module-null-sink: module {module}")
        player = None
        try:
            probe_sink = sink_index(SINK)
            mic = soundcard.get_microphone(MONITOR, include_loopback=True)
            if mic.id != MONITOR:  # get_microphone can match a name substring (soundcard 0.4.6)
                sys.exit(f"probe_audio: get_microphone gave {mic.id!r}, not {MONITOR!r}")
            print(f"sim: recording from {mic.id!r}")
            opened = time.monotonic()
            with mic.recorder(samplerate=RATE, channels=1, blocksize=BLOCK) as recorder:
                print(f"sim: stream latency at open {recorder.latency * 1000:.1f} ms")
                watchdog.last = opened
                blocks, arrivals = record_blocks(recorder, SILENT_BLOCKS, watchdog)
                inputs_before = {row[0] for row in pactl_rows("sink-inputs")}
                play_start = time.monotonic()
                player = subprocess.Popen(
                    ["pw-play", "--target", SINK, str(tone)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                check = RoutingCheck(player, probe_sink, inputs_before)
                check.start()
                more_blocks, more_arrivals = record_blocks(
                    recorder, SIM_BLOCKS - SILENT_BLOCKS, watchdog
                )
                watchdog.last = None
                print(f"sim: stream latency at the end {recorder.latency * 1000:.1f} ms")
            blocks += more_blocks
            arrivals += more_arrivals
            check.join()
            print(f"sim: routing check: {check.result}")
            if not check.ok:
                problems.append(f"routing: {check.result}")
            _, player_errors = player.communicate()
            print(f"sim: pw-play exit code {player.returncode}; stderr: {player_errors.strip()!r}")
            if player.returncode != 0 and check.ok:
                problems.append(f"pw-play exit code {player.returncode}")
        finally:
            if player is not None and player.poll() is None:
                player.kill()
            run("pactl", "unload-module", module)
            print(f"unloaded module {module}")

    problems += describe("sim", blocks, arrivals, opened)
    problems += tone_report(blocks, arrivals, play_start)

    mic = soundcard.default_microphone()
    print(f"mic: recording from the default microphone {mic.id!r}")
    opened = time.monotonic()
    with mic.recorder(samplerate=RATE, channels=1, blocksize=BLOCK) as recorder:
        print(f"mic: stream latency at open {recorder.latency * 1000:.1f} ms")
        watchdog.last = opened
        blocks, arrivals = record_blocks(recorder, MIC_BLOCKS, watchdog)
        watchdog.last = None
        print(f"mic: stream latency at the end {recorder.latency * 1000:.1f} ms")
    problems += describe("mic", blocks, arrivals, opened)
    x = np.concatenate([block.reshape(-1) for block in blocks]).astype(np.float64)
    print(f"mic: RMS {np.sqrt(np.mean(x**2)):.4f}")

    after = defaults()
    print(f"defaults after: sink={after[0]!r} source={after[1]!r}")
    if after != before:
        problems.append("the defaults after the probe are not the defaults before it")

    for problem in problems:
        print(f"PROBLEM: {problem}")
    print("probe B: OK" if not problems else f"probe B: {len(problems)} problem(s)")
    return 1 if problems else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("probe", choices=["a", "b"])
    args = parser.parse_args()
    return probe_a() if args.probe == "a" else probe_b()


if __name__ == "__main__":
    sys.exit(main())
