"""T-IMPORT-01: core modules have no `laptop` import (D-021).

Each core module is imported in a new Python process. Then the process checks `sys.modules`.
The core modules are all modules of the package except the adapters (ARCHITECTURE.md
section 2). Only an adapter may import a `laptop` package.
"""

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

FORBIDDEN = [
    "torch",
    "nemo",
    "ctranslate2",
    "silero_vad",
    "soundcard",
    "transformers",
]

ADAPTERS = {
    "tir_asr.segment.silero",
    "tir_asr.asr.nemo_rnnt",
    "tir_asr.mt.ct2_nllb",
    "tir_asr.audio.soundcard_source",
    "tir_asr.app",
    "tir_asr.eval.nemo_ctc",
    "tir_asr.eval.opus_ct2",
    "tir_asr.eval.buzz_whisper",
    "tir_asr.eval.seamless",
    "tir_asr.speakers.titanet",
    "tir_asr.text.seamless",
}

# The core modules that the branch must have. Each component branch adds its own modules.
REQUIRED = {
    "tir_asr.types",
    "tir_asr.config",
    "tir_asr.segment",
    "tir_asr.segment.endpoint",
    "tir_asr.asr",
    "tir_asr.mt",
    "tir_asr.output",
    "tir_asr.audio",
    "tir_asr.audio.devices",
    "tir_asr.errors",
    "tir_asr.pipeline",
    "tir_asr.cli",
    "tir_asr.eval",
    "tir_asr.eval.normalize",
    "tir_asr.eval.metrics",
    "tir_asr.eval.data",
    "tir_asr.eval.run",
    "tir_asr.speakers",
    "tir_asr.speakers.cluster",
    "tir_asr.eval.nearest",
    "tir_asr.eval.streams",
    "tir_asr.eval.spk_run",
    "tir_asr.speakers.labeler",
    "tir_asr.text",
    "tir_asr.text.step",
    "tir_asr.text.clean",
}

CHECK = """
import importlib, sys
importlib.import_module(sys.argv[1])
found = sorted(name for name in {forbidden!r} if name in sys.modules)
print(",".join(found))
sys.exit(1 if found else 0)
"""


def core_modules() -> set[str]:
    root = Path(importlib.util.find_spec("tir_asr").submodule_search_locations[0])
    names = set()
    for path in root.rglob("*.py"):
        parts = path.relative_to(root.parent).with_suffix("").parts
        if parts[-1] == "__init__":
            parts = parts[:-1]
        names.add(".".join(parts))
    return {name for name in names if name not in ADAPTERS}


def test_import_01_the_branch_has_its_core_modules():
    assert REQUIRED <= core_modules()


@pytest.mark.parametrize("module", sorted(core_modules()))
def test_import_01_core_module_imports_no_laptop_package(module):
    result = subprocess.run(
        [sys.executable, "-I", "-c", CHECK.format(forbidden=FORBIDDEN), module],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, (
        f"{module}: imports {result.stdout.strip() or 'nothing'}; stderr: {result.stderr.strip()}"
    )
