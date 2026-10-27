"""Speaker embedding adapter: TitaNet-large on NeMo, on `cuda` (ARCHITECTURE.md 2.8, D-058).

Model: nvidia/speakerverification_en_titanet_large (SPK-3). The model file comes from the
Hugging Face cache only; nothing downloads at runtime. There is no CPU fallback (R10).
`infer_segment` takes the 16 kHz audio as a numpy array [SOURCE: NeMo 3.0.0 `label_models.py`].

This module imports `torch`, `nemo`, and `huggingface_hub`. Only `app.py`, the sweep script, and
the model tests import it. The core modules do not (D-021, T-IMPORT-01). The adapter has no
warm-up method; the pipeline does the warm-up call (D-022, D-059).
"""

import numpy as np
import torch
from huggingface_hub import hf_hub_download
from huggingface_hub.errors import LocalEntryNotFoundError
from nemo.collections.asr.models import EncDecSpeakerLabelModel

from tir_asr.speakers.cluster import SpeakerError

SPK_REPO = "nvidia/speakerverification_en_titanet_large"
SPK_FILE = "speakerverification_en_titanet_large.nemo"  # [RUN] the name in the load log (C5)


class TitanetEmbedder:
    """`embed(audio)` gives the speaker embedding of one segment (one dimension, float32).

    The constructor loads the model on the GPU. `repo` and `filename` locate the model file in
    the Hugging Face cache; they are not tunable parameters (as D-037).
    """

    def __init__(self, repo: str = SPK_REPO, filename: str = SPK_FILE) -> None:
        if not torch.cuda.is_available():
            raise SpeakerError("speakers: CUDA is not available")
        try:
            path = hf_hub_download(repo, filename, local_files_only=True)
        except LocalEntryNotFoundError as error:
            raise SpeakerError(
                f"speakers: model file not in the Hugging Face cache: {repo}/{filename}"
            ) from error
        model = EncDecSpeakerLabelModel.restore_from(path, map_location=torch.device("cuda"))
        model.eval()
        self._model = model

    def embed(self, audio: np.ndarray) -> np.ndarray:
        """Take float32, mono, 16 kHz audio. Return the embedding as a float32 vector."""
        embedding, _ = self._model.infer_segment(audio)
        return embedding.squeeze(0).float().cpu().numpy()
