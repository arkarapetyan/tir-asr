"""Speaker candidate SPK-3: TitaNet-large on NeMo, on `cuda` (D-017, D-057). Eval only.

The model file comes from the Hugging Face cache only; nothing downloads at runtime. There is no
CPU fallback (R10). `infer_segment` takes the 16 kHz audio as a numpy array [SOURCE: NeMo 3.0.0
`label_models.py`]. This module imports `torch`, `nemo`, and `huggingface_hub`; it is in
`ADAPTERS` of T-IMPORT-01.
"""

from pathlib import Path

import numpy as np
import torch
from huggingface_hub import snapshot_download
from huggingface_hub.errors import LocalEntryNotFoundError
from nemo.collections.asr.models import EncDecSpeakerLabelModel

from tir_asr.speakers.cluster import SpeakerError

REPO = "nvidia/speakerverification_en_titanet_large"


class TitanetEmbedder:
    """`embed(audio)` gives the speaker embedding of one segment (one dimension, float32)."""

    def __init__(self, repo: str = REPO) -> None:
        if not torch.cuda.is_available():
            raise SpeakerError("speakers: CUDA is not available")
        try:
            folder = Path(snapshot_download(repo, local_files_only=True))
        except LocalEntryNotFoundError as error:
            raise SpeakerError(f"speakers: model not in the Hugging Face cache: {repo}") from error
        files = sorted(folder.glob("*.nemo"))
        if len(files) != 1:
            raise SpeakerError(f"speakers: {repo} has {len(files)} .nemo files, expected 1")
        model = EncDecSpeakerLabelModel.restore_from(
            str(files[0]), map_location=torch.device("cuda")
        )
        model.eval()
        self._model = model

    def embed(self, audio: np.ndarray) -> np.ndarray:
        embedding, _ = self._model.infer_segment(audio)
        return embedding.squeeze(0).float().cpu().numpy()
