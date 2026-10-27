"""Probe (C6, D-062 part 1, R6, R8): P4 variants on the GPU and on the CPU. Research only.

The program does not import this script. P4 is facebook/seamless-m4t-v2-large with
`SeamlessM4Tv2ForSpeechToText`. The variants of one segment:
- V0: two full `generate` calls (tgt_lang "hye", then "eng"), as in C3 (`eval/seamless.py`).
- V1: one encoder pass, then two decodes that get the encoder output (`encoder_outputs`).
- V2: one encoder pass, then one decode of a batch of two rows (the "hye" and the "eng" code).
- V1g, V2g: V1 and V2 with num_beams=1, only if the default num_beams of the model is larger.
Each `generate` call gets a new `BaseModelOutput`, because `generate` changes the given encoder
output in place for the beams (`_expand_dict_for_generation`, transformers 5.20.2).

gpu: float16 on cuda, the 34 segments of S1-S3 (the program's VAD with Params(), as in C3).
For each segment, the variants run one after the other, so that a slow phase of the GPU has
the same effect on all variants. Report: WER, CER, chrF, the line time, the decode steps, and
the time of one decode step (batch of one against batch of two, D-062 part 8).
cpu: float32 on the CPU, the 3 segments of the C3 CPU probe, cut with the labels. No Silero
import, so torch keeps its default thread count. All variants at 24 and at 8 threads; then INT8
(`torch.ao.quantization.quantize_dynamic` on nn.Linear) at the faster thread count.

Run on the laptop (D-030; nothing downloads):
  env -u LD_LIBRARY_PATH HF_HUB_OFFLINE=1 uv run --no-sync python scripts/probe_p4.py gpu
  env -u LD_LIBRARY_PATH HF_HUB_OFFLINE=1 uv run --no-sync python scripts/probe_p4.py cpu
"""

import importlib.metadata
import json
import os
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np
import torch
from transformers import AutoProcessor, SeamlessM4Tv2ForSpeechToText
from transformers.generation import LogitsProcessor, LogitsProcessorList
from transformers.generation.utils import GenerationMixin
from transformers.modeling_outputs import BaseModelOutput

from tir_asr.config import SAMPLE_RATE, WARMUP_AUDIO_S, Params
from tir_asr.eval.data import load_wav_16k, read_labels, read_references
from tir_asr.eval.metrics import cer, chrf, wer
from tir_asr.eval.run import segment_file

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "eval" / "raw"
SCRIPTS_MD = ROOT / "docs" / "eval" / "scripts.md"
OUT = ROOT / "test-results" / "bakeoff"
REPO = "facebook/seamless-m4t-v2-large"
SCRIPT_IDS = ("s1", "s2", "s3")
SIDES = ("mic", "call")
CPU_IDS = ("s3-01", "s3-05", "s3-07")  # the segments of the C3 CPU probe (mic side)
CPU_THREADS = (24, 8)
GENERATE_KEYS = (
    "num_beams",
    "max_new_tokens",
    "max_length",
    "early_stopping",
    "length_penalty",
    "no_repeat_ngram_size",
    "repetition_penalty",
    "do_sample",
    "decoder_start_token_id",
    "eos_token_id",
    "pad_token_id",
)
MIB = 2**20


def say(text: str) -> None:
    print(text, flush=True)


class StepCounter(LogitsProcessor):
    """Count the decode steps of one `generate` call: `generate` calls it one time each step."""

    def __init__(self) -> None:
        self.steps = 0

    def __call__(self, input_ids: torch.LongTensor, scores: torch.FloatTensor) -> torch.FloatTensor:
        self.steps += 1
        return scores


class P4:
    """The Seamless model and the variants V0, V1, and V2 for one segment."""

    def __init__(self, device: str, dtype: torch.dtype) -> None:
        self.device = device
        self.dtype = dtype
        start = time.perf_counter()
        self.processor = AutoProcessor.from_pretrained(REPO, local_files_only=True)
        self.model = (
            SeamlessM4Tv2ForSpeechToText.from_pretrained(REPO, dtype=dtype, local_files_only=True)
            .to(device)
            .eval()
        )
        self.load_s = time.perf_counter() - start
        config = self.model.generation_config
        self.codes = {lang: config.text_decoder_lang_to_code_id[lang] for lang in ("hye", "eng")}
        self.generate_values = {key: getattr(config, key, None) for key in GENERATE_KEYS}
        self.default_beams = config.num_beams or 1

    def _now(self) -> float:
        if self.device == "cuda":
            torch.cuda.synchronize()
        return time.perf_counter()

    def _features(self, audio: np.ndarray) -> tuple[torch.Tensor, torch.Tensor | None]:
        inputs = self.processor(audio=audio, sampling_rate=SAMPLE_RATE, return_tensors="pt")
        features = inputs["input_features"].to(self.device, self.dtype)
        mask = inputs.get("attention_mask")
        return features, (mask.to(self.device) if mask is not None else None)

    def _text(self, row: torch.Tensor) -> str:
        return self.processor.decode(row.tolist(), skip_special_tokens=True).strip()

    def v0(self, audio: np.ndarray, extra: dict) -> dict:
        """Two full calls, as in C3: the features and the encoder run two times."""
        texts, steps, seconds = {}, {}, {}
        for lang in ("hye", "eng"):
            start = self._now()
            features, mask = self._features(audio)
            counter = StepCounter()
            with torch.inference_mode():
                tokens = self.model.generate(
                    input_features=features,
                    attention_mask=mask,
                    tgt_lang=lang,
                    logits_processor=LogitsProcessorList([counter]),
                    **extra,
                )
            texts[lang] = self._text(tokens[0])
            seconds[lang] = self._now() - start
            steps[lang] = counter.steps
        return {
            "hy": texts["hye"],
            "en": texts["eng"],
            "asr_s": seconds["hye"],
            "mt_s": seconds["eng"],
            "line_s": seconds["hye"] + seconds["eng"],
            "steps": [steps["hye"], steps["eng"]],
            "decode_s": None,
        }

    def _encode(self, audio: np.ndarray):
        features, mask = self._features(audio)
        with torch.inference_mode():
            hidden = self.model.get_encoder()(input_features=features, attention_mask=mask)[0]
        return features, mask, hidden

    def v1(self, audio: np.ndarray, extra: dict) -> dict:
        """One encoder pass, then one decode for each language."""
        start = self._now()
        features, mask, hidden = self._encode(audio)
        encoded = self._now()
        texts, steps, ends = {}, {}, {}
        for lang in ("hye", "eng"):
            counter = StepCounter()
            with torch.inference_mode():
                tokens = self.model.generate(
                    input_features=features,
                    attention_mask=mask,
                    encoder_outputs=BaseModelOutput(last_hidden_state=hidden),  # a new one
                    tgt_lang=lang,
                    logits_processor=LogitsProcessorList([counter]),
                    **extra,
                )
            texts[lang] = self._text(tokens[0])
            ends[lang] = self._now()
            steps[lang] = counter.steps
        return {
            "hy": texts["hye"],
            "en": texts["eng"],
            "asr_s": ends["hye"] - start,
            "mt_s": ends["eng"] - ends["hye"],
            "line_s": ends["eng"] - start,
            "encode_s": encoded - start,
            "steps": [steps["hye"], steps["eng"]],
            "decode_s": ends["eng"] - encoded,
        }

    def v2(self, audio: np.ndarray, extra: dict) -> dict:
        """One encoder pass, then one decode of a batch of two rows ("hye" and "eng")."""
        start = self._now()
        features, mask, hidden = self._encode(audio)
        encoded = self._now()
        rows = torch.tensor([[self.codes["hye"]], [self.codes["eng"]]], device=self.device)
        counter = StepCounter()
        kwargs = {"attention_mask": mask.repeat(2, 1)} if mask is not None else {}
        with torch.inference_mode():
            # The base `generate`: the Seamless `generate` with no tgt_lang writes a warning at
            # each call. The decoder start token comes before each row (base `generate`).
            tokens = GenerationMixin.generate(
                self.model,
                features.repeat(2, 1, 1),
                encoder_outputs=BaseModelOutput(last_hidden_state=hidden.repeat(2, 1, 1)),
                decoder_input_ids=rows,
                logits_processor=LogitsProcessorList([counter]),
                **kwargs,
                **extra,
            )
        hy, en = self._text(tokens[0]), self._text(tokens[1])
        end = self._now()
        return {
            "hy": hy,
            "en": en,
            "asr_s": end - start,
            "mt_s": 0.0,
            "line_s": end - start,
            "encode_s": encoded - start,
            "steps": [counter.steps],
            "decode_s": end - encoded,
        }

    def variants(self) -> dict:
        """Name -> (method, extra generate arguments)."""
        names = {"V0": (self.v0, {}), "V1": (self.v1, {}), "V2": (self.v2, {})}
        if self.default_beams > 1:
            names["V1g"] = (self.v1, {"num_beams": 1})
            names["V2g"] = (self.v2, {"num_beams": 1})
        return names


def versions() -> dict:
    return {name: importlib.metadata.version(name) for name in ("torch", "transformers")}


def step_s(results: list[dict]) -> float | None:
    """The mean time of one decode step over all segments (V1: batch of one; V2: of two)."""
    decode = sum(r["decode_s"] for r in results if r["decode_s"] is not None)
    steps = sum(sum(r["steps"]) for r in results if r["decode_s"] is not None)
    return decode / steps if steps else None


def summary(name: str, results: list[dict], reference: list[dict]) -> dict:
    lines = [r["line_s"] for r in results]
    same = sum(
        r["hy"] == ref["hy"] and r["en"] == ref["en"]
        for r, ref in zip(results, reference, strict=True)
    )
    return {
        "line_mean_s": float(np.mean(lines)),
        "line_max_s": float(np.max(lines)),
        "asr_mean_s": float(np.mean([r["asr_s"] for r in results])),
        "mt_mean_s": float(np.mean([r["mt_s"] for r in results])),
        "steps_mean": float(np.mean([sum(r["steps"]) for r in results])),
        "steps_max": int(max(max(r["steps"]) for r in results)),
        "step_s": step_s(results),
        "empty_hy": sum(not r["hy"] for r in results),
        "same_as_V0": same,
    }


def print_table(rows: dict) -> None:
    say(
        f"{'variant':8} {'WER':>6} {'CER':>6} {'chrF':>6} {'line mean':>10} {'line max':>9}"
        f" {'asr':>6} {'mt':>6} {'steps':>6} {'max':>4} {'step ms':>8} {'same':>5} {'empty':>5}"
    )
    for name, row in rows.items():
        step = f"{row['step_s'] * 1000:8.1f}" if row["step_s"] is not None else f"{'-':>8}"
        say(
            f"{name:8} {row['wer'] * 100:5.1f}% {row['cer'] * 100:5.1f}% {row['chrf']:6.1f}"
            f" {row['line_mean_s']:9.3f}s {row['line_max_s']:8.3f}s"
            f" {row['asr_mean_s']:5.3f}s {row['mt_mean_s']:5.3f}s {row['steps_mean']:6.1f}"
            f" {row['steps_max']:4d} {step} {row['same_as_V0']:5d} {row['empty_hy']:5d}"
        )


def run_gpu() -> dict:
    if not torch.cuda.is_available():
        raise SystemExit("probe_p4: CUDA is not available")
    base = torch.cuda.mem_get_info()
    p4 = P4("cuda", torch.float16)
    free, total = torch.cuda.mem_get_info()
    result = {
        "device": "cuda",
        "gpu": torch.cuda.get_device_name(0),
        "versions": versions(),
        "attn_implementation": p4.model.config._attn_implementation,
        "load_s": p4.load_s,
        "vram_load_mib": (base[0] - free) // MIB,
        "generate": p4.generate_values,
        "codes": p4.codes,
    }
    say(f"GPU {result['gpu']}; {result['versions']}; attention {result['attn_implementation']}")
    say(f"load {p4.load_s:.1f} s; VRAM +{result['vram_load_mib']} MiB")
    say(f"generate values {p4.generate_values}")
    variants = p4.variants()
    zeros = np.zeros(int(WARMUP_AUDIO_S * SAMPLE_RATE), dtype=np.float32)
    result["warmup_s"] = {}
    for name, (method, extra) in variants.items():
        start = time.perf_counter()
        method(zeros, extra)
        result["warmup_s"][name] = time.perf_counter() - start
    say(f"warm-up {', '.join(f'{k} {v:.2f} s' for k, v in result['warmup_s'].items())}")

    # The VAD loads after the model, as in the program (D-043): silero_vad sets 1 CPU thread.
    from tir_asr.segment.silero import SileroSpeechProbability

    params = Params()
    files = []
    peaks = dict.fromkeys(variants, 0)
    for script in SCRIPT_IDS:
        lines_all = read_references(SCRIPTS_MD, script)
        for side in SIDES:
            lines = [line for line in lines_all if line.side == side]
            audio = load_wav_16k(RAW / f"{script}.{side}.wav")
            segments = segment_file(audio, SileroSpeechProbability(), params)
            record = {
                "script": script,
                "side": side,
                "ref_hy": " ".join(line.hy for line in lines),
                "ref_en": " ".join(line.en for line in lines),
                "segments": [],
            }
            for segment in segments:
                item = {"audio_s": len(segment.audio) / SAMPLE_RATE, "variants": {}}
                for name, (method, extra) in variants.items():
                    torch.cuda.reset_peak_memory_stats()
                    item["variants"][name] = method(segment.audio, extra)
                    peaks[name] = max(peaks[name], torch.cuda.max_memory_allocated() // MIB)
                record["segments"].append(item)
                say(
                    f"{script} {side} {item['audio_s']:5.2f} s: "
                    + ", ".join(
                        f"{name} {r['line_s']:.3f} s/{sum(r['steps'])} st"
                        for name, r in item["variants"].items()
                    )
                )
            files.append(record)
    result["files"] = files
    result["peak_torch_mib"] = peaks

    rows = {}
    for name in variants:
        results = [s["variants"][name] for f in files for s in f["segments"]]
        reference = [s["variants"]["V0"] for f in files for s in f["segments"]]
        row = summary(name, results, reference)
        hyp_hy = [" ".join(s["variants"][name]["hy"] for s in f["segments"]) for f in files]
        hyp_en = [" ".join(s["variants"][name]["en"] for s in f["segments"]) for f in files]
        row["wer"] = wer([f["ref_hy"] for f in files], hyp_hy)
        row["cer"] = cer([f["ref_hy"] for f in files], hyp_hy)
        row["chrf"] = chrf([f["ref_en"] for f in files], hyp_en)
        row["peak_torch_mib"] = peaks[name]
        rows[name] = row
    result["summary"] = rows
    segments = sum(len(f["segments"]) for f in files)
    say(f"\nGPU, {segments} segments; 'same': HY and EN equal to V0; 'empty': segments with no HY")
    print_table(rows)
    if rows["V1"]["step_s"] and rows["V2"]["step_s"]:
        ratio = rows["V2"]["step_s"] / rows["V1"]["step_s"]
        result["step_ratio_v2_v1"] = ratio
        say(f"one decode step: batch of two / batch of one = {ratio:.2f} (D-062 part 8)")
    say(f"peak torch memory (MiB): {peaks}")
    return result


def core_counts() -> dict:
    """The number of CPUs for each maximum frequency (P-cores and E-cores differ)."""
    counts: Counter = Counter()
    for path in Path("/sys/devices/system/cpu").glob("cpu[0-9]*/cpufreq/cpuinfo_max_freq"):
        counts[int(path.read_text().strip()) // 1000] += 1
    return {f"{mhz} MHz": n for mhz, n in sorted(counts.items(), reverse=True)}


def cpu_segments() -> list[tuple[str, np.ndarray, str, str]]:
    lines = {line.id: line for line in read_references(SCRIPTS_MD, "s3")}
    labels = {x.id: x for x in read_labels(RAW / "s3.labels.txt", list(lines.values()))}
    audio = load_wav_16k(RAW / "s3.mic.wav")
    return [
        (
            i,
            audio[int(labels[i].start * SAMPLE_RATE) : int(labels[i].end * SAMPLE_RATE)],
            lines[i].hy,
            lines[i].en,
        )
        for i in CPU_IDS
    ]


def cpu_phase(p4: P4, segs, variants: dict, threads: int, label: str, reference) -> dict:
    torch.set_num_threads(threads)
    zeros = np.zeros(int(WARMUP_AUDIO_S * SAMPLE_RATE), dtype=np.float32)
    phase = {"threads": threads, "label": label, "warmup_s": {}, "segments": []}
    for name, (method, extra) in variants.items():
        start = time.perf_counter()
        method(zeros, extra)
        phase["warmup_s"][name] = time.perf_counter() - start
    for line_id, audio, _, _ in segs:
        item = {"id": line_id, "audio_s": len(audio) / SAMPLE_RATE, "variants": {}}
        for name, (method, extra) in variants.items():
            item["variants"][name] = method(audio, extra)
            r = item["variants"][name]
            say(
                f"{label} {threads} threads {line_id} {name}: {r['line_s']:.2f} s"
                f" (asr {r['asr_s']:.2f} s, mt {r['mt_s']:.2f} s), steps {r['steps']}"
                f" | {r['hy']} | {r['en']}"
            )
        phase["segments"].append(item)
    rows = {}
    for name in variants:
        results = [s["variants"][name] for s in phase["segments"]]
        ref = reference
        if ref is None:  # the first phase is the reference: V0, float32, 24 threads
            ref = [s["variants"]["V0"] for s in phase["segments"]]
        row = summary(name, results, ref)
        row["wer"] = wer([s[2] for s in segs], [r["hy"] for r in results])
        row["cer"] = cer([s[2] for s in segs], [r["hy"] for r in results])
        row["chrf"] = chrf([s[3] for s in segs], [r["en"] for r in results])
        rows[name] = row
    phase["summary"] = rows
    say(
        f"\nCPU {label}, {threads} threads ('same': equal to V0, float32, {CPU_THREADS[0]} threads)"
    )
    print_table(rows)
    return phase


def run_cpu(path: Path) -> dict:
    say(f"CPUs {os.cpu_count()}; by maximum frequency: {core_counts()}")
    p4 = P4("cpu", torch.float32)
    result = {
        "device": "cpu",
        "versions": versions(),
        "cpu_count": os.cpu_count(),
        "cores": core_counts(),
        "load_s": p4.load_s,
        "generate": p4.generate_values,
        "phases": [],
    }
    say(f"load {p4.load_s:.1f} s (float32); generate {p4.generate_values}")
    segs = cpu_segments()
    variants = p4.variants()
    reference = None
    for threads in CPU_THREADS:
        phase = cpu_phase(p4, segs, variants, threads, "float32", reference)
        if reference is None:
            reference = [s["variants"]["V0"] for s in phase["segments"]]
        result["phases"].append(phase)
        path.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")

    best = min(result["phases"], key=lambda ph: ph["summary"]["V2"]["line_mean_s"])["threads"]
    say(f"\nINT8 (quantize_dynamic, nn.Linear) at {best} threads, the faster count for V2")
    torch.ao.quantization.quantize_dynamic(
        p4.model, qconfig_spec={torch.nn.Linear}, dtype=torch.qint8, inplace=True
    )
    int8 = {name: variants[name] for name in variants if name.startswith("V2")}
    result["phases"].append(cpu_phase(p4, segs, int8, best, "int8", reference))
    return result


def main() -> int:
    which = sys.argv[1] if len(sys.argv) > 1 else ""
    if which not in ("gpu", "cpu"):
        raise SystemExit("usage: probe_p4.py gpu|cpu")
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"p4-probe-{which}.json"
    result = run_gpu() if which == "gpu" else run_cpu(path)
    path.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    say(f"wrote {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
