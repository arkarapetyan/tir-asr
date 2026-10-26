"""Bake-off core: segments, ASR and MT calls, and scores for one side file (D-046, D-051).

This module imports no model package (D-021): the caller gives the VAD, the transcriber, and
the translator. The segments come from the program's Endpointer with `Params()`. Frame k gets
the arrival time (k + 1) * 0.032 s, so all segment times are audio times (seconds from the
start of the file), the same as the label times.
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass

import numpy as np

from tir_asr.config import SAMPLE_RATE, VAD_FRAME, Params
from tir_asr.eval.data import Label, ScriptLine, assign_segments, with_end_silence
from tir_asr.eval.metrics import cer, chrf, digit_words, wer
from tir_asr.segment.endpoint import FRAME_S, Endpointer
from tir_asr.types import AudioBlock, Segment, SpeechProbability, Transcriber, Translator


@dataclass(frozen=True)
class Timed:
    text: str
    seconds: float


@dataclass(frozen=True)
class LineScore:
    id: str
    segments: int
    wer: float
    chrf: float


@dataclass(frozen=True)
class SideScore:
    wer: float  # joined text (D-046 point 2)
    cer: float
    chrf: float
    digit_words: int
    segments: int
    outside: int  # segments with no label overlap (line view)
    lines: list[LineScore]  # line view (D-046 point 3)
    audio_s: float  # total audio of the segments
    asr_rtf: float
    asr_mean_s: float
    asr_max_s: float
    mt_calls: int
    mt_mean_s: float
    mt_max_s: float


def segment_file(
    audio: np.ndarray, vad: SpeechProbability, params: Params, source: str = "eval"
) -> list[Segment]:
    """The segments of one file, with the end rule of D-048 (1.0 s of zeros at the end)."""
    endpointer = Endpointer(params, vad)
    padded = with_end_silence(audio)
    whole = len(padded) // VAD_FRAME * VAD_FRAME
    segments = []
    for k, frame in enumerate(padded[:whole].reshape(-1, VAD_FRAME)):
        segment = endpointer.push(
            AudioBlock(source=source, samples=frame, arrival=(k + 1) * FRAME_S)
        )
        if segment is not None:
            segments.append(segment)
    return segments


def transcribe_all(
    segments: Sequence[Segment], transcriber: Transcriber, clock: Callable[[], float]
) -> list[Timed]:
    """One ASR call for each segment, with the time of the call."""
    result = []
    for segment in segments:
        start = clock()
        text = transcriber.transcribe(segment.audio)
        result.append(Timed(text, clock() - start))
    return result


def translate_all(
    texts: Sequence[str], translator: Translator, clock: Callable[[], float]
) -> list[Timed]:
    """One MT call for each non-empty text. An empty text gets no call (D-031): "" and 0.0 s."""
    result = []
    for text in texts:
        if not text.strip():
            result.append(Timed("", 0.0))
            continue
        start = clock()
        english = translator.translate(text)
        result.append(Timed(english, clock() - start))
    return result


def score_side(
    lines: Sequence[ScriptLine],
    labels: Sequence[Label],
    segments: Sequence[Segment],
    hy: Sequence[str],
    en: Sequence[str],
    asr_s: Sequence[float],
    mt_s: Sequence[float],
) -> SideScore:
    """Scores of one side file. `hy`, `en`, `asr_s`, and `mt_s` have one value for each segment."""
    joined = " ".join
    main_wer = wer([joined(line.hy for line in lines)], [joined(hy)])
    main_cer = cer([joined(line.hy for line in lines)], [joined(hy)])
    main_chrf = chrf([joined(line.en for line in lines)], [joined(en)])

    owners = assign_segments([(s.start, s.speech_end) for s in segments], labels)
    line_scores = []
    for line in lines:
        mine = [i for i, owner in enumerate(owners) if owner == line.id]
        line_scores.append(
            LineScore(
                id=line.id,
                segments=len(mine),
                wer=wer([line.hy], [joined(hy[i] for i in mine)]),
                chrf=chrf([line.en], [joined(en[i] for i in mine)]),
            )
        )

    audio_s = sum(len(s.audio) for s in segments) / SAMPLE_RATE
    mt_times = [t for t, text in zip(mt_s, hy, strict=True) if text.strip()]
    return SideScore(
        wer=main_wer,
        cer=main_cer,
        chrf=main_chrf,
        digit_words=digit_words(hy),
        segments=len(segments),
        outside=sum(owner is None for owner in owners),
        lines=line_scores,
        audio_s=audio_s,
        asr_rtf=sum(asr_s) / audio_s if audio_s else 0.0,
        asr_mean_s=sum(asr_s) / len(asr_s) if asr_s else 0.0,
        asr_max_s=max(asr_s, default=0.0),
        mt_calls=len(mt_times),
        mt_mean_s=sum(mt_times) / len(mt_times) if mt_times else 0.0,
        mt_max_s=max(mt_times, default=0.0),
    )
