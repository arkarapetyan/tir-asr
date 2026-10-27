"""Speaker bake-off: the threshold sweep (C5, D-057, D-058). Model level (Aren's laptop).

D-058 selected TitaNet. The ECAPA and WeSpeaker candidates and their packages are removed; the
`c5-embed` commits keep them, and docs/eval/results.md has their numbers.

One run = one speaker model on the four eval streams (S1, S2, S3 call sides and stream D), with
both clustering rules (A: centroid, B-max: nearest) and the thresholds 0.20 to 0.90. The
segments come from the program's VAD with `Params()`. The run writes
test-results/bakeoff/spk-<model>.json and prints a table for each rule.

Example (D-030: no LD_LIBRARY_PATH; nothing downloads):
  env -u LD_LIBRARY_PATH HF_HUB_OFFLINE=1 \
    uv run --no-sync python scripts/spk_bakeoff.py --model titanet
"""

import argparse
import importlib.metadata
import json
import sys
import time
from dataclasses import asdict
from pathlib import Path

import numpy as np

from tir_asr.config import SAMPLE_RATE, WARMUP_AUDIO_S, Params, parameter_lines
from tir_asr.eval.data import load_wav_16k, read_labels, read_references
from tir_asr.eval.nearest import NearestClusterer
from tir_asr.eval.run import segment_file
from tir_asr.eval.spk_run import (
    MIN_RANGE,
    THRESHOLDS,
    embed_all,
    pairwise,
    pass_range,
    sweep,
)
from tir_asr.eval.streams import STREAM_D_CUT_S, call_stream, stream_d
from tir_asr.speakers.cluster import CentroidClusterer

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "eval" / "raw"
SCRIPTS_MD = ROOT / "docs" / "eval" / "scripts.md"
OUT = ROOT / "test-results" / "bakeoff"
MODELS = ("titanet",)
RULES = {"centroid": CentroidClusterer, "nearest": NearestClusterer}
MIN_NEW_S = 1.0  # s; the start value of spk_min_new_s (D-057, part 5B)
PACKAGES = ("tir-asr", "torch", "nemo-toolkit", "silero-vad")
MIB = 2**20


def load_model(name: str):
    if name == "titanet":
        from tir_asr.eval.spk_titanet import TitanetEmbedder

        return TitanetEmbedder()
    raise SystemExit(f"spk_bakeoff: unknown model {name}")


def version(name: str) -> str:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return "not installed"


def say(text: str) -> None:
    print(text, flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(prog="spk_bakeoff")
    parser.add_argument("--model", choices=MODELS, required=True)
    args = parser.parse_args()

    import torch

    def used_mib() -> int:
        free, total = torch.cuda.mem_get_info()
        return (total - free) // MIB

    params = Params()
    clock = time.perf_counter
    run = {
        "model": args.model,
        "versions": {name: version(name) for name in PACKAGES},
        "gpu": torch.cuda.get_device_name(0),
        "parameters": parameter_lines(params),
        "min_new_s": MIN_NEW_S,
        "stream_d_cut_s": STREAM_D_CUT_S,
        "thresholds": list(THRESHOLDS),
        "streams": {},
    }

    base = used_mib()
    start = clock()
    model = load_model(args.model)
    run["load_s"] = clock() - start
    run["vram_mib"] = used_mib() - base
    start = clock()
    model.embed(np.zeros(int(WARMUP_AUDIO_S * SAMPLE_RATE), dtype=np.float32))
    run["warmup_s"] = clock() - start
    say(f"{args.model}: load {run['load_s']:.2f} s, warm-up {run['warmup_s']:.2f} s")

    # The VAD loads last, as in the program (D-043): silero_vad sets the CPU threads at import.
    from tir_asr.segment.silero import SileroSpeechProbability

    calls = {}
    for script in ("s1", "s2", "s3"):
        lines = read_references(SCRIPTS_MD, script)
        labels = read_labels(RAW / f"{script}.labels.txt", lines)
        calls[script] = call_stream(script, load_wav_16k(RAW / f"{script}.call.wav"), lines, labels)
    streams = [
        calls["s1"],
        calls["s2"],
        calls["s3"],
        stream_d(calls["s1"], calls["s2"], calls["s3"]),
    ]

    points = {rule: {} for rule in RULES}
    for stream in streams:
        segments = segment_file(stream.audio, SileroSpeechProbability(), params)
        items = embed_all(segments, stream.turns, model, clock)
        record = {
            "audio_s": len(stream.audio) / SAMPLE_RATE,
            "true_speakers": sorted({turn.speaker for turn in stream.turns}),
            "turns": len(stream.turns),
            "segments": [
                {
                    "start": s.start,
                    "speech_end": s.speech_end,
                    "duration_s": item.duration_s,
                    "truth": item.truth,
                    "embed_s": item.seconds,
                }
                for s, item in zip(segments, items, strict=True)
            ],
            "outside": sum(item.truth is None for item in items),
            "embed_mean_s": sum(i.seconds for i in items) / len(items),
            "embed_max_s": max(i.seconds for i in items),
            "pairwise": asdict(pairwise(items)),
            "sweep": {},
        }
        for rule, cls in RULES.items():
            points[rule][stream.name] = sweep(items, cls, THRESHOLDS, MIN_NEW_S)
            record["sweep"][rule] = [asdict(p) for p in points[rule][stream.name]]
        run["streams"][stream.name] = record
        pw = record["pairwise"]
        same = "-" if pw["same_min"] is None else f"{pw['same_min']:.3f}"
        diff = "-" if pw["different_max"] is None else f"{pw['different_max']:.3f}"
        say(
            f"stream {stream.name}: {len(segments)} segments, {record['outside']} outside,"
            f" speakers {len(record['true_speakers'])}; same-speaker min {same},"
            f" different-speaker max {diff}; embed max {record['embed_max_s']:.3f} s"
        )

    run["pass"] = {}
    for rule in RULES:
        names = list(points[rule])
        say(f"\nrule {rule}: wrong / scored (speaker count) for each stream")
        say("threshold  " + "  ".join(f"{name:>12}" for name in names))
        for k, threshold in enumerate(THRESHOLDS):
            cells = []
            for name in names:
                p = points[rule][name][k]
                cells.append(f"{p.wrong:>3}/{p.scored:<3} ({p.speakers:>2})")
            say(f"{threshold:9.2f}  " + "  ".join(f"{cell:>12}" for cell in cells))
        found = pass_range(points[rule])
        width = None if found is None else round(found[1] - found[0], 2)
        passes = width is not None and width >= MIN_RANGE
        run["pass"][rule] = {"range": found, "width": width, "passes": passes}
        say(f"rule {rule}: passing range {found}, width {width}, passes {passes}")

    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"spk-{args.model}.json"
    path.write_text(json.dumps(run, ensure_ascii=False, indent=1), encoding="utf-8")
    say(f"wrote {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
