"""Bake-off runner (C3, D-049, D-051). Model level: Aren runs it on the laptop.

One run = one ASR candidate and one MT candidate on S1-S3, both sides. The run writes
test-results/bakeoff/<asr>+<mt>.json and prints a summary. With --mt-input reference, the MT
candidate translates the reference Armenian lines (no ASR), which shows the MT quality with no
ASR errors.

Example (D-030: no LD_LIBRARY_PATH; nothing downloads):
  env -u LD_LIBRARY_PATH HF_HUB_OFFLINE=1 \
    uv run python scripts/bakeoff.py --asr nemo-rnnt --mt nllb-ct2
"""

import argparse
import importlib.metadata
import json
import sys
import time
from dataclasses import asdict
from pathlib import Path

import numpy as np

from tir_asr.config import SAMPLE_RATE, WARMUP_AUDIO_S, WARMUP_TEXT, Params, parameter_lines
from tir_asr.eval.data import load_wav_16k, read_labels, read_references
from tir_asr.eval.metrics import cer, chrf, wer
from tir_asr.eval.run import score_side, segment_file, transcribe_all, translate_all

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "eval" / "raw"
SCRIPTS_MD = ROOT / "docs" / "eval" / "scripts.md"
OUT = ROOT / "test-results" / "bakeoff"
SCRIPT_IDS = ("s1", "s2", "s3")
SIDES = ("mic", "call")
ASR_NAMES = ("nemo-rnnt",)
MT_NAMES = ("nllb-ct2",)
PACKAGES = ("tir-asr", "torch", "nemo-toolkit", "ctranslate2", "transformers", "silero-vad")
MIB = 2**20


def load_asr(name: str):
    if name == "nemo-rnnt":
        from tir_asr.asr.nemo_rnnt import NemoRnntTranscriber

        return NemoRnntTranscriber()
    raise SystemExit(f"bakeoff: unknown ASR candidate {name}")


def load_mt(name: str, params: Params):
    if name == "nllb-ct2":
        from tir_asr.mt.ct2_nllb import MT_MODEL_DIR, Ct2NllbTranslator

        return Ct2NllbTranslator(params, ROOT / MT_MODEL_DIR)
    raise SystemExit(f"bakeoff: unknown MT candidate {name}")


def say(text: str) -> None:
    print(text, flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(prog="bakeoff")
    parser.add_argument("--asr", choices=(*ASR_NAMES, "none"), required=True)
    parser.add_argument("--mt", choices=MT_NAMES, required=True)
    parser.add_argument("--mt-input", choices=("asr", "reference"), default="asr")
    args = parser.parse_args()
    if (args.asr == "none") != (args.mt_input == "reference"):
        raise SystemExit("bakeoff: use --asr none together with --mt-input reference")

    import torch

    def used_mib() -> int:
        free, total = torch.cuda.mem_get_info()
        return (total - free) // MIB

    params = Params()
    run = {
        "asr": args.asr,
        "mt": args.mt,
        "mt_input": args.mt_input,
        "versions": {name: importlib.metadata.version(name) for name in PACKAGES},
        "gpu": torch.cuda.get_device_name(0),
        "parameters": parameter_lines(params),
        "files": [],
    }
    clock = time.perf_counter

    asr = None
    base = used_mib()
    if args.asr != "none":
        start = clock()
        asr = load_asr(args.asr)
        run["asr_load_s"] = clock() - start
        run["asr_vram_mib"] = used_mib() - base
        start = clock()
        asr.transcribe(np.zeros(int(WARMUP_AUDIO_S * SAMPLE_RATE), dtype=np.float32))
        run["asr_warmup_s"] = clock() - start
    base = used_mib()
    start = clock()
    mt = load_mt(args.mt, params)
    run["mt_load_s"] = clock() - start
    run["mt_vram_mib"] = used_mib() - base
    start = clock()
    mt.translate(WARMUP_TEXT)
    run["mt_warmup_s"] = clock() - start

    # The VAD loads last, as in the program (D-043): silero_vad sets the CPU threads at import.
    from tir_asr.segment.silero import SileroSpeechProbability

    for script in SCRIPT_IDS:
        lines_all = read_references(SCRIPTS_MD, script)
        labels_all = read_labels(RAW / f"{script}.labels.txt", lines_all)
        for side in SIDES:
            lines = [line for line in lines_all if line.side == side]
            ids = {line.id for line in lines}
            labels = [label for label in labels_all if label.id in ids]
            record = {"script": script, "side": side}
            if asr is None:  # --mt-input reference
                out = translate_all([line.hy for line in lines], mt, clock)
                record["ref_hy"] = " ".join(line.hy for line in lines)
                record["ref_en"] = " ".join(line.en for line in lines)
                record["hyp_en"] = " ".join(t.text for t in out)
                record["lines"] = [
                    {
                        "id": line.id,
                        "en": t.text,
                        "mt_s": t.seconds,
                        "chrf": chrf([line.en], [t.text]),
                    }
                    for line, t in zip(lines, out, strict=True)
                ]
                record["chrf"] = chrf([record["ref_en"]], [record["hyp_en"]])
                say(f"{script} {side}: chrF {record['chrf']:.1f}")
            else:
                audio = load_wav_16k(RAW / f"{script}.{side}.wav")
                segments = segment_file(audio, SileroSpeechProbability(), params)
                hy = transcribe_all(segments, asr, clock)
                en = translate_all([t.text for t in hy], mt, clock)
                score = score_side(
                    lines,
                    labels,
                    segments,
                    [t.text for t in hy],
                    [t.text for t in en],
                    [t.seconds for t in hy],
                    [t.seconds for t in en],
                )
                record["ref_hy"] = " ".join(line.hy for line in lines)
                record["ref_en"] = " ".join(line.en for line in lines)
                record["hyp_hy"] = " ".join(t.text for t in hy)
                record["hyp_en"] = " ".join(t.text for t in en)
                record["score"] = asdict(score)
                record["segments"] = [
                    {
                        "start": s.start,
                        "speech_end": s.speech_end,
                        "cut": s.cut,
                        "hy": h.text,
                        "en": e.text,
                        "asr_s": h.seconds,
                        "mt_s": e.seconds,
                    }
                    for s, h, e in zip(segments, hy, en, strict=True)
                ]
                say(
                    f"{script} {side}: WER {score.wer:.3f} CER {score.cer:.3f}"
                    f" chrF {score.chrf:.1f}"
                    f" segments {score.segments} outside {score.outside}"
                    f" digit words {score.digit_words} ASR RTF {score.asr_rtf:.3f}"
                )
            run["files"].append(record)

    totals = {}
    groups = {"mic": ["mic"], "call": ["call"], "all": list(SIDES)}
    for group, sides in groups.items():
        files = [f for f in run["files"] if f["side"] in sides]
        total = {"chrf": chrf([f["ref_en"] for f in files], [f["hyp_en"] for f in files])}
        if asr is not None:
            total["wer"] = wer([f["ref_hy"] for f in files], [f["hyp_hy"] for f in files])
            total["cer"] = cer([f["ref_hy"] for f in files], [f["hyp_hy"] for f in files])
            asr_s = [s["asr_s"] for f in files for s in f["segments"]]
            audio_s = sum(f["score"]["audio_s"] for f in files)
            total["asr_rtf"] = sum(asr_s) / audio_s
            total["asr_max_s"] = max(asr_s)
            mt_s = [s["mt_s"] for f in files for s in f["segments"] if s["hy"].strip()]
            total["mt_max_s"] = max(mt_s, default=0.0)
        totals[group] = total
        say(f"total {group}: " + ", ".join(f"{key} {value:.3f}" for key, value in total.items()))
    run["totals"] = totals

    OUT.mkdir(parents=True, exist_ok=True)
    suffix = "+ref" if args.mt_input == "reference" else ""
    path = OUT / f"{args.asr}+{args.mt}{suffix}.json"
    path.write_text(json.dumps(run, ensure_ascii=False, indent=1), encoding="utf-8")
    say(f"wrote {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
