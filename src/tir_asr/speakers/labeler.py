"""The speaker step of the program: one label for each segment (D-057 part 6, D-059).

`SpeakerLabeler` holds an embedder (the adapter) and a clusterer (core, `cluster.py`). The
pipeline calls `label(segment)` for the sources that have a labeler (only "System"), after MT,
and only for a segment with an Armenian text (D-059 point 3). When the clusterer gives no label
(a short first segment), the line gets `UNIDENTIFIED` (D-060). This module imports no model
(D-021): the embedder comes as an argument.
"""

from tir_asr.speakers.cluster import OnlineClusterer
from tir_asr.types import Segment, SpeakerEmbedder

UNIDENTIFIED = "Unidentified"  # the label of a segment with no speaker (D-060)


class SpeakerLabeler:
    """`label(segment)`: the embedding of the segment audio, then the clusterer label."""

    def __init__(self, embedder: SpeakerEmbedder, clusterer: OnlineClusterer) -> None:
        self._embedder = embedder
        self._clusterer = clusterer

    def label(self, segment: Segment) -> str:
        embedding = self._embedder.embed(segment.audio)
        label = self._clusterer.assign(embedding, segment.speech_end - segment.start)
        return UNIDENTIFIED if label is None else label
