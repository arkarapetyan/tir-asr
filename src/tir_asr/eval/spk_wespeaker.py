"""Speaker candidate SPK-1: WeSpeaker ResNet34-LM on pyannote.audio, on `cuda` (D-017, D-057).

Eval only. The package `pyannote.audio` is in the dependency group `spk-eval` (D-057).

Telemetry: pyannote.audio 4.0.7 sends usage metrics by default to `otel.pyannote.ai`. It reads
`PYANNOTE_METRICS_ENABLED` at import and sets it only if it is not set [SOURCE:
`telemetry/config.yaml`, `telemetry/metrics.py`]. Thus this module sets it to "false" before the
import, and the constructor stops with an error if the metrics are still on (R10).

The model loads from its folder in the Hugging Face cache, so nothing downloads. `Inference` with
`window="whole"` takes `{"waveform": (channel, time), "sample_rate": ...}` and gives one numpy
array [SOURCE: `core/inference.py`, `core/io.py`]. This module is in `ADAPTERS` of T-IMPORT-01.
"""

import os

os.environ["PYANNOTE_METRICS_ENABLED"] = "false"  # before the import of pyannote.audio

import numpy as np  # noqa: E402
import torch  # noqa: E402
from huggingface_hub import snapshot_download  # noqa: E402
from huggingface_hub.errors import LocalEntryNotFoundError  # noqa: E402
from pyannote.audio import Inference, Model  # noqa: E402
from pyannote.audio.telemetry.metrics import is_metrics_enabled  # noqa: E402

from tir_asr.config import SAMPLE_RATE  # noqa: E402
from tir_asr.speakers.cluster import SpeakerError  # noqa: E402

REPO = "pyannote/wespeaker-voxceleb-resnet34-LM"


class WespeakerEmbedder:
    """`embed(audio)` gives the speaker embedding of one segment (one dimension, float32)."""

    def __init__(self, repo: str = REPO) -> None:
        if is_metrics_enabled():
            raise SpeakerError("speakers: the pyannote telemetry is on")
        if not torch.cuda.is_available():
            raise SpeakerError("speakers: CUDA is not available")
        try:
            folder = snapshot_download(repo, local_files_only=True)
        except LocalEntryNotFoundError as error:
            raise SpeakerError(f"speakers: model not in the Hugging Face cache: {repo}") from error
        model = Model.from_pretrained(folder)
        self._inference = Inference(model, window="whole")
        self._inference.to(torch.device("cuda"))

    def embed(self, audio: np.ndarray) -> np.ndarray:
        waveform = torch.from_numpy(audio).unsqueeze(0)  # (channel, time)
        output = self._inference({"waveform": waveform, "sample_rate": SAMPLE_RATE})
        return np.asarray(output, dtype=np.float32).reshape(-1)
