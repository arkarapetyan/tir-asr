"""C11 speaker replay (D-083): the decision log, the 2-D grid, and the decision rule. Model level.

Subcommands:

  embed --name <name> ...  for each name: the segments with `Params()` and Silero (as
                           `c9_run.py dump`), the OhanASR text of each segment, and a TitaNet
                           embedding for each segment with a text  -> data/c11/replay/<name>.*
  grid                     the grid on all saved names, with no model
                           -> test-results/c11/grid.{txt,json}

Names (D-083 part 3):
  p1, p4   data/c7/<name>.system.wav (p1 is cut at 234 s, D-072): one person on the call side
  r1, r2   data/c11/<name>.system.wav: one person on the call side
  s1, s2, s3, d   the eval streams of C5 (D-057 part 1), with the true speakers from the labels

A segment gets its text as in the program: the text step applies the output rules
(`clean_armenian`, D-066), and a segment with an empty text gets no speaker step (D-031,
D-059 point 3A). Thus only a segment with a text gets an embedding and goes to the clusterer.

Examples (nothing downloads):
  HF_HUB_OFFLINE=1 uv run --no-sync python scripts/c11_spk.py embed --name p1 p4 s1 s2 s3 d
  uv run --no-sync python scripts/c11_spk.py grid
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
from tir_asr.eval.c9 import S5_CUT_S, cut_audio
from tir_asr.eval.data import load_wav_16k, read_labels, read_references
from tir_asr.eval.run import segment_file
from tir_asr.eval.spk_replay import (
    GRID_MIN_NEW_S,
    GRID_THRESHOLDS,
    ONE_PERSON,
    decisions,
    grid,
    select,
)
from tir_asr.eval.spk_run import Embedded, truth_of
from tir_asr.eval.streams import Turn, call_stream, stream_d
from tir_asr.text.clean import clean_armenian

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "eval" / "raw"
SCRIPTS_MD = ROOT / "docs" / "eval" / "scripts.md"
C7 = ROOT / "data" / "c7"
C11 = ROOT / "data" / "c11"
REPLAY = C11 / "replay"
OUT = ROOT / "test-results" / "c11"
ONE_PERSON_FILES = {
    "p1": C7 / "p1.system.wav",
    "p4": C7 / "p4.system.wav",
    "r1": C11 / "r1.system.wav",
    "r2": C11 / "r2.system.wav",
}
SCRIPTS = ("s1", "s2", "s3")
D_NAME = "d"
EVAL_NAMES = (*SCRIPTS, D_NAME)
NAMES = (*ONE_PERSON_FILES, *EVAL_NAMES)
PACKAGES = ("tir-asr", "torch", "omnilingual-asr", "fairseq2", "nemo-toolkit", "silero-vad")
TEXT_CHARS = 60  # the length of the text in a line of the decision log


def say(text: str = "") -> None:
    print(text, flush=True)


def inputs(name: str) -> list[Path]:
    """The input files of a name."""
    if name in ONE_PERSON_FILES:
        return [ONE_PERSON_FILES[name]]
    scripts = SCRIPTS if name == D_NAME else (name,)
    return [
        SCRIPTS_MD,
        *[RAW / f"{s}.call.wav" for s in scripts],
        *[RAW / f"{s}.labels.txt" for s in scripts],
    ]


def load(name: str) -> tuple[np.ndarray, list[Turn] | None]:
    """The audio of a name, and the turns of an eval stream (None for a one-person stream)."""
    if name in ONE_PERSON_FILES:
        return cut_audio(load_wav_16k(ONE_PERSON_FILES[name]), S5_CUT_S.get(name)), None
    calls = {}
    for script in SCRIPTS if name == D_NAME else (name,):
        lines = read_references(SCRIPTS_MD, script)
        labels = read_labels(RAW / f"{script}.labels.txt", lines)
        audio = load_wav_16k(RAW / f"{script}.call.wav")
        calls[script] = call_stream(script, audio, lines, labels)
    stream = stream_d(calls["s1"], calls["s2"], calls["s3"]) if name == D_NAME else calls[name]
    return stream.audio, stream.turns


def clock_text(seconds: float) -> str:
    """hh:mm:ss.s, to compare with the block times of the program output."""
    minutes, rest = divmod(seconds, 60.0)
    hours, minutes = divmod(int(minutes), 60)
    return f"{hours:02d}:{minutes:02d}:{rest:04.1f}"


def num(value: float | None) -> str:
    return "  -  " if value is None else f"{value:.3f}"


# embed


def cmd_embed(args: argparse.Namespace) -> int:
    missing = [str(p.relative_to(ROOT)) for name in args.name for p in inputs(name)]
    missing = [p for p in dict.fromkeys(missing) if not (ROOT / p).exists()]
    if missing:  # R10: a missing input file is an error
        raise SystemExit(f"c11_spk: missing input files: {', '.join(missing)}")
    params = Params()
    clock = time.perf_counter
    start = clock()
    from tir_asr.asr.ohanasr import MODEL_DIR, OhanasrTranscriber

    transcriber = OhanasrTranscriber(ROOT / MODEL_DIR)  # the program adapter (D-081)
    from tir_asr.speakers.titanet import TitanetEmbedder

    embedder = TitanetEmbedder()  # the program adapter (D-058)
    zeros = np.zeros(int(WARMUP_AUDIO_S * SAMPLE_RATE), dtype=np.float32)
    transcriber.transcribe(zeros)
    embedder.embed(zeros)
    say(f"models: load and warm-up {clock() - start:.1f} s")
    # The VAD loads last, as in the program (D-043): silero_vad sets the CPU threads at import.
    from tir_asr.segment.silero import SileroSpeechProbability

    versions = {name: importlib.metadata.version(name) for name in PACKAGES}
    REPLAY.mkdir(parents=True, exist_ok=True)
    for name in args.name:
        audio, turns = load(name)
        segments = segment_file(audio, SileroSpeechProbability(), params)
        rows, vectors = [], []
        for n, s in enumerate(segments):
            start = clock()
            hy = clean_armenian(transcriber.transcribe(s.audio))  # as TextStep.process (D-066)
            row = {
                "n": n,
                "start": s.start,
                "speech_end": s.speech_end,
                "duration_s": s.speech_end - s.start,
                "cut": s.cut,
                "hy": hy,
                "asr_s": clock() - start,
                "embedded": bool(hy),  # D-059 point 3A: no speaker step for an empty text
                "embed_s": None,
                "truth": None,
            }
            if hy:
                start = clock()
                vectors.append(np.asarray(embedder.embed(s.audio), dtype=np.float32))
                row["embed_s"] = clock() - start
                if turns is None:
                    row["truth"] = ONE_PERSON
                else:
                    row["truth"] = truth_of(s.start, s.speech_end, turns)
            rows.append(row)
            say(f"{name} {n:4d} {clock_text(s.start)} {row['duration_s']:5.2f} s: {hy or '-'}")
        embeddings = np.stack(vectors) if vectors else np.zeros((0, 0), dtype=np.float32)
        np.savez(REPLAY / f"{name}.npz", embeddings=embeddings)
        meta = {
            "name": name,
            "files": [str(p.relative_to(ROOT)) for p in inputs(name)],
            "audio_s": len(audio) / SAMPLE_RATE,
            "cut_s": S5_CUT_S.get(name),
            "parameters": parameter_lines(params),
            "versions": versions,
            "segments": rows,
        }
        path = REPLAY / f"{name}.json"
        path.write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
        speech = sum(r["duration_s"] for r in rows if r["embedded"])
        say(
            f"{name}: {meta['audio_s']:.1f} s of audio; {len(rows)} segments, {len(vectors)} with"
            f" a text ({speech:.1f} s of speech); wrote {path.relative_to(ROOT)} and .npz"
        )
    return 0


# grid


def cmd_grid(args: argparse.Namespace) -> int:
    params = Params()
    program = (params.spk_min_new_s, params.spk_threshold)  # (min_new_s, threshold)
    saved = [name for name in NAMES if (REPLAY / f"{name}.json").exists()]
    if not saved:
        raise SystemExit("c11_spk: no saved names in data/c11/replay; run `embed` first")
    report: list[str] = []

    def out(text: str = "") -> None:
        report.append(text)
        say(text)

    streams = {}
    for name in saved:
        meta = json.loads((REPLAY / f"{name}.json").read_text(encoding="utf-8"))
        embeddings = np.load(REPLAY / f"{name}.npz")["embeddings"]
        rows = [r for r in meta["segments"] if r["embedded"]]
        items = [
            Embedded(e, r["embed_s"], r["duration_s"], r["truth"])
            for e, r in zip(embeddings, rows, strict=True)
        ]
        streams[name] = (meta, rows, items)

    out("C11 speaker replay (D-083).")
    values = f"spk_threshold {params.spk_threshold}, spk_min_new_s {params.spk_min_new_s}"
    out(f"Program values: {values}")
    out("name, kind, segments, segments with a text, speech s with a text, files")
    for name, (meta, rows, _) in streams.items():
        kind = "one person" if name in ONE_PERSON_FILES else "eval"
        speech = sum(r["duration_s"] for r in rows)
        out(
            f"  {name:3} {kind:10} {len(meta['segments']):4d} {len(rows):4d} {speech:8.1f}"
            f"  {', '.join(meta['files'])}"
        )

    points = {
        name: grid(items, GRID_THRESHOLDS, GRID_MIN_NEW_S)
        for name, (_, _, items) in streams.items()
    }
    out()
    out("Grid. One person: labels / share of the largest label. Eval: wrong / scored (labels).")
    out("min_new_s  threshold  " + "  ".join(f"{name:>14}" for name in points))
    first = next(iter(points.values()))
    for k, key_point in enumerate(first):
        cells = []
        for name, column in points.items():
            p = column[k].point
            if name in ONE_PERSON_FILES:
                cells.append(f"{p.speakers} / {100 * p.accuracy_time:5.1f}%")
            else:
                cells.append(f"{p.wrong}/{p.scored} ({p.speakers})")
        out(
            f"{key_point.min_new_s:9.1f}  {key_point.point.threshold:9.2f}  "
            + "  ".join(f"{cell:>14}" for cell in cells)
        )

    one = {name: column for name, column in points.items() if name in ONE_PERSON_FILES}
    evals = {name: column for name, column in points.items() if name not in ONE_PERSON_FILES}
    missing = [name for name in EVAL_NAMES if name not in evals]
    out()
    selection = None
    if not one or missing:
        out(f"Rule (D-083 part 4): not checked; missing: {missing or 'a one-person stream'}")
    else:
        selection = select(one, evals, D_NAME)
        out(f"Rule (D-083 part 4) on {', '.join(points)}:")
        out(f"  passing (min_new_s, threshold): {selection.passing}")
        out(f"  chosen: {selection.chosen}")
        if "r1" not in one:
            out("  Not final: M3 (r1) is not in this run (D-083 part 3).")

    log_points = [program]
    if selection is not None and selection.chosen not in (None, program):
        log_points.append(selection.chosen)
    logs = {}
    for name in one:
        _, rows, items = streams[name]
        for min_new_s, threshold in log_points:
            result = decisions(items, threshold, min_new_s)
            logs[f"{name} {threshold} {min_new_s}"] = [asdict(d) for d in result]
            out()
            out(f"Decision log {name}, spk_threshold {threshold}, spk_min_new_s {min_new_s}:")
            out("     n  start        length  label         kind   best   second text")
            for r, d in zip(rows, result, strict=True):
                out(
                    f"  {r['n']:4d}  {clock_text(r['start'])}  {r['duration_s']:5.2f} s"
                    f"  {str(d.label):12}  {d.kind:5}  {num(d.best)}  {num(d.second)}"
                    f"  {r['hy'][:TEXT_CHARS]}"
                )

    OUT.mkdir(parents=True, exist_ok=True)
    data = {
        "parameters": parameter_lines(params),
        "names": {name: meta["files"] for name, (meta, _, _) in streams.items()},
        "grid": {name: [asdict(p) for p in column] for name, column in points.items()},
        "selection": None if selection is None else asdict(selection),
        "logs": logs,
    }
    (OUT / "grid.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    (OUT / "grid.txt").write_text("\n".join(report) + "\n", encoding="utf-8")
    say(f"wrote {(OUT / 'grid.txt').relative_to(ROOT)} and grid.json")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="c11_spk")
    sub = parser.add_subparsers(dest="command", required=True)
    embed = sub.add_parser("embed")
    embed.add_argument("--name", nargs="+", choices=NAMES, required=True)
    sub.add_parser("grid")
    args = parser.parse_args(argv)
    commands = {"embed": cmd_embed, "grid": cmd_grid}
    return commands[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
