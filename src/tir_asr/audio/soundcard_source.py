"""soundcard source adapter: the AudioSource for PulseAudio (ARCHITECTURE.md section 2.1).

`soundcard` 0.4.6 records from PulseAudio (on PipeWire). The stream asks for 16 kHz, 1 channel,
and blocks of 512 samples; PulseAudio converts the device format. Each block gets the label of
the source and the `time.monotonic()` value at its arrival. Decisions: D-020, D-041, D-054.

A source is a microphone or the monitor of an output (the system audio, F1). `soundcard` calls
both of them "microphones" (`include_loopback=True`). This module also lists the sources and
finds the two default ids, for `--list-devices` and for a flag that is not given (D-054).

This module imports `soundcard` inside its functions, not at the top of the file: `soundcard`
connects to the server at import and, with no server, fails with a bare `AssertionError`
(D-041, part 5). Only `app.py` and the sim tests use this module. The core modules do not
(D-021, T-IMPORT-01).
"""

import contextlib
import time
from collections.abc import Iterator

from tir_asr.audio.devices import SourceInfo
from tir_asr.config import SAMPLE_RATE, VAD_FRAME
from tir_asr.errors import TirError
from tir_asr.types import AudioBlock

MONITOR_SUFFIX = ".monitor"  # PulseAudio: the monitor of the output <id> is the source <id>.monitor


class AudioError(TirError):
    """An error of the audio adapter. The message is `audio: <cause>`."""


def _soundcard():
    """Import `soundcard`. With no server, the import fails with an `AssertionError`."""
    try:
        import soundcard
    except AssertionError as error:  # soundcard 0.4.6: the server connection is not READY
        raise AudioError("audio: cannot connect to the PulseAudio server") from error
    return soundcard


def list_sources() -> list[SourceInfo]:
    """All sources of the server, the monitors included, in the server order."""
    soundcard = _soundcard()
    return [
        SourceInfo(id=source.id, name=source.name, monitor=source.isloopback)
        for source in soundcard.all_microphones(include_loopback=True)
    ]


def default_microphone_id() -> str:
    """The exact id of the default source of the server: the source of `--mic` with no flag."""
    soundcard = _soundcard()
    try:
        return soundcard.default_microphone().id
    except IndexError as error:  # soundcard 0.4.6: no source matches the default id
        raise AudioError("audio: no default microphone") from error


def default_system_id() -> str:
    """The exact id of the monitor of the default output: the source of `--system` with no flag.

    `soundcard` does not give the monitor of an output. The id comes from the PulseAudio rule
    `<output id>.monitor` ([RUN] for a null sink, probe A). The function checks that this source
    exists and is a monitor, so that a different rule gives an error, not a wrong source (R10).
    """
    soundcard = _soundcard()
    try:
        output = soundcard.default_speaker().id
    except IndexError as error:  # soundcard 0.4.6: no output matches the default id
        raise AudioError("audio: no default output") from error
    monitor = output + MONITOR_SUFFIX
    if not any(source.id == monitor and source.monitor for source in list_sources()):
        raise AudioError(f"audio: no monitor source for the default output {output}")
    return monitor


class SoundcardSource:
    """`blocks()` gives one AudioBlock for each 512 samples of one source, with its label.

    `label` is the source label of each block: "Me" for the microphone, "System" for the system
    audio (D-054). `device` is the exact PulseAudio source id, for example `<sink>.monitor`.
    `app.py` gets the default ids from `default_microphone_id()` and `default_system_id()`.
    The adapter checks the exact id first, because `soundcard.get_microphone` also accepts a
    part of the name (D-041, part 5).
    """

    def __init__(self, label: str, device: str) -> None:
        soundcard = _soundcard()
        ids = {source.id for source in soundcard.all_microphones(include_loopback=True)}
        if device not in ids:
            raise AudioError(f"audio: no source with the exact id {device}")
        self._source = soundcard.get_microphone(device, include_loopback=True)
        self.label = label
        self.id = device
        self.name = self._source.name  # for the startup log (section 2.7)

    def blocks(self) -> Iterator[AudioBlock]:
        """Open the stream, then give blocks until the caller closes the iterator.

        The stream opens here, not in the constructor. The stream keeps all audio from the
        moment it opens, so a stream that opened at startup would give old audio after
        "Listening" (D-041, part 5).
        """
        with contextlib.ExitStack() as stack:
            try:
                recorder = stack.enter_context(
                    self._source.recorder(samplerate=SAMPLE_RATE, channels=1, blocksize=VAD_FRAME)
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
                    source=self.label, samples=data.reshape(VAD_FRAME), arrival=arrival
                )
