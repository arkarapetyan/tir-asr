"""T-MODEL-P4-01, T-MODEL-P4-02, T-PERF-P4-01: the P4 text step on the GPU (C6, c6-seamless).

Contract: ARCHITECTURE.md sections 2.9 and 7. Decisions: D-053, D-062, D-063. The adapter has no
warm-up method of its own: `TextStep.warm_up` (the template) gets 2 s of zeros, as the pipeline
does. T-PERF-P4-01 is the performance test of P4 alone (D-056 part 2.4): the program's VAD cuts
S1-S3 with `Params()` (the 34 segments of C3 and of the probe), and `process` gives the texts of
each segment; the limits come from D-063 part 5.

The tests run on Aren's laptop only. Run them with `env -u LD_LIBRARY_PATH HF_HUB_OFFLINE=1`
(D-030). They import the adapter inside the test functions, so that CI can collect this file
without the `laptop` dependency group (D-021).

Input files (local only, data/ is in .gitignore):
  data/eval/c2-check{1,2}.16k.wav   16 kHz mono PCM (Aren's voice)
  data/eval/raw/s{1,2,3}.{mic,call}.wav and s{1,2,3}.labels.txt (D-046)
"""

import re
import time
import wave
from pathlib import Path

import numpy as np
import pytest

from tir_asr.config import SAMPLE_RATE, WARMUP_AUDIO_S, Params

pytestmark = pytest.mark.model

ROOT = Path(__file__).resolve().parents[2]
EVAL_DIR = ROOT / "data" / "eval"
RAW = EVAL_DIR / "raw"
SCRIPTS_MD = ROOT / "docs" / "eval" / "scripts.md"
ARMENIAN = re.compile("[Ա-և]")
LATIN = re.compile("[A-Za-z]")
MIB = 2**20
# T-PERF-P4-01 limits (D-063 part 5): the V2 values of the probe with a margin.
WER_MAX = 0.076
CHRF_MIN = 58.5
LINE_MEAN_MAX_S = 0.40
LINE_MAX_S = 0.55


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


def zeros() -> np.ndarray:
    return np.zeros(int(WARMUP_AUDIO_S * SAMPLE_RATE), dtype=np.float32)


@pytest.fixture(scope="module")
def p4():
    """One load of the adapter for T-MODEL-P4-01 and T-PERF-P4-01, with its warm-up."""
    import torch

    from tir_asr.text.seamless import SeamlessTextStep

    free_before, _ = torch.cuda.mem_get_info()
    start = time.perf_counter()
    step = SeamlessTextStep()
    load_s = time.perf_counter() - start
    free_after, _ = torch.cuda.mem_get_info()
    report(f"P4 load {load_s:.2f} s; VRAM +{(free_before - free_after) // MIB} MiB")
    report(f"generate values: num_beams {step.num_beams}, max_new_tokens {step.max_new_tokens}")
    start = time.perf_counter()
    warm = step.warm_up(zeros(), time.perf_counter)
    report(f"warm-up {warm.mt_end - start:.3f} s; HY {warm.hy!r}; EN {warm.en!r}")
    return step


def test_model_p4_01_seamless_text_step(p4):
    import torch

    from tir_asr.text.seamless import SeamlessTextStep

    clip1, clip2 = read_clip("c2-check1"), read_clip("c2-check2")
    torch.cuda.reset_peak_memory_stats()
    results = []
    for name, audio in (("clip 1", clip1), ("clip 2", clip2), ("clip 1", clip1)):
        start = time.perf_counter()
        result = p4.process(audio, time.perf_counter)
        results.append(result)
        report(f"{name}: {result.mt_end - start:.3f} s | {result.hy} | {result.en}")
    report(f"peak torch memory {torch.cuda.max_memory_allocated() // MIB} MiB")

    for result in results:
        assert result.hy and ARMENIAN.search(result.hy), f"no Armenian text: {result.hy!r}"
        assert result.en and LATIN.search(result.en), f"no English text: {result.en!r}"
    assert (results[2].hy, results[2].en) == (results[0].hy, results[0].en)
    assert SeamlessTextStep.STEPS == ("s2t",)
    # The template stays in TextStep (D-062 part 2).
    assert "process" not in vars(SeamlessTextStep)
    assert "warm_up" not in vars(SeamlessTextStep)


def test_model_p4_02_errors(monkeypatch):
    import torch

    from tir_asr.text.seamless import SeamlessTextStep
    from tir_asr.text.step import TextError

    missing = "facebook/no-such-model"
    with pytest.raises(TextError) as raised:
        SeamlessTextStep(repo=missing)
    message = str(raised.value)
    report(message)
    assert message.startswith("text: model not in the Hugging Face cache: "), message
    assert missing in message

    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    with pytest.raises(TextError) as raised:
        SeamlessTextStep()
    report(str(raised.value))
    assert str(raised.value) == "text: CUDA is not available"


def test_perf_p4_01_s1_to_s3(p4):
    import torch

    from tir_asr.eval.data import load_wav_16k, read_references
    from tir_asr.eval.metrics import cer, chrf, wer
    from tir_asr.eval.run import segment_file

    # The VAD loads after the model, as in the program (D-043).
    from tir_asr.segment.silero import SileroSpeechProbability

    params = Params()
    refs_hy, refs_en, hyps_hy, hyps_en, lines_s = [], [], [], [], []
    empty = 0
    for script in ("s1", "s2", "s3"):
        references = read_references(SCRIPTS_MD, script)
        for side in ("mic", "call"):
            lines = [line for line in references if line.side == side]
            audio = load_wav_16k(RAW / f"{script}.{side}.wav")
            hy, en = [], []
            for segment in segment_file(audio, SileroSpeechProbability(), params):
                start = time.perf_counter()
                result = p4.process(segment.audio, time.perf_counter)
                lines_s.append(result.mt_end - start)
                hy.append(result.hy)
                en.append(result.en)
                empty += not result.hy
            refs_hy.append(" ".join(line.hy for line in lines))
            refs_en.append(" ".join(line.en for line in lines))
            hyps_hy.append(" ".join(hy))
            hyps_en.append(" ".join(en))

    scores = {
        "wer": wer(refs_hy, hyps_hy),
        "cer": cer(refs_hy, hyps_hy),
        "chrf": chrf(refs_en, hyps_en),
        "line_mean_s": float(np.mean(lines_s)),
        "line_max_s": float(np.max(lines_s)),
    }
    report(
        f"{len(lines_s)} segments, {empty} with no Armenian text: WER {scores['wer']:.3f}, "
        f"CER {scores['cer']:.3f}, chrF {scores['chrf']:.1f}, line mean "
        f"{scores['line_mean_s']:.3f} s, line max {scores['line_max_s']:.3f} s"
    )
    report(f"peak torch memory {torch.cuda.max_memory_allocated() // MIB} MiB")
    assert len(lines_s) == 34, f"{len(lines_s)} segments, expected the 34 segments of C3"
    assert scores["wer"] <= WER_MAX, scores
    assert scores["chrf"] >= CHRF_MIN, scores
    assert scores["line_mean_s"] <= LINE_MEAN_MAX_S, scores
    assert scores["line_max_s"] <= LINE_MAX_S, scores
