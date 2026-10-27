"""The text step of one segment: Template Method for P1 and P4 (ARCHITECTURE.md section 2.9).

Decisions: D-031, D-053 (addition), D-062 part 2, D-063 part 2. `TextStep.process` and
`TextStep.warm_up` are the template methods. They fix the order of the steps, the empty-text
rule (D-031), and the clock reads, the same for P1 and P4. A subclass gives only the hooks:
`_prepare` (default: the audio, with no work), `_armenian`, and `_english`. A subclass does not
define `process` or `warm_up` (T-TEXT-04). `STEPS` gives the names of the text steps on the
latency line: two names (P1: `asr`, `mt`), or one name when one step gives both texts (P4:
`s2t`, D-063 part 2).

This module is core: it imports no model package (D-021). `CascadeTextStep` (P1) gets its
adapters as arguments. The P4 subclass is an adapter in its own file (`text/seamless.py`).
"""

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any

import numpy as np

from tir_asr.config import WARMUP_TEXT
from tir_asr.errors import TirError
from tir_asr.types import TextResult, Transcriber, Translator

Clock = Callable[[], float]


class TextError(TirError):
    """An error of a text step adapter. The message is `text: <cause>`."""


class TextStep(ABC):
    """The Armenian text, then the English text, of the audio of one segment."""

    STEPS: tuple[str, ...] = ("asr", "mt")  # the names on the latency line (D-063 part 2)

    def process(self, audio: np.ndarray, clock: Clock) -> TextResult:
        """The texts of one segment. The clock gives the end of each of the two steps.

        An empty Armenian text gets no English step: the English text is "", and the end of the
        English step is the end of the Armenian step (D-031). An error of a hook goes up with no
        change (R10).
        """
        state = self._prepare(audio)
        hy = self._armenian(state)
        asr_end = clock()
        if not hy:
            return TextResult(hy=hy, en="", asr_end=asr_end, mt_end=asr_end)
        en = self._english(state, hy)
        mt_end = clock()
        return TextResult(hy=hy, en=en, asr_end=asr_end, mt_end=mt_end)

    def warm_up(self, audio: np.ndarray, clock: Clock) -> TextResult:
        """One call of each model path with a synthetic input (D-022, D-037).

        The English step always runs, with `WARMUP_TEXT` as the Armenian text, also when the
        audio (zeros) gives no Armenian text. P1 translates `WARMUP_TEXT`; P4 does not use it.
        """
        state = self._prepare(audio)
        hy = self._armenian(state)
        asr_end = clock()
        en = self._english(state, WARMUP_TEXT)
        mt_end = clock()
        return TextResult(hy=hy, en=en, asr_end=asr_end, mt_end=mt_end)

    def _prepare(self, audio: np.ndarray) -> Any:
        """The state that `_armenian` and `_english` get. Default: the audio, with no work."""
        return audio

    @abstractmethod
    def _armenian(self, state: Any) -> str:
        """The Armenian text of the segment. It can be empty."""

    @abstractmethod
    def _english(self, state: Any, hy: str) -> str:
        """The English text of the segment. `hy` is the Armenian text, which is not empty."""


class CascadeTextStep(TextStep):
    """P1: the ASR adapter gives the Armenian text, and the MT adapter translates it (D-014)."""

    def __init__(self, transcriber: Transcriber, translator: Translator) -> None:
        self._transcriber = transcriber
        self._translator = translator

    def _armenian(self, state: np.ndarray) -> str:
        return self._transcriber.transcribe(state)

    def _english(self, state: np.ndarray, hy: str) -> str:
        return self._translator.translate(hy)
