"""Terminal output: one block for each segment (ARCHITECTURE.md section 2.5).

Decisions: D-024 (format, one write), D-031 (empty ASR text), D-040 (interface, blank line).
This module imports no model and no audio-device package (D-021).
"""

from typing import TextIO

from tir_asr.types import Line

NO_TEXT = "(no text)"


def _clock(seconds: float) -> str:
    """`hh:mm:ss`. The seconds are cut, not rounded (D-040)."""
    whole = int(seconds)
    return f"{whole // 3600:02d}:{whole % 3600 // 60:02d}:{whole % 60:02d}"


def format_block(line: Line, session_start: float) -> str:
    """The text of one block. The block ends with an empty line (D-040).

    Each printed step is the rounded raw step. The total is the rounded raw total, so the
    printed steps can differ from the printed total by rounding (section 2.5).
    """
    vad = line.closed - line.speech_end
    asr = line.asr_end - line.closed
    total = line.write - line.speech_end
    head = f"[{_clock(line.start - session_start)}] {line.label}"

    if not line.hy:
        # D-031: no MT call, so the block has no EN line and no mt and out steps.
        steps = f"vad {vad:.2f}s, asr {asr:.2f}s"
        rows = [head, f" HY: {NO_TEXT}"]
    else:
        mt = line.mt_end - line.asr_end
        out = line.write - line.mt_end
        steps = f"vad {vad:.2f}s, asr {asr:.2f}s, mt {mt:.2f}s, out {out:.2f}s"
        rows = [head, f" HY: {line.hy}", f" EN: {line.en}"]

    rows.append(f" [Latency: {steps} | Total {total:.2f}s]")
    return "\n".join(rows) + "\n\n"


def write_block(line: Line, session_start: float, stream: TextIO) -> None:
    """Write one block with one `write` call, then flush (D-024).

    One call for each block, so that the lines of two sources do not mix (C4).
    """
    stream.write(format_block(line, session_start))
    stream.flush()
