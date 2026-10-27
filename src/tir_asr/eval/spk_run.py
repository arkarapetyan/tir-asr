"""Speaker bake-off core: embeddings, the threshold sweep, and the pass rule (D-057).

This module imports no model package (D-021): the caller gives the embedder. All segments of a
stream go into the clusterer in time order, as in the program. Only the segments that overlap a
turn get a score; a segment with no turn (for example a noise) still changes the clusterer.
"""

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from itertools import combinations

import numpy as np

from tir_asr.eval.metrics import label_accuracy
from tir_asr.eval.streams import Turn
from tir_asr.speakers.cluster import OnlineClusterer
from tir_asr.types import Segment, SpeakerEmbedder

THRESHOLDS = tuple(round(0.20 + 0.05 * i, 2) for i in range(15))  # 0.20 to 0.90 (D-057)
MAX_WRONG = 1  # the pass rule: at most one wrong segment on each stream (D-057, part 3)
MIN_RANGE = 0.10  # the pass rule: the passing thresholds cover 0.10 or more in cosine


@dataclass(frozen=True, eq=False)
class Embedded:
    embedding: np.ndarray
    seconds: float  # the time of the embedding call
    duration_s: float  # the speech time of the segment: speech_end - start
    truth: str | None  # the speaker of the turn with the largest overlap; None: no overlap


@dataclass(frozen=True)
class SweepPoint:
    threshold: float
    accuracy_time: float  # weighted by the speech time (D-057, part 2)
    accuracy_count: float  # each scored segment counts 1
    wrong: int  # scored segments with a wrong label after the best mapping
    scored: int  # segments with a true speaker
    speakers: int  # the speaker count of the clusterer (all segments)


@dataclass(frozen=True)
class Pairwise:
    same_pairs: int
    same_min: float | None  # the lowest cosine of two segments of one speaker
    same_mean: float | None
    different_pairs: int
    different_max: float | None  # the highest cosine of two segments of two speakers
    different_mean: float | None


def truth_of(start: float, end: float, turns: Sequence[Turn]) -> str | None:
    """The speaker of the turn with the largest overlap. On equal overlaps, the earlier turn."""
    best: str | None = None
    best_overlap = 0.0
    for turn in sorted(turns, key=lambda t: t.start):
        overlap = min(end, turn.end) - max(start, turn.start)
        if overlap > best_overlap:
            best, best_overlap = turn.speaker, overlap
    return best


def embed_all(
    segments: Sequence[Segment],
    turns: Sequence[Turn],
    embedder: SpeakerEmbedder,
    clock: Callable[[], float],
) -> list[Embedded]:
    """One embedding call for each segment, with its time and the true speaker."""
    result = []
    for segment in segments:
        start = clock()
        embedding = embedder.embed(segment.audio)
        seconds = clock() - start
        result.append(
            Embedded(
                embedding=embedding,
                seconds=seconds,
                duration_s=segment.speech_end - segment.start,
                truth=truth_of(segment.start, segment.speech_end, turns),
            )
        )
    return result


def sweep(
    items: Sequence[Embedded],
    rule: Callable[[float, float], OnlineClusterer],
    thresholds: Sequence[float],
    min_new_s: float,
) -> list[SweepPoint]:
    """For each threshold: a new clusterer gets all segments in order; then the scores."""
    points = []
    for threshold in thresholds:
        clusterer = rule(threshold, min_new_s)
        labels = [clusterer.assign(item.embedding, item.duration_s) for item in items]
        scored = [(item, label) for item, label in zip(items, labels, strict=True) if item.truth]
        truths = [item.truth for item, _ in scored]
        names = [label for _, label in scored]
        accuracy_count = label_accuracy(truths, names, [1.0] * len(scored))
        points.append(
            SweepPoint(
                threshold=threshold,
                accuracy_time=label_accuracy(truths, names, [i.duration_s for i, _ in scored]),
                accuracy_count=accuracy_count,
                wrong=len(scored) - round(accuracy_count * len(scored)),
                scored=len(scored),
                speakers=clusterer.count,
            )
        )
    return points


def pairwise(items: Sequence[Embedded]) -> Pairwise:
    """The cosine similarities of all pairs of scored segments, same speaker or not."""
    scored = [item for item in items if item.truth]
    same: list[float] = []
    different: list[float] = []
    for a, b in combinations(scored, 2):
        x = a.embedding / np.linalg.norm(a.embedding)
        y = b.embedding / np.linalg.norm(b.embedding)
        (same if a.truth == b.truth else different).append(float(x @ y))
    return Pairwise(
        same_pairs=len(same),
        same_min=min(same) if same else None,
        same_mean=sum(same) / len(same) if same else None,
        different_pairs=len(different),
        different_max=max(different) if different else None,
        different_mean=sum(different) / len(different) if different else None,
    )


def pass_range(
    points: Mapping[str, Sequence[SweepPoint]], max_wrong: int = MAX_WRONG
) -> tuple[float, float] | None:
    """The longest run of thresholds that pass on all streams: (lowest, highest), or None.

    A threshold passes when each stream has `max_wrong` or fewer wrong segments. All streams
    must have the same thresholds. On two runs of equal length, the first run.
    """
    columns = list(points.values())
    thresholds = [p.threshold for p in columns[0]]
    for column in columns[1:]:
        if [p.threshold for p in column] != thresholds:
            raise ValueError("spk_run: the streams have different thresholds")
    passing = [
        all(column[i].wrong <= max_wrong for column in columns) for i in range(len(thresholds))
    ]
    best: tuple[int, int] | None = None
    i = 0
    while i < len(passing):
        if not passing[i]:
            i += 1
            continue
        j = i
        while j + 1 < len(passing) and passing[j + 1]:
            j += 1
        if best is None or j - i > best[1] - best[0]:
            best = (i, j)
        i = j + 1
    if best is None:
        return None
    return thresholds[best[0]], thresholds[best[1]]
