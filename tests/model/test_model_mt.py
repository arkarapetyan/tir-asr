"""T-MODEL-MT-01, T-MODEL-ERR-02, T-MODEL-ERR-04: the Google Translate adapter (C10).

Contract: ARCHITECTURE.md sections 2.4 and 7. Decisions: D-022, D-037, D-079, D-081 point 3. The
adapter has no warm-up method (D-037, part 3). The test does the warm-up as the caller does: one
call with WARMUP_TEXT. Then it translates text 1, text 2, text 1, and text 2. Until C9, these IDs
tested the CTranslate2 NLLB adapter (D-081 point 5).

CAUTION: T-MODEL-MT-01 and T-MODEL-ERR-02 send the Armenian reference texts to Google over the
network (D-079). With no network, they fail. T-MODEL-MT-01 has no time limit, because the time
is network time (D-080).

The tests run on Aren's laptop only. They import the adapter inside the test functions, so that
CI can collect this file without the `laptop` dependency group (D-021).

Input files (local only, data/ is in .gitignore):
  data/eval/c2-check{1,2}.hy.txt    Armenian reference text
  data/eval/c2-check{1,2}.en.txt    English reference text
"""

import re
import time
from pathlib import Path

import pytest

from tir_asr.config import WARMUP_TEXT

pytestmark = pytest.mark.model

ROOT = Path(__file__).resolve().parents[2]
EVAL_DIR = ROOT / "data" / "eval"
CLIPS = ["c2-check1", "c2-check2"]
ARMENIAN = re.compile("[Ա-և]")  # the Armenian letters (TESTS.md section 2.11)
LATIN = re.compile("[A-Za-z]")
FAIL_TIMEOUT_S = 0.001  # T-MODEL-ERR-02: a timeout that no real call can meet


def report(line: str) -> None:
    print(f"RESULT {line}", flush=True)


def read_text(name: str, lang: str) -> str:
    return (EVAL_DIR / f"{name}.{lang}.txt").read_text(encoding="utf-8").strip()


def test_model_mt_01_google_adapter_with_warmup():
    from tir_asr.mt.google import GoogleTranslator

    text1, text2 = (read_text(name, "hy") for name in CLIPS)
    calls = [
        ("text 1", text1),
        ("text 2", text2),
        ("text 1 again", text1),
        ("text 2 again", text2),
    ]

    mt = GoogleTranslator()
    report(f"mt service URLs: {mt.service_urls}")

    start = time.perf_counter()
    warmup_text = mt.translate(WARMUP_TEXT)
    elapsed = time.perf_counter() - start
    report(f"mt warm-up: time {elapsed:.3f} s, text: {warmup_text!r}")

    texts = []
    for label, text in calls:
        start = time.perf_counter()
        english = mt.translate(text)
        elapsed = time.perf_counter() - start
        texts.append(english)
        report(f"mt {label}: time {elapsed:.3f} s, text: {english}")
    for name in CLIPS:
        report(f"mt reference {name}: {read_text(name, 'en')}")

    assert all(english.strip() for english in texts), "mt: an empty text"
    assert all(LATIN.search(english) for english in texts), f"mt: no Latin letter: {texts}"
    assert not any(ARMENIAN.search(english) for english in texts), f"mt: Armenian: {texts}"
    assert texts[0] == texts[2], "mt: text 1 gave two different translations"


def test_model_err_02_failed_call_raises(monkeypatch):
    from tir_asr.mt import google

    monkeypatch.setattr(google, "TIMEOUT_S", FAIL_TIMEOUT_S)
    mt = google.GoogleTranslator()
    with pytest.raises(google.MtError) as raised:
        mt.translate(read_text(CLIPS[0], "hy"))

    message = str(raised.value)
    report(f"mt error message: {message}")
    assert message.startswith("mt: Google Translate failed: ")


def test_model_err_04_empty_input_text():
    from tir_asr.mt.google import GoogleTranslator, MtError

    mt = GoogleTranslator()
    with pytest.raises(MtError) as raised:
        mt.translate("")

    message = str(raised.value)
    report(f"mt error message: {message}")
    assert message == "mt: empty input text"
