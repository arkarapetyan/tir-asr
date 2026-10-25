"""T-MODEL-ASR-01, T-MODEL-ERR-01, T-MODEL-ERR-03: the NeMo RNNT adapter (C2c, branch c2c-asr).

Contract: ARCHITECTURE.md sections 2.3 and 7. Decisions: D-014, D-022, D-037. The adapter has no
warm-up method (D-037, part 3). The test does the warm-up as the caller does: one call with 2 s
of zeros. Then it transcribes clip 1, clip 2, clip 1, and clip 2.

The error `asr: unexpected output type` has no test: it needs a fake model (Aren, 2026-10-25).

The tests run on Aren's laptop only. They import the adapter inside the test functions, so that
CI can collect this file without the `laptop` dependency group (D-021).

Input files (local only, data/ is in .gitignore):
  data/eval/c2-check{1,2}.16k.wav   16 kHz mono PCM
  data/eval/c2-check{1,2}.hy.txt    Armenian reference text
"""

import statistics
import time
import wave
from pathlib import Path

import numpy as np
import pytest

from tir_asr.config import SAMPLE_RATE, WARMUP_AUDIO_S

pytestmark = pytest.mark.model

ROOT = Path(__file__).resolve().parents[2]
EVAL_DIR = ROOT / "data" / "eval"
CLIPS = ["c2-check1", "c2-check2"]
WRONG_FILE = "no-such-model.nemo"
FIRST_CALL_LIMIT = 3.0  # T-MODEL-ASR-01: the first real call, as a multiple of the median


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


def test_model_asr_01_nemo_adapter_with_synthetic_warmup():
    import torch

    from tir_asr.asr.nemo_rnnt import NemoRnntTranscriber

    clip1, clip2 = (read_clip(name) for name in CLIPS)
    calls = [
        ("clip 1", clip1),
        ("clip 2", clip2),
        ("clip 1 again", clip1),
        ("clip 2 again", clip2),
    ]

    start = time.perf_counter()
    asr = NemoRnntTranscriber()
    report(f"asr load time {time.perf_counter() - start:.2f} s")

    warmup_audio = np.zeros(int(WARMUP_AUDIO_S * SAMPLE_RATE), dtype=np.float32)
    start = time.perf_counter()
    warmup_text = asr.transcribe(warmup_audio)
    elapsed = time.perf_counter() - start
    report(
        f"asr warm-up: audio {WARMUP_AUDIO_S:.2f} s, time {elapsed:.3f} s, text: {warmup_text!r}"
    )

    texts = []
    times = []
    for label, audio in calls:
        start = time.perf_counter()
        text = asr.transcribe(audio)
        elapsed = time.perf_counter() - start
        texts.append(text)
        times.append(elapsed)
        report(f"asr {label}: audio {len(audio) / SAMPLE_RATE:.2f} s, time {elapsed:.3f} s")
        report(f"asr {label}: text: {text}")

    median_next = statistics.median(times[1:])
    report(
        f"asr first real call {times[0]:.3f} s, median of the next 3 calls {median_next:.3f} s, "
        f"ratio {times[0] / median_next:.2f}"
    )
    report(f"asr peak torch VRAM {torch.cuda.max_memory_allocated() / 2**20:.0f} MiB")
    for name in CLIPS:
        reference = (EVAL_DIR / f"{name}.hy.txt").read_text(encoding="utf-8").strip()
        report(f"asr reference {name}: {reference}")

    assert torch.cuda.memory_allocated() > 0, "asr: the model is not on the GPU"
    assert all(text.strip() for text in texts), "asr: an empty text"
    assert times[0] <= FIRST_CALL_LIMIT * median_next, (
        f"asr: the first real call took {times[0]:.3f} s, more than {FIRST_CALL_LIMIT:.0f} times "
        f"the median {median_next:.3f} s of the next 3 calls"
    )


def test_model_err_01_missing_asr_model_file():
    from tir_asr.asr.nemo_rnnt import AsrError, NemoRnntTranscriber

    with pytest.raises(AsrError) as raised:
        NemoRnntTranscriber(filename=WRONG_FILE)

    message = str(raised.value)
    report(f"asr error message: {message}")
    assert message.startswith("asr: model file not in the Hugging Face cache: ")
    assert WRONG_FILE in message


def test_model_err_03_cuda_not_available(monkeypatch):
    import torch

    from tir_asr.asr.nemo_rnnt import AsrError, NemoRnntTranscriber

    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    start = time.perf_counter()
    with pytest.raises(AsrError) as raised:
        NemoRnntTranscriber()
    elapsed = time.perf_counter() - start

    message = str(raised.value)
    report(f"asr error message: {message}, after {elapsed:.3f} s")
    assert message == "asr: CUDA is not available"
