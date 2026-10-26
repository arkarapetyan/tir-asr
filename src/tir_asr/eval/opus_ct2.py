"""Eval candidate MT-1: Helsinki-NLP/opus-mt-hy-en on CTranslate2 (D-015, D-049, D-051). Adapter.

The model was converted on the laptop with:
  HF_HUB_OFFLINE=1 uv run --no-sync ct2-transformers-converter --model Helsinki-NLP/opus-mt-hy-en
    --output_dir models/opus-mt-hy-en-ct2-float16 --quantization float16
`compute_type` and `beam_size` come from `Params`, the same as for NLLB (D-015, D-033).
The program does not import this module.
"""

from pathlib import Path

from tir_asr.config import Params

# This import loads the CUDA 12 cuBLAS, then ctranslate2 (D-030). Thus the imports of
# ctranslate2 and transformers below are inside the constructor, after it.
from tir_asr.mt.ct2_nllb import MtError

MODEL_REPO = "Helsinki-NLP/opus-mt-hy-en"
MODEL_DIR = Path("models") / "opus-mt-hy-en-ct2-float16"  # from the project folder


class OpusCt2Translator:
    """`translate(text)` gives the English text of one Armenian text, with no context."""

    def __init__(self, params: Params, model_dir: Path = MODEL_DIR) -> None:
        import ctranslate2
        from transformers import AutoTokenizer

        if not (model_dir / "model.bin").is_file():
            raise MtError(f"mt: CTranslate2 model not found: {model_dir.resolve()}")
        self._tokenizer = AutoTokenizer.from_pretrained(MODEL_REPO, local_files_only=True)
        self._translator = ctranslate2.Translator(
            str(model_dir), device="cuda", compute_type=params.mt_compute_type
        )
        self._beam_size = params.mt_beam_size

    def translate(self, text: str) -> str:
        if not text.strip():
            raise MtError("mt: empty input text")
        source = self._tokenizer.convert_ids_to_tokens(self._tokenizer.encode(text))
        result = self._translator.translate_batch([source], beam_size=self._beam_size)
        target = result[0].hypotheses[0]
        return self._tokenizer.decode(self._tokenizer.convert_tokens_to_ids(target))
