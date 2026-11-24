"""T-CFG-01, T-CFG-02: the approved parameters (RULES.md R10, ARCHITECTURE.md sections 2.7, 6).

T-CFG-01: the expected values are written out here from the section 6 table. They do not come
from `config.py`. A new parameter in `Params` without Aren's approval makes this test fail.

T-CFG-02: the startup log has one line for each parameter, with its name and value (D-043).

C10 (D-081 point 5): the NLLB parameters `mt_compute_type` and `mt_beam_size` left with NLLB.

C11 (D-072 part 5): T-CFG-02 checks the format and the order of the lines, not a value.
"""

from dataclasses import asdict, fields

from tir_asr.config import Params, parameter_lines

SECTION_6 = {
    "vad_threshold": 0.5,
    "vad_end_threshold": 0.35,
    "vad_min_silence_ms": 500,
    "vad_speech_pad_ms": 30,
    "vad_min_speech_ms": 250,
    "vad_max_speech_s": 15,
    "spk_threshold": 0.50,
    "spk_min_new_s": 1.0,
}


def test_cfg_01_each_value_is_equal_to_the_section_6_table():
    assert asdict(Params()) == SECTION_6


def test_cfg_02_startup_log_has_one_line_for_each_parameter():
    params = Params()

    lines = parameter_lines(params)

    assert lines == [
        f"parameter {field.name} = {getattr(params, field.name)}" for field in fields(params)
    ]
    assert lines[0] == f"parameter vad_threshold = {params.vad_threshold}"
