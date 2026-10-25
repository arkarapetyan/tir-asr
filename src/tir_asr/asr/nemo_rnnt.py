"""NeMo ASR adapter: the Transcriber on the GPU (ARCHITECTURE.md section 2.3).

Model: nvidia/stt_hy_fastconformer_hybrid_large_pc, RNNT decoder, on `cuda` (D-014). The model
file comes from the Hugging Face cache only; nothing downloads at runtime. There is no CPU
fallback (R10).

This module imports `torch`, `nemo`, and `huggingface_hub`. Only the CLI and the model tests
import it. The core modules do not (D-021, T-IMPORT-01).

The adapter has no warm-up method. The pipeline does the warm-up call (D-022, D-037).
"""

import nemo.collections.asr as nemo_asr
import numpy as np
import torch
from huggingface_hub import hf_hub_download
from huggingface_hub.errors import LocalEntryNotFoundError

ASR_REPO = "nvidia/stt_hy_fastconformer_hybrid_large_pc"
ASR_FILE = "stt_hy_fastconformer_hybrid_large_pc.nemo"


class AsrError(Exception):
    """An error of the ASR adapter. The message is `asr: <cause>`."""


class NemoRnntTranscriber:
    """`transcribe(audio)` gives the Armenian text of one segment. The text can be empty.

    The constructor loads the model on the GPU. `repo` and `filename` locate the model file in
    the Hugging Face cache; they are not tunable parameters (D-037).
    """

    def __init__(self, repo: str = ASR_REPO, filename: str = ASR_FILE) -> None:
        if not torch.cuda.is_available():
            raise AsrError("asr: CUDA is not available")
        try:
            path = hf_hub_download(repo, filename, local_files_only=True)
        except LocalEntryNotFoundError as error:
            raise AsrError(
                f"asr: model file not in the Hugging Face cache: {repo}/{filename}"
            ) from error
        model = nemo_asr.models.ASRModel.restore_from(path, map_location=torch.device("cuda"))
        model.eval()
        model.change_decoding_strategy(decoder_type="rnnt")
        self._model = model

    def transcribe(self, audio: np.ndarray) -> str:
        """Take float32, mono, 16 kHz audio. Return the Armenian text (batch size 1)."""
        # verbose=False: no progress bar for each segment on the terminal.
        output = self._model.transcribe([audio], batch_size=1, verbose=False)
        if isinstance(output, tuple):  # some NeMo versions return (best, all) for RNNT
            output = output[0]
        first = output[0]
        text = getattr(first, "text", first)
        if not isinstance(text, str):
            raise AsrError(f"asr: unexpected output type {type(first).__name__}")
        return text
