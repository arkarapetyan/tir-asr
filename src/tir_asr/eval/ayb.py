"""Eval candidate: Metric-AI/Ayb-0.5-4B as the Armenian to English translator (D-072).

Adapter: it imports torch and transformers (D-021). The model files come from the local folder
`models/ayb-0.5-4b` (Aren's download; `models/` is in .gitignore); nothing downloads.

- The text model only: `AutoModelForCausalLM` gives `Qwen3_5ForCausalLM`, which does not load
  the vision weights (transformers 5.20.2, `_keys_to_ignore_on_load_unexpected`).
- The messages come from `tir_asr.eval.c9.build_messages` (the approved prompt, D-072 part 2).
- Greedy decode, thinking off (`enable_thinking=False` in the chat template), at most
  `MAX_NEW_TOKENS` new tokens.
- Forms: "bf16" puts the full model on the GPU in bfloat16. Other forms (quantized, CPU) come
  only after the install check numbers and Aren's approval (D-072 part 2).

The program does not import this module.
"""

from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from tir_asr.errors import TirError

MODEL_DIR = Path("models") / "ayb-0.5-4b"  # from the project folder
MAX_NEW_TOKENS = 256
FORMS = ("bf16",)


class AybError(TirError):
    """An error of the Ayb eval adapter. The message is `mt: <cause>`."""


class AybTranslator:
    """`translate_messages(messages)` gives the English text of the last user message."""

    def __init__(self, model_dir: Path, form: str = "bf16") -> None:
        if form not in FORMS:
            raise AybError(f"mt: unknown Ayb form {form}, expected one of {', '.join(FORMS)}")
        if not torch.cuda.is_available():
            raise AybError("mt: CUDA is not available")
        model_dir = Path(model_dir)
        if not (model_dir / "config.json").is_file():
            raise AybError(f"mt: no Ayb model in {model_dir} (download it first)")
        self.form = form
        self._tokenizer = AutoTokenizer.from_pretrained(model_dir, local_files_only=True)
        model = AutoModelForCausalLM.from_pretrained(
            model_dir, dtype=torch.bfloat16, local_files_only=True
        )
        self._model = model.to("cuda").eval()
        self.model_class = type(self._model).__name__

    def translate_messages(self, messages: list[dict]) -> str:
        inputs = self._tokenizer.apply_chat_template(
            messages,
            add_generation_prompt=True,
            enable_thinking=False,
            tokenize=True,
            return_dict=True,
            return_tensors="pt",
        ).to("cuda")
        with torch.inference_mode():
            tokens = self._model.generate(**inputs, max_new_tokens=MAX_NEW_TOKENS, do_sample=False)
        new = tokens[0][inputs["input_ids"].shape[-1] :]
        return self._tokenizer.decode(new, skip_special_tokens=True).strip()
