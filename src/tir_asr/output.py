"""Terminal output: one block for each segment (ARCHITECTURE.md section 2.5).

Decisions: D-024 (format, one write), D-031 (empty ASR text), D-040 (interface, blank line),
D-059 (the `spk` step on the system side), D-063 part 2 (one text step for P4: `s2t`).
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
    printed steps can differ from the printed total by rounding (section 2.5). The text steps
    have the names of `line.steps`: two names (`asr`, `mt`), or one name for one step from the
    segment close to the end of both texts (P4: `s2t`, D-063 part 2).
    """
    vad = line.closed - line.speech_end
    total = line.write - line.speech_end
    head = f"[{_clock(line.start - session_start)}] {line.label}"
    first = line.steps[0]

    if not line.hy:
        # D-031: no English step, so the block has no EN line, no second step, and no out step.
        steps = f"vad {vad:.2f}s, {first} {line.asr_end - line.closed:.2f}s"
        rows = [head, f" HY: {NO_TEXT}"]
    else:
        if len(line.steps) == 1:  # one step gives both texts (P4)
            steps = f"vad {vad:.2f}s, {first} {line.mt_end - line.closed:.2f}s"
        else:
            asr = line.asr_end - line.closed
            mt = line.mt_end - line.asr_end
            _, second = line.steps
            steps = f"vad {vad:.2f}s, {first} {asr:.2f}s, {second} {mt:.2f}s"
        if line.spk_end is None:
            out = line.write - line.mt_end
        else:  # D-059: the speaker step comes after MT
            spk = line.spk_end - line.mt_end
            out = line.write - line.spk_end
            steps += f", spk {spk:.2f}s"
        steps += f", out {out:.2f}s"
        rows = [head, f" HY: {line.hy}", f" EN: {line.en}"]

    rows.append(f" [Latency: {steps} | Total {total:.2f}s]")
    return "\n".join(rows) + "\n\n"


def write_block(line: Line, session_start: float, stream: TextIO) -> None:
    """Write one block with one `write` call, then flush (D-024).

    One call for each block, so that the lines of two sources do not mix (C4).
    """
    stream.write(format_block(line, session_start))
    stream.flush()
