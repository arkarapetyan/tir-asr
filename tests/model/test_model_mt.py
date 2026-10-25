"""T-MODEL-MT-01, T-MODEL-ERR-02, T-MODEL-ERR-04: the CTranslate2 NLLB adapter (C2c, c2c-mt).

Contract: ARCHITECTURE.md sections 2.4 and 7. Decisions: D-015, D-022, D-030, D-033, D-037. The
adapter has no warm-up method (D-037, part 3). The test does the warm-up as the caller does: one
call with WARMUP_TEXT. Then it translates text 1, text 2, text 1, and text 2.

The command sets no LD_LIBRARY_PATH: the adapter loads the CUDA 12 cuBLAS itself (D-030).
The error `mt: libcublas.so.12 not found …` has no test: it needs a missing package (Aren,
2026-10-25). The tests use no private attribute of the adapter (Aren, 2026-10-25).

The tests run on Aren's laptop only. They import the adapter inside the test functions, so that
CI can collect this file without the `laptop` dependency group (D-021).

Input files (local only, data/ and models/ are in .gitignore):
  data/eval/c2-check{1,2}.hy.txt                 Armenian reference text
  data/eval/c2-check{1,2}.en.txt                 English reference text
  models/nllb-200-distilled-600M-ct2-float16/    the converted CTranslate2 model
"""

import os
import statistics
import subprocess
import time
from pathlib import Path

import pytest

from tir_asr.config import WARMUP_TEXT, Params

pytestmark = pytest.mark.model

ROOT = Path(__file__).resolve().parents[2]
EVAL_DIR = ROOT / "data" / "eval"
CLIPS = ["c2-check1", "c2-check2"]
FIRST_CALL_LIMIT = 3.0  # T-MODEL-MT-01: the first real call, as a multiple of the median
# T-MODEL-MT-01, "CTranslate2 runs on cuda": the float16 weights (model.bin) are 1175 MiB, so a
# model on the GPU adds more than this. A model on the CPU adds no weights to the GPU.
MIN_GPU_GROWTH_MIB = 1000


def report(line: str) -> None:
    print(f"RESULT {line}", flush=True)


def gpu_memory_used_mib() -> int:
    out = subprocess.run(
        ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return int(out.strip().splitlines()[0])


def read_text(name: str, lang: str) -> str:
    return (EVAL_DIR / f"{name}.{lang}.txt").read_text(encoding="utf-8").strip()


def test_model_mt_01_ct2_adapter_with_warmup_and_no_ld_library_path():
    ld_library_path = os.environ.get("LD_LIBRARY_PATH", "")
    report(f"mt LD_LIBRARY_PATH: {ld_library_path!r}")
    assert "cublas" not in ld_library_path, "mt: run this test with no cuBLAS in LD_LIBRARY_PATH"

    from tir_asr.mt.ct2_nllb import Ct2NllbTranslator

    text1, text2 = (read_text(name, "hy") for name in CLIPS)
    calls = [
        ("text 1", text1),
        ("text 2", text2),
        ("text 1 again", text1),
        ("text 2 again", text2),
    ]

    used_before = gpu_memory_used_mib()
    start = time.perf_counter()
    mt = Ct2NllbTranslator(Params())
    report(f"mt load time {time.perf_counter() - start:.2f} s")
    gpu_growth = gpu_memory_used_mib() - used_before
    report(f"mt nvidia-smi used +{gpu_growth} MiB after the load (before {used_before} MiB)")

    start = time.perf_counter()
    warmup_text = mt.translate(WARMUP_TEXT)
    elapsed = time.perf_counter() - start
    report(f"mt warm-up: time {elapsed:.3f} s, text: {warmup_text!r}")

    texts = []
    times = []
    for label, text in calls:
        start = time.perf_counter()
        english = mt.translate(text)
        elapsed = time.perf_counter() - start
        texts.append(english)
        times.append(elapsed)
        report(f"mt {label}: time {elapsed:.3f} s, text: {english}")

    median_next = statistics.median(times[1:])
    report(
        f"mt first real call {times[0]:.3f} s, median of the next 3 calls {median_next:.3f} s, "
        f"ratio {times[0] / median_next:.2f}"
    )
    for name in CLIPS:
        report(f"mt reference {name}: {read_text(name, 'en')}")

    assert gpu_growth > MIN_GPU_GROWTH_MIB, f"mt: the GPU memory grew by {gpu_growth} MiB only"
    assert all(english.strip() for english in texts), "mt: an empty text"
    assert times[0] <= FIRST_CALL_LIMIT * median_next, (
        f"mt: the first real call took {times[0]:.3f} s, more than {FIRST_CALL_LIMIT:.0f} times "
        f"the median {median_next:.3f} s of the next 3 calls"
    )


def test_model_err_02_missing_mt_model_folder(tmp_path):
    from tir_asr.mt.ct2_nllb import Ct2NllbTranslator, MtError

    missing = tmp_path / "no-such-model"
    with pytest.raises(MtError) as raised:
        Ct2NllbTranslator(Params(), model_dir=missing)

    message = str(raised.value)
    report(f"mt error message: {message}")
    assert message.startswith("mt: CTranslate2 model not found: ")
    assert str(missing.resolve()) in message
    assert "ct2-transformers-converter" in message


def test_model_err_04_empty_input_text():
    from tir_asr.mt.ct2_nllb import Ct2NllbTranslator, MtError

    mt = Ct2NllbTranslator(Params())
    with pytest.raises(MtError) as raised:
        mt.translate("")

    message = str(raised.value)
    report(f"mt error message: {message}")
    assert message == "mt: empty input text"
