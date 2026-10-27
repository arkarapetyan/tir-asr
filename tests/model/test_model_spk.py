"""T-MODEL-SPK-01, T-MODEL-SPK-02: the TitaNet speaker adapter (C5, branch c5-pipeline).

Contract: ARCHITECTURE.md sections 2.8 and 7. Decisions: D-022, D-058, D-059. The adapter has no
warm-up method (D-059 point 5). The test does the warm-up as the pipeline does: one call with
2 s of zeros. Then it embeds clip 1, clip 2, and clip 1 again.

The tests run on Aren's laptop only. They import the adapter inside the test functions, so that
CI can collect this file without the `laptop` dependency group (D-021).

Input files (local only, data/ is in .gitignore):
  data/eval/c2-check{1,2}.16k.wav   16 kHz mono PCM (Aren's voice)
"""

import time
import wave
from pathlib import Path

import numpy as np
import pytest

from tir_asr.config import SAMPLE_RATE, WARMUP_AUDIO_S

pytestmark = pytest.mark.model

ROOT = Path(__file__).resolve().parents[2]
EVAL_DIR = ROOT / "data" / "eval"
WRONG_FILE = "no-such-model.nemo"
SAME_AUDIO_LIMIT = 0.999  # T-MODEL-SPK-01: the cosine of two embeddings of the same audio


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


def cosine(x: np.ndarray, y: np.ndarray) -> float:
    return float(x @ y / (np.linalg.norm(x) * np.linalg.norm(y)))


def test_model_spk_01_titanet_embedding():
    import torch

    from tir_asr.speakers.titanet import TitanetEmbedder

    clip1, clip2 = read_clip("c2-check1"), read_clip("c2-check2")
    start = time.perf_counter()
    embedder = TitanetEmbedder()
    report(f"speaker load time {time.perf_counter() - start:.2f} s")

    start = time.perf_counter()
    embedder.embed(np.zeros(int(WARMUP_AUDIO_S * SAMPLE_RATE), dtype=np.float32))
    report(f"speaker warm-up {time.perf_counter() - start:.3f} s")

    embeddings = []
    for label, audio in [("clip 1", clip1), ("clip 2", clip2), ("clip 1 again", clip1)]:
        start = time.perf_counter()
        embedding = embedder.embed(audio)
        elapsed = time.perf_counter() - start
        embeddings.append(embedding)
        norm = np.linalg.norm(embedding)
        report(
            f"speaker {label}: audio {len(audio) / SAMPLE_RATE:.2f} s, time {elapsed:.3f} s, "
            f"shape {embedding.shape}, dtype {embedding.dtype}, norm {norm:.3f}"
        )
    same_audio = cosine(embeddings[0], embeddings[2])
    same_voice = cosine(embeddings[0], embeddings[1])
    report(f"speaker cosine: same audio {same_audio:.6f}, two clips of Aren {same_voice:.3f}")
    report(f"speaker peak torch VRAM {torch.cuda.max_memory_allocated() / 2**20:.0f} MiB")

    for embedding in embeddings:
        assert embedding.ndim == 1
        assert embedding.dtype == np.float32
        assert np.all(np.isfinite(embedding))
        assert np.linalg.norm(embedding) > 0
    assert same_audio >= SAME_AUDIO_LIMIT, f"the same audio gives cosine {same_audio:.6f}"


def test_model_spk_02_missing_model_file():
    from tir_asr.speakers.cluster import SpeakerError
    from tir_asr.speakers.titanet import TitanetEmbedder

    with pytest.raises(SpeakerError) as raised:
        TitanetEmbedder(filename=WRONG_FILE)

    message = str(raised.value)
    report(f"speaker error message: {message}")
    assert message.startswith("speakers: model file not in the Hugging Face cache: ")
    assert WRONG_FILE in message


def test_model_spk_02_cuda_not_available(monkeypatch):
    import torch

    from tir_asr.speakers.cluster import SpeakerError
    from tir_asr.speakers.titanet import TitanetEmbedder

    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    with pytest.raises(SpeakerError) as raised:
        TitanetEmbedder()

    assert str(raised.value) == "speakers: CUDA is not available"
