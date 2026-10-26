"""The test WAV source (ARCHITECTURE.md section 3, D-025, D-032). Test code only.

The program has no WAV source and no flag for one (D-025). This source plays 16 kHz, mono,
16-bit WAV files at real-time speed. Each block gets its true `time.monotonic()` arrival, as
the microphone adapter does. The source gives only whole frames: it drops the last part of a
clip that is shorter than one frame. It adds no silence (D-032).
"""

import time
import wave
from pathlib import Path

import numpy as np

from tir_asr.config import SAMPLE_RATE, VAD_FRAME
from tir_asr.types import AudioBlock

FRAME_S = VAD_FRAME / SAMPLE_RATE  # 0.032 s


def read_frames(path: Path) -> list[np.ndarray]:
    """The whole frames of one clip, as float32 in [-1, 1]."""
    with wave.open(str(path), "rb") as wav:
        assert wav.getframerate() == SAMPLE_RATE, f"{path}: {wav.getframerate()} Hz, not 16000"
        assert wav.getnchannels() == 1, f"{path}: {wav.getnchannels()} channels, not 1"
        assert wav.getsampwidth() == 2, f"{path}: {wav.getsampwidth()} bytes per sample, not 2"
        data = wav.readframes(wav.getnframes())
    samples = np.frombuffer(data, dtype="<i2").astype(np.float32) / 32768.0
    whole = len(samples) // VAD_FRAME * VAD_FRAME
    return list(samples[:whole].reshape(-1, VAD_FRAME))


class WavSource:
    """An AudioSource that plays the clips one after the other, at real-time speed."""

    def __init__(self, paths: list[Path], source: str = "Me") -> None:
        self.frames = [frame for path in paths for frame in read_frames(path)]
        self.source = source

    def blocks(self):
        start = time.monotonic()
        for k, frame in enumerate(self.frames):
            due = start + (k + 1) * FRAME_S  # the time at which frame k is complete
            time.sleep(max(0.0, due - time.monotonic()))
            yield AudioBlock(source=self.source, samples=frame, arrival=time.monotonic())
