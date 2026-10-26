"""Eval candidate ASR-5: BuzzASR/armenian (Whisper-large-v3, full fine-tune) (D-014, D-049, D-051).

Adapter: it imports torch and transformers. The usage comes from the model card
(test-results/cards): float16 on CUDA, the WhisperProcessor features, and
generate(num_beams=1, no_repeat_ngram_size=3, repetition_penalty=1.2). The language and task
prompt is in the generation config of the model. The program does not import this module.
"""

import numpy as np
import torch
from transformers import WhisperForConditionalGeneration, WhisperProcessor

from tir_asr.config import SAMPLE_RATE
from tir_asr.errors import TirError

REPO = "BuzzASR/armenian"
GENERATE = {"num_beams": 1, "no_repeat_ngram_size": 3, "repetition_penalty": 1.2}  # model card


class CandidateError(TirError):
    """An error of an eval candidate. The message is `asr: <cause>`."""


class BuzzWhisperTranscriber:
    """`transcribe(audio)` gives the Armenian text of one segment (at most 30 s for Whisper)."""

    def __init__(self) -> None:
        if not torch.cuda.is_available():
            raise CandidateError("asr: CUDA is not available")
        self._processor = WhisperProcessor.from_pretrained(REPO, local_files_only=True)
        self._model = (
            WhisperForConditionalGeneration.from_pretrained(
                REPO, dtype=torch.float16, local_files_only=True
            )
            .to("cuda")
            .eval()
        )

    def transcribe(self, audio: np.ndarray) -> str:
        features = self._processor(
            audio=audio, sampling_rate=SAMPLE_RATE, return_tensors="pt"
        ).input_features
        with torch.inference_mode():
            ids = self._model.generate(features.to("cuda", dtype=torch.float16), **GENERATE)
        return self._processor.batch_decode(ids, skip_special_tokens=True)[0].strip()
