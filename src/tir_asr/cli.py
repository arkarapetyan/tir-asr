"""Command line: the `argparse` interface (ARCHITECTURE.md section 2.7, D-037, D-043, D-054).

`cli.py` has no other work. It imports `app` only after the parse, so that `--help` imports no
model and no audio-device package (D-021, T-CLI-01). The device flags take exact source ids;
`--list-devices` prints them (F1, D-054). `--seamless` selects the P4 text step (D-062 part 4).
"""

import argparse

DESCRIPTION = "Live Armenian speech transcription and English translation in the terminal."


def main(argv: list[str] | None = None) -> int:
    """Parse the command line, then run the program or print the devices. Return the exit code."""
    parser = argparse.ArgumentParser(prog="tir-asr", description=DESCRIPTION)
    parser.add_argument(
        "--mic",
        metavar="ID",
        help="exact source id of the microphone (label Me); default: the default microphone",
    )
    parser.add_argument(
        "--system",
        metavar="ID",
        help="exact source id of the system audio (label System), normally a monitor; "
        "default: the monitor of the default output",
    )
    parser.add_argument(
        "--seamless",
        action="store_true",
        help="P4: one Seamless model gives the Armenian text and the English text; "
        "default: P1, NeMo ASR, then NLLB MT",
    )
    parser.add_argument(
        "--list-devices",
        action="store_true",
        help="print the sources with their exact ids and the defaults, then stop",
    )
    args = parser.parse_args(argv)
    if args.mic is not None and args.mic == args.system:
        parser.error(f"--mic and --system select the same source {args.mic}")

    from tir_asr import app  # after the parse (T-CLI-01)

    if args.list_devices:
        return app.list_devices()
    return app.main(mic=args.mic, system=args.system, seamless=args.seamless)
