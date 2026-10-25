"""T-OUT-01 to T-OUT-04: the output block (ARCHITECTURE.md section 2.5, D-024, D-031, D-040).

All times are `time.monotonic()` values. The session starts at SESSION_START.
"""

from dataclasses import replace

from tir_asr.output import format_block, write_block
from tir_asr.types import Line

SESSION_START = 1000.0

# The block of make_line(). It ends with an empty line, so that the blocks have a blank line
# between them (D-040).
BLOCK = (
    "[00:01:12] Me\n"
    " HY: Լավ եմ, շնորհակալություն։\n"
    " EN: I'm fine, thank you.\n"
    " [Latency: vad 0.53s, asr 0.41s, mt 0.18s, out 0.00s | Total 1.12s]\n"
    "\n"
)


def make_line(**changes) -> Line:
    """A line that starts 72.4 s after the session start, with the steps 0.53/0.41/0.18/0.00 s."""
    line = Line(
        label="Me",
        start=SESSION_START + 72.4,
        hy="Լավ եմ, շնորհակալություն։",
        en="I'm fine, thank you.",
        speech_end=1075.0,
        closed=1075.53,
        asr_end=1075.94,
        mt_end=1076.12,
        write=1076.12,
    )
    return replace(line, **changes)


def latency_line(block: str) -> str:
    lines = [line for line in block.splitlines() if line.startswith(" [Latency:")]
    assert len(lines) == 1, block
    return lines[0]


class FakeStream:
    """Records each call in order."""

    def __init__(self):
        self.calls = []

    def write(self, text):
        self.calls.append(("write", text))
        return len(text)

    def flush(self):
        self.calls.append(("flush",))


def test_out_01_block_has_the_format_of_the_architecture():
    assert format_block(make_line(), SESSION_START) == BLOCK


def test_out_01_time_is_hours_minutes_seconds_since_the_session_start():
    # 3671.9 s = 1 h 1 min 11.9 s. The seconds are cut, not rounded (D-040).
    block = format_block(make_line(start=SESSION_START + 3671.9), SESSION_START)

    assert block.splitlines()[0] == "[01:01:11] Me"


def test_out_02_total_comes_from_the_raw_values():
    line = make_line(
        speech_end=2000.0,
        closed=2000.534,
        asr_end=2000.947,
        mt_end=2001.124,
        write=2001.128,
    )

    # The rounded steps add up to 1.12 s. The total is the rounded raw total: 1.128 s.
    assert latency_line(format_block(line, SESSION_START)) == (
        " [Latency: vad 0.53s, asr 0.41s, mt 0.18s, out 0.00s | Total 1.13s]"
    )


def test_out_03_empty_asr_text_gives_a_short_block():
    # The write comes 0.03 s after the ASR end, so the total (0.97 s) is more than vad + asr.
    line = make_line(hy="", en="", mt_end=1075.94, write=1075.97)

    block = format_block(line, SESSION_START)

    assert block == (
        "[00:01:12] Me\n HY: (no text)\n [Latency: vad 0.53s, asr 0.41s | Total 0.97s]\n\n"
    )
    assert "EN:" not in block


def test_out_04_one_write_and_one_flush_for_each_block():
    stream = FakeStream()

    write_block(make_line(), SESSION_START, stream)

    assert stream.calls == [("write", BLOCK), ("flush",)]
