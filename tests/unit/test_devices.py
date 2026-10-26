"""T-DEV-01: the text of the device list (C4, branch c4-audio).

Contract: ARCHITECTURE.md section 2.1. Decision: D-054. The adapter gives the records; the core
function `format_source_list` makes the text of `--list-devices`.
"""

from tir_asr.audio.devices import SourceInfo, format_source_list

SOURCES = [
    SourceInfo("mic-a", "Laptop microphone", monitor=False),
    SourceInfo("out-a.monitor", "Monitor of HDMI", monitor=True),
    SourceInfo("mic-b", "USB microphone", monitor=False),
    SourceInfo("out-b.monitor", "Monitor of Headphones", monitor=True),
]


def test_dev_01_full_list_marks_the_defaults():
    text = format_source_list(SOURCES, "mic-a", "out-b.monitor")

    assert text == (
        "Microphones (--mic):\n"
        "* mic-a  Laptop microphone\n"
        "  mic-b  USB microphone\n"
        "System audio (--system):\n"
        "  out-a.monitor  Monitor of HDMI\n"
        "* out-b.monitor  Monitor of Headphones\n"
        "* = the default, used when the flag is not given\n"
    )


def test_dev_01_group_with_no_source():
    microphones = [source for source in SOURCES if not source.monitor]

    text = format_source_list(microphones, "mic-a", "out-b.monitor")

    assert text == (
        "Microphones (--mic):\n"
        "* mic-a  Laptop microphone\n"
        "  mic-b  USB microphone\n"
        "System audio (--system):\n"
        "  (none)\n"
        "* = the default, used when the flag is not given\n"
    )
