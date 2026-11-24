"""Speaker replay core for C11: the decision log, the 2-D grid, and the decision rule (D-083).

The replay runs the program rule (`CentroidClusterer`) again on saved embeddings, with no model.

- `decisions` gives the label of each segment, the kind of the decision, and the two highest
  similarities before the decision.
- `grid` runs `sweep` (`spk_run`) for each `min_new_s`.
- `select` applies the decision rule of D-083 part 4, which was fixed before the run.

One-person streams (D-083 part 3): each segment with a text gets the true speaker `ONE_PERSON`.
Then `accuracy_time` of a sweep point is the share of the largest label in the labelled speech
time (the best mapping maps `ONE_PERSON` to that label), and `speakers` is the label count.

This module imports no model package (D-021).
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np

from tir_asr.errors import TirError
from tir_asr.eval.spk_run import MAX_WRONG, Embedded, SweepPoint, sweep
from tir_asr.speakers.cluster import CentroidClusterer

GRID_THRESHOLDS = (0.40, 0.45, 0.50)  # spk_threshold values of the grid (D-083 part 2)
GRID_MIN_NEW_S = (1.0, 1.5, 2.0, 2.5, 3.0)  # spk_min_new_s values of the grid, s (D-083 part 2)
MAX_LABELS_ONE = 2  # a one-person stream passes with 2 labels or fewer (D-083 part 4)
MIN_SHARE_ONE = 0.95  # ... and with 95 % or more of the labelled speech time on its largest label
STREAM_D_SPEAKERS = 4  # stream D must have 4 labels (D-057)
ONE_PERSON = "person"  # the true speaker of each segment of a one-person stream


class ReplayError(TirError):
    """An error of the replay core. The message is `spk_replay: <cause>`."""


@dataclass(frozen=True)
class Decision:
    label: str | None  # None: no label (a short segment before the first speaker, D-060)
    kind: str  # "new", "join", "short", or "none"
    best: float | None  # the highest similarity to a speaker before the decision
    second: float | None  # the second highest similarity; None with fewer than two speakers


@dataclass(frozen=True)
class GridPoint:
    min_new_s: float
    point: SweepPoint  # the threshold is `point.threshold`


@dataclass(frozen=True)
class Selection:
    passing: list[tuple[float, float]]  # (min_new_s, threshold) of each passing point, grid order
    chosen: tuple[float, float] | None  # the selected point; None when no point passes


class _RecordedCentroid(CentroidClusterer):
    """The program rule. It keeps the similarities of its last `assign` call."""

    def __init__(self, threshold: float, min_new_s: float) -> None:
        super().__init__(threshold, min_new_s)
        self.last: np.ndarray | None = None

    def _similarities(self, unit: np.ndarray) -> np.ndarray:
        values = super()._similarities(unit)
        self.last = values
        return values


def decisions(items: Sequence[Embedded], threshold: float, min_new_s: float) -> list[Decision]:
    """The decision of the program rule for each segment, in time order (T-C11-01)."""
    clusterer = _RecordedCentroid(threshold, min_new_s)
    result = []
    for item in items:
        clusterer.last = None
        before = clusterer.count
        label = clusterer.assign(item.embedding, item.duration_s)
        best = second = None
        if clusterer.last is not None:
            ordered = np.sort(clusterer.last)[::-1]
            best = float(ordered[0])
            if len(ordered) > 1:
                second = float(ordered[1])
        if label is None:
            kind = "none"
        elif clusterer.count > before:
            kind = "new"
        elif item.duration_s < min_new_s:
            kind = "short"
        else:
            kind = "join"
        result.append(Decision(label=label, kind=kind, best=best, second=second))
    return result


def grid(
    items: Sequence[Embedded], thresholds: Sequence[float], min_new_values: Sequence[float]
) -> list[GridPoint]:
    """`sweep` with the program rule for each `min_new_s`, in the given order (T-C11-02)."""
    return [
        GridPoint(min_new_s, point)
        for min_new_s in min_new_values
        for point in sweep(items, CentroidClusterer, thresholds, min_new_s)
    ]


def select(
    one_person: Mapping[str, Sequence[GridPoint]],
    eval_streams: Mapping[str, Sequence[GridPoint]],
    d_name: str,
) -> Selection:
    """The decision rule of D-083 part 4 (T-C11-03).

    A point passes when each one-person stream has `MAX_LABELS_ONE` labels or fewer and a share
    of `MIN_SHARE_ONE` or more, each eval stream has `MAX_WRONG` wrong segments or fewer, and the
    stream `d_name` has `STREAM_D_SPEAKERS` labels. Among the passing points, the highest
    threshold wins; on an equal threshold, the smallest `min_new_s`.
    """
    columns = [*one_person.values(), *eval_streams.values()]
    keys = [_key(p) for p in columns[0]]
    for column in columns[1:]:
        if [_key(p) for p in column] != keys:
            raise ReplayError("spk_replay: the streams have different grid points")
    passing = []
    for i, key in enumerate(keys):
        ones = all(
            column[i].point.speakers <= MAX_LABELS_ONE
            and column[i].point.accuracy_time >= MIN_SHARE_ONE
            for column in one_person.values()
        )
        evals = all(column[i].point.wrong <= MAX_WRONG for column in eval_streams.values())
        stream_d = eval_streams[d_name][i].point.speakers == STREAM_D_SPEAKERS
        if ones and evals and stream_d:
            passing.append(key)
    chosen = max(passing, key=lambda k: (k[1], -k[0]), default=None)
    return Selection(passing=passing, chosen=chosen)


def _key(point: GridPoint) -> tuple[float, float]:
    return (point.min_new_s, point.point.threshold)
