"""T-DATA-01 to T-DATA-11: eval data (D-046, D-048, D-049).

Each test makes its own files in tmp_path. The expected values come from the approved test table
(TESTS.md section 2.5), not from the code.
"""

import re
from pathlib import Path

import numpy as np
import pytest
from scipy.io import wavfile

from tir_asr.eval.data import (
    DataError,
    Label,
    ScriptLine,
    assign_segments,
    load_wav_16k,
    read_labels,
    read_references,
    with_end_silence,
)

SCRIPTS = Path(__file__).resolve().parents[2] / "docs" / "eval" / "scripts.md"

SMALL_TABLE = """# Test scripts

| ID | Speaker | Armenian | English |
|---|---|---|---|
| s1-01 | Me | Բարև։ | Hi. |
| s1-02 † | Speaker 1 | Նա եկավ։ | He/she came. |
| s1-03 | Speaker 2 | Լավ։ | Good. |
| s2-01 | Speaker 1 | Այո։ | Yes. |
"""


def tone(freq_hz: float, rate: int, seconds: float = 1.0, amplitude: float = 0.5) -> np.ndarray:
    t = np.arange(int(rate * seconds)) / rate
    return (amplitude * np.sin(2 * np.pi * freq_hz * t)).astype(np.float32)


def rms(x: np.ndarray) -> float:
    return float(np.sqrt(np.mean(x.astype(np.float64) ** 2)))


def small_lines(tmp_path: Path) -> list[ScriptLine]:
    path = tmp_path / "scripts.md"
    path.write_text(SMALL_TABLE, encoding="utf-8")
    return read_references(path, "s1")


def test_data_01_resample_48k_to_16k(tmp_path):
    path = tmp_path / "tone.wav"
    wavfile.write(path, 48000, tone(440, 48000))

    audio = load_wav_16k(path)

    assert audio.dtype == np.float32
    assert len(audio) == 16000
    spectrum = np.abs(np.fft.rfft(audio.astype(np.float64) * np.hanning(len(audio))))
    peak_hz = np.argmax(spectrum) * 16000 / len(audio)
    assert abs(peak_hz - 440) <= 1
    assert rms(audio[2000:-2000]) == pytest.approx(0.5 / np.sqrt(2), rel=0.02)


def test_data_02_no_aliasing(tmp_path):
    path = tmp_path / "high.wav"
    source = tone(11000, 48000)
    wavfile.write(path, 48000, source)

    audio = load_wav_16k(path)

    assert 20 * np.log10(rms(audio[2000:-2000]) / rms(source)) <= -40


def test_data_03_16k_is_not_changed(tmp_path):
    path = tmp_path / "16k.wav"
    source = np.random.default_rng(0).uniform(-0.5, 0.5, 8000).astype(np.float32)
    wavfile.write(path, 16000, source)

    assert np.array_equal(load_wav_16k(path), source)


@pytest.mark.parametrize(
    ("rate", "samples", "message"),
    [
        (48000, np.zeros((480, 2), dtype=np.float32), "2 channels, expected 1"),
        (44100, np.zeros(441, dtype=np.float32), "sample rate 44100 Hz, expected 48000 or 16000"),
        (48000, np.zeros(480, dtype=np.int16), "sample format int16, expected float32"),
    ],
)
def test_data_04_errors(tmp_path, rate, samples, message):
    path = tmp_path / "bad.wav"
    wavfile.write(path, rate, samples)

    with pytest.raises(DataError, match=f"^data: bad.wav: {re.escape(message)}$"):
        load_wav_16k(path)


def test_data_05_end_silence():
    audio = np.ones(100, dtype=np.float32)

    result = with_end_silence(audio)

    assert result.dtype == np.float32
    assert len(result) == 16100
    assert np.all(result[:100] == 1.0)
    assert np.all(result[100:] == 0.0)


def test_data_06_references(tmp_path):
    assert small_lines(tmp_path) == [
        ScriptLine("s1-01", "Me", "mic", "Բարև։", "Hi."),
        ScriptLine("s1-02", "Speaker 1", "call", "Նա եկավ։", "He/she came."),
        ScriptLine("s1-03", "Speaker 2", "call", "Լավ։", "Good."),
    ]


@pytest.mark.parametrize(("script", "count"), [("s1", 14), ("s2", 10), ("s3", 10)])
def test_data_07_references_in_the_real_file(script, count):
    lines = read_references(SCRIPTS, script)

    assert len(lines) == count
    assert sum(line.side == "mic" for line in lines) == 5


def test_data_08_references_error(tmp_path):
    path = tmp_path / "scripts.md"
    path.write_text(SMALL_TABLE, encoding="utf-8")

    with pytest.raises(DataError, match="^data: no lines for s9 in scripts.md$"):
        read_references(path, "s9")


def test_data_09_labels(tmp_path):
    lines = small_lines(tmp_path)
    path = tmp_path / "s1.labels.txt"
    path.write_text("1.0\t2.5\ts1-01\n3.0\t4.25\ts1-02\n4.0\t6.0\ts1-03\n", encoding="utf-8")

    assert read_labels(path, lines) == [
        Label("s1-01", 1.0, 2.5),
        Label("s1-02", 3.0, 4.25),
        Label("s1-03", 4.0, 6.0),
    ]


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("1.0\t2.0\n", "line 1: 2 fields, expected 3"),
        ("a\t2.0\ts1-01\n", "line 1: time is not a number"),
        ("3.0\t2.0\ts1-01\n", "line 1: end 2.0 is before start 3.0"),
        ("1\t2\ts1-01\n3\t4\ts1-99\n", "line 2: unknown ID s1-99"),
        ("1\t2\ts1-01\n3\t4\ts1-02\n", "missing ID s1-03"),
        ("1\t2\ts1-01\n3\t4\ts1-01\n", "line 2: repeated ID s1-01"),
    ],
)
def test_data_10_label_errors(tmp_path, text, message):
    lines = small_lines(tmp_path)
    path = tmp_path / "s1.labels.txt"
    path.write_text(text, encoding="utf-8")

    with pytest.raises(DataError, match=f"^data: s1.labels.txt: {re.escape(message)}$"):
        read_labels(path, lines)


def test_data_11_line_view():
    labels = [Label("b", 6.0, 10.0), Label("a", 0.0, 5.0)]
    segments = [(0.2, 4.8), (4.9, 6.5), (11.0, 12.0), (4.5, 6.5)]

    assert assign_segments(segments, labels) == ["a", "b", None, "a"]
