"""Speaker candidate SPK-2: SpeechBrain ECAPA-TDNN, on `cuda` (D-017, D-057). Eval only.

The package `speechbrain` is in the dependency group `spk-eval` (D-057). The model files come
from the Hugging Face cache: the constructor checks the cache first, and the run command sets
`HF_HUB_OFFLINE=1`, so nothing downloads. SpeechBrain links the files into `SAVEDIR`
(`models/` is in `.gitignore`). `encode_batch` takes a 1-D waveform at 16 kHz [SOURCE:
speechbrain 1.1.2 `inference/classifiers.py`]. This module is in `ADAPTERS` of T-IMPORT-01.
"""

from pathlib import Path

import numpy as np
import torch
from huggingface_hub import snapshot_download
from huggingface_hub.errors import LocalEntryNotFoundError
from speechbrain.inference.classifiers import EncoderClassifier

from tir_asr.speakers.cluster import SpeakerError

REPO = "speechbrain/spkrec-ecapa-voxceleb"
SAVEDIR = Path("models") / "spkrec-ecapa-voxceleb"  # relative to the project folder


class EcapaEmbedder:
    """`embed(audio)` gives the speaker embedding of one segment (one dimension, float32)."""

    def __init__(self, repo: str = REPO, savedir: Path = SAVEDIR) -> None:
        if not torch.cuda.is_available():
            raise SpeakerError("speakers: CUDA is not available")
        try:
            snapshot_download(repo, local_files_only=True)
        except LocalEntryNotFoundError as error:
            raise SpeakerError(f"speakers: model not in the Hugging Face cache: {repo}") from error
        self._model = EncoderClassifier.from_hparams(
            source=repo, savedir=str(savedir), run_opts={"device": "cuda"}
        )

    def embed(self, audio: np.ndarray) -> np.ndarray:
        with torch.inference_mode():
            embedding = self._model.encode_batch(torch.from_numpy(audio))
        return embedding.reshape(-1).float().cpu().numpy()
