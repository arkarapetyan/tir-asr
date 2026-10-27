"""T-SPK-01 to T-SPK-05, T-SPK-07, T-SPK-11: speaker clustering, label accuracy, labeler.

No model. The embeddings are small vectors at known angles, so each cosine similarity is known
from the angle between two vectors. The expected labels come from the approved test table
(TESTS.md section 2.7), not from the code.
"""

import math
import re

import numpy as np
import pytest

from tir_asr.eval.metrics import MetricError, label_accuracy
from tir_asr.eval.nearest import NearestClusterer
from tir_asr.speakers.cluster import CentroidClusterer, SpeakerError
from tir_asr.speakers.labeler import SpeakerLabeler
from tir_asr.types import Segment

RULES = [CentroidClusterer, NearestClusterer]
LONG = 3.0  # s of speech: longer than min_new_s in all tests


def at(degrees: float) -> np.ndarray:
    """A 2-D vector with length 1 at an angle: cos(a - b) is the similarity of two of them."""
    radians = math.radians(degrees)
    return np.array([math.cos(radians), math.sin(radians)], dtype=np.float32)


@pytest.mark.parametrize("rule", RULES)
def test_spk_01_labels_in_order_of_the_first_segment(rule):
    clusterer = rule(threshold=0.5, min_new_s=1.0)
    vectors = [
        np.array([1.0, 0.0, 0.0]),
        np.array([0.9, 0.1, 0.0]),
        np.array([0.0, 1.0, 0.0]),
        np.array([0.05, 1.0, 0.0]),
        np.array([0.0, 0.0, 1.0]),
    ]

    labels = [clusterer.assign(vector, LONG) for vector in vectors]

    assert labels == ["Speaker 1", "Speaker 1", "Speaker 2", "Speaker 2", "Speaker 3"]
    assert clusterer.count == 3


def test_spk_02_the_centroid_moves_with_each_update():
    clusterer = CentroidClusterer(threshold=0.7, min_new_s=1.0)

    # 40 deg: cos 40 = 0.77 >= 0.7. The centroid of 0 and 40 deg is at 20 deg.
    # 60 deg: cos(60 - 20) = 0.77 >= 0.7, but cos 60 = 0.5 to the first vector only.
    labels = [clusterer.assign(at(a), LONG) for a in (0, 40, 60)]

    assert labels == ["Speaker 1", "Speaker 1", "Speaker 1"]

    control = CentroidClusterer(threshold=0.7, min_new_s=1.0)
    assert [control.assign(at(a), LONG) for a in (0, 60)] == ["Speaker 1", "Speaker 2"]


@pytest.mark.parametrize("rule", RULES)
def test_spk_03_a_short_segment_starts_no_speaker_and_changes_no_speaker(rule):
    clusterer = rule(threshold=0.9, min_new_s=1.0)

    # A short first segment starts "Speaker 1": no other label is possible.
    assert clusterer.assign(at(0), 0.5) == "Speaker 1"
    assert clusterer.assign(at(90), LONG) == "Speaker 2"

    # Short, no match (cos 40 = 0.77 and cos 50 = 0.64, both < 0.9): the most similar speaker.
    assert clusterer.assign(at(40), 0.5) == "Speaker 1"
    assert clusterer.count == 2

    # Speaker 1 did not change: cos 35 = 0.82 < 0.9 to the 0 deg vector, so a new speaker.
    # (An update with the 40 deg vector would give cos 15 = 0.97 with the centroid,
    # or cos 5 = 1.00 with the stored vector, and the label "Speaker 1".)
    assert clusterer.assign(at(35), LONG) == "Speaker 3"

    # A duration equal to min_new_s counts as long: no match, so a new speaker.
    assert clusterer.assign(at(180), 1.0) == "Speaker 4"
    assert clusterer.count == 4


@pytest.mark.parametrize("rule", RULES)
def test_spk_04_wrong_parameters(rule):
    with pytest.raises(SpeakerError, match=re.escape("speakers: threshold 1.5 is not in [-1, 1]")):
        rule(threshold=1.5, min_new_s=1.0)
    with pytest.raises(SpeakerError, match=re.escape("speakers: min_new_s -0.1 is negative")):
        rule(threshold=0.5, min_new_s=-0.1)


@pytest.mark.parametrize("rule", RULES)
@pytest.mark.parametrize(
    ("embedding", "message"),
    [
        (np.ones((1, 3)), "speakers: embedding has shape (1, 3), expected one dimension"),
        (np.array([1.0, np.nan, 0.0]), "speakers: embedding has values that are not finite"),
        (np.array([1.0, np.inf, 0.0]), "speakers: embedding has values that are not finite"),
        (np.zeros(3), "speakers: embedding has zero length"),
    ],
)
def test_spk_04_wrong_embedding(rule, embedding, message):
    clusterer = rule(threshold=0.5, min_new_s=1.0)

    with pytest.raises(SpeakerError, match=f"^{re.escape(message)}$"):
        clusterer.assign(embedding, LONG)
    assert clusterer.count == 0


@pytest.mark.parametrize("rule", RULES)
def test_spk_04_embedding_size_changes(rule):
    clusterer = rule(threshold=0.5, min_new_s=1.0)
    clusterer.assign(np.array([1.0, 0.0, 0.0]), LONG)

    with pytest.raises(SpeakerError, match="^speakers: embedding has 2 values, expected 3$"):
        clusterer.assign(np.array([1.0, 0.0]), LONG)


@pytest.mark.parametrize(
    ("truths", "labels", "weights", "expected"),
    [
        # Permuted labels: the mapping finds them.
        (["A", "A", "B", "B"], ["S2", "S2", "S1", "S1"], [1, 1, 1, 1], 1.0),
        # An extra label: S1 -> A (2) and S3 -> B (1); the S2 segment is an error.
        (["A", "A", "A", "B"], ["S1", "S1", "S2", "S3"], [1, 1, 1, 1], 0.75),
        # The weights are seconds: S1 -> A gives 3 of 4.
        (["A", "B"], ["S1", "S1"], [3.0, 1.0], 0.75),
        # More true speakers than labels: S1 -> B gives 2 of 4.
        (["A", "B", "C"], ["S1", "S1", "S1"], [1, 2, 1], 0.5),
    ],
)
def test_spk_05_label_accuracy(truths, labels, weights, expected):
    assert label_accuracy(truths, labels, weights) == pytest.approx(expected)


@pytest.mark.parametrize(
    ("truths", "labels", "weights", "message"),
    [
        (
            ["A", "B", "A"],
            ["S1", "S2"],
            [1, 1, 1],
            "metrics: 3 true speakers, 2 labels, and 3 weights",
        ),
        ([], [], [], "metrics: no segments"),
        (["A"], ["S1"], [0.0], "metrics: weight 0.0 is not positive"),
        (["A"], ["S1"], [float("nan")], "metrics: weight nan is not positive"),
    ],
)
def test_spk_05_label_accuracy_wrong_input(truths, labels, weights, message):
    with pytest.raises(MetricError, match=f"^{re.escape(message)}$"):
        label_accuracy(truths, labels, weights)


def test_spk_07_the_two_rules_differ_after_a_chain():
    # 0, 40, then 80 deg, threshold 0.7. Centroid of 0 and 40 deg: 20 deg; cos 60 = 0.5 < 0.7.
    # Nearest stored vector to 80 deg: 40 deg; cos 40 = 0.77 >= 0.7.
    angles = (0, 40, 80)
    centroid = CentroidClusterer(threshold=0.7, min_new_s=1.0)
    nearest = NearestClusterer(threshold=0.7, min_new_s=1.0)

    assert [centroid.assign(at(a), LONG) for a in angles] == ["Speaker 1", "Speaker 1", "Speaker 2"]
    assert [nearest.assign(at(a), LONG) for a in angles] == ["Speaker 1", "Speaker 1", "Speaker 1"]


class FakeEmbedder:
    """Gives the vectors in order and records the audio of each call."""

    def __init__(self, vectors):
        self.vectors = list(vectors)
        self.calls = []

    def embed(self, audio):
        self.calls.append(audio)
        return self.vectors.pop(0)


def segment(start: float, end: float) -> Segment:
    audio = np.full(16, start, dtype=np.float32)  # the audio shows which segment it is
    return Segment("System", audio, start, end, end + 0.5, cut=False)


def test_spk_11_labeler_gives_the_audio_and_the_speech_time():
    embedder = FakeEmbedder([at(0), at(90), at(80)])
    labeler = SpeakerLabeler(embedder, CentroidClusterer(threshold=0.9, min_new_s=1.0))
    segments = [segment(1.0, 4.0), segment(5.0, 8.0), segment(9.0, 9.5)]

    labels = [labeler.label(s) for s in segments]

    # The third segment: 0.5 s of speech, so it is short: the most similar speaker (cos 10 deg).
    assert labels == ["Speaker 1", "Speaker 2", "Speaker 2"]
    assert [call[0] for call in embedder.calls] == [1.0, 5.0, 9.0]
