"""T-MODEL-VAD-01: the Silero adapter and the Endpointer on the recorded clips (C2b).

Contract: ARCHITECTURE.md section 2.2. Decisions: D-026, D-027. The test plays clip 1 and then
clip 2 frame by frame, with no added silence (D-032), through one adapter and one Endpointer.
Clip 1 ends 152 ms after its speech. The 500 ms rule closes the segment of clip 1 in the
silence at the start of clip 2 (T-INSTALL-04 shows the pauses).

The test runs on Aren's laptop only. It imports the adapter inside the test function, so that
CI can collect this file without the `laptop` dependency group (D-021).

Input files (local only, data/ is in .gitignore):
  data/eval/c2-check{1,2}.16k.wav   16 kHz mono PCM
  data/eval/c2-check{1,2}.hy.txt    Armenian reference text
"""

import time
import wave
from pathlib import Path

import numpy as np
import pytest

from tir_asr.config import SAMPLE_RATE, VAD_FRAME, Params
from tir_asr.segment.endpoint import Endpointer
from tir_asr.types import AudioBlock

pytestmark = pytest.mark.model

ROOT = Path(__file__).resolve().parents[2]
EVAL_DIR = ROOT / "data" / "eval"
CLIPS = ["c2-check1", "c2-check2"]
FRAME_S = VAD_FRAME / SAMPLE_RATE


def report(line: str) -> None:
    print(f"RESULT {line}", flush=True)


def read_clip(name: str) -> np.ndarray:
    path = EVAL_DIR / f"{name}.16k.wav"
    with wave.open(str(path), "rb") as wav:
        assert wav.getframerate() == SAMPLE_RATE, f"{path}: {wav.getframerate()} Hz, not 16000"
        assert wav.getnchannels() == 1, f"{path}: {wav.getnchannels()} channels, not 1"
        assert wav.getsampwidth() == 2, f"{path}: {wav.getsampwidth()} bytes per sample, not 2"
        frames = wav.readframes(wav.getnframes())
    return np.frombuffer(frames, dtype="<i2").astype(np.float32) / 32768.0


def test_model_vad_01_silero_adapter_and_endpointer():
    import torch

    from tir_asr.segment.silero import SileroSpeechProbability

    vad = SileroSpeechProbability()
    report(f"vad torch threads {torch.get_num_threads()}")

    probabilities = []

    def recorded(samples: np.ndarray) -> float:
        probability = vad(samples)
        probabilities.append(probability)
        return probability

    params = Params()
    endpointer = Endpointer(params, recorded)
    segments = []
    frame = 0  # the frame counter goes on from clip 1 to clip 2
    start = time.perf_counter()
    for name in CLIPS:
        audio = read_clip(name)
        clip_first_frame = frame
        for i in range(len(audio) // VAD_FRAME):
            samples = audio[i * VAD_FRAME : (i + 1) * VAD_FRAME]
            block = AudioBlock(source="Me", samples=samples, arrival=(frame + 1) * FRAME_S)
            segment = endpointer.push(block)
            frame += 1
            if segment is not None:
                segments.append(segment)
                audio_s = len(segment.audio) / SAMPLE_RATE
                report(
                    f"vad segment {len(segments)} closed in {name}: "
                    f"start {segment.start:.3f} s, speech end {segment.speech_end:.3f} s, "
                    f"closed {segment.closed:.3f} s, audio {audio_s:.3f} s, cut {segment.cut}"
                )
        report(
            f"vad {name}: frames {clip_first_frame}-{frame - 1}, ends at {frame * FRAME_S:.3f} s"
        )
    elapsed = time.perf_counter() - start

    report(f"vad {frame} frames, {1000 * elapsed / frame:.3f} ms per frame on the CPU")
    report(f"vad probability min {min(probabilities):.3f}, max {max(probabilities):.3f}")
    report(f"vad short segments {endpointer.short_segments}")
    for name in CLIPS:
        text = (EVAL_DIR / f"{name}.hy.txt").read_text(encoding="utf-8").strip()
        report(f"vad reference {name}: {text}")

    assert all(0.0 <= p <= 1.0 for p in probabilities), "vad: a probability is not in [0, 1]"
    assert len(segments) == 2, f"vad: {len(segments)} segments, expected 2"
