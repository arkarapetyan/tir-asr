"""Eval streams for the speaker labels (D-057, part 1). The program does not use this module.

A stream is the audio of the call side and its turns: the time of each call-side line and its
true speaker. The true speaker is `<script>/<speaker>`, for example `s1/Speaker 1`, because the
speakers of different scripts are different people (Aren, C5). The lines of "Me" are not turns:
the call file has no echo of the microphone side (D-046).

Stream D tests that a person keeps one label for the full session: the S1 call from 0 to
`STREAM_D_CUT_S`, then the S2 call, then the S1 call from `STREAM_D_CUT_S` to the end, then the
S3 call. The two S1 voices come back after a new voice. A cut inside a turn stops with an error.
"""

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from tir_asr.config import SAMPLE_RATE
from tir_asr.eval.data import DataError, Label, ScriptLine

STREAM_D_CUT_S = 34.0  # s; in the 7.3 s silence of the S1 call side after s1-06 (D-057)


@dataclass(frozen=True)
class Turn:
    start: float  # s from the start of the stream
    end: float
    speaker: str  # the true speaker: "<script>/<speaker>"


@dataclass(frozen=True, eq=False)
class Stream:
    name: str
    audio: np.ndarray  # float32, 16 kHz
    turns: list[Turn]  # in time order


def call_stream(
    script: str, audio: np.ndarray, lines: Sequence[ScriptLine], labels: Sequence[Label]
) -> Stream:
    """The call side of one script as a stream. Only the call-side lines become turns."""
    speakers = {line.id: f"{script}/{line.speaker}" for line in lines if line.side == "call"}
    turns = [
        Turn(label.start, label.end, speakers[label.id]) for label in labels if label.id in speakers
    ]
    return Stream(script, audio, sorted(turns, key=lambda turn: turn.start))


def cut(stream: Stream, start_s: float, end_s: float | None, name: str) -> Stream:
    """The part of a stream from `start_s` to `end_s` (None: to the end).

    The turn times shift by `start_s`. A turn across a cut point stops with `DataError`.
    """
    length_s = len(stream.audio) / SAMPLE_RATE
    end_s = length_s if end_s is None else end_s
    turns = []
    for turn in stream.turns:
        for point in (start_s, end_s):
            if turn.start < point < turn.end:
                raise DataError(
                    f"data: {stream.name}: the cut at {point:.2f} s is inside a turn "
                    f"({turn.start:.2f}–{turn.end:.2f} s)"
                )
        if turn.start >= start_s and turn.end <= end_s:
            turns.append(Turn(turn.start - start_s, turn.end - start_s, turn.speaker))
    first = round(start_s * SAMPLE_RATE)
    last = round(end_s * SAMPLE_RATE)
    return Stream(name, stream.audio[first:last], turns)


def join(streams: Sequence[Stream], name: str) -> Stream:
    """The streams one after the other. The turn times shift by the start of each part."""
    turns = []
    offset = 0.0
    for stream in streams:
        turns += [Turn(t.start + offset, t.end + offset, t.speaker) for t in stream.turns]
        offset += len(stream.audio) / SAMPLE_RATE
    audio = np.concatenate([stream.audio for stream in streams]).astype(np.float32, copy=False)
    return Stream(name, audio, turns)


def stream_d(s1: Stream, s2: Stream, s3: Stream) -> Stream:
    """Stream D (D-057, part 1): S1 to the cut, S2, S1 from the cut, S3."""
    return join(
        [
            cut(s1, 0.0, STREAM_D_CUT_S, "s1a"),
            s2,
            cut(s1, STREAM_D_CUT_S, None, "s1b"),
            s3,
        ],
        "D",
    )
