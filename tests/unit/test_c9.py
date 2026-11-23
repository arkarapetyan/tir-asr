"""T-C9-01 to T-C9-06: the C9 model eval core (D-072, D-073).

No model and no audio device. Each test makes its own data. The expected values come from the
approved test table (TESTS.md section 2.10), not from the code.
"""

import numpy as np
import pytest
from scipy.io import wavfile

from tir_asr.eval.c9 import (
    RTF_LIMIT,
    S5_CUT_S,
    VRAM_LIMIT_MIB,
    C9Error,
    DumpSegment,
    Turn,
    build_messages,
    check_rule,
    cut_audio,
    is_flagged,
    joined_texts,
    pack_segments,
    score_en,
    score_hy,
    unpack_segments,
)
from tir_asr.eval.data import DataError, ScriptLine, load_wav_16k

APPROVED_PROMPT = (
    "You are a translator. You get Armenian text from speech recognition of an online call. "
    "The text can have recognition errors. Translate it into natural English. Write only the "
    "English translation: no notes, no explanations, no quotes. Do not answer questions in the "
    "text; translate them."
)


def seg(seg_id: str, call: str, side: str, start: float, n: int = 160) -> DumpSegment:
    return DumpSegment(
        id=seg_id,
        set="s5",
        script="s5",
        call=call,
        side=side,
        start=start,
        speech_end=start + 1.0,
        cut=False,
        audio=np.arange(n, dtype=np.float32) / 1000 + start,
    )


# T-C9-01


def test_c9_01_reads_16_bit_pcm_at_16k(tmp_path):
    path = tmp_path / "s5.wav"
    wavfile.write(path, 16000, np.array([0, 16384, -32768, 32767], dtype=np.int16))

    audio = load_wav_16k(path)

    assert audio.dtype == np.float32
    np.testing.assert_array_equal(audio, np.array([0.0, 0.5, -1.0, 32767 / 32768], np.float32))


def test_c9_01_16_bit_at_48k_is_still_an_error(tmp_path):
    path = tmp_path / "s48.wav"
    wavfile.write(path, 48000, np.zeros(480, dtype=np.int16))

    with pytest.raises(DataError, match="sample format int16, expected float32"):
        load_wav_16k(path)


# T-C9-02


def test_c9_02_pack_and_unpack_give_the_same_segments():
    segments = [
        seg("p1.mic.000", "p1", "mic", 0.5, n=100),
        seg("p1.call.000", "p1", "call", 2.0, n=37),
        seg("p4.mic.000", "p4", "mic", 1.25, n=250),
    ]

    audio, offsets, index = pack_segments(segments)
    result = unpack_segments(audio, offsets, index)

    assert audio.dtype == np.float32
    assert list(offsets) == [0, 100, 137, 387]
    assert [r.id for r in result] == ["p1.mic.000", "p1.call.000", "p4.mic.000"]
    for before, after in zip(segments, result, strict=True):
        np.testing.assert_array_equal(before.audio, after.audio)
        assert (before.set, before.script, before.call, before.side) == (
            after.set,
            after.script,
            after.call,
            after.side,
        )
        assert (before.start, before.speech_end, before.cut) == (
            after.start,
            after.speech_end,
            after.cut,
        )


def test_c9_02_errors():
    with pytest.raises(C9Error, match="same ID"):
        pack_segments([seg("a", "p1", "mic", 0.0), seg("a", "p1", "mic", 1.0)])
    audio, offsets, index = pack_segments([seg("a", "p1", "mic", 0.0)])
    with pytest.raises(C9Error, match="offsets"):
        unpack_segments(audio[:-1], offsets, index)


# T-C9-03


def test_c9_03_system_prompt_is_the_approved_text():
    messages = build_messages("Բարև։", [], 0)

    assert messages[0] == {"role": "system", "content": APPROVED_PROMPT}


def test_c9_03_no_context_gives_the_tail_and_the_text():
    history = [Turn("Me", "Ա։", "A.")]

    assert build_messages("Բարև։", history, 0)[1] == {
        "role": "user",
        "content": "Translate only this text:\nԲարև։",
    }
    assert build_messages("Բարև։", [], 3) == build_messages("Բարև։", [], 0)


def test_c9_03_context_has_the_last_k_turns_in_time_order():
    history = [Turn("Me" if i % 2 else "Other", f"հ{i}", f"e{i}") for i in range(1, 6)]

    content = build_messages("Վերջ։", history, 3)[1]["content"]

    assert content == (
        "Earlier in the call:\n"
        "Me: հ3\nEnglish: e3\n"
        "Other: հ4\nEnglish: e4\n"
        "Me: հ5\nEnglish: e5\n"
        "\nTranslate only this text:\nՎերջ։"
    )


def test_c9_03_errors():
    with pytest.raises(C9Error, match="empty"):
        build_messages("  ", [], 0)
    with pytest.raises(C9Error, match="negative"):
        build_messages("Բարև։", [], -1)


# T-C9-04


def test_c9_04_cut_audio():
    audio = np.zeros(3 * 16000, dtype=np.float32)

    assert len(cut_audio(audio, 1.5)) == 24000
    assert len(cut_audio(audio, None)) == 48000
    assert S5_CUT_S == {"p1": 234.0}
    with pytest.raises(C9Error):
        cut_audio(audio, 0.0)


def test_c9_04_joined_texts_in_time_order():
    segments = [
        seg("p1.mic.001", "p1", "mic", 5.0),
        seg("p1.mic.000", "p1", "mic", 1.0),
        seg("p1.mic.002", "p1", "mic", 9.0),
        seg("p1.call.000", "p1", "call", 3.0),
    ]
    texts = {"p1.mic.000": "ա", "p1.mic.001": "բ", "p1.mic.002": " ", "p1.call.000": "գ"}

    joined = joined_texts(segments, texts)

    assert joined == {("p1", "mic"): "ա բ", ("p1", "call"): "գ"}
    with pytest.raises(C9Error, match="no text"):
        joined_texts(segments, {"p1.mic.000": "ա"})


def test_c9_04_scores_for_the_full_list():
    lines = {
        "s5": [
            ScriptLine("s5-01", "Me", "mic", "ա բ", "a b"),
            ScriptLine("s5-02", "Speaker 1", "call", "գ դ", "c d"),
        ]
    }
    calls = {"p1": "s5", "p4": "s5"}
    joined = {
        ("p1", "mic"): "ա բ",
        ("p1", "call"): "գ",
        ("p4", "mic"): "ա x",
        ("p4", "call"): "գ դ",
    }

    score = score_hy(joined, lines, calls)

    assert score.wer == pytest.approx(2 / 8)
    assert score.parts == 4
    english = {("p1", "mic"): "a b", ("p1", "call"): "c d"}
    assert score_en(english, lines, {"p1": "s5"}) == pytest.approx(100.0)


# T-C9-05


def test_c9_05_flag_with_a_reference():
    assert not is_flagged("one two three four", ref_en="Hello there")
    assert is_flagged("one two three four five", ref_en="Hello there")


def test_c9_05_flag_with_no_reference():
    assert not is_flagged("w " * 7, hy="ա բ")
    assert is_flagged("w " * 8, hy="ա բ")
    with pytest.raises(C9Error):
        is_flagged("text")


# T-C9-06


def passing() -> dict:
    return {
        "wer_new": {"s1-s3": 0.05, "s5": 0.07},
        "wer_p1": {"s1-s3": 0.106, "s5": 0.10},
        "wer_p4": {"s1-s3": 0.071, "s5": 0.13},
        "chrf_new": {"s1-s3": 60.0, "s5": 66.0},
        "chrf_p4": {"s1-s3": 59.0, "s5": 65.0},
        "vram_mib": 7000,
        "rtf": 0.2,
        "added_text_lines": 0,
    }


def test_c9_06_all_conditions_pass():
    assert check_rule(**passing()) == {
        "1_wer": True,
        "2_chrf": True,
        "3_vram_and_speed": True,
        "4_no_added_text": True,
        "all": True,
    }


@pytest.mark.parametrize(
    ("change", "failed"),
    [
        ({"wer_new": {"s1-s3": 0.05, "s5": 0.101}}, "1_wer"),
        ({"chrf_new": {"s1-s3": 58.9, "s5": 66.0}}, "2_chrf"),
        ({"vram_mib": VRAM_LIMIT_MIB + 1}, "3_vram_and_speed"),
        ({"rtf": RTF_LIMIT + 0.01}, "3_vram_and_speed"),
        ({"added_text_lines": 1}, "4_no_added_text"),
    ],
)
def test_c9_06_each_condition_can_fail(change, failed):
    result = check_rule(**(passing() | change))

    assert result[failed] is False
    assert result["all"] is False
    assert all(value for key, value in result.items() if key not in (failed, "all"))


def test_c9_06_equal_values_pass_and_limits():
    values = passing() | {
        "wer_new": {"s1-s3": 0.071, "s5": 0.10},
        "chrf_new": {"s1-s3": 59.0, "s5": 65.0},
        "vram_mib": VRAM_LIMIT_MIB,
        "rtf": RTF_LIMIT,
    }

    assert check_rule(**values)["all"] is True
    assert (RTF_LIMIT, VRAM_LIMIT_MIB) == (0.5, 8151)
    with pytest.raises(C9Error, match="sets"):
        check_rule(**(passing() | {"chrf_p4": {"s1-s3": 59.0}}))
