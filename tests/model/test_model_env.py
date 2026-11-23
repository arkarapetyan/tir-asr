"""T-MODEL-ENV-01: fairseq2 and NeMo in one process (C10, D-081 weak point 3).

D-081 puts OhanASR (fairseq2) and TitaNet (NeMo) in one process. One library can change a global
torch setting that the other then uses [UNVERIFIED]. The test gets the TitaNet embedding and the
Silero probabilities of clip 1 before the OhanASR load and after it. Both must stay the same: the
cosine limit is the limit of T-MODEL-SPK-01, and the Silero limit is 1e-6 (TESTS.md 2.11).

The test runs on Aren's laptop only. It imports the adapters inside the test function, so that
CI can collect this file without the `laptop` dependency group (D-021).

Input files (local only, data/ and models/ are in .gitignore):
  data/eval/c2-check1.16k.wav   16 kHz mono PCM
  models/ohanasr-v0.1/          the OhanASR model
"""

import subprocess
import wave
from pathlib import Path

import numpy as np
import pytest

from tir_asr.config import SAMPLE_RATE, VAD_FRAME, WARMUP_AUDIO_S

pytestmark = pytest.mark.model

ROOT = Path(__file__).resolve().parents[2]
CLIP = ROOT / "data" / "eval" / "c2-check1.16k.wav"
SAME_AUDIO_LIMIT = 0.999  # the cosine limit of T-MODEL-SPK-01
SAME_VAD_LIMIT = 1e-6  # the largest difference of two Silero probabilities (TESTS.md 2.11)


def report(line: str) -> None:
    print(f"RESULT {line}", flush=True)


def read_clip(path: Path) -> np.ndarray:
    with wave.open(str(path), "rb") as wav:
        assert wav.getframerate() == SAMPLE_RATE, f"{path}: {wav.getframerate()} Hz, not 16000"
        assert wav.getnchannels() == 1, f"{path}: {wav.getnchannels()} channels, not 1"
        assert wav.getsampwidth() == 2, f"{path}: {wav.getsampwidth()} bytes per sample, not 2"
        frames = wav.readframes(wav.getnframes())
    return np.frombuffer(frames, dtype="<i2").astype(np.float32) / 32768.0


def gpu_memory_used_mib() -> int:
    out = subprocess.run(
        ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return int(out.strip().splitlines()[0])


def cosine(x: np.ndarray, y: np.ndarray) -> float:
    return float(x @ y / (np.linalg.norm(x) * np.linalg.norm(y)))


def probabilities(audio: np.ndarray) -> np.ndarray:
    """The Silero probability of each whole frame, with a new instance (new model state)."""
    from tir_asr.segment.silero import SileroSpeechProbability

    vad = SileroSpeechProbability()
    frames = len(audio) // VAD_FRAME
    return np.array([vad(audio[k * VAD_FRAME : (k + 1) * VAD_FRAME]) for k in range(frames)])


def test_model_env_01_titanet_and_silero_do_not_change_after_the_ohanasr_load():
    from tir_asr.speakers.titanet import TitanetEmbedder

    clip = read_clip(CLIP)
    report(f"env GPU memory before the loads {gpu_memory_used_mib()} MiB")

    embedder = TitanetEmbedder()
    report(f"env GPU memory after TitaNet {gpu_memory_used_mib()} MiB")
    embedder.embed(np.zeros(int(WARMUP_AUDIO_S * SAMPLE_RATE), dtype=np.float32))
    e1 = embedder.embed(clip)
    p1 = probabilities(clip)

    from tir_asr.asr.ohanasr import OhanasrTranscriber

    asr = OhanasrTranscriber()
    report(f"env GPU memory after OhanASR {gpu_memory_used_mib()} MiB")
    text = asr.transcribe(clip)
    report(f"env OhanASR text of clip 1: {text}")

    e2 = embedder.embed(clip)
    p2 = probabilities(clip)
    report(f"env GPU memory after the calls {gpu_memory_used_mib()} MiB")

    similarity = cosine(e1, e2)
    difference = float(np.max(np.abs(p1 - p2)))
    report(f"env TitaNet cosine before and after the OhanASR load {similarity:.6f}")
    report(f"env Silero largest difference {difference:.2e} ({len(p1)} frames)")
    assert similarity >= SAME_AUDIO_LIMIT, f"env: cosine {similarity:.6f}"
    assert difference <= SAME_VAD_LIMIT, f"env: Silero difference {difference:.2e}"
