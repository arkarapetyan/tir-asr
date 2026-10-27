"""Rule B-max for the threshold sweep only (D-057, part 4). The program does not use it.

The similarity of an embedding to a speaker is its highest cosine similarity to one stored
embedding of that speaker (the nearest one). All other steps come from `OnlineClusterer`, so the
sweep compares the two rules with the same short-segment rule and the same labels.
"""

import numpy as np

from tir_asr.speakers.cluster import OnlineClusterer


class NearestClusterer(OnlineClusterer):
    """Rule B-max: each speaker keeps all its embeddings (each with length 1)."""

    def __init__(self, threshold: float, min_new_s: float) -> None:
        super().__init__(threshold, min_new_s)
        self._stored: list[list[np.ndarray]] = []

    def _add(self, unit: np.ndarray) -> None:
        self._stored.append([unit])

    def _similarities(self, unit: np.ndarray) -> np.ndarray:
        return np.array([max(float(e @ unit) for e in stored) for stored in self._stored])

    def _update(self, speaker: int, unit: np.ndarray) -> None:
        self._stored[speaker].append(unit)
