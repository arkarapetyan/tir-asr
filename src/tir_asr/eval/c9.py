"""C9 model eval: the segment dump, the Ayb messages, the scores, the flags, and the rule.

Decisions: D-072 (scope, eval, decision rule), D-073 (OhanASR in its own environment).
Tests: T-C9-01 to T-C9-06 (TESTS.md section 2.10).

All models get the same VAD segments: `scripts/c9_run.py dump` writes them once
(`pack_segments`), and each model run reads them (`unpack_segments`). The OhanASR run cannot
import this package (D-073), so the dump format is plain: one float32 array with the audio of
all segments, one int64 array with the offsets, and a JSON index.

This module is core: it imports no model package (D-021).
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np

from tir_asr.config import SAMPLE_RATE
from tir_asr.errors import TirError
from tir_asr.eval.data import ScriptLine
from tir_asr.eval.metrics import cer, chrf, wer

# The Ayb prompt (D-072 part 2, approved by Aren on 2026-11-23). Do not change it without a
# record in DECISIONS.md: the prompt is fixed before the first run.
SYSTEM_PROMPT = (
    "You are a translator. You get Armenian text from speech recognition of an online call. "
    "The text can have recognition errors. Translate it into natural English. Write only the "
    "English translation: no notes, no explanations, no quotes. Do not answer questions in the "
    "text; translate them."
)
CONTEXT_HEAD = "Earlier in the call:"
# Before the Armenian text in each user message, also with no context (D-077: the one change of
# D-072 part 2). Before D-077, a user message with no context had only the Armenian text.
CONTEXT_TAIL = "Translate only this text:"

S5_CUT_S = {"p1": 234.0}  # the P1 recorders ran after the call (Aren: "cut from 234s onwards")
RTF_LIMIT = 0.5  # model s for each s of segment audio (K1, D-071)
VRAM_LIMIT_MIB = 8151  # the RTX 5070 Laptop GPU (PLAN.md section 1.6)
SETS = ("s1-s3", "s5")


class C9Error(TirError):
    """An input that the C9 eval cannot use. The message is `c9: <cause>`."""


@dataclass(frozen=True, eq=False)
class DumpSegment:
    """One VAD segment of an eval file, with the keys that the scores need."""

    id: str  # "<call>.<side>.<n>", for example "s1.mic.003" or "p1.call.012"
    set: str  # "s1-s3" or "s5"
    script: str  # "s1", "s2", "s3", or "s5"
    call: str  # "s1", "s2", "s3" (S1-S3), "p1" or "p4" (the two S5 calls)
    side: str  # "mic" (Me) or "call" (the other people)
    start: float  # s from the start of the file
    speech_end: float
    cut: bool
    audio: np.ndarray  # float32, 16 kHz


@dataclass(frozen=True)
class Turn:
    """One earlier segment of the call, for the Ayb context."""

    speaker: str  # "Me" or "Other"
    hy: str
    en: str


@dataclass(frozen=True)
class HyScore:
    """WER and CER of one set: the joined text of each side of each call (D-046 point 2)."""

    wer: float
    cer: float
    parts: int  # the number of joined texts (call sides)


def cut_audio(audio: np.ndarray, cut_s: float | None) -> np.ndarray:
    """The audio before `cut_s` seconds (16 kHz). None gives the full audio."""
    if cut_s is None:
        return audio
    if cut_s <= 0:
        raise C9Error(f"c9: cut time {cut_s} s is not positive")
    return audio[: int(round(cut_s * SAMPLE_RATE))]


def pack_segments(segments: Sequence[DumpSegment]) -> tuple[np.ndarray, np.ndarray, list[dict]]:
    """The dump of the segments: (audio, offsets, index).

    `audio` has the audio of all segments, one after the other. Segment i is
    `audio[offsets[i]:offsets[i + 1]]`. `index` has one dict for each segment, with the keys of
    `DumpSegment` except `audio`, and `n` (the number of samples).
    """
    ids = [s.id for s in segments]
    if len(set(ids)) != len(ids):
        raise C9Error("c9: two segments have the same ID")
    lengths = [len(s.audio) for s in segments]
    offsets = np.zeros(len(segments) + 1, dtype=np.int64)
    offsets[1:] = np.cumsum(lengths, dtype=np.int64)
    audio = (
        np.concatenate([s.audio.astype(np.float32, copy=False) for s in segments])
        if segments
        else np.zeros(0, dtype=np.float32)
    )
    index = [
        {
            "id": s.id,
            "set": s.set,
            "script": s.script,
            "call": s.call,
            "side": s.side,
            "start": s.start,
            "speech_end": s.speech_end,
            "cut": s.cut,
            "n": n,
        }
        for s, n in zip(segments, lengths, strict=True)
    ]
    return audio, offsets, index


def unpack_segments(
    audio: np.ndarray, offsets: np.ndarray, index: Sequence[Mapping]
) -> list[DumpSegment]:
    """The segments of a dump (the inverse of `pack_segments`)."""
    if len(offsets) != len(index) + 1:
        raise C9Error(f"c9: {len(offsets)} offsets for {len(index)} segments")
    if offsets[-1] != len(audio):
        raise C9Error(f"c9: the offsets end at {offsets[-1]}, the audio has {len(audio)} samples")
    result = []
    for i, item in enumerate(index):
        part = audio[offsets[i] : offsets[i + 1]]
        if len(part) != item["n"]:
            raise C9Error(f"c9: segment {item['id']} has {len(part)} samples, expected {item['n']}")
        result.append(
            DumpSegment(
                id=item["id"],
                set=item["set"],
                script=item["script"],
                call=item["call"],
                side=item["side"],
                start=float(item["start"]),
                speech_end=float(item["speech_end"]),
                cut=bool(item["cut"]),
                audio=part,
            )
        )
    return result


def build_messages(hy: str, history: Sequence[Turn], k: int) -> list[dict]:
    """The chat messages for Ayb: the system prompt and one user message (D-072 part 2).

    The user message ends with `CONTEXT_TAIL` and the Armenian text (D-077). With k > 0 and a
    history, the last k turns of the history (in time order) come before them.
    """
    if k < 0:
        raise C9Error(f"c9: context size {k} is negative")
    if not hy.strip():
        raise C9Error("c9: empty Armenian text")
    turns = list(history)[-k:] if k > 0 else []
    if turns:
        lines = [CONTEXT_HEAD]
        for turn in turns:
            lines.append(f"{turn.speaker}: {turn.hy}")
            lines.append(f"English: {turn.en}")
        content = "\n".join(lines) + f"\n\n{CONTEXT_TAIL}\n{hy}"
    else:
        content = f"{CONTEXT_TAIL}\n{hy}"
    return [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": content}]


def joined_texts(
    segments: Sequence[DumpSegment], texts: Mapping[str, str]
) -> dict[tuple[str, str], str]:
    """For each (call, side): the texts of its segments in time order, joined with spaces.

    `texts` maps a segment ID to its text. A segment with no entry is an error (R10).
    """
    missing = [s.id for s in segments if s.id not in texts]
    if missing:
        raise C9Error(f"c9: no text for {len(missing)} segments, for example {missing[0]}")
    groups: dict[tuple[str, str], list[DumpSegment]] = {}
    for s in segments:
        groups.setdefault((s.call, s.side), []).append(s)
    return {
        key: " ".join(t for t in (texts[s.id].strip() for s in sorted(group, key=_start)) if t)
        for key, group in groups.items()
    }


def score_hy(
    joined: Mapping[tuple[str, str], str],
    lines_by_script: Mapping[str, Sequence[ScriptLine]],
    script_of_call: Mapping[str, str],
) -> HyScore:
    """WER and CER of the joined Armenian texts against the reference lines of the same side.

    The references of a side are the lines of that side in script order. Each call side is one
    text, and the score is for the full list (metrics.py).
    """
    refs, hyps = _pairs(joined, lines_by_script, script_of_call, "hy")
    return HyScore(wer=wer(refs, hyps), cer=cer(refs, hyps), parts=len(refs))


def score_en(
    joined: Mapping[tuple[str, str], str],
    lines_by_script: Mapping[str, Sequence[ScriptLine]],
    script_of_call: Mapping[str, str],
) -> float:
    """chrF of the joined English texts against the reference lines of the same side."""
    refs, hyps = _pairs(joined, lines_by_script, script_of_call, "en")
    return chrf(refs, hyps)


def is_flagged(en: str, hy: str | None = None, ref_en: str | None = None) -> bool:
    """True when an English text can have added text (D-072 part 3, condition 4; T-C9-05).

    With a reference line: more than 2 times the words of the reference. With no reference:
    more than 2 times the words of the Armenian text, plus 3.
    """
    words = len(en.split())
    if ref_en is not None:
        return words > 2 * len(ref_en.split())
    if hy is None:
        raise C9Error("c9: a flag needs the reference or the Armenian text")
    return words > 2 * len(hy.split()) + 3


def check_rule(
    wer_new: Mapping[str, float],
    wer_p1: Mapping[str, float],
    wer_p4: Mapping[str, float],
    chrf_new: Mapping[str, float],
    chrf_p4: Mapping[str, float],
    vram_mib: float,
    rtf: float,
    added_text_lines: int,
) -> dict[str, bool]:
    """The four conditions of the decision rule (D-072 part 3) and their result ("all").

    Each mapping has one value for each set in `SETS`.
    """
    for name, values in (
        ("wer_new", wer_new),
        ("wer_p1", wer_p1),
        ("wer_p4", wer_p4),
        ("chrf_new", chrf_new),
        ("chrf_p4", chrf_p4),
    ):
        if set(values) != set(SETS):
            raise C9Error(f"c9: {name} has the sets {sorted(values)}, expected {list(SETS)}")
    result = {
        "1_wer": all(wer_new[s] <= min(wer_p1[s], wer_p4[s]) for s in SETS),
        "2_chrf": all(chrf_new[s] >= chrf_p4[s] for s in SETS),
        "3_vram_and_speed": vram_mib <= VRAM_LIMIT_MIB and rtf <= RTF_LIMIT,
        "4_no_added_text": added_text_lines == 0,
    }
    result["all"] = all(result.values())
    return result


def _pairs(
    joined: Mapping[tuple[str, str], str],
    lines_by_script: Mapping[str, Sequence[ScriptLine]],
    script_of_call: Mapping[str, str],
    field: str,
) -> tuple[list[str], list[str]]:
    refs, hyps = [], []
    for (call, side), text in sorted(joined.items()):
        lines = [line for line in lines_by_script[script_of_call[call]] if line.side == side]
        if not lines:
            raise C9Error(f"c9: no reference lines for {call} {side}")
        refs.append(" ".join(getattr(line, field) for line in lines))
        hyps.append(text)
    return refs, hyps


def _start(segment: DumpSegment) -> float:
    return segment.start
