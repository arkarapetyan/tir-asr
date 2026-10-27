"""P4 text step: Seamless end to end on the GPU (ARCHITECTURE.md section 2.9, D-053, D-063).

Model: facebook/seamless-m4t-v2-large, `SeamlessM4Tv2ForSpeechToText`, float16, on `cuda`. The
model files come from the Hugging Face cache only; nothing downloads at runtime. There is no CPU
fallback and no CPU mode (R10, D-063 part 4).

Variant V2 (D-063 part 1, `scripts/probe_p4.py`): for each segment, one encoder pass, then one
decode of a batch of two rows. The "hye" row gives the Armenian text, and the "eng" row gives the
English text. The adapter calls the base `GenerationMixin.generate`, because the Seamless
`generate` with no `tgt_lang` writes a warning at each call. Each call gets a new
`BaseModelOutput`, because `generate` changes the given encoder output in place for the beams
(transformers 5.20.2, `_expand_dict_for_generation`). The generate values are the defaults of
the model: greedy and `max_new_tokens` 256 (D-063 part 6).

This module imports `torch`, `transformers`, and `huggingface_hub`. Only `app.py` and the model
tests import it; the core modules do not (D-021, T-IMPORT-01). The template methods are in
`TextStep`: this class gives only the hooks, and its one latency step is `s2t` (D-063 part 2).
"""

import numpy as np
import torch
from huggingface_hub import hf_hub_download
from huggingface_hub.errors import LocalEntryNotFoundError
from transformers import AutoProcessor, SeamlessM4Tv2ForSpeechToText
from transformers.generation.utils import GenerationMixin
from transformers.modeling_outputs import BaseModelOutput

from tir_asr.config import SAMPLE_RATE
from tir_asr.text.step import TextError, TextStep

S2T_REPO = "facebook/seamless-m4t-v2-large"
LANGUAGES = ("hye", "eng")  # the rows of the batch: the Armenian text, then the English text


class SeamlessTextStep(TextStep):
    """P4: the Armenian text and the English text of one segment from one Seamless model.

    The constructor loads the model on the GPU. `repo` locates the model in the Hugging Face
    cache; it is not a tunable parameter (as D-037).
    """

    STEPS = ("s2t",)

    def __init__(self, repo: str = S2T_REPO) -> None:
        if not torch.cuda.is_available():
            raise TextError("text: CUDA is not available")
        try:
            hf_hub_download(repo, "config.json", local_files_only=True)
        except LocalEntryNotFoundError as error:
            raise TextError(f"text: model not in the Hugging Face cache: {repo}") from error
        self._processor = AutoProcessor.from_pretrained(repo, local_files_only=True)
        model = SeamlessM4Tv2ForSpeechToText.from_pretrained(
            repo, dtype=torch.float16, local_files_only=True
        )
        self._model = model.to("cuda").eval()
        config = self._model.generation_config
        codes = config.text_decoder_lang_to_code_id
        self._rows = torch.tensor([[codes[lang]] for lang in LANGUAGES], device="cuda")
        self.num_beams = config.num_beams or 1  # None in the model files: greedy
        self.max_new_tokens = config.max_new_tokens

    def _prepare(self, audio: np.ndarray) -> tuple[str, str]:
        """One encoder pass and one decode of the two rows. Return (Armenian, English)."""
        inputs = self._processor(audio=audio, sampling_rate=SAMPLE_RATE, return_tensors="pt")
        features = inputs["input_features"].to("cuda", torch.float16)
        mask = inputs.get("attention_mask")
        rows = len(LANGUAGES)
        extra = {}
        if mask is not None:
            mask = mask.to("cuda")
            extra["attention_mask"] = mask.repeat(rows, 1)
        with torch.inference_mode():
            hidden = self._model.get_encoder()(input_features=features, attention_mask=mask)[0]
            tokens = GenerationMixin.generate(
                self._model,
                features.repeat(rows, 1, 1),
                encoder_outputs=BaseModelOutput(last_hidden_state=hidden.repeat(rows, 1, 1)),
                decoder_input_ids=self._rows,
                **extra,
            )
        hy, en = (
            self._processor.decode(row.tolist(), skip_special_tokens=True).strip() for row in tokens
        )
        return hy, en

    def _armenian(self, state: tuple[str, str]) -> str:
        return state[0]

    def _english(self, state: tuple[str, str], hy: str) -> str:
        return state[1]
