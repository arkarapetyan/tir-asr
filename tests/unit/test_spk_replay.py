"""T-C11-01 to T-C11-03: the speaker replay core with fakes (D-083, TESTS.md section 2.12).

No model. The embeddings are 2-D vectors at known angles, so each cosine similarity is known
from the angle between two vectors. The expected values come from the approved test table, not
from the code.
"""

import math

import numpy as np
import pytest

from tir_asr.eval.spk_replay import (
    GridPoint,
    ReplayError,
    Selection,
    decisions,
    grid,
    select,
)
from tir_asr.eval.spk_run import Embedded, SweepPoint
from tir_asr.speakers.cluster import CentroidClusterer

LONG = 3.0  # s of speech: longer than min_new_s


def at(degrees: float) -> np.ndarray:
    """A 2-D vector with length 1 at an angle: cos(a - b) is the similarity of two of them."""
    radians = math.radians(degrees)
    return np.array([math.cos(radians), math.sin(radians)])


def cos(degrees: float) -> float:
    return math.cos(math.radians(degrees))


def item(degrees: float, duration_s: float, truth: str | None = None) -> Embedded:
    return Embedded(at(degrees), 0.0, duration_s, truth)


def test_c11_01_decisions():
    inputs = [(0, 0.5), (0, LONG), (20, LONG), (90, LONG), (85, 0.5), (45, LONG)]
    items = [item(degrees, duration) for degrees, duration in inputs]

    result = decisions(items, threshold=0.9, min_new_s=1.0)

    assert [(d.label, d.kind) for d in result] == [
        (None, "none"),
        ("Speaker 1", "new"),
        ("Speaker 1", "join"),
        ("Speaker 2", "new"),  # the centroid of Speaker 1 is at 10 deg
        ("Speaker 2", "short"),
        ("Speaker 3", "new"),
    ]
    bests = [d.best for d in result]
    seconds = [d.second for d in result]
    assert bests[:2] == [None, None]
    assert bests[2:] == pytest.approx([cos(20), cos(80), cos(5), cos(35)])
    assert seconds[:4] == [None, None, None, None]
    assert seconds[4:] == pytest.approx([cos(75), cos(45)])
    plain = CentroidClusterer(threshold=0.9, min_new_s=1.0)
    assert [d.label for d in result] == [plain.assign(i.embedding, i.duration_s) for i in items]


def test_c11_02_grid():
    # The T-SPK-08 inputs: A at 0 and 30 deg, B at 100 and 130 deg, then a segment with no turn.
    items = [
        item(0, 4.0, "A"),
        item(30, 2.0, "A"),
        item(100, 3.0, "B"),
        item(130, 1.0, "B"),
        item(200, 3.0),
    ]

    points = grid(items, [0.5, 0.95], [1.0, 2.5])

    assert points == [
        GridPoint(1.0, SweepPoint(0.5, 1.0, 1.0, wrong=0, scored=4, speakers=3)),
        GridPoint(1.0, SweepPoint(0.95, 0.7, 0.5, wrong=2, scored=4, speakers=5)),
        GridPoint(2.5, SweepPoint(0.5, 1.0, 1.0, wrong=0, scored=4, speakers=3)),
        # The 2 s and 1 s segments are short, so they get the nearest speaker.
        GridPoint(2.5, SweepPoint(0.95, 1.0, 1.0, wrong=0, scored=4, speakers=3)),
    ]


KEYS = [(1.0, 0.45), (1.0, 0.50), (2.0, 0.45), (2.0, 0.50)]  # (min_new_s, threshold)


def column(values: dict | None = None, keys: list = KEYS) -> list[GridPoint]:
    """Grid points; a value that is not given is 0 wrong, 4 speakers, and a share of 1.0."""
    values = values or {}
    result = []
    for min_new_s, threshold in keys:
        v = {"wrong": 0, "speakers": 4, "share": 1.0, **values.get((min_new_s, threshold), {})}
        point = SweepPoint(threshold, v["share"], v["share"], v["wrong"], 10, v["speakers"])
        result.append(GridPoint(min_new_s, point))
    return result


P1 = {
    (1.0, 0.45): {"speakers": 2, "share": 0.96},
    (1.0, 0.50): {"speakers": 3, "share": 0.90},
    (2.0, 0.45): {"speakers": 1, "share": 1.0},
    (2.0, 0.50): {"speakers": 2, "share": 0.95},
}
S1 = {(2.0, 0.50): {"wrong": 1}}
D = {(1.0, 0.45): {"wrong": 1}, (2.0, 0.45): {"wrong": 1}}


def test_c11_03_select_the_highest_threshold():
    result = select({"p1": column(P1)}, {"s1": column(S1), "d": column(D)}, "d")

    # A share of 0.95 and 1 wrong segment are at the limit, and they pass.
    assert result == Selection(passing=[(1.0, 0.45), (2.0, 0.45), (2.0, 0.50)], chosen=(2.0, 0.50))


def test_c11_03_select_the_smallest_min_new_s_on_an_equal_threshold():
    d = column({**D, (2.0, 0.50): {"speakers": 3}})

    result = select({"p1": column(P1)}, {"s1": column(S1), "d": d}, "d")

    assert result == Selection(passing=[(1.0, 0.45), (2.0, 0.45)], chosen=(1.0, 0.45))


def test_c11_03_select_with_no_passing_point():
    s1 = column({key: {"wrong": 2} for key in KEYS})

    result = select({"p1": column(P1)}, {"s1": s1, "d": column(D)}, "d")

    assert result == Selection(passing=[], chosen=None)


def test_c11_03_streams_with_different_grid_points():
    d = column(D, keys=KEYS[:3])

    with pytest.raises(ReplayError) as error:
        select({"p1": column(P1)}, {"s1": column(S1), "d": d}, "d")

    assert str(error.value) == "spk_replay: the streams have different grid points"
