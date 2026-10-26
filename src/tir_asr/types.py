"""Data types and interfaces of the core (ARCHITECTURE.md section 3).

All times are `time.monotonic()` values in seconds. All audio is float32, mono, 16 kHz,
normally in [-1, 1]; a loud input can give values a little outside (D-041). This module imports
no model and no audio-device package (D-021).
"""

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Protocol

import numpy as np


@dataclass(frozen=True, eq=False)
class AudioBlock:
    """One VAD frame of 512 samples (32 ms) and its arrival time."""

    source: str  # source label: "Me" or "System" (D-054)
    samples: np.ndarray  # shape (512,)
    arrival: float


@dataclass(frozen=True, eq=False)
class Segment:
    """One speech segment, closed by the Endpointer."""

    source: str
    audio: np.ndarray  # speech with the pads (ARCHITECTURE.md section 2.2, rule 6)
    start: float  # start of speech (no pad)
    speech_end: float  # true end of speech (D-023)
    closed: float  # time when the Endpointer closed the segment
    cut: bool  # True for a hard cut at the maximum length (rule 5)


@dataclass(frozen=True)
class Line:
    """One output block: the texts and the times of ARCHITECTURE.md section 2.5."""

    label: str  # the source label "Me" or "System" (C4); "Speaker N" (C5)
    start: float  # Segment.start
    hy: str  # Armenian text
    en: str  # English text
    speech_end: float
    closed: float
    asr_end: float
    mt_end: float
    write: float


class AudioSource(Protocol):
    label: str  # the source label of its blocks; the name of its capture thread (D-054)

    def blocks(self) -> Iterator[AudioBlock]: ...


class SpeechProbability(Protocol):
    def __call__(self, samples: np.ndarray) -> float: ...


class Transcriber(Protocol):
    def transcribe(self, audio: np.ndarray) -> str: ...


class Translator(Protocol):
    def translate(self, text: str) -> str: ...
