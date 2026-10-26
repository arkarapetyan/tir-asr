"""Command line: the `argparse` interface (ARCHITECTURE.md section 2.7, D-037, D-043).

`cli.py` has no other work. It imports `app` only after the parse, so that `--help` imports no
model and no audio-device package (D-021, T-CLI-01). C2 has no flags except `--help`; C4 adds
the device flags.
"""

import argparse

DESCRIPTION = "Live Armenian speech transcription and English translation in the terminal."


def main(argv: list[str] | None = None) -> int:
    """Parse the command line, then run the program. Return the exit code."""
    parser = argparse.ArgumentParser(prog="tir-asr", description=DESCRIPTION)
    parser.parse_args(argv)

    from tir_asr import app  # after the parse (T-CLI-01)

    return app.main()
