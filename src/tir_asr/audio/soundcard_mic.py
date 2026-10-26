"""soundcard microphone adapter: the AudioSource for PulseAudio (ARCHITECTURE.md section 2.1).

`soundcard` 0.4.6 records from PulseAudio (on PipeWire). The stream asks for 16 kHz, 1 channel,
and blocks of 512 samples; PulseAudio converts the device format. Each block gets the
`time.monotonic()` value at its arrival. Decisions: D-020, D-041.

This module imports `soundcard` inside the constructor, not at the top of the file: `soundcard`
connects to the server at import and, with no server, fails with a bare `AssertionError`
(D-041, part 5). Only the CLI and the sim tests use this module. The core modules do not
(D-021, T-IMPORT-01).
"""

import contextlib
import time
from collections.abc import Iterator

from tir_asr.config import SAMPLE_RATE, VAD_FRAME
from tir_asr.errors import TirError
from tir_asr.types import AudioBlock

SOURCE_LABEL = "Me"  # C2: the microphone is "Me" (F4). C4 adds the system source.


class AudioError(TirError):
    """An error of the audio adapter. The message is `audio: <cause>`."""


class SoundcardMicrophone:
    """`blocks()` gives one AudioBlock for each 512 samples of the selected source.

    With no `device`, the source is the default microphone of the server. A `device` is the
    exact PulseAudio source id, for example `<sink>.monitor`. The adapter checks the exact id
    first, because `soundcard.get_microphone` also accepts a part of the name (D-041, part 5).
    """

    def __init__(self, device: str | None = None) -> None:
        try:
            import soundcard
        except AssertionError as error:  # soundcard 0.4.6: the server connection is not READY
            raise AudioError("audio: cannot connect to the PulseAudio server") from error

        if device is None:
            try:
                microphone = soundcard.default_microphone()
            except IndexError as error:  # soundcard 0.4.6: no source matches the default id
                raise AudioError("audio: no default microphone") from error
        else:
            ids = {source.id for source in soundcard.all_microphones(include_loopback=True)}
            if device not in ids:
                raise AudioError(f"audio: no source with the exact id {device}")
            microphone = soundcard.get_microphone(device, include_loopback=True)

        self._microphone = microphone
        self.name = microphone.name  # for the startup log (section 2.7, step 5)

    def blocks(self) -> Iterator[AudioBlock]:
        """Open the stream, then give blocks until the caller closes the iterator.

        The stream opens here, not in the constructor. The stream keeps all audio from the
        moment it opens, so a stream that opened at startup would give old audio after
        "Listening" (D-041, part 5).
        """
        with contextlib.ExitStack() as stack:
            try:
                recorder = stack.enter_context(
                    self._microphone.recorder(
                        samplerate=SAMPLE_RATE, channels=1, blocksize=VAD_FRAME
                    )
                )
            except RuntimeError as error:
                raise AudioError(f"audio: recording failed: {error}") from error

            while True:
                try:
                    data = recorder.record(numframes=VAD_FRAME)
                except RuntimeError as error:
                    raise AudioError(f"audio: recording failed: {error}") from error
                arrival = time.monotonic()
                if data.shape != (VAD_FRAME, 1):
                    raise AudioError(f"audio: block has {data.size} samples, expected {VAD_FRAME}")
                yield AudioBlock(
                    source=SOURCE_LABEL, samples=data.reshape(VAD_FRAME), arrival=arrival
                )
