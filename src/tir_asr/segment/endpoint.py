"""Endpointer: a state machine over the VAD frames (ARCHITECTURE.md section 2.2, core).

`push(block)` asks the SpeechProbability for the probability of the block. It returns a
`Segment` when the block closes one, and `None` in all other cases.

The times in a `Segment` (`start`, `speech_end`, `closed`) come from the arrival times of the
blocks. The lengths (silence, minimum speech, maximum speech) are counted in frames, that is
in audio time. Thus a burst of late blocks does not change a length.

This module imports no model package (D-021).
"""

import math
from collections import deque

import numpy as np

from tir_asr.config import SAMPLE_RATE, VAD_FRAME, Params
from tir_asr.errors import TirError
from tir_asr.types import AudioBlock, Segment, SpeechProbability

FRAME_S = VAD_FRAME / SAMPLE_RATE  # 0.032 s


class SegmentError(TirError):
    """An error of the segment module. The message is `segment: <cause>`."""


class Endpointer:
    def __init__(self, params: Params, vad: SpeechProbability) -> None:
        self._vad = vad
        self._threshold = params.vad_threshold
        self._end_threshold = params.vad_end_threshold
        self._min_speech_ms = params.vad_min_speech_ms
        # Whole frames: 500 ms is 15.625 frames, so 16 frames (512 ms).
        self._close_frames = math.ceil(params.vad_min_silence_ms * SAMPLE_RATE / (1000 * VAD_FRAME))
        self._max_frames = math.ceil(params.vad_max_speech_s * SAMPLE_RATE / VAD_FRAME)
        self._pad = round(params.vad_speech_pad_ms * SAMPLE_RATE / 1000)  # samples

        # The last frames before a segment: the source of the start pad.
        self._preroll: deque[np.ndarray] = deque(maxlen=math.ceil(self._pad / VAD_FRAME))
        self._frames: list[np.ndarray] = []  # preroll frames, then the frames of the segment
        self._open = False
        self._source = ""
        self._start = 0.0
        self._preroll_count = 0  # frames of `_frames` before the start frame
        self._silence_start: float | None = None  # None while the speech goes on
        self._silent_frames = 0
        self._speech_frames = 0  # frames from the start frame to the first frame of the silence

        self.short_segments = 0  # segments under vad_min_speech_ms (rule 4)

    def push(self, block: AudioBlock) -> Segment | None:
        samples = block.samples
        if samples.shape != (VAD_FRAME,):
            raise SegmentError(f"segment: frame has {samples.size} samples, expected {VAD_FRAME}")
        probability = self._vad(samples)
        if not 0.0 <= probability <= 1.0:
            raise SegmentError(f"segment: probability {probability} is not in [0, 1]")

        if not self._open:
            if probability < self._threshold:
                self._preroll.append(samples)
                return None
            self._begin(block)  # rule 1
        else:
            self._frames.append(samples)
            self._track_silence(block, probability)

        if self._silence_start is not None and self._silent_frames >= self._close_frames:
            return self._close(block, cut=False)  # rule 3
        if len(self._frames) - self._preroll_count >= self._max_frames:
            return self._close(block, cut=self._silence_start is None)  # rule 5
        return None

    def _begin(self, block: AudioBlock) -> None:
        self._open = True
        self._source = block.source
        self._start = block.arrival - FRAME_S
        self._preroll_count = len(self._preroll)
        self._frames = [*self._preroll, block.samples]
        self._silence_start = None
        self._silent_frames = 0

    def _track_silence(self, block: AudioBlock, probability: float) -> None:
        if self._silence_start is None:
            if probability < self._end_threshold:  # rule 2: a silence starts
                self._silence_start = block.arrival - FRAME_S
                self._silent_frames = 1
                self._speech_frames = len(self._frames) - 1 - self._preroll_count
        elif probability >= self._threshold:  # rule 2: the speech goes on
            self._silence_start = None
        else:  # a frame under vad_threshold counts as silence during a silence
            self._silent_frames += 1

    def _close(self, block: AudioBlock, *, cut: bool) -> Segment | None:
        stream = np.concatenate(self._frames)
        first = self._preroll_count * VAD_FRAME  # index of the start frame in `stream`
        if cut:
            speech_end = block.arrival
            speech_frames = len(self._frames) - self._preroll_count
            end = len(stream)  # a hard cut has no end pad
        else:
            speech_end = self._silence_start
            speech_frames = self._speech_frames
            end = min(first + speech_frames * VAD_FRAME + self._pad, len(stream))
        segment = Segment(
            source=self._source,
            audio=stream[max(0, first - self._pad) : end],
            start=self._start,
            speech_end=speech_end,
            closed=block.arrival,
            cut=cut,
        )

        # The next start pad uses the last frames of this segment.
        self._preroll.clear()
        self._preroll.extend(self._frames)
        self._frames = []
        self._open = False
        self._silence_start = None

        # Rule 4: the length of the speech is counted in frames.
        if speech_frames * VAD_FRAME * 1000 < self._min_speech_ms * SAMPLE_RATE:
            self.short_segments += 1
            return None
        return segment
