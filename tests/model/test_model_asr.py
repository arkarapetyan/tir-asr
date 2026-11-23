"""T-MODEL-ASR-01, T-MODEL-ERR-01, T-MODEL-ERR-03, T-MODEL-ERR-05: the OhanASR adapter (C10).

Contract: ARCHITECTURE.md sections 2.3 and 7. Decisions: D-022, D-037, D-080, D-081 point 2. The
adapter has no warm-up method (D-037, part 3). The test does the warm-up as the caller does: one
call with 2 s of zeros. Then it transcribes clip 1, clip 2, clip 1, and clip 2. Until C9, these
IDs tested the NeMo RNNT adapter (D-081 point 5).

The model loads one time for the file (fixture `asr`), because the load reads a 9.1 GB file.
T-MODEL-ERR-01 and T-MODEL-ERR-03 fail before the load, so they make their own instance.

The tests run on Aren's laptop only. They import the adapter inside the test functions, so that
CI can collect this file without the `laptop` dependency group (D-021).

Input files (local only, data/ and models/ are in .gitignore):
  data/eval/c2-check{1,2}.16k.wav   16 kHz mono PCM
  data/eval/c2-check{1,2}.hy.txt    Armenian reference text
  models/ohanasr-v0.1/              the OhanASR model (gated download)
"""

import re
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
FIRST_CALL_LIMIT = 3.0  # T-MODEL-ASR-01: the first real call, as a multiple of the median
ARMENIAN = re.compile("[Ա-և]")  # the Armenian letters (TESTS.md section 2.11)
LIMIT_SAMPLES = 640_000  # T-MODEL-ERR-05: the 40 s model limit at 16 kHz (section 2.3)


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


@pytest.fixture(scope="module")
def asr():
    from tir_asr.asr.ohanasr import OhanasrTranscriber

    start = time.perf_counter()
    transcriber = OhanasrTranscriber()
    report(f"asr load time {time.perf_counter() - start:.2f} s")
    return transcriber


def test_model_asr_01_ohanasr_adapter_with_synthetic_warmup(asr):
    import torch

    clip1, clip2 = (read_clip(name) for name in CLIPS)
    calls = [
        ("clip 1", clip1),
        ("clip 2", clip2),
        ("clip 1 again", clip1),
        ("clip 2 again", clip2),
    ]

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
    assert all(ARMENIAN.search(text) for text in texts), (
        f"asr: a text has no Armenian letter: {texts}"
    )
    assert texts[0] == texts[2], "asr: clip 1 gave two different texts"
    assert times[0] <= FIRST_CALL_LIMIT * median_next, (
        f"asr: the first real call took {times[0]:.3f} s, more than {FIRST_CALL_LIMIT:.0f} times "
        f"the median {median_next:.3f} s of the next 3 calls"
    )


def test_model_err_05_segment_over_the_model_limit(asr):
    from tir_asr.asr.ohanasr import AsrError

    audio = np.zeros(LIMIT_SAMPLES + 1, dtype=np.float32)
    with pytest.raises(AsrError) as raised:
        asr.transcribe(audio)

    message = str(raised.value)
    report(f"asr error message: {message}")
    assert message == (
        f"asr: segment of {LIMIT_SAMPLES + 1} samples is over the model limit of "
        f"{LIMIT_SAMPLES} samples (40 s)"
    )


def test_model_err_01_missing_ohanasr_model(tmp_path):
    from tir_asr.asr.ohanasr import AsrError, OhanasrTranscriber

    missing = tmp_path / "no-such-model"
    with pytest.raises(AsrError) as raised:
        OhanasrTranscriber(model_dir=missing)

    message = str(raised.value)
    report(f"asr error message: {message}")
    assert message == f"asr: OhanASR model not found: {missing / 'model.pt'}"


def test_model_err_03_cuda_not_available(monkeypatch):
    import torch

    from tir_asr.asr.ohanasr import AsrError, OhanasrTranscriber

    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    start = time.perf_counter()
    with pytest.raises(AsrError) as raised:
        OhanasrTranscriber()
    elapsed = time.perf_counter() - start

    message = str(raised.value)
    report(f"asr error message: {message}, after {elapsed:.3f} s")
    assert message == "asr: CUDA is not available"
