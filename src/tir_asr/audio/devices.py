"""The device list of `--list-devices` (ARCHITECTURE.md section 2.1, D-054).

Core module: it imports no audio-device package (D-021). The adapter `soundcard_source.py` gives
the records; this module only makes the text, so that a unit test can check it.
"""

from collections.abc import Sequence
from dataclasses import dataclass

DEFAULT_MARK = "*"
GROUPS = (
    ("Microphones (--mic):", False),
    ("System audio (--system):", True),
)


@dataclass(frozen=True)
class SourceInfo:
    """One PulseAudio source: its exact id, its description, and its kind."""

    id: str
    name: str
    monitor: bool  # True for the monitor of an output (the system audio, F1)


def format_source_list(sources: Sequence[SourceInfo], default_mic: str, default_system: str) -> str:
    """The text of `--list-devices`: the microphones, then the monitors, in the server order.

    A `*` marks the default of each group: the source that the program uses when the flag is not
    given. The id is exact; `--mic` and `--system` take it (D-041, D-054).
    """
    lines = []
    for heading, monitor in GROUPS:
        default = default_system if monitor else default_mic
        group = [source for source in sources if source.monitor == monitor]
        lines.append(heading)
        if not group:
            lines.append("  (none)")
        for source in group:
            mark = DEFAULT_MARK if source.id == default else " "
            lines.append(f"{mark} {source.id}  {source.name}")
    lines.append(f"{DEFAULT_MARK} = the default, used when the flag is not given")
    return "\n".join(lines) + "\n"
