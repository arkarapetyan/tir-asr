"""Constants and approved parameters (ARCHITECTURE.md sections 5 and 6).

Only Aren adds a parameter (RULES.md R10). Each parameter in `Params` is in the table of
ARCHITECTURE.md section 6 with its reason and its approval date. T-CFG-01 checks the values.
"""

from dataclasses import dataclass, fields

# Constants: fixed by a model, not tunable (ARCHITECTURE.md section 5).
SAMPLE_RATE = 16_000  # Hz. The ASR model and Silero VAD need 16 kHz.
VAD_FRAME = 512  # samples. The only frame size that Silero VAD accepts at 16 kHz.
WARMUP_AUDIO_S = 2.0  # s of zeros. The synthetic input of the ASR warm-up call (D-022, R11).
WARMUP_TEXT = "Բարև, ինչպե՞ս ես։"  # The synthetic input of the MT warm-up call (D-022).
MT_SRC_LANG = "hye_Armn"  # NLLB language code: Armenian.
MT_TGT_LANG = "eng_Latn"  # NLLB language code: English.


@dataclass(frozen=True)
class Params:
    """The approved parameters. The default values are the program values."""

    mt_compute_type: str = "float16"  # D-015
    vad_threshold: float = 0.5  # probability, D-026
    vad_end_threshold: float = 0.35  # probability, D-026
    vad_min_silence_ms: int = 500  # ms, D-027 (start value)
    vad_speech_pad_ms: int = 30  # ms, D-026
    vad_min_speech_ms: int = 250  # ms, D-026
    vad_max_speech_s: int = 10  # s, D-026
    mt_beam_size: int = 2  # D-033
    spk_threshold: float = 0.50  # cosine, D-058 (start value; L-06 tests it)
    spk_min_new_s: float = 1.0  # s, D-057 part 5B, D-058 (start value; L-06 tests it)


def parameter_lines(params: Params) -> list[str]:
    """One startup log line for each parameter, in the field order (T-CFG-02, D-043)."""
    return [f"parameter {field.name} = {getattr(params, field.name)}" for field in fields(params)]
