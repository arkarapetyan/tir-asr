"""T-CLI-01: `tir-asr --help` (ARCHITECTURE.md section 2.7, D-037, D-043).

`cli.py` is only the `argparse` interface. It imports `app` after the parse, so `--help`
imports no model and no audio-device package (D-021). Case (a) calls `main` in a new Python
process and then checks `sys.modules`. Case (b) runs the installed command from
`[project.scripts]`; it exists after `uv sync`.
"""

import subprocess
import sys
from pathlib import Path

FORBIDDEN = ["torch", "nemo", "ctranslate2", "silero_vad", "soundcard", "transformers"]
FORBIDDEN += ["tir_asr.app"]
USAGE = "usage: tir-asr"

HELP_SCRIPT = f"""
import sys
from tir_asr.cli import main

try:
    main(["--help"])
except SystemExit as stop:
    code = stop.code
else:
    code = "no exit"
found = sorted(name for name in {FORBIDDEN!r} if name in sys.modules)
print(f"RESULT code={{code}} imports={{found}}")
"""


def test_cli_01_help_in_a_new_process_imports_no_laptop_package(tmp_path):
    # A script file, not `python -c`: the same way as the program starts.
    script = tmp_path / "help.py"
    script.write_text(HELP_SCRIPT, encoding="utf-8")

    result = subprocess.run([sys.executable, "-I", str(script)], capture_output=True, text=True)

    assert result.returncode == 0, result.stderr
    assert result.stdout.startswith(USAGE), result.stdout
    assert result.stdout.splitlines()[-1] == "RESULT code=0 imports=[]", result.stdout


def test_cli_01_installed_command_gives_the_help():
    command = Path(sys.executable).with_name("tir-asr")
    assert command.exists(), f"{command} does not exist; run `uv sync` one time (D-043)"

    result = subprocess.run([str(command), "--help"], capture_output=True, text=True)

    assert result.returncode == 0, result.stderr
    assert result.stdout.startswith(USAGE), result.stdout
