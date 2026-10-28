"""T-TEXT-01 to T-TEXT-07: the text step, Template Method for P1 and P4 (C6, `c6-textstep`).

Contract: ARCHITECTURE.md section 2.9. Decisions: D-022, D-031, D-037, D-062 part 2. A recorder
subclass of `TextStep` records each hook call. Its `_prepare` gives a new state object at each
call, so that a test sees which state each hook gets. The fake clock fails when the text step
reads it more often than the contract says. T-TEXT-06 and T-TEXT-07 (C7, `c7-p4`, D-066) test the
output rules of `text/clean.py` and their place in the template.
"""

import numpy as np
import pytest

from tir_asr.config import SAMPLE_RATE, WARMUP_AUDIO_S, WARMUP_TEXT
from tir_asr.errors import TirError
from tir_asr.text.clean import FOREIGN, clean_armenian, clean_english
from tir_asr.text.step import CascadeTextStep, TextStep
from tir_asr.types import TextResult


class FakeClock:
    def __init__(self, values: list[float]):
        self.values = list(values)

    def __call__(self) -> float:
        assert self.values, "the fake clock has no more values"
        return self.values.pop(0)


class FakeAsrError(TirError):
    """An error with the message format of AsrError (the real class needs `torch`)."""


class Recorder(TextStep):
    """Records the hook calls. `hy` and `en` are the texts; an error replaces a text."""

    def __init__(self, hy="բարև", en="hi", hy_error=None, en_error=None):
        self.hy, self.en = hy, en
        self.hy_error, self.en_error = hy_error, en_error
        self.calls = []
        self.states = []

    def _prepare(self, audio):
        state = object()
        self.states.append(state)
        self.calls.append(("prepare", audio))
        return state

    def _armenian(self, state):
        self.calls.append(("armenian", state))
        if self.hy_error is not None:
            raise self.hy_error
        return self.hy

    def _english(self, state, hy):
        self.calls.append(("english", state, hy))
        if self.en_error is not None:
            raise self.en_error
        return self.en


class FakeTranscriber:
    def __init__(self, texts: list[str]):
        self.texts = list(texts)
        self.calls = []

    def transcribe(self, audio: np.ndarray) -> str:
        self.calls.append(audio)
        return self.texts.pop(0)


class FakeTranslator:
    def __init__(self, text: str = "hi"):
        self.text = text
        self.calls = []

    def translate(self, text: str) -> str:
        self.calls.append(text)
        return self.text


def zeros() -> np.ndarray:
    return np.zeros(int(WARMUP_AUDIO_S * SAMPLE_RATE), dtype=np.float32)


def test_text_01_template_order_and_clock_reads():
    step = Recorder()
    audio = np.ones(16_000, dtype=np.float32)
    clock = FakeClock([1.0, 2.0])

    result = step.process(audio, clock)

    state = step.states[0]
    assert len(step.calls) == 3
    assert step.calls[0][0] == "prepare" and step.calls[0][1] is audio
    assert step.calls[1] == ("armenian", state)
    assert step.calls[2] == ("english", state, "բարև")
    assert result == TextResult(hy="բարև", en="hi", asr_end=1.0, mt_end=2.0)
    assert clock.values == []  # 2 reads


def test_text_02_empty_armenian_text_gets_no_english_step():
    step = Recorder(hy="")
    clock = FakeClock([1.0])

    result = step.process(np.ones(16_000, dtype=np.float32), clock)

    assert [call[0] for call in step.calls] == ["prepare", "armenian"]
    assert result == TextResult(hy="", en="", asr_end=1.0, mt_end=1.0)
    assert clock.values == []  # 1 read


def test_text_03_warm_up_runs_the_english_step_also_with_no_armenian_text():
    step = Recorder(hy="")
    audio = zeros()
    clock = FakeClock([10.4, 10.5])

    result = step.warm_up(audio, clock)

    state = step.states[0]
    assert step.calls[0][0] == "prepare" and step.calls[0][1] is audio
    assert step.calls[1:] == [("armenian", state), ("english", state, WARMUP_TEXT)]
    assert result == TextResult(hy="", en="hi", asr_end=10.4, mt_end=10.5)
    assert clock.values == []


def test_text_04_p1_in_the_template():
    transcriber = FakeTranscriber(["բարև"])
    translator = FakeTranslator("hi")
    audio = np.ones(16_000, dtype=np.float32)

    result = CascadeTextStep(transcriber, translator).process(audio, FakeClock([1.0, 2.0]))

    assert len(transcriber.calls) == 1 and transcriber.calls[0] is audio
    assert translator.calls == ["բարև"]
    assert result == TextResult(hy="բարև", en="hi", asr_end=1.0, mt_end=2.0)

    transcriber = FakeTranscriber([""])
    translator = FakeTranslator("hi")
    audio = zeros()

    result = CascadeTextStep(transcriber, translator).warm_up(audio, FakeClock([10.4, 10.5]))

    assert len(transcriber.calls) == 1 and transcriber.calls[0] is audio
    assert translator.calls == [WARMUP_TEXT]
    assert result == TextResult(hy="", en="hi", asr_end=10.4, mt_end=10.5)
    # The template stays in TextStep (D-062 part 2).
    assert "process" not in vars(CascadeTextStep)
    assert "warm_up" not in vars(CascadeTextStep)


def test_text_05_error_of_the_armenian_hook_goes_up_with_no_change():
    error = FakeAsrError("asr: test")
    step = Recorder(hy_error=error)
    clock = FakeClock([])

    with pytest.raises(FakeAsrError) as raised:
        step.process(np.ones(16_000, dtype=np.float32), clock)

    assert raised.value is error
    assert [call[0] for call in step.calls] == ["prepare", "armenian"]  # no English step


def test_text_05_error_of_the_english_hook_goes_up_with_no_change():
    error = KeyError("x")
    step = Recorder(en_error=error)
    clock = FakeClock([1.0])

    with pytest.raises(KeyError) as raised:
        step.process(np.ones(16_000, dtype=np.float32), clock)

    assert raised.value is error
    assert clock.values == []  # 1 read: the end of the Armenian step


# T-TEXT-06 (C7, D-066 parts 1 and 3): the output rules. The first case of each list is the P4
# line of s5-43 in the live call (test-results/c7-live-p4.txt).
@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("իսկապես #err ոնց էր, դուր եկավ։", "իսկապես ոնց էր, դուր եկավ։"),
        ("#err", ""),
        ("#err, լավ եմ։", "լավ եմ։"),
        (" Ալո, բարև։ ", " Ալո, բարև։ "),  # no change: the spaces stay
        (
            "Ո՞նց ես: Վա՜յ, ժամը 8-ին «Նռնենի» ռեստորանում։",
            "Ո՞նց ես: Վա՜յ, ժամը 8-ին «Նռնենի» ռեստորանում։",
        ),
        ("Hello, how are you?", FOREIGN),  # an English line in place of the Armenian line
        ("լավ, OK Google, գնանք", f"լավ, {FOREIGN} գնանք"),  # one mark for a run of words
        ("Привет բարև", f"{FOREIGN} բարև"),
        ("համար #1", f"համար {FOREIGN}"),  # "#" is not an Armenian character
    ],
)
def test_text_06_armenian_line_has_only_armenian_text(text, expected):
    assert clean_armenian(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Really? #Hmm, how was it? Did you like it?", "Really? Hmm, how was it? Did you like it?"),
        (" No change. ", " No change. "),
        ("Song #1 is “fine” — it’s ok…", "Song #1 is “fine” — it’s ok…"),
        ("Hello Սոնա, how are you?", f"Hello {FOREIGN} how are you?"),
        ("Hi Сона Սոնա!", f"Hi {FOREIGN}"),
        ("A café", f"A {FOREIGN}"),  # a letter with an accent is not allowed
    ],
)
def test_text_06_english_line_has_only_english_text(text, expected):
    assert clean_english(text) == expected


def test_text_07_template_cleans_both_texts_before_their_use():
    step = Recorder(hy="բարև OK", en="hi Привет")
    clock = FakeClock([1.0, 2.0])

    result = step.process(np.ones(16_000, dtype=np.float32), clock)

    state = step.states[0]
    assert step.calls[2] == ("english", state, f"բարև {FOREIGN}")  # P1 translates the clean text
    assert result == TextResult(hy=f"բարև {FOREIGN}", en=f"hi {FOREIGN}", asr_end=1.0, mt_end=2.0)


def test_text_07_a_text_with_only_hesitation_marks_is_an_empty_text():
    step = Recorder(hy="#err", en="#Hmm")
    clock = FakeClock([1.0])

    result = step.process(np.ones(16_000, dtype=np.float32), clock)

    assert [call[0] for call in step.calls] == ["prepare", "armenian"]  # D-031: no English step
    assert result == TextResult(hy="", en="", asr_end=1.0, mt_end=1.0)
