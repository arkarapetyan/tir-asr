"""T-CLI-01 to T-CLI-03: `tir-asr --help`, the device flags, and `--seamless` (ARCHITECTURE 2.7).

Decisions: D-037, D-043, D-054, D-062 part 4. `cli.py` is only the `argparse` interface. It
imports `app` after the parse, so `--help` imports no model and no audio-device package (D-021).
T-CLI-01 case (a) calls `main` in a new Python process and then checks `sys.modules`. Case (b)
runs the installed command from `[project.scripts]`; it exists after `uv sync`. T-CLI-02 and
T-CLI-03 replace `app.main` and `app.list_devices` with fakes; `app` imports no `laptop` package
at the top.
"""

import subprocess
import sys
from pathlib import Path

import pytest

from tir_asr import app, cli

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


@pytest.fixture
def fake_app(monkeypatch):
    """Replace `app.main` and `app.list_devices`. Return the list of their calls."""
    calls = []

    def main(**kwargs):
        calls.append(("main", kwargs))
        return 7

    def list_devices():
        calls.append(("list_devices", {}))
        return 3

    monkeypatch.setattr(app, "main", main)
    monkeypatch.setattr(app, "list_devices", list_devices)
    return calls


def test_cli_02_device_flags_go_to_the_program(fake_app):
    assert cli.main(["--mic", "a", "--system", "b"]) == 7
    assert fake_app == [("main", {"mic": "a", "system": "b", "seamless": False})]


def test_cli_02_no_flags_select_the_defaults(fake_app):
    assert cli.main([]) == 7
    assert fake_app == [("main", {"mic": None, "system": None, "seamless": False})]


def test_cli_02_list_devices_does_not_start_the_program(fake_app):
    assert cli.main(["--list-devices"]) == 3
    assert fake_app == [("list_devices", {})]


def test_cli_02_same_source_for_both_flags(fake_app, capsys):
    with pytest.raises(SystemExit) as stop:
        cli.main(["--mic", "x", "--system", "x"])

    assert stop.value.code == 2
    error = capsys.readouterr().err
    assert error.endswith("tir-asr: error: --mic and --system select the same source x\n"), error
    assert fake_app == []


def test_cli_03_seamless_selects_p4(fake_app):
    assert cli.main(["--seamless"]) == 7
    assert cli.main(["--seamless", "--mic", "a"]) == 7
    assert fake_app == [
        ("main", {"mic": None, "system": None, "seamless": True}),
        ("main", {"mic": "a", "system": None, "seamless": True}),
    ]


def test_cli_03_help_names_the_flag(fake_app, capsys):
    with pytest.raises(SystemExit) as stop:
        cli.main(["--help"])

    assert stop.value.code == 0
    assert "--seamless" in capsys.readouterr().out
    assert fake_app == []
