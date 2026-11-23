"""Eval candidate: Metric-AI/Ayb-0.5-4B as the Armenian to English translator (D-072, D-076).

Adapter: it imports torch and transformers (D-021). The model files come from the local folder
`models/ayb-0.5-4b` (Aren's download; `models/` is in .gitignore); nothing downloads.

- The text model only: `AutoModelForCausalLM` gives `Qwen3_5ForCausalLM`, which ignores the
  vision and MTP weights of the checkpoint (`_keys_to_ignore_on_load_unexpected`, transformers
  5.20.2).
- The load fails loudly (R10): transformers gives a missing parameter random values and only
  prints a report. Thus a missing, mismatched, or unexpected key, or a load error, gives `AybError`.
- The messages come from `tir_asr.eval.c9.build_messages` (the approved prompt, D-072 part 2).
- Greedy decode, thinking off (`enable_thinking=False` in the chat template), at most
  `MAX_NEW_TOKENS` new tokens.
- Forms (`FORM_PARAMS`, D-076). Both need the dependency group `c9-eval` (accelerate,
  bitsandbytes):
  - "nf4": the program form, on the GPU. bitsandbytes 4-bit NF4 for the linear layers; the
    embedding (tied to the output layer) and the norms stay in bfloat16.
  - "bf16-cpu": the upper bound, for the eval only. bfloat16; accelerate puts the layers that do
    not fit under the GPU limit into CPU memory.
- Linear attention: with no `fla` and no `causal_conv1d` package, transformers uses its torch
  code (`test-results/c9-ayb-env.txt`).

The program does not import this module.
"""

from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

from tir_asr.errors import TirError

MODEL_DIR = Path("models") / "ayb-0.5-4b"  # from the project folder
MAX_NEW_TOKENS = 256
MIB = 2**20
# The parameters of each form (D-076, approved by Aren on 2026-11-23). The run file keeps them.
FORM_PARAMS = {
    # The defaults of BitsAndBytesConfig are "fp4" and float32. Double quantization saves about
    # 160 MiB [calc], and the space next to OhanASR and TitaNet is small.
    "nf4": {"quant_type": "nf4", "compute_dtype": "bfloat16", "double_quant": True},
    # 7000 MiB of weights on the GPU keeps about 1000 MiB for the CUDA context and the
    # activations [calc]; the other layers go into CPU memory.
    "bf16-cpu": {"dtype": "bfloat16", "max_memory": {0: "7000MiB", "cpu": "16GiB"}},
}
FORMS = tuple(FORM_PARAMS)
LOAD_PROBLEMS = ("missing_keys", "mismatched_keys", "unexpected_keys", "error_msgs")


class AybError(TirError):
    """An error of the Ayb eval adapter. The message is `mt: <cause>`."""


class AybTranslator:
    """`translate_messages(messages)` gives the English text of the last user message."""

    def __init__(self, model_dir: Path, form: str = "nf4") -> None:
        if form not in FORMS:
            raise AybError(f"mt: unknown Ayb form {form}, expected one of {', '.join(FORMS)}")
        if not torch.cuda.is_available():
            raise AybError("mt: CUDA is not available")
        model_dir = Path(model_dir)
        if not (model_dir / "config.json").is_file():
            raise AybError(f"mt: no Ayb model in {model_dir} (download it first)")
        self.form = form
        self.form_params = FORM_PARAMS[form]
        self._tokenizer = AutoTokenizer.from_pretrained(model_dir, local_files_only=True)
        model, info = AutoModelForCausalLM.from_pretrained(
            model_dir, local_files_only=True, output_loading_info=True, **_load_kwargs(form)
        )
        _check_load(info)
        self._model = model.eval()
        self.model_class = type(model).__name__
        self.footprint_mib = model.get_memory_footprint() // MIB
        device_map = getattr(model, "hf_device_map", None) or {}
        self.cpu_modules = sorted(name for name, device in device_map.items() if device == "cpu")

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


def _load_kwargs(form: str) -> dict:
    params = FORM_PARAMS[form]
    if form == "nf4":
        quantization = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type=params["quant_type"],
            bnb_4bit_compute_dtype=getattr(torch, params["compute_dtype"]),
            bnb_4bit_use_double_quant=params["double_quant"],
        )
        return {"dtype": torch.bfloat16, "device_map": {"": 0}, "quantization_config": quantization}
    return {
        "dtype": getattr(torch, params["dtype"]),
        "device_map": "auto",
        "max_memory": dict(params["max_memory"]),
    }


def _check_load(info: dict) -> None:
    """Stop when a weight of the text model did not load (R10)."""
    problems = {name: sorted(str(item) for item in info[name]) for name in LOAD_PROBLEMS}
    problems = {name: items for name, items in problems.items() if items}
    if problems:
        counts = ", ".join(f"{len(items)} {name}" for name, items in problems.items())
        name, items = next(iter(problems.items()))
        raise AybError(f"mt: the Ayb weights did not load ({counts}); first {name}: {items[0]}")
