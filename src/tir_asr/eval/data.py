"""Eval data: audio files, references, and labels (D-046, D-048, D-049).

The eval reads each side of a recording as one file, the references from docs/eval/scripts.md,
and the Audacity labels. The program does not use this module.
"""

import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy.io import wavfile
from scipy.signal import resample_poly

from tir_asr.errors import TirError

RECORDING_RATE = 48000
TARGET_RATE = 16000  # the same value as SAMPLE_RATE (ARCHITECTURE.md section 5)
END_SILENCE_S = 1.0  # zeros after the end of a file, so that the last segment closes (D-048)


class DataError(TirError):
    """An eval file that the eval cannot use."""


@dataclass(frozen=True)
class ScriptLine:
    id: str
    speaker: str
    side: str  # "mic" for "Me", "call" for the other speakers
    hy: str
    en: str


@dataclass(frozen=True)
class Label:
    id: str
    start: float
    end: float


def load_wav_16k(path: Path) -> np.ndarray:
    """Read a mono float32 WAV file at 48 kHz or 16 kHz. Return float32 audio at 16 kHz."""
    path = Path(path)
    rate, audio = wavfile.read(path)
    if audio.ndim != 1:
        raise DataError(f"data: {path.name}: {audio.shape[1]} channels, expected 1")
    if audio.dtype != np.float32:
        raise DataError(f"data: {path.name}: sample format {audio.dtype}, expected float32")
    if rate == RECORDING_RATE:
        return resample_poly(audio, 1, RECORDING_RATE // TARGET_RATE).astype(np.float32)
    if rate == TARGET_RATE:
        return audio
    raise DataError(
        f"data: {path.name}: sample rate {rate} Hz, expected {RECORDING_RATE} or {TARGET_RATE}"
    )


def with_end_silence(audio: np.ndarray) -> np.ndarray:
    """Add END_SILENCE_S of zeros after the audio (16 kHz)."""
    zeros = np.zeros(int(END_SILENCE_S * TARGET_RATE), dtype=np.float32)
    return np.concatenate([audio.astype(np.float32, copy=False), zeros])


def read_references(scripts_md: Path, script: str) -> list[ScriptLine]:
    """The lines of one script (for example "s1"), in the order of the table."""
    scripts_md = Path(scripts_md)
    row_start = re.compile(rf"\|\s*{re.escape(script)}-\d\d\b")
    lines = []
    for number, row in enumerate(scripts_md.read_text(encoding="utf-8").splitlines(), start=1):
        if not row_start.match(row):
            continue
        cells = [cell.strip() for cell in row.strip().strip("|").split("|")]
        if len(cells) != 4:
            raise DataError(
                f"data: {scripts_md.name}: line {number}: {len(cells)} columns, expected 4"
            )
        line_id = cells[0].replace("†", "").strip()
        side = "mic" if cells[1] == "Me" else "call"
        lines.append(ScriptLine(line_id, cells[1], side, cells[2], cells[3]))
    if not lines:
        raise DataError(f"data: no lines for {script} in {scripts_md.name}")
    return lines


def read_labels(path: Path, lines: Sequence[ScriptLine]) -> list[Label]:
    """Read an Audacity label file (start, tab, end, tab, ID) and check it against the lines."""
    path = Path(path)
    known = {line.id for line in lines}
    labels: list[Label] = []
    seen: set[str] = set()
    for number, row in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        fields = row.split("\t")
        if len(fields) != 3:
            raise DataError(f"data: {path.name}: line {number}: {len(fields)} fields, expected 3")
        try:
            start, end = float(fields[0]), float(fields[1])
        except ValueError:
            raise DataError(f"data: {path.name}: line {number}: time is not a number") from None
        if end < start:
            raise DataError(f"data: {path.name}: line {number}: end {end} is before start {start}")
        label_id = fields[2].strip()
        if label_id not in known:
            raise DataError(f"data: {path.name}: line {number}: unknown ID {label_id}")
        if label_id in seen:
            raise DataError(f"data: {path.name}: line {number}: repeated ID {label_id}")
        seen.add(label_id)
        labels.append(Label(label_id, start, end))
    missing = [line.id for line in lines if line.id not in seen]
    if missing:
        raise DataError(f"data: {path.name}: missing ID {', '.join(missing)}")
    return labels


def assign_segments(
    segments: Sequence[tuple[float, float]], labels: Sequence[Label]
) -> list[str | None]:
    """For each segment (start, end), the ID of the label with the largest time overlap.

    On equal overlaps, the label that starts first. No overlap gives None (D-046, line view).
    """
    ordered = sorted(labels, key=lambda label: label.start)
    result: list[str | None] = []
    for seg_start, seg_end in segments:
        best: str | None = None
        best_overlap = 0.0
        for label in ordered:
            overlap = min(seg_end, label.end) - max(seg_start, label.start)
            if overlap > best_overlap:
                best, best_overlap = label.id, overlap
        result.append(best)
    return result
