"""T-CFG-01: the approved parameters (RULES.md R10, ARCHITECTURE.md section 6).

The expected values are written out here from the section 6 table. They do not come from
`config.py`. A new parameter in `Params` without Aren's approval makes this test fail.
"""

from dataclasses import asdict

from tir_asr.config import Params

SECTION_6 = {
    "mt_compute_type": "float16",
    "vad_threshold": 0.5,
    "vad_end_threshold": 0.35,
    "vad_min_silence_ms": 500,
    "vad_speech_pad_ms": 30,
    "vad_min_speech_ms": 250,
    "vad_max_speech_s": 10,
    "mt_beam_size": 2,
}


def test_cfg_01_each_value_is_equal_to_the_section_6_table():
    assert asdict(Params()) == SECTION_6
