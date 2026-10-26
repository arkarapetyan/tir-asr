"""CTranslate2 MT adapter: the Translator on the GPU (ARCHITECTURE.md section 2.4).

Model: facebook/nllb-200-distilled-600M, converted to CTranslate2, on `cuda`, with
`compute_type = mt_compute_type` (D-015) and `beam_size = mt_beam_size` (D-033). The tokenizer
comes from the Hugging Face cache only; nothing downloads at runtime.

The CTranslate2 4.8.3 wheels need the CUDA 12 cuBLAS. Before `import ctranslate2`, this module
loads it from the package `nvidia-cublas-cu12` (D-030). The program needs no LD_LIBRARY_PATH.

This module imports `ctranslate2` and `transformers`. Only `app.py` and the model tests
import it. The core modules do not (D-021, T-IMPORT-01).

The adapter has no warm-up method. The pipeline does the warm-up call (D-022, D-037).
"""

import ctypes
from importlib import metadata
from pathlib import Path

from tir_asr.config import MT_SRC_LANG, MT_TGT_LANG, Params
from tir_asr.errors import TirError

MT_REPO = "facebook/nllb-200-distilled-600M"
MT_MODEL_DIR = Path("models") / "nllb-200-distilled-600M-ct2-float16"  # from the project folder
CONVERT_COMMAND = (  # the command that made the model on Aren's laptop (C2)
    f"HF_HUB_OFFLINE=1 uv run --no-sync ct2-transformers-converter --model {MT_REPO} "
    f"--output_dir {MT_MODEL_DIR} --quantization float16"
)
CUBLAS_PACKAGE = "nvidia-cublas-cu12"
CUBLAS_FILES = ("libcublasLt.so.12", "libcublas.so.12")  # libcublas.so.12 needs libcublasLt


class MtError(TirError):
    """An error of the MT adapter. The message is `mt: <cause>`."""


def _preload_cublas() -> None:
    """Load the CUDA 12 cuBLAS with RTLD_GLOBAL, so that CTranslate2 finds it (D-030)."""
    try:
        files = metadata.files(CUBLAS_PACKAGE) or []
    except metadata.PackageNotFoundError as error:
        raise MtError(
            f"mt: libcublas.so.12 not found in the package {CUBLAS_PACKAGE} "
            "(the package is not installed)"
        ) from error
    for name in CUBLAS_FILES:
        paths = [file.locate() for file in files if file.name == name]
        if len(paths) != 1:
            raise MtError(f"mt: {name} not found in the package {CUBLAS_PACKAGE}")
        ctypes.CDLL(str(paths[0]), mode=ctypes.RTLD_GLOBAL)


_preload_cublas()

# These imports come after the cuBLAS preload (D-030).
import ctranslate2  # noqa: E402
from transformers import AutoTokenizer  # noqa: E402


class Ct2NllbTranslator:
    """`translate(text)` gives the English text of one Armenian text, with no context.

    The constructor loads the tokenizer and the model on the GPU. `model_dir` locates the
    converted model; it is not a tunable parameter (D-037).
    """

    def __init__(self, params: Params, model_dir: Path = MT_MODEL_DIR) -> None:
        if not (model_dir / "model.bin").is_file():
            raise MtError(
                f"mt: CTranslate2 model not found: {model_dir.resolve()}. "
                f"Convert it with: {CONVERT_COMMAND}"
            )
        self._tokenizer = AutoTokenizer.from_pretrained(
            MT_REPO, src_lang=MT_SRC_LANG, local_files_only=True
        )
        self._translator = ctranslate2.Translator(
            str(model_dir), device="cuda", compute_type=params.mt_compute_type
        )
        self._beam_size = params.mt_beam_size

    def translate(self, text: str) -> str:
        """Take a non-empty Armenian text. Return the English text."""
        if not text.strip():
            raise MtError("mt: empty input text")
        source = self._tokenizer.convert_ids_to_tokens(self._tokenizer.encode(text))
        result = self._translator.translate_batch(
            [source], target_prefix=[[MT_TGT_LANG]], beam_size=self._beam_size
        )
        target = result[0].hypotheses[0][1:]  # remove the target language token
        return self._tokenizer.decode(self._tokenizer.convert_tokens_to_ids(target))
