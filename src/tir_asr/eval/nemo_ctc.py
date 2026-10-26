"""Eval candidate: ASR-1 with the CTC decoder (D-014, D-049, D-051). Adapter: it imports NeMo.

The same model file as the program adapter `tir_asr.asr.nemo_rnnt`, with the CTC head of the
hybrid model: `change_decoding_strategy(decoder_type="ctc")`. The program does not import this
module.
"""

import nemo.collections.asr as nemo_asr
import numpy as np
import torch
from huggingface_hub import hf_hub_download

from tir_asr.asr.nemo_rnnt import ASR_FILE, ASR_REPO, AsrError


class NemoCtcTranscriber:
    """`transcribe(audio)` gives the Armenian text of one segment, with the CTC decoder."""

    def __init__(self) -> None:
        if not torch.cuda.is_available():
            raise AsrError("asr: CUDA is not available")
        path = hf_hub_download(ASR_REPO, ASR_FILE, local_files_only=True)
        model = nemo_asr.models.ASRModel.restore_from(path, map_location=torch.device("cuda"))
        model.eval()
        model.change_decoding_strategy(decoder_type="ctc")
        self._model = model

    def transcribe(self, audio: np.ndarray) -> str:
        output = self._model.transcribe([audio], batch_size=1, verbose=False)
        if isinstance(output, tuple):
            output = output[0]
        first = output[0]
        text = getattr(first, "text", first)
        if not isinstance(text, str):
            raise AsrError(f"asr: unexpected output type {type(first).__name__}")
        return text
