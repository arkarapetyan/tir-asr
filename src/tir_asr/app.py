"""The program: the startup log, the two sources, the model loads, the warm-up, and the pipeline.

ARCHITECTURE.md section 2.7. Decisions: D-022, D-030, D-037, D-042, D-043, D-054, D-059, D-062,
D-063. This module imports the adapters, so it is in ADAPTERS of T-IMPORT-01. `cli.py` imports it
only after the parse of the command line. Each startup line starts with "startup: ", so that it
is easy to find between the lines that NeMo prints at its load (D-043, point 3).
"""

import importlib.metadata
import sys
import time
import traceback
from typing import TextIO

from tir_asr.config import Params, parameter_lines
from tir_asr.errors import TirError
from tir_asr.pipeline import PROGRAM, run, warm_up
from tir_asr.speakers.cluster import CentroidClusterer
from tir_asr.speakers.labeler import SpeakerLabeler
from tir_asr.text.step import CascadeTextStep, TextStep

PACKAGES = [
    "tir-asr",
    "torch",
    "nemo-toolkit",
    "ctranslate2",
    "transformers",
    "silero-vad",
    "soundcard",
]
MIB = 2**20
SOURCE_LABELS = ("Me", "System")  # the microphone and the system audio (F1, D-054)
SPEAKER_SOURCE = "System"  # only the system side gets speaker labels (F4, D-057, D-059)


def log_line(log: TextIO, text: str) -> None:
    log.write(f"startup: {text}\n")
    log.flush()


def log_versions(params: Params, log: TextIO) -> None:
    """Print the package versions and the parameters. Import no package (D-054, point 6)."""
    versions = "; ".join(f"{name} {importlib.metadata.version(name)}" for name in PACKAGES)
    log_line(log, versions)
    for line in parameter_lines(params):
        log_line(log, line)


def select_sources(mic: str | None, system: str | None, log: TextIO) -> list:
    """Find and check the two sources before the model load, so that a wrong id fails fast.

    A flag that is not given selects the default: the default microphone for "Me", the monitor
    of the default output for "System" (D-054). The streams open later, in `run()` (D-041).
    """
    from tir_asr.audio.soundcard_source import (
        SoundcardSource,
        default_microphone_id,
        default_system_id,
    )

    ids = (
        mic if mic is not None else default_microphone_id(),
        system if system is not None else default_system_id(),
    )
    sources = [
        SoundcardSource(label, device) for label, device in zip(SOURCE_LABELS, ids, strict=True)
    ]
    for source in sources:
        log_line(log, f"source {source.label}: {source.name} ({source.id})")
    return sources


def load_models(params: Params, log: TextIO, labels: list[str], seamless: bool = False):
    """Load the text step, one VAD for each source label, and the speaker model, in this order.

    P1 (the default): ASR, then MT; they make `CascadeTextStep` (D-062). ASR loads first, so
    that a missing CUDA gives `asr: CUDA is not available` (D-043, point 2a). The MT adapter
    loads the CUDA 12 cuBLAS before its `import ctranslate2` (D-030); no other module imports
    `ctranslate2`. P4 (`seamless`): the Seamless adapter is the text step, and it checks CUDA
    first (`text: CUDA is not available`); NeMo ASR and NLLB do not load (D-062 part 5). Each
    source needs its own VAD, because the Silero model keeps its state (D-036, D-054). The
    speaker model loads last (D-057 part 6). Return (vads, text_step, embedder).
    """
    import torch

    def used_mib() -> int:
        free, total = torch.cuda.mem_get_info()  # the full device: CTranslate2 is included
        return (total - free) // MIB

    if seamless:
        text_step = load_seamless(log, used_mib)
    else:
        text_step = load_cascade(params, log, used_mib)

    from tir_asr.segment.silero import SileroSpeechProbability

    start = time.perf_counter()
    vads = [SileroSpeechProbability() for _ in labels]
    elapsed = time.perf_counter() - start
    log_line(
        log,
        f"VAD loaded in {elapsed:.2f} s ({', '.join(labels)}); "
        f"torch CPU threads {torch.get_num_threads()}",
    )

    from tir_asr.speakers.titanet import TitanetEmbedder

    before = used_mib()
    start = time.perf_counter()
    embedder = TitanetEmbedder()
    elapsed = time.perf_counter() - start
    spk_used = used_mib()
    log_line(
        log,
        f"speaker model loaded in {elapsed:.2f} s; "
        f"GPU memory used {spk_used} MiB ({spk_used - before:+d} MiB)",
    )
    return vads, text_step, embedder


def load_cascade(params: Params, log: TextIO, used_mib) -> TextStep:
    """P1: the NeMo ASR adapter, then the CTranslate2 MT adapter (D-014, D-015, D-043)."""
    import torch

    from tir_asr.asr.nemo_rnnt import NemoRnntTranscriber

    log_line(log, "text step cascade (P1): NeMo RNNT ASR, then NLLB MT")
    start = time.perf_counter()
    transcriber = NemoRnntTranscriber()  # checks CUDA first (section 2.3)
    elapsed = time.perf_counter() - start
    log_line(log, f"GPU {torch.cuda.get_device_name(0)}; CUDA (torch) {torch.version.cuda}")
    asr_used = used_mib()
    log_line(log, f"ASR loaded in {elapsed:.2f} s; GPU memory used {asr_used} MiB")

    from tir_asr.mt.ct2_nllb import Ct2NllbTranslator

    start = time.perf_counter()
    translator = Ct2NllbTranslator(params)
    elapsed = time.perf_counter() - start
    mt_used = used_mib()
    log_line(
        log,
        f"MT loaded in {elapsed:.2f} s; "
        f"GPU memory used {mt_used} MiB ({mt_used - asr_used:+d} MiB)",
    )
    return CascadeTextStep(transcriber, translator)


def load_seamless(log: TextIO, used_mib) -> TextStep:
    """P4: one Seamless model gives both texts (D-053, D-063)."""
    import torch

    from tir_asr.text.seamless import SeamlessTextStep

    log_line(log, "text step seamless (P4): Seamless end to end, one call for both texts")
    start = time.perf_counter()
    text_step = SeamlessTextStep()  # checks CUDA first (section 2.9)
    elapsed = time.perf_counter() - start
    log_line(log, f"GPU {torch.cuda.get_device_name(0)}; CUDA (torch) {torch.version.cuda}")
    log_line(
        log,
        f"Seamless loaded in {elapsed:.2f} s; GPU memory used {used_mib()} MiB; "
        f"generate num_beams {text_step.num_beams}, max_new_tokens {text_step.max_new_tokens}",
    )
    return text_step


def list_devices(out: TextIO | None = None, err: TextIO | None = None) -> int:
    """Print the sources with their exact ids and the two defaults (`--list-devices`, D-054).

    Load no model. Return the exit code.
    """
    out = out or sys.stdout
    err = err or sys.stderr
    from tir_asr.audio.devices import format_source_list
    from tir_asr.audio.soundcard_source import (
        default_microphone_id,
        default_system_id,
        list_sources,
    )

    try:
        text = format_source_list(list_sources(), default_microphone_id(), default_system_id())
    except TirError as error:
        err.write(f"{PROGRAM}: {error}\n")
        err.flush()
        return 1
    out.write(text)
    out.flush()
    return 0


def main(
    mic: str | None = None,
    system: str | None = None,
    seamless: bool = False,
    out: TextIO | None = None,
    err: TextIO | None = None,
) -> int:
    """Run the startup, then the pipeline. Return the exit code (D-042, D-043, D-054, D-062).

    `seamless` selects the P4 text step; the default is P1 (D-062 part 4).
    """
    out = out or sys.stdout
    err = err or sys.stderr
    params = Params()
    try:
        log_versions(params, out)
        sources = select_sources(mic, system, out)
        vads, text_step, embedder = load_models(params, out, list(SOURCE_LABELS), seamless)
        asr_s, mt_s, spk_s = warm_up(text_step, embedder, time.monotonic)
        log_line(out, warm_up_line(text_step, asr_s, mt_s, spk_s))
        labelers = {SPEAKER_SOURCE: speaker_labeler(embedder, params)}
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

    pairs = list(zip(sources, vads, strict=True))
    return run(pairs, text_step, params, time.monotonic, out, err, labelers)


def warm_up_line(text_step: TextStep, asr_s: float, mt_s: float, spk_s: float) -> str:
    """The warm-up times with the names of the text steps (D-063 part 2): P4 has one step."""
    if len(text_step.STEPS) == 1:
        text = f"{text_step.STEPS[0]} {asr_s + mt_s:.2f} s"
    else:
        text = f"ASR {asr_s:.2f} s, MT {mt_s:.2f} s"
    return f"warm-up {text}, speaker {spk_s:.2f} s"


def speaker_labeler(embedder, params: Params) -> SpeakerLabeler:
    """The speaker step of the system side: rule A with the approved parameters (D-058)."""
    return SpeakerLabeler(embedder, CentroidClusterer(params.spk_threshold, params.spk_min_new_s))
