"""OhanASR adapter: the Transcriber on the GPU, in the program process (ARCHITECTURE.md 2.3).

Model: Metric-AI/OhanASR-v0.1 in `models/ohanasr-v0.1` (gated download, not in git), an
omniASR LLM 1B v2 model with the OhanASR checkpoint (D-072, D-080). The adapter loads it with the
model's own `load_model` (`ohanasr.py` in the model folder): bfloat16 on `cuda`, with the rotary
tables in float32. The model code falls back to the CPU when CUDA is missing, so the adapter checks
CUDA first (no CPU fallback, R10). Nothing downloads at runtime.

Each `transcribe` call is one segment (batch size 1), as in the C9 eval (D-073). A segment must be
at most 40 s (the model limit, `max_audio_seconds_per_call` in `model.json`); the program segments
are at most `vad_max_speech_s` (15 s).

This module imports `torch`, and the load imports `fairseq2` and `omnilingual_asr` (D-081). Only
`app.py`, `scripts/c9_run.py`, and the model tests import it. The core modules do not (D-021,
T-IMPORT-01). The adapter has no warm-up method. The pipeline does the warm-up call (D-022, D-037).
"""

import importlib.util
from pathlib import Path

import numpy as np
import torch

from tir_asr.config import SAMPLE_RATE
from tir_asr.errors import TirError

MODEL_DIR = Path("models") / "ohanasr-v0.1"  # relative to the project folder; not a parameter
LANG = "hye_Armn"  # the language code of the model for Armenian
MAX_SAMPLES = 40 * SAMPLE_RATE  # the model limit: 40 s at 16 kHz


class AsrError(TirError):
    """An error of the ASR adapter. The message is `asr: <cause>`."""


class OhanasrTranscriber:
    """`transcribe(audio)` gives the Armenian text of one segment. The text can be empty.

    The constructor loads the model on the GPU. `model_dir` locates the model folder; it is not
    a tunable parameter (as D-037).
    """

    def __init__(self, model_dir: Path = MODEL_DIR) -> None:
        if not torch.cuda.is_available():
            raise AsrError("asr: CUDA is not available")
        model_dir = Path(model_dir)
        checkpoint = model_dir / "model.pt"
        if not checkpoint.is_file():
            raise AsrError(f"asr: OhanASR model not found: {checkpoint}")
        # The model's own code, by its file path (no change to sys.path). Claude read it in C9
        # and in C10: it imports only installed packages.
        spec = importlib.util.spec_from_file_location("ohanasr", model_dir / "ohanasr.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self._pipeline = module.load_model(model_dir)

    def transcribe(self, audio: np.ndarray) -> str:
        """Take float32, mono, 16 kHz audio. Return the Armenian text (batch size 1)."""
        if len(audio) > MAX_SAMPLES:
            raise AsrError(
                f"asr: segment of {len(audio)} samples is over the model limit of "
                f"{MAX_SAMPLES} samples (40 s)"
            )
        with torch.inference_mode():
            texts = self._pipeline.transcribe(
                [{"waveform": audio, "sample_rate": SAMPLE_RATE}], lang=[LANG], batch_size=1
            )
        return texts[0].strip()
