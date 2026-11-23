"""C9 model eval runner (D-072, D-073; changed in C10, D-081). Model level: Aren runs it.

Subcommands (all model runs read the same segment dump, so all models get the same segments):

  dump    the VAD segments of S1-S3 and S5 with `Params()`  -> data/c9/segments.{npz,json}
  asr     one ASR model on the dump                          -> test-results/c9/asr-<model>.json
  mt      one MT model on the reference text or an ASR file  -> test-results/c9/mt-<m>+<input>.json
  report  the tables and the check of the decision rule      -> test-results/c9/report.txt

C10 (D-081): the program environment has OhanASR, so `asr` runs the program adapter
(`tir_asr.asr.ohanasr`) in this process, and `mt` runs the program adapter `tir_asr.mt.google`.
The C9 models `nemo-rnnt`, `p4`, `nllb-ct2`, and `seamless` left with P1 and P4 (D-081 point 5);
their C9 result files stay in test-results/c9/, and `report` still reads them.

Examples (nothing downloads from Hugging Face; `mt` sends text to Google, D-079):
  uv run --no-sync python scripts/c9_run.py dump
  HF_HUB_OFFLINE=1 uv run --no-sync python scripts/c9_run.py asr --model ohanasr
  HF_HUB_OFFLINE=1 uv run --no-sync python scripts/c9_run.py mt --model google --input asr-ohanasr
  uv run --no-sync python scripts/c9_run.py report

The texts in the files are the raw model texts. The output rules of the program
(`text/clean.py`, D-066) apply to the MT input and in the report, as in `TextStep.process`.
"""

import argparse
import importlib.metadata
import json
import sys
import time
from pathlib import Path

import numpy as np

from tir_asr.config import SAMPLE_RATE, WARMUP_AUDIO_S, WARMUP_TEXT, Params, parameter_lines
from tir_asr.eval.c9 import (
    S5_CUT_S,
    SETS,
    DumpSegment,
    check_rule,
    cut_audio,
    is_flagged,
    joined_texts,
    pack_segments,
    score_en,
    score_hy,
    unpack_segments,
)
from tir_asr.eval.data import load_wav_16k, read_references
from tir_asr.eval.metrics import chrf
from tir_asr.eval.run import segment_file
from tir_asr.text.clean import clean_armenian, clean_english

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "eval" / "raw"
C7 = ROOT / "data" / "c7"
DUMP = ROOT / "data" / "c9" / "segments"
OUT = ROOT / "test-results" / "c9"
SCRIPTS_MD = ROOT / "docs" / "eval" / "scripts.md"
MIB = 2**20
SCRIPT_OF_CALL = {"s1": "s1", "s2": "s2", "s3": "s3", "p1": "s5", "p4": "s5"}
TITANET_MIB = 200  # [RUN] C5 sweep, D-058: the speaker model in the program
# (set, script, call, side, file). Side "call" is the other people: "call" in S1-S3,
# the monitor ("system") in the C7 recordings.
FILES = [
    *[
        ("s1-s3", s, s, side, RAW / f"{s}.{side}.wav")
        for s in ("s1", "s2", "s3")
        for side in ("mic", "call")
    ],
    *[
        ("s5", "s5", call, side, C7 / f"{call}.{name}.wav")
        for call in ("p1", "p4")
        for side, name in (("mic", "mic"), ("call", "system"))
    ],
]
PACKAGES = (
    "tir-asr",
    "torch",
    "omnilingual-asr",
    "fairseq2",
    "nemo-toolkit",
    "silero-vad",
    "googletrans",
)


def say(text: str) -> None:
    print(text, flush=True)


def versions() -> dict:
    return {name: importlib.metadata.version(name) for name in PACKAGES}


def load_dump() -> list[DumpSegment]:
    arrays = np.load(DUMP.with_suffix(".npz"))
    index = json.loads(DUMP.with_suffix(".json").read_text(encoding="utf-8"))["segments"]
    return unpack_segments(arrays["audio"], arrays["offsets"], index)


def write_json(name: str, data: dict) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{name}.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    say(f"wrote {path.relative_to(ROOT)}")


class Gpu:
    """Used GPU memory of the full device, from `torch.cuda.mem_get_info()`."""

    def __init__(self) -> None:
        import torch

        self._torch = torch
        torch.cuda.init()
        self.base = self.used()
        self.peak = self.base

    def used(self) -> int:
        free, total = self._torch.cuda.mem_get_info()
        return (total - free) // MIB

    def sample(self) -> int:
        now = self.used()
        self.peak = max(self.peak, now)
        return now


# dump


def cmd_dump(args: argparse.Namespace) -> int:
    from tir_asr.segment.silero import SileroSpeechProbability

    params = Params()
    segments = []
    files = []
    for set_name, script, call, side, path in FILES:
        full = load_wav_16k(path)
        audio = cut_audio(full, S5_CUT_S.get(call))
        found = segment_file(audio, SileroSpeechProbability(), params)
        for n, s in enumerate(found):
            segments.append(
                DumpSegment(
                    id=f"{call}.{side}.{n:03d}",
                    set=set_name,
                    script=script,
                    call=call,
                    side=side,
                    start=s.start,
                    speech_end=s.speech_end,
                    cut=s.cut,
                    audio=s.audio,
                )
            )
        speech = sum(s.speech_end - s.start for s in found)
        files.append({"file": str(path.relative_to(ROOT)), "segments": len(found)})
        say(
            f"{path.relative_to(ROOT)}: {len(full) / SAMPLE_RATE:.1f} s, used "
            f"{len(audio) / SAMPLE_RATE:.1f} s; {len(found)} segments, {speech:.1f} s of speech, "
            f"{sum(s.cut for s in found)} hard cuts"
        )
        if call in S5_CUT_S:
            for s in found[-3:]:
                say(f"  last segments: {s.start:.2f}-{s.speech_end:.2f} s")
    audio, offsets, index = pack_segments(segments)
    DUMP.parent.mkdir(parents=True, exist_ok=True)
    np.savez(DUMP.with_suffix(".npz"), audio=audio, offsets=offsets)
    meta = {"parameters": parameter_lines(params), "files": files, "segments": index}
    DUMP.with_suffix(".json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    say(f"wrote {DUMP.relative_to(ROOT)}.npz and .json: {len(segments)} segments")
    return 0


# asr


def cmd_asr(args: argparse.Namespace) -> int:
    segments = load_dump()[: args.limit]
    gpu = Gpu()
    clock = time.perf_counter
    start = clock()
    from tir_asr.asr.ohanasr import MODEL_DIR, OhanasrTranscriber

    model = OhanasrTranscriber(ROOT / MODEL_DIR)  # the program adapter (D-081)

    def run(audio: np.ndarray) -> dict:
        return {"hy": model.transcribe(audio)}

    load_s = clock() - start
    loaded = gpu.sample()
    start = clock()
    run(np.zeros(int(WARMUP_AUDIO_S * SAMPLE_RATE), dtype=np.float32))
    warmup_s = clock() - start
    items = []
    for s in segments:
        start = clock()
        item = run(s.audio)
        item = {"id": s.id, **item, "seconds": clock() - start}
        gpu.sample()
        items.append(item)
        say(f"{s.id}: {item['seconds']:.3f} s: {item['hy']}")
    write_json(
        f"asr-{args.model}",
        {
            "model": args.model,
            "versions": versions(),
            "load_s": load_s,
            "warmup_s": warmup_s,
            "vram_base_mib": gpu.base,
            "vram_loaded_mib": loaded,
            "vram_peak_mib": gpu.peak,
            "segments": items,
        },
    )
    return 0


# mt


def mt_items(source: str, limit: int | None) -> list[dict]:
    """The texts to translate, grouped by conversation, each group in time order.

    Each item: id, group, speaker ("Me" or "Other"), hy (after the output rules), and for the
    reference input the reference English text.
    """
    if source == "reference":
        items = []
        for script in ("s1", "s2", "s3", "s5"):
            for line in read_references(SCRIPTS_MD, script):
                items.append(
                    {
                        "id": line.id,
                        "group": script,
                        "speaker": "Me" if line.side == "mic" else "Other",
                        "hy": line.hy,
                        "ref_en": line.en,
                    }
                )
        return items[:limit]
    asr = json.loads((OUT / f"{source}.json").read_text(encoding="utf-8"))
    texts = {item["id"]: item["hy"] for item in asr["segments"]}
    segments = [s for s in load_dump() if s.id in texts]
    segments.sort(key=lambda s: (s.call, s.start))
    items = [
        {
            "id": s.id,
            "group": s.call,
            "speaker": "Me" if s.side == "mic" else "Other",
            "hy": clean_armenian(texts[s.id]),
        }
        for s in segments
    ]
    return items[:limit]


def cmd_mt(args: argparse.Namespace) -> int:
    items = mt_items(args.input, args.limit)
    gpu = Gpu()
    clock = time.perf_counter
    start = clock()
    from tir_asr.mt.google import PARAMS, GoogleTranslator

    model = GoogleTranslator()  # the program adapter (D-081)
    extra = {
        "params": PARAMS,
        "service_urls": model.service_urls,
        "versions_mt": {
            name: importlib.metadata.version(name) for name in ("googletrans", "httpx")
        },
    }

    load_s = clock() - start
    loaded = gpu.sample()
    say(f"{args.model}: load {load_s:.1f} s, VRAM +{loaded - gpu.base} MiB, {extra}")
    start = clock()
    model.translate(WARMUP_TEXT)
    warmup_s = clock() - start
    out = []
    for item in items:
        if not item["hy"]:  # D-031: no MT call for an empty text
            out.append({"id": item["id"], "hy": "", "en": "", "seconds": 0.0})
            continue
        start = clock()
        en = model.translate(item["hy"])
        seconds = clock() - start
        gpu.sample()
        out.append({"id": item["id"], "hy": item["hy"], "en": en, "seconds": seconds})
        say(f"{item['id']}: {seconds:.3f} s: {en}")
    write_json(
        f"mt-{args.model}+{args.input}",
        {
            "model": args.model,
            "input": args.input,
            **extra,
            "versions": versions(),
            "load_s": load_s,
            "warmup_s": warmup_s,
            "vram_base_mib": gpu.base,
            "vram_loaded_mib": loaded,
            "vram_peak_mib": gpu.peak,
            "items": out,
        },
    )
    return 0


# report


def cmd_report(args: argparse.Namespace) -> int:
    meta = json.loads(DUMP.with_suffix(".json").read_text(encoding="utf-8"))
    index = meta["segments"]
    by_set = {name: [i for i in index if i["set"] == name] for name in SETS}
    audio_s = {name: sum(i["n"] for i in items) / SAMPLE_RATE for name, items in by_set.items()}
    lines = {s: read_references(SCRIPTS_MD, s) for s in ("s1", "s2", "s3", "s5")}
    ref_en = {line.id: line.en for script_lines in lines.values() for line in script_lines}
    report: list[str] = []

    def out(text: str = "") -> None:
        report.append(text)
        say(text)

    def segs(set_name: str) -> list[DumpSegment]:
        return [
            DumpSegment(
                id=i["id"],
                set=i["set"],
                script=i["script"],
                call=i["call"],
                side=i["side"],
                start=i["start"],
                speech_end=i["speech_end"],
                cut=i["cut"],
                audio=np.zeros(0, dtype=np.float32),
            )
            for i in by_set[set_name]
        ]

    def read(path: Path) -> dict:
        return json.loads(path.read_text(encoding="utf-8"))

    asr_runs = {p.stem.removeprefix("asr-"): read(p) for p in sorted(OUT.glob("asr-*.json"))}
    mt_runs = {p.stem.removeprefix("mt-"): read(p) for p in sorted(OUT.glob("mt-*.json"))}

    out(f"C9 report. Segments: {len(index)}; audio s: {audio_s}")
    out()
    out("ASR (output rules applied): set, WER %, CER %, model s per audio s, VRAM MiB")
    wer_of: dict[str, dict[str, float]] = {}
    asr_seconds: dict[str, dict[str, float]] = {}
    for name, run in asr_runs.items():
        texts = {i["id"]: clean_armenian(i["hy"]) for i in run["segments"]}
        wer_of[name], asr_seconds[name] = {}, {}
        vram = run["vram_peak_mib"] - run["vram_base_mib"]
        for set_name in SETS:
            score = score_hy(joined_texts(segs(set_name), texts), lines, SCRIPT_OF_CALL)
            ids = {i["id"] for i in by_set[set_name]}
            seconds = sum(i["seconds"] for i in run["segments"] if i["id"] in ids)
            wer_of[name][set_name] = score.wer
            asr_seconds[name][set_name] = seconds
            out(
                f"  {name:12} {set_name:6} WER {100 * score.wer:5.1f}  CER {100 * score.cer:5.1f}"
                f"  rtf {seconds / audio_s[set_name]:.3f}  vram +{vram}"
            )
    out()
    out("MT: model+input, set, chrF, model s per audio s (ASR + MT), flagged lines, VRAM MiB")
    chrf_of: dict[str, dict[str, float]] = {}
    flagged: dict[str, list[str]] = {}
    for name, run in mt_runs.items():
        en = {i["id"]: clean_english(i["en"]) for i in run["items"]}
        hy = {i["id"]: i["hy"] for i in run["items"]}
        vram = run["vram_peak_mib"] - run["vram_base_mib"]
        chrf_of[name] = {}
        if run["input"] == "reference":
            flagged[name] = [k for k, v in en.items() if is_flagged(v, ref_en=ref_en[k])]
            for set_name, scripts in (("s1-s3", ("s1", "s2", "s3")), ("s5", ("s5",))):
                refs, hyps = [], []
                for script in scripts:
                    for side in ("mic", "call"):
                        side_lines = [x for x in lines[script] if x.side == side]
                        refs.append(" ".join(x.en for x in side_lines))
                        hyps.append(" ".join(en.get(x.id, "") for x in side_lines).strip())
                chrf_of[name][set_name] = chrf(refs, hyps)
                out(f"  {name:32} {set_name:6} chrF {chrf_of[name][set_name]:5.1f}")
        else:
            asr = run["input"].removeprefix("asr-")
            flagged[name] = [k for k, v in en.items() if v and is_flagged(v, hy=hy[k])]
            for set_name in SETS:
                ids = {i["id"] for i in by_set[set_name]}
                score = score_en(joined_texts(segs(set_name), en), lines, SCRIPT_OF_CALL)
                chrf_of[name][set_name] = score
                mt_s = sum(i["seconds"] for i in run["items"] if i["id"] in ids)
                rtf = (asr_seconds[asr][set_name] + mt_s) / audio_s[set_name]
                out(f"  {name:32} {set_name:6} chrF {score:5.1f}  rtf {rtf:.3f}  vram +{vram}")
        out(f"  {name:32} flagged {len(flagged[name])}: {', '.join(flagged[name][:20])}")
    if "p4" in asr_runs:
        en = {i["id"]: clean_english(i.get("en", "")) for i in asr_runs["p4"]["segments"]}
        chrf_of["p4"] = {
            s: score_en(joined_texts(segs(s), en), lines, SCRIPT_OF_CALL) for s in SETS
        }
        for set_name in SETS:
            out(f"  {'p4 (end to end)':32} {set_name:6} chrF {chrf_of['p4'][set_name]:5.1f}")
    out()
    candidate = args.candidate
    p1_mt = "nllb-ct2+asr-nemo-rnnt"
    needed = ("ohanasr" in wer_of, "nemo-rnnt" in wer_of, "p4" in wer_of, candidate in mt_runs)
    if all(needed) and p1_mt in chrf_of:
        mt_run = mt_runs[candidate]
        asr_run = asr_runs["ohanasr"]
        vram = (
            (asr_run["vram_peak_mib"] - asr_run["vram_base_mib"])
            + (mt_run["vram_peak_mib"] - mt_run["vram_base_mib"])
            + max(asr_run["vram_base_mib"], mt_run["vram_base_mib"])
            + TITANET_MIB
        )
        rtf = 0.0
        for set_name in SETS:
            ids = {i["id"] for i in by_set[set_name]}
            mt_s = sum(i["seconds"] for i in mt_run["items"] if i["id"] in ids)
            rtf = max(rtf, (asr_seconds["ohanasr"][set_name] + mt_s) / audio_s[set_name])
        added = len(flagged[candidate]) if args.added_text is None else args.added_text
        result = check_rule(
            wer_new=wer_of["ohanasr"],
            wer_p1=wer_of["nemo-rnnt"],
            wer_p4=wer_of["p4"],
            chrf_new=chrf_of[candidate],
            chrf_p4=chrf_of["p4"],
            vram_mib=vram,
            rtf=rtf,
            added_text_lines=added,
        )
        out(f"Rule (D-072 part 3) for ohanasr + {candidate}:")
        out(f"  VRAM estimate {vram} MiB [calc: two processes, one base, TitaNet {TITANET_MIB}]")
        out(f"  model s per audio s {rtf:.3f}; added-text lines {added}")
        out(f"  P1 chrF (NeMo RNNT + NLLB): {chrf_of[p1_mt]}")
        out(f"  {result}")
    else:
        out(f"Rule: not checked; missing runs (ohanasr, nemo-rnnt, p4, {candidate}): {needed}")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "report.txt").write_text("\n".join(report) + "\n", encoding="utf-8")
    say(f"wrote {(OUT / 'report.txt').relative_to(ROOT)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="c9_run")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("dump")
    asr = sub.add_parser("asr")
    asr.add_argument("--model", choices=("ohanasr",), required=True)
    asr.add_argument("--limit", type=int, default=None)
    mt = sub.add_parser("mt")
    mt.add_argument("--model", choices=("google",), required=True)
    mt.add_argument("--input", required=True, help="reference, or asr-<model>")
    mt.add_argument("--limit", type=int, default=None)
    report = sub.add_parser("report")
    report.add_argument("--candidate", default="google+asr-ohanasr")
    report.add_argument("--added-text", type=int, default=None)
    args = parser.parse_args(argv)
    commands = {"dump": cmd_dump, "asr": cmd_asr, "mt": cmd_mt, "report": cmd_report}
    return commands[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
