"""The program: the startup log, the model loads, the warm-up, and the pipeline.

ARCHITECTURE.md section 2.7. Decisions: D-022, D-030, D-037, D-042, D-043. This module imports
the adapters, so it is in ADAPTERS of T-IMPORT-01. `cli.py` imports it only after the parse of
the command line. Each startup line starts with "startup: ", so that it is easy to find between
the lines that NeMo prints at its load (D-043, point 3).
"""

import importlib.metadata
import sys
import time
import traceback
from typing import TextIO

from tir_asr.config import Params, parameter_lines
from tir_asr.errors import TirError
from tir_asr.pipeline import PROGRAM, run, warm_up

PACKAGES = ["tir-asr", "torch", "nemo-toolkit", "ctranslate2", "silero-vad", "soundcard"]
MIB = 2**20


def log_line(log: TextIO, text: str) -> None:
    log.write(f"startup: {text}\n")
    log.flush()


def load_models(params: Params, log: TextIO):
    """Print the versions and the parameters, then load ASR, MT, and VAD, in this order.

    ASR loads first, so that a missing CUDA gives `asr: CUDA is not available` (D-043, point
    2a). The MT adapter loads the CUDA 12 cuBLAS before its `import ctranslate2` (D-030); no
    other module imports `ctranslate2`. Return (vad, transcriber, translator).
    """
    import torch

    versions = "; ".join(f"{name} {importlib.metadata.version(name)}" for name in PACKAGES)
    log_line(log, f"{versions}; CUDA (torch) {torch.version.cuda}")
    for line in parameter_lines(params):
        log_line(log, line)

    def used_mib() -> int:
        free, total = torch.cuda.mem_get_info()  # the full device: CTranslate2 is included
        return (total - free) // MIB

    from tir_asr.asr.nemo_rnnt import NemoRnntTranscriber

    start = time.perf_counter()
    transcriber = NemoRnntTranscriber()  # checks CUDA first (section 2.3)
    elapsed = time.perf_counter() - start
    log_line(log, f"GPU {torch.cuda.get_device_name(0)}")
    asr_used = used_mib()
    log_line(log, f"ASR loaded in {elapsed:.2f} s; GPU memory used {asr_used} MiB")

    from tir_asr.mt.ct2_nllb import Ct2NllbTranslator

    start = time.perf_counter()
    translator = Ct2NllbTranslator(params)
    elapsed = time.perf_counter() - start
    mt_used = used_mib()
    log_line(
        log,
        f"MT loaded in {elapsed:.2f} s; GPU memory used {mt_used} MiB (+{mt_used - asr_used} MiB)",
    )

    from tir_asr.segment.silero import SileroSpeechProbability

    start = time.perf_counter()
    vad = SileroSpeechProbability()
    elapsed = time.perf_counter() - start
    log_line(log, f"VAD loaded in {elapsed:.2f} s; torch CPU threads {torch.get_num_threads()}")
    return vad, transcriber, translator


def main(out: TextIO | None = None, err: TextIO | None = None) -> int:
    """Run the startup, then the pipeline. Return the exit code (D-042, D-043)."""
    out = out or sys.stdout
    err = err or sys.stderr
    params = Params()
    try:
        vad, transcriber, translator = load_models(params, out)
        asr_s, mt_s = warm_up(transcriber, translator, time.monotonic)
        log_line(out, f"warm-up ASR {asr_s:.2f} s, MT {mt_s:.2f} s")

        from tir_asr.audio.soundcard_source import SoundcardSource, default_microphone_id

        microphone = SoundcardSource("Me", default_microphone_id())
        log_line(out, f"microphone {microphone.name}")
    except KeyboardInterrupt:
        out.write("Stopped during the startup.\n")
        out.flush()
        return 0
    except TirError as error:
        err.write(f"{PROGRAM}: {error}\n")
        err.flush()
        return 1
    except Exception as error:  # the rule of D-042, point 6
        err.write("".join(traceback.format_exception(error)))
        err.write(f"{PROGRAM}: startup: {type(error).__name__}: {error}\n")
        err.flush()
        return 1

    return run([(microphone, vad)], transcriber, translator, params, time.monotonic, out, err)
