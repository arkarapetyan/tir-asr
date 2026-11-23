"""T-INSTALL-01 and T-INSTALL-04: the install check (C2; T-INSTALL-01 changed in C10).

T-INSTALL-01 (D-016, D-081 point 1) checks the new environment on the RTX 5070. T-INSTALL-02
and T-INSTALL-03 (NeMo RNNT and NLLB) left with P1 (D-081 point 5). These tests measure. They
have no quality limit (TESTS.md section 2.3): C3 sets the quality with the eval set and the
tested metric code. They run on Aren's laptop only.

Each `laptop` package is imported inside a test function, so that CI can collect
this file without the `laptop` dependency group (D-021).

Input files (local only, data/ is in .gitignore):
  data/eval/c2-check{1,2}.16k.wav   16 kHz mono PCM, converted from Aren's recordings
  data/eval/c2-check{1,2}.hy.txt    Armenian reference text
  data/eval/c2-check{1,2}.en.txt    English reference text
"""

import importlib.metadata
import sys
import time
import wave
from itertools import pairwise
from pathlib import Path

import numpy as np
import pytest

pytestmark = pytest.mark.model

ROOT = Path(__file__).resolve().parents[2]
EVAL_DIR = ROOT / "data" / "eval"
CLIPS = ["c2-check1", "c2-check2"]
SAMPLE_RATE = 16_000

# T-INSTALL-01: the packages of the new environment (D-081 point 1), for the report.
VERSIONS = (
    "torch",
    "fairseq2",
    "omnilingual-asr",
    "nemo-toolkit",
    "silero-vad",
    "soundcard",
    "googletrans",
    "numpy",
)
TORCH_VERSION = "2.8.0"  # D-081: fairseq2n 0.5.2 needs torch==2.8.0
CAPABILITY = (12, 0)  # the RTX 5070 (Blackwell, sm_120)

VAD_FRAME = 512  # samples at 16 kHz; the only frame size the model accepts
VAD_THRESHOLD = 0.5  # D-026
VAD_END_THRESHOLD = 0.35  # D-026
VAD_MIN_SPEECH_MS = 250  # D-026
VAD_SPEECH_PAD_MS = 30  # D-026
VAD_MAX_SPEECH_S = 10  # D-026
VAD_MIN_SILENCE_CANDIDATES_MS = (300, 500, 800)  # D-027: 500 ms is the approved start value


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


def read_text(name: str, lang: str) -> str:
    return (EVAL_DIR / f"{name}.{lang}.txt").read_text(encoding="utf-8").strip()


def seconds(samples: int) -> float:
    return samples / SAMPLE_RATE


def test_install_01_new_environment_on_the_gpu():
    import torch

    for name in VERSIONS:
        report(f"install version {name} {importlib.metadata.version(name)}")
    report(f"install python {sys.version.split()[0]}; torch CUDA {torch.version.cuda}")
    assert sys.version_info[:2] == (3, 11), sys.version
    assert importlib.metadata.version("torch").split("+")[0] == TORCH_VERSION

    assert torch.cuda.is_available(), "install: CUDA is not available"
    capability = torch.cuda.get_device_capability(0)
    report(
        f"install GPU {torch.cuda.get_device_name(0)}; capability {capability}; "
        f"arch list {torch.cuda.get_arch_list()}"
    )
    assert capability == CAPABILITY

    ones = torch.ones((256, 256), dtype=torch.bfloat16, device="cuda")
    product = ones @ ones
    torch.cuda.synchronize()
    report(f"install bfloat16 product on {product.device}, value {float(product[0, 0])}")
    assert product.device.type == "cuda"
    assert product.dtype == torch.bfloat16
    assert float(product[0, 0]) == 256.0


def test_install_04_silero_vad_cpu_pauses_and_segments():
    import torch

    threads_before = torch.get_num_threads()
    from silero_vad import get_speech_timestamps, load_silero_vad

    model = load_silero_vad()
    report(f"vad torch threads before import {threads_before}, after {torch.get_num_threads()}")

    for name in CLIPS:
        audio = torch.from_numpy(read_clip(name))
        n_frames = len(audio) // VAD_FRAME
        start = time.perf_counter()
        regions = get_speech_timestamps(
            audio,
            model,
            threshold=VAD_THRESHOLD,
            neg_threshold=VAD_END_THRESHOLD,
            sampling_rate=SAMPLE_RATE,
            min_speech_duration_ms=0,
            min_silence_duration_ms=0,
            speech_pad_ms=0,
        )
        elapsed = time.perf_counter() - start
        report(
            f"vad {name}: {seconds(len(audio)):.2f} s, {n_frames} frames, "
            f"{1000 * elapsed / n_frames:.3f} ms per frame on the CPU"
        )
        for region in regions:
            report(
                f"vad {name}: speech {seconds(region['start']):.3f}-{seconds(region['end']):.3f} s"
            )
        for before, after in pairwise(regions):
            pause_ms = 1000 * seconds(after["start"] - before["end"])
            report(f"vad {name}: pause at {seconds(before['end']):.3f} s, length {pause_ms:.0f} ms")
        assert regions, f"vad {name}: no speech found"

        for min_silence_ms in VAD_MIN_SILENCE_CANDIDATES_MS:
            segments = get_speech_timestamps(
                audio,
                model,
                threshold=VAD_THRESHOLD,
                neg_threshold=VAD_END_THRESHOLD,
                sampling_rate=SAMPLE_RATE,
                min_speech_duration_ms=VAD_MIN_SPEECH_MS,
                min_silence_duration_ms=min_silence_ms,
                speech_pad_ms=VAD_SPEECH_PAD_MS,
                max_speech_duration_s=VAD_MAX_SPEECH_S,
            )
            spans = ", ".join(
                f"{seconds(s['start']):.2f}-{seconds(s['end']):.2f}" for s in segments
            )
            report(
                f"vad {name}: min silence {min_silence_ms} ms -> {len(segments)} segments: {spans}"
            )
        report(f"vad reference {name}: {read_text(name, 'hy')}")
