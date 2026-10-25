"""Silero VAD adapter: the SpeechProbability on the CPU (ARCHITECTURE.md section 2.2).

This module imports `torch` and `silero_vad`. Only the CLI and the model tests import it.
The core modules do not (D-021, T-IMPORT-01).

`silero_vad` sets the PyTorch CPU threads to 1 at import [RUN]. The startup log shows the
thread count.
"""

import numpy as np
import torch
from silero_vad import load_silero_vad

from tir_asr.config import SAMPLE_RATE


class SileroSpeechProbability:
    """One call for each 512-sample frame at 16 kHz gives a speech probability in [0, 1].

    The model keeps its state between the calls. Use one instance for one audio stream.
    """

    def __init__(self) -> None:
        self._model = load_silero_vad()  # the JIT model, on the CPU

    def __call__(self, samples: np.ndarray) -> float:
        frame = torch.tensor(samples, dtype=torch.float32)
        with torch.inference_mode():
            return self._model(frame, SAMPLE_RATE).item()
