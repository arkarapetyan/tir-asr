"""Online speaker clustering: one label for each speaker embedding (D-057, parts 4 and 5).

`OnlineClusterer` holds the steps that all rules share (Template Method). A subclass gives only
the similarity of an embedding to each speaker and the update of a speaker. The program uses
`CentroidClusterer` (rule A). The eval has a second rule (`tir_asr.eval.nearest`), so that the
threshold sweep can compare the two rules (D-057, part 4).

The steps of `assign` (ARCHITECTURE.md section 2.8):
1. Check the embedding, and make its length 1 (L2 norm).
2. With no speaker yet, the embedding starts "Speaker 1", also for a short segment.
3. A segment shorter than `min_new_s` gets the label of the most similar speaker. It starts no
   new speaker and changes no speaker (part 5B).
4. Else, if the highest similarity is `threshold` or more, the segment gets that speaker, and
   the speaker is updated. If not, the segment starts a new speaker.

Labels are "Speaker 1", "Speaker 2", ... in the order of the first segment of each speaker.
A label never changes after `assign` gives it (F4). This module imports no model (D-021).
"""

from abc import ABC, abstractmethod

import numpy as np

from tir_asr.errors import TirError


class SpeakerError(TirError):
    """An error of the speaker step. The message is `speakers: <cause>`."""


class OnlineClusterer(ABC):
    """The shared steps of an online clustering rule. Subclasses give the similarities."""

    def __init__(self, threshold: float, min_new_s: float) -> None:
        if not -1.0 <= threshold <= 1.0:
            raise SpeakerError(f"speakers: threshold {threshold} is not in [-1, 1]")
        if min_new_s < 0.0:
            raise SpeakerError(f"speakers: min_new_s {min_new_s} is negative")
        self._threshold = threshold
        self._min_new_s = min_new_s
        self._dim: int | None = None
        self._count = 0

    @property
    def count(self) -> int:
        """The number of speakers so far."""
        return self._count

    def assign(self, embedding: np.ndarray, duration_s: float) -> str:
        """The label of one segment. `duration_s` is the speech time of the segment."""
        unit = self._unit(embedding)
        if self._count == 0:
            return self._start_speaker(unit)
        similarities = self._similarities(unit)
        best = int(np.argmax(similarities))  # on equal values, the speaker that came first
        if duration_s < self._min_new_s:
            return _label(best)
        if similarities[best] >= self._threshold:
            self._update(best, unit)
            return _label(best)
        return self._start_speaker(unit)

    @abstractmethod
    def _add(self, unit: np.ndarray) -> None:
        """Store a new speaker with its first embedding (length 1)."""

    @abstractmethod
    def _similarities(self, unit: np.ndarray) -> np.ndarray:
        """The cosine similarity of the embedding to each speaker, in speaker order."""

    @abstractmethod
    def _update(self, speaker: int, unit: np.ndarray) -> None:
        """Add one embedding (length 1) to a speaker."""

    def _start_speaker(self, unit: np.ndarray) -> str:
        self._add(unit)
        self._count += 1
        return _label(self._count - 1)

    def _unit(self, embedding: np.ndarray) -> np.ndarray:
        values = np.asarray(embedding)
        if values.ndim != 1:
            raise SpeakerError(
                f"speakers: embedding has shape {values.shape}, expected one dimension"
            )
        if self._dim is not None and values.shape[0] != self._dim:
            raise SpeakerError(
                f"speakers: embedding has {values.shape[0]} values, expected {self._dim}"
            )
        values = values.astype(np.float64)
        if not np.all(np.isfinite(values)):
            raise SpeakerError("speakers: embedding has values that are not finite")
        norm = float(np.linalg.norm(values))
        if norm == 0.0:
            raise SpeakerError("speakers: embedding has zero length")
        self._dim = values.shape[0]
        return values / norm


class CentroidClusterer(OnlineClusterer):
    """Rule A (D-057, part 4): the similarity to the centroid of each speaker.

    The centroid of a speaker is the mean of its embeddings (each with length 1), scaled to
    length 1. The class keeps the sum of the embeddings, so an update costs one addition.
    """

    def __init__(self, threshold: float, min_new_s: float) -> None:
        super().__init__(threshold, min_new_s)
        self._sums: list[np.ndarray] = []

    def _add(self, unit: np.ndarray) -> None:
        self._sums.append(unit.copy())

    def _similarities(self, unit: np.ndarray) -> np.ndarray:
        centroids = np.stack(self._sums)
        centroids /= np.linalg.norm(centroids, axis=1, keepdims=True)
        return centroids @ unit

    def _update(self, speaker: int, unit: np.ndarray) -> None:
        self._sums[speaker] += unit


def _label(speaker: int) -> str:
    return f"Speaker {speaker + 1}"
