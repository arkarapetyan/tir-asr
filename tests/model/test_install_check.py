"""T-INSTALL-02 to T-INSTALL-04: install check of the first-candidate models (C2).

These tests measure. They have no quality limit (TESTS.md section 2.3): C3 sets the
quality with the eval set and the tested metric code. They run on Aren's laptop only.

Each `laptop` package is imported inside a test function, so that CI can collect
this file without the `laptop` dependency group (D-021).

Input files (local only, data/ is in .gitignore):
  data/eval/c2-check{1,2}.16k.wav   16 kHz mono PCM, converted from Aren's recordings
  data/eval/c2-check{1,2}.hy.txt    Armenian reference text
  data/eval/c2-check{1,2}.en.txt    English reference text
"""

import subprocess
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

ASR_REPO = "nvidia/stt_hy_fastconformer_hybrid_large_pc"
ASR_FILE = "stt_hy_fastconformer_hybrid_large_pc.nemo"

MT_REPO = "facebook/nllb-200-distilled-600M"
MT_CT2_DIR = ROOT / "models" / "nllb-200-distilled-600M-ct2-float16"
MT_COMPUTE_TYPE = "float16"  # D-015, approved by Aren on 2026-10-24
MT_SRC_LANG = "hye_Armn"
MT_TGT_LANG = "eng_Latn"
MT_BEAM_SIZES = (1, 2)  # measurement only; the program value is a C2 parameter proposal

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


def gpu_memory_used_mib() -> int:
    out = subprocess.run(
        ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return int(out.strip().splitlines()[0])


def seconds(samples: int) -> float:
    return samples / SAMPLE_RATE


def test_install_02_asr_nemo_rnnt_on_gpu():
    import nemo.collections.asr as nemo_asr
    import torch
    from huggingface_hub import hf_hub_download

    clip1, clip2 = (read_clip(name) for name in CLIPS)
    calls = [
        ("call 1: clip 1", clip1),
        ("call 2: clip 1 again", clip1),
        ("clip 2 (new length)", clip2),
        ("first half of clip 1 (new length)", clip1[: len(clip1) // 2]),
        ("clip 1 + clip 2 (new length)", np.concatenate([clip1, clip2])),
        ("clip 1 again (old length)", clip1),
    ]

    path = hf_hub_download(ASR_REPO, ASR_FILE, local_files_only=True)
    used_before = gpu_memory_used_mib()
    start = time.perf_counter()
    model = nemo_asr.models.ASRModel.restore_from(path, map_location=torch.device("cuda"))
    model.eval()
    model.change_decoding_strategy(decoder_type="rnnt")
    load_s = time.perf_counter() - start
    report(f"asr model class {type(model).__name__}, device {next(model.parameters()).device}")
    report(f"asr load time {load_s:.2f} s")

    texts = []
    for label, audio in calls:
        torch.cuda.synchronize()
        start = time.perf_counter()
        output = model.transcribe([audio], batch_size=1)
        torch.cuda.synchronize()
        elapsed = time.perf_counter() - start
        if isinstance(output, tuple):  # some NeMo versions return (best, all) for RNNT
            output = output[0]
        text = getattr(output[0], "text", output[0])
        assert isinstance(text, str), f"asr: unexpected output type {type(output[0])}"
        texts.append(text)
        duration = seconds(len(audio))
        rtf = elapsed / duration
        report(f"asr {label}: audio {duration:.2f} s, time {elapsed:.3f} s, RTF {rtf:.3f}")
        report(f"asr {label}: text: {text}")

    report(f"asr peak torch VRAM {torch.cuda.max_memory_allocated() / 2**20:.0f} MiB")
    report(f"asr nvidia-smi used {gpu_memory_used_mib()} MiB (before load {used_before} MiB)")
    for name in CLIPS:
        report(f"asr reference {name}: {read_text(name, 'hy')}")

    assert next(model.parameters()).device.type == "cuda"
    assert all(text.strip() for text in texts), "asr: an empty text"
    del model
    torch.cuda.empty_cache()


def test_install_03_mt_nllb_ctranslate2_and_pytorch():
    import ctranslate2
    import torch
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

    text1, text2 = (read_text(name, "hy") for name in CLIPS)
    calls = [
        ("call 1: text 1", text1),
        ("call 2: text 1 again", text1),
        ("text 2 (new length)", text2),
        ("text 1 + text 2 (new length)", f"{text1} {text2}"),
    ]
    tokenizer = AutoTokenizer.from_pretrained(MT_REPO, src_lang=MT_SRC_LANG, local_files_only=True)
    english = []

    used_before = gpu_memory_used_mib()
    start = time.perf_counter()
    translator = ctranslate2.Translator(
        str(MT_CT2_DIR), device="cuda", compute_type=MT_COMPUTE_TYPE
    )
    report(f"mt ct2 load time {time.perf_counter() - start:.2f} s, compute type {MT_COMPUTE_TYPE}")
    for beam in MT_BEAM_SIZES:
        for label, text in calls:
            source = tokenizer.convert_ids_to_tokens(tokenizer.encode(text))
            start = time.perf_counter()
            result = translator.translate_batch(
                [source], target_prefix=[[MT_TGT_LANG]], beam_size=beam
            )
            elapsed = time.perf_counter() - start
            target = result[0].hypotheses[0][1:]  # remove the target language token
            out = tokenizer.decode(tokenizer.convert_tokens_to_ids(target))
            english.append(out)
            report(f"mt ct2 beam {beam} {label}: {len(source)} tokens, time {elapsed:.3f} s")
            report(f"mt ct2 beam {beam} {label}: text: {out}")
    report(f"mt ct2 nvidia-smi used {gpu_memory_used_mib()} MiB (before load {used_before} MiB)")
    del translator

    used_before = gpu_memory_used_mib()
    start = time.perf_counter()
    model = AutoModelForSeq2SeqLM.from_pretrained(
        MT_REPO, dtype=torch.float16, local_files_only=True
    ).to("cuda")
    model.eval()
    report(f"mt pytorch load time {time.perf_counter() - start:.2f} s, dtype float16")
    target_id = tokenizer.convert_tokens_to_ids(MT_TGT_LANG)
    for beam in MT_BEAM_SIZES:
        for label, text in calls:
            inputs = tokenizer(text, return_tensors="pt").to("cuda")
            torch.cuda.synchronize()
            start = time.perf_counter()
            with torch.inference_mode():
                ids = model.generate(**inputs, forced_bos_token_id=target_id, num_beams=beam)
            torch.cuda.synchronize()
            elapsed = time.perf_counter() - start
            out = tokenizer.batch_decode(ids, skip_special_tokens=True)[0]
            english.append(out)
            report(f"mt pytorch beam {beam} {label}: time {elapsed:.3f} s")
            report(f"mt pytorch beam {beam} {label}: text: {out}")
    report(
        f"mt pytorch nvidia-smi used {gpu_memory_used_mib()} MiB (before load {used_before} MiB)"
    )
    for name in CLIPS:
        report(f"mt reference {name}: {read_text(name, 'en')}")

    assert all(out.strip() for out in english), "mt: an empty text"
    del model
    torch.cuda.empty_cache()


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
