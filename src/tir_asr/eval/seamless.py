"""Eval candidates ASR-2 and MT-5: facebook/seamless-m4t-v2-large on Transformers (D-014, D-015).

Adapter: it imports torch and transformers (D-049, D-051). Three uses of one model:
- `SeamlessSpeech.transcribe(audio)`: speech to Armenian text (ASR, `tgt_lang="hye"`).
- `SeamlessSpeech.to_english(audio)`: speech to English text (end-to-end S2TT, `tgt_lang="eng"`).
- `SeamlessText.translate(text)`: Armenian text to English text (T2TT).
float16 on CUDA. The generate settings are the defaults of the model. The program does not import
this module.
"""

import numpy as np
import torch
from transformers import AutoProcessor, SeamlessM4Tv2ForSpeechToText, SeamlessM4Tv2ForTextToText

from tir_asr.config import SAMPLE_RATE
from tir_asr.errors import TirError

REPO = "facebook/seamless-m4t-v2-large"


class CandidateError(TirError):
    """An error of an eval candidate. The message is `<module>: <cause>`."""


def _check_cuda(module: str) -> None:
    if not torch.cuda.is_available():
        raise CandidateError(f"{module}: CUDA is not available")


class SeamlessSpeech:
    """Speech input: Armenian text (ASR) or English text (S2TT) for one segment."""

    def __init__(self) -> None:
        _check_cuda("asr")
        self._processor = AutoProcessor.from_pretrained(REPO, local_files_only=True)
        self._model = (
            SeamlessM4Tv2ForSpeechToText.from_pretrained(
                REPO, dtype=torch.float16, local_files_only=True
            )
            .to("cuda")
            .eval()
        )

    def _generate(self, audio: np.ndarray, tgt_lang: str) -> str:
        inputs = self._processor(audio=audio, sampling_rate=SAMPLE_RATE, return_tensors="pt")
        inputs = {key: value.to("cuda") for key, value in inputs.items()}
        inputs["input_features"] = inputs["input_features"].to(torch.float16)
        with torch.inference_mode():
            tokens = self._model.generate(**inputs, tgt_lang=tgt_lang)
        return self._processor.decode(tokens[0].tolist(), skip_special_tokens=True).strip()

    def transcribe(self, audio: np.ndarray) -> str:
        return self._generate(audio, "hye")

    def to_english(self, audio: np.ndarray) -> str:
        return self._generate(audio, "eng")


class SeamlessText:
    """Text input: the English text of one Armenian text (T2TT), with no context."""

    def __init__(self) -> None:
        _check_cuda("mt")
        self._processor = AutoProcessor.from_pretrained(REPO, local_files_only=True)
        self._model = (
            SeamlessM4Tv2ForTextToText.from_pretrained(
                REPO, dtype=torch.float16, local_files_only=True
            )
            .to("cuda")
            .eval()
        )

    def translate(self, text: str) -> str:
        if not text.strip():
            raise CandidateError("mt: empty input text")
        inputs = self._processor(text=text, src_lang="hye", return_tensors="pt")
        inputs = {key: value.to("cuda") for key, value in inputs.items()}
        with torch.inference_mode():
            tokens = self._model.generate(**inputs, tgt_lang="eng")
        return self._processor.decode(tokens[0].tolist(), skip_special_tokens=True).strip()
