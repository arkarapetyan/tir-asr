# /// script
# requires-python = "==3.11.*"
# dependencies = [
#     "torch==2.8.0",
#     "torchaudio==2.8.0",
#     "fairseq2n==0.5.2",
#     "fairseq2==0.5.2",
#     "omnilingual-asr==0.2.0",
#     "numpy==1.26.4",
#     "pyarrow==21.0.0",
#     "pandas==2.2.3",
#     "polars==1.42.1",
#     "numba==0.61.2",
#     "soundfile==0.13.1",
#     "huggingface_hub==0.34.4",
# ]
# ///
"""OhanASR-v0.1 on the C9 segment dump, in its own environment (D-073). Model level.

The pins above are the `requirements.txt` of the model (Metric-AI/OhanASR-v0.1). This script
cannot import `tir_asr` (Python 3.12 or newer), so it reads the plain dump format of
`tir_asr.eval.c9.pack_segments`: data/c9/segments.npz (audio, offsets) and
data/c9/segments.json (the index). It writes test-results/c9/asr-ohanasr.json in the format of
`scripts/c9_run.py asr`. The texts are the raw model texts; the report applies the output rules.

The model loads with `load_model` of the model's own `ohanasr.py` (models/ohanasr-v0.1, read by
Claude on 2026-11-23): omniASR_LLM_1B_v2 with the OhanASR checkpoint, bfloat16 on CUDA, with
the rotary tables in float32. Each segment is one call of the inference pipeline (batch 1), as in
the program. The segments are at most 15 s (`vad_max_speech_s`), under the 40 s model limit.

Commands (on the laptop; the first `uv lock` needs the network):
  uv lock --script scripts/ohanasr_transcribe.py
  env -u LD_LIBRARY_PATH HF_HUB_OFFLINE=1 uv run --python 3.11 --script \\
      scripts/ohanasr_transcribe.py [--limit N]
"""

import argparse
import importlib.metadata
import json
import sys
import time
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT / "models" / "ohanasr-v0.1"
DUMP = ROOT / "data" / "c9" / "segments"
OUT = ROOT / "test-results" / "c9" / "asr-ohanasr.json"
SAMPLE_RATE = 16_000
WARMUP_AUDIO_S = 2.0  # the same value as tir_asr.config.WARMUP_AUDIO_S
LANG = "hye_Armn"
MAX_SAMPLES = 40 * SAMPLE_RATE  # the model limit (model.json: max_audio_seconds_per_call)
MIB = 2**20
PACKAGES = ("torch", "torchaudio", "fairseq2", "fairseq2n", "omnilingual-asr", "numpy")


def say(text: str) -> None:
    print(text, flush=True)


def used_mib() -> int:
    free, total = torch.cuda.mem_get_info()
    return (total - free) // MIB


def main() -> int:
    parser = argparse.ArgumentParser(prog="ohanasr_transcribe")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    if not torch.cuda.is_available():
        raise SystemExit("asr: CUDA is not available")  # no CPU fallback (R10)
    if not (MODEL_DIR / "model.pt").is_file():
        raise SystemExit(f"asr: no OhanASR model in {MODEL_DIR}")

    arrays = np.load(DUMP.with_suffix(".npz"))
    audio, offsets = arrays["audio"], arrays["offsets"]
    index = json.loads(DUMP.with_suffix(".json").read_text(encoding="utf-8"))["segments"]
    if len(offsets) != len(index) + 1 or offsets[-1] != len(audio):
        raise SystemExit("asr: the dump offsets do not agree with the index")
    index = index[: args.limit]

    torch.cuda.init()
    base = used_mib()
    clock = time.perf_counter
    start = clock()
    sys.path.insert(0, str(MODEL_DIR))
    from ohanasr import load_model  # the model's own code, models/ohanasr-v0.1

    pipeline = load_model(MODEL_DIR)
    load_s = clock() - start
    loaded = used_mib()
    peak = loaded

    def transcribe(samples: np.ndarray) -> str:
        if len(samples) > MAX_SAMPLES:
            raise SystemExit(f"asr: a segment of {len(samples)} samples is over the model limit")
        with torch.inference_mode():
            texts = pipeline.transcribe(
                [{"waveform": samples, "sample_rate": SAMPLE_RATE}], lang=[LANG], batch_size=1
            )
        return texts[0].strip()

    start = clock()
    transcribe(np.zeros(int(WARMUP_AUDIO_S * SAMPLE_RATE), dtype=np.float32))
    warmup_s = clock() - start
    items = []
    for i, item in enumerate(index):
        samples = audio[offsets[i] : offsets[i + 1]]
        if len(samples) != item["n"]:
            raise SystemExit(f"asr: segment {item['id']} has {len(samples)} samples")
        start = clock()
        text = transcribe(samples)
        seconds = clock() - start
        peak = max(peak, used_mib())
        items.append({"id": item["id"], "hy": text, "seconds": seconds})
        say(f"{item['id']}: {seconds:.3f} s: {text}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    result = {
        "model": "ohanasr",
        "versions": {name: importlib.metadata.version(name) for name in PACKAGES},
        "gpu": torch.cuda.get_device_name(0),
        "load_s": load_s,
        "warmup_s": warmup_s,
        "vram_base_mib": base,
        "vram_loaded_mib": loaded,
        "vram_peak_mib": peak,
        "segments": items,
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    say(f"wrote {OUT.relative_to(ROOT)}; load {load_s:.1f} s; VRAM +{peak - base} MiB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
