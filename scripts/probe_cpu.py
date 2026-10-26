"""Probe (C3, D-053, Q16): P4 (Seamless end to end) and P1 (NeMo RNNT + NLLB) on the CPU.

It times each model call on 3 real segments of the S3 mic file, cut with the labels. All models
load on the CPU; the GPU is not used. Seamless runs in float32, CTranslate2 in int8, and torch
uses its default thread count (no Silero VAD import, which sets 1 thread).

Run on the laptop (D-030):
  env -u LD_LIBRARY_PATH HF_HUB_OFFLINE=1 uv run python scripts/probe_cpu.py [p4|p1|all]
"""

import os
import sys
import time
from pathlib import Path

import numpy as np
import torch

from tir_asr.config import MT_SRC_LANG, MT_TGT_LANG, SAMPLE_RATE
from tir_asr.eval.data import load_wav_16k, read_labels, read_references
from tir_asr.mt import ct2_nllb  # loads the CUDA 12 cuBLAS, then ctranslate2 (D-030)

ROOT = Path(__file__).resolve().parents[1]
IDS = ("s3-01", "s3-05", "s3-07")  # mic side, about 5.4 s, 7.8 s, and 5.4 s of speech
SEAMLESS = "facebook/seamless-m4t-v2-large"


def say(text: str) -> None:
    print(text, flush=True)


def segments() -> list[tuple[str, np.ndarray]]:
    lines = read_references(ROOT / "docs" / "eval" / "scripts.md", "s3")
    labels = {label.id: label for label in read_labels(ROOT / "data/eval/raw/s3.labels.txt", lines)}
    audio = load_wav_16k(ROOT / "data/eval/raw/s3.mic.wav")
    return [
        (i, audio[int(labels[i].start * SAMPLE_RATE) : int(labels[i].end * SAMPLE_RATE)])
        for i in IDS
    ]


def timed(fn, *args):
    start = time.perf_counter()
    result = fn(*args)
    return result, time.perf_counter() - start


def probe_p4(segs) -> None:
    from transformers import AutoProcessor, SeamlessM4Tv2ForSpeechToText

    start = time.perf_counter()
    processor = AutoProcessor.from_pretrained(SEAMLESS, local_files_only=True)
    model = SeamlessM4Tv2ForSpeechToText.from_pretrained(
        SEAMLESS, dtype=torch.float32, local_files_only=True
    ).eval()
    say(f"P4 load {time.perf_counter() - start:.1f} s (cpu, float32)")

    def run(audio: np.ndarray, lang: str) -> str:
        inputs = processor(audio=audio, sampling_rate=SAMPLE_RATE, return_tensors="pt")
        with torch.inference_mode():
            tokens = model.generate(**inputs, tgt_lang=lang)
        return processor.decode(tokens[0].tolist(), skip_special_tokens=True)

    _, warm = timed(run, np.zeros(2 * SAMPLE_RATE, dtype=np.float32), "hye")
    say(f"P4 warm-up {warm:.2f} s")
    for line_id, audio in segs:
        hy, t_asr = timed(run, audio, "hye")
        en, t_s2tt = timed(run, audio, "eng")
        say(
            f"P4 {line_id} audio {len(audio) / SAMPLE_RATE:.1f} s: ASR {t_asr:.2f} s + S2TT"
            f" {t_s2tt:.2f} s = {t_asr + t_s2tt:.2f} s | {hy} | {en}"
        )


def probe_p1(segs) -> None:
    import ctranslate2
    import nemo.collections.asr as nemo_asr
    from huggingface_hub import hf_hub_download
    from transformers import AutoTokenizer

    from tir_asr.asr.nemo_rnnt import ASR_FILE, ASR_REPO

    start = time.perf_counter()
    path = hf_hub_download(ASR_REPO, ASR_FILE, local_files_only=True)
    asr = nemo_asr.models.ASRModel.restore_from(path, map_location=torch.device("cpu")).eval()
    asr.change_decoding_strategy(decoder_type="rnnt")
    tokenizer = AutoTokenizer.from_pretrained(
        ct2_nllb.MT_REPO, src_lang=MT_SRC_LANG, local_files_only=True
    )
    mt = ctranslate2.Translator(
        str(ROOT / ct2_nllb.MT_MODEL_DIR), device="cpu", compute_type="int8"
    )
    say(f"P1 load {time.perf_counter() - start:.1f} s (cpu; MT int8)")

    def transcribe(audio: np.ndarray) -> str:
        output = asr.transcribe([audio], batch_size=1, verbose=False)
        if isinstance(output, tuple):
            output = output[0]
        return getattr(output[0], "text", output[0])

    def translate(text: str) -> str:
        source = tokenizer.convert_ids_to_tokens(tokenizer.encode(text))
        result = mt.translate_batch([source], target_prefix=[[MT_TGT_LANG]], beam_size=2)
        return tokenizer.decode(tokenizer.convert_tokens_to_ids(result[0].hypotheses[0][1:]))

    transcribe(np.zeros(2 * SAMPLE_RATE, dtype=np.float32))
    translate("Բարև")
    for line_id, audio in segs:
        hy, t_asr = timed(transcribe, audio)
        en, t_mt = timed(translate, hy)
        say(
            f"P1 {line_id} audio {len(audio) / SAMPLE_RATE:.1f} s: ASR {t_asr:.2f} s + MT"
            f" {t_mt:.2f} s = {t_asr + t_mt:.2f} s | {hy} | {en}"
        )


def main() -> int:
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    say(f"torch {torch.__version__}; CPU threads {torch.get_num_threads()}; cores {os.cpu_count()}")
    segs = segments()
    if which in ("p4", "all"):
        probe_p4(segs)
    if which in ("p1", "all"):
        probe_p1(segs)
    return 0


if __name__ == "__main__":
    sys.exit(main())
