# ARCHITECTURE.md

**Project:** tir-asr · **Version:** 0.29 · **Date:** 2026-10-27
**Status:** v0.3 APPROVED by Aren on 2026-10-25. The v0.4 changes (C2b) apply D-036, ACCEPTED on 2026-10-25. The v0.5 and v0.6 changes (C2c) apply D-037, ACCEPTED on 2026-10-25; Aren reviews the text (see §10). The v0.7 changes (C2d) apply D-040, ACCEPTED on 2026-10-25. The v0.8 changes (C2d) apply D-041, ACCEPTED on 2026-10-26. The v0.9 changes (C2d) apply D-042, ACCEPTED on 2026-10-26. The v0.10 changes (C2d) apply D-043, ACCEPTED on 2026-10-26. The v0.11 changes (C2d) apply D-044, ACCEPTED on 2026-10-26. The v0.12 change (C2d) applies D-045. The v0.13 change (C3) applies D-046 and D-047. The v0.14 and v0.15 changes (C3) apply D-049. The v0.16 to v0.18 changes (C3) apply D-051. The v0.19 to v0.21 changes (C4) apply D-054, ACCEPTED on 2026-10-26. The v0.22 and v0.23 changes (C5) apply D-057. The v0.24 change applies D-058. The v0.25 change applies D-058 and D-059. The v0.26 change applies D-060. The v0.27 change applies D-061. The v0.28 change (C6) applies D-062. The v0.29 change (C6) applies D-063. C2 contracts for the walking skeleton (microphone → VAD → ASR → MT → terminal). C4 adds the system audio, C5 adds the speakers. §8 is complete (S1, D-012).

---

## 1. Overview

The program captures the microphone and the system audio (C4), cuts the audio of each source into speech segments, gives the Armenian text and the English text of each segment (the text step, §2.9: P1 transcribes, then translates), gives each system-side segment a speaker label (C5), and prints one block for each segment.
Core modules have no model import and no audio-device import. Adapter modules hold the model and device code (D-021). Unit tests give fakes to the core modules.

```
 microphone ──► audio (adapter) ──AudioBlock──► segment: Endpointer (core) ◄── SpeechProbability (Silero adapter, CPU)
 "Me"           capture thread "capture Me"             │
 system audio ─► audio (adapter) ──AudioBlock──► segment: Endpointer (core) ◄── SpeechProbability (Silero adapter, CPU)
 "System"       capture thread "capture System"         │
                                                        ▼ Segment (from both sources)
                                                 segment queue (unbounded)
                                                        │
                                   worker thread        ▼
                                   text: TextStep (core, §2.9); P1: CascadeTextStep
                                     asr: Transcriber (NeMo adapter, GPU) ──► Armenian text
                                     mt:  Translator (CTranslate2 adapter, GPU) ──► English text
                                   speakers ("System" only, text not empty): SpeakerLabeler (core)
                                        ◄── SpeakerEmbedder (TitaNet adapter, GPU) ──► "Speaker N"
                                   output: format_block (core) ──► terminal (one write for each block)
```

## 2. Modules and contracts

| Module | Kind | Input | Output | Errors (fail loudly, R10) | Limits |
|---|---|---|---|---|---|
| `audio` | adapter | microphone (C2), system audio (C4) | `AudioBlock` stream | `AudioError` | §2.1 |
| `segment` | core + adapter | `AudioBlock` | `Segment` | `SegmentError` | §2.2 |
| `asr` | adapter | `Segment.audio` | Armenian text (`str`) | `AsrError` | §2.3 |
| `mt` | adapter | Armenian text | English text (`str`) | `MtError` | §2.4 |
| `text` | core + adapter (C6) | `Segment.audio` | `TextResult`: the Armenian text, the English text, and the end of each of the two steps | `TextError` (P4 adapter); the errors of the P1 adapters, with no change | §2.9 |
| `speakers` | core + adapter (C5) | a system-side `Segment` | the label `"Speaker N"` | `SpeakerError` | §2.8 |
| `output` | core | `Line` | one text block | none | §2.5 |
| `pipeline` | core | the modules above | threads, queue, stop, exit code | the first error of a thread | §2.6 |
| `errors` | core | — | `TirError`, the base class of the module errors | — | §2.6 |
| `cli` | core | command line | calls `app.main()`; its exit code | — (`argparse` stops on a wrong argument) | §2.7 |
| `app` | loads the adapters (in `ADAPTERS` of T-IMPORT-01) | the adapters | startup log, exit code | the error line (§7) | §2.7 |

Each error class has the module name in its message: `<module>: <cause>`. Each error class inherits from `TirError` in `errors.py` (D-042).

### 2.1 `audio`

- **Sources (F1, D-054):** a source is a PulseAudio source: a microphone, or the monitor of an output (the system audio). `soundcard` calls both of them "microphones" (`include_loopback=True`) [SOURCE: `soundcard` 0.4.6]. The program has two sources: `"Me"` (the microphone) and `"System"` (the system audio). C5 changes the line label of the system side to `"Speaker N"`; the source label stays `"System"`.
- **Adapter** `audio/soundcard_source.py` (`SoundcardSource(label, device)`, D-041, D-054): `soundcard` 0.4.6 recorder with `samplerate=16000`, `channels=1`, `blocksize=512`. Each `record(numframes=512)` gives one `AudioBlock`.
  - **Constructor:** it imports `soundcard` and selects the source, so that the errors come at startup. `device` is required: an exact source id among all sources, monitors included (for example `<sink>.monitor`). The adapter checks the exact id first, because `soundcard.get_microphone` also accepts a part of the name or a regex match [SOURCE: `soundcard` 0.4.6], which can select a different device with no error (R10).
  - **`blocks()`:** it opens the stream, then gives blocks until the caller closes the iterator. The stream keeps all audio from the moment it opens, with no limit [SOURCE], so it must not open before "Listening".
  - The attributes `label`, `id`, and `name` give the source label, the exact id, and the device name (for the startup log).
- **Adapter functions (D-054):**
  - `list_sources() -> list[SourceInfo]`: all sources of the server, monitors included, in the server order. `SourceInfo(id, name, monitor)` is in the core module `audio/devices.py`; `monitor` is the `soundcard` value `isloopback` (`device.class` is `monitor`) [SOURCE].
  - `default_microphone_id()`: the id of the default source of the server.
  - `default_system_id()`: `<default output id>.monitor`. `soundcard` does not give the monitor of an output, so the id comes from the PulseAudio rule ([RUN] for a null sink, probe A, and for the laptop output, T-AUDIO-04). The function checks that this source exists and is a monitor.
- **Core** `audio/devices.py` (D-054): `format_source_list(sources, default_mic, default_system) -> str` gives the text of `--list-devices` (T-DEV-01): the heading `Microphones (--mic):`, the sources that are not monitors, the heading `System audio (--system):`, the monitors, then the line `* = the default, used when the flag is not given`. Each source line is `<mark> <id>  <name>`; the mark is `*` for the default of its group, else a space. A group with no source has the line `  (none)`.
- **Contract:** each block has exactly 512 float32 samples in an array of shape (512,) (32 ms at 16 kHz, mono), the label of its source, and the `time.monotonic()` value at its arrival. `soundcard` gives (512, 1); the adapter makes it flat.
- **Errors:**
  - `audio: cannot connect to the PulseAudio server` (the `soundcard` import fails with an `AssertionError`) [RUN]. The constructor and the three functions. T-AUDIO-02.
  - `audio: no default microphone`; `audio: no default output`; `audio: no monitor source for the default output <id>`. No test: a test must change the system defaults.
  - `audio: no source with the exact id <id>`. T-AUDIO-03.
  - `audio: recording failed: <cause>` (`soundcard` raises `RuntimeError` when the stream fails) [SOURCE].
  - `audio: block has <n> samples, expected 512`.
- **Limits:**
  - PulseAudio converts the device format to 16 kHz mono. [RUN] A 440 Hz tone through a null sink (2 channels, 48 kHz) keeps its frequency and its level (probe B, T-AUDIO-01). C4 tests the call path.
  - [RUN] The arrival gaps alternate between about 21 ms and 43 ms, with a mean of 32 ms (probe B). Thus an arrival time can be up to about 11 ms late against an even 32 ms grid.
  - [RUN] A monitor with no audio gives blocks of zeros (probe B). Thus the `Endpointer` can close a segment during a silence on the system side (C4).
  - [RUN] The samples can be a little outside [−1, 1]: the default microphone gave −1.0496 (probe B, Q-11). The adapter does not clip them (D-041).
  - T-AUDIO-04 compares the device list and the two default ids with the `pactl` values. The default sources record only in T-E2E-02 and in the live tests (L-01).
  - A change of the default output during a run does not move the `"System"` source: it stays on the old monitor and gives silence, with no error (D-054). The user connects the headphones before the start.
  - [RUN] Noises (coughs, short sounds) of 250 ms or more pass the VAD; the ASR then gives one letter, and the MT invents a sentence (L-05, Q-14).
  - When PulseAudio reports lost audio, `soundcard` fills the gap with zeros and gives no warning [SOURCE: `soundcard` 0.4.6]. The program cannot see this loss. [RUN] T-SIM-01: two sources for 72.7 s, span ÷ real time 1.0000 for each, so no drift between them; the test cannot see lost audio that `soundcard` fills with zeros.
  - The arrival time does not include the time between the sound and the arrival of its block (device and server buffers). [RUN] `soundcard` gives a stream latency of 21–44 ms (probe B). Thus the measured latency is up to about 44 ms lower than the real latency.

### 2.2 `segment`

- **Adapter** `segment/silero.py` (`SpeechProbability`): Silero VAD 6.2.3, JIT model on the CPU. One call for each 512-sample frame gives a speech probability in [0, 1].
  - `silero_vad` sets the PyTorch CPU threads to 1 at import [RUN]. The startup log shows the thread count.
- **Core** `segment/endpoint.py` (`Endpointer`): a state machine over the frames. `Endpointer(params, vad)` gets a `Params` (§5) and a `SpeechProbability`. `push(block)` calls `vad(block.samples)` and returns zero or one `Segment`. Rules (D-026, D-027):
  1. **Start:** the first frame with `p >= vad_threshold` starts the speech. `start` = the start time of this frame.
  2. **Silence:** in speech, a frame with `p < vad_end_threshold` starts a silence. `speech_end` = the start time of this frame (D-023). During a silence, a frame with `p >= vad_threshold` ends the silence, and the speech continues. Other frames count as silence.
  3. **End:** when the silence reaches `vad_min_silence_ms` (whole frames: 16 frames = 512 ms for 500 ms), the segment closes. `closed` = the arrival time of the frame that closes it.
  4. **Minimum length:** a segment with `speech_end - start < vad_min_speech_ms` gives no output. The `Endpointer` counts these segments in the public attribute `short_segments`, and the shutdown line shows the count.
  5. **Maximum length:** when `vad_max_speech_s` is reached from `start`, the segment closes. If a silence is open, the segment ends at `speech_end` (rule 3). If not, it is a hard cut: `speech_end` = `closed` = the end of the current frame, and `cut = True`. After a cut, the next frame with `p >= vad_threshold` starts a new segment.
  6. **Audio:** the segment audio goes from `start - vad_speech_pad_ms` to `speech_end + vad_speech_pad_ms`, limited to the samples that exist (a hard cut has no end pad).
- **Times:** the start time of a frame = its arrival time − 32 ms.
- **Lengths:** the silence, the minimum length, and the maximum length are counted in whole frames (audio time), not from the arrival times. A burst of late blocks does not change a length.
- **Errors:** `segment: frame has <n> samples, expected 512`; `segment: probability <p> is not in [0, 1]`. `SegmentError` is in `segment/endpoint.py`. The `Endpointer` checks the frame length before it calls the VAD.
- **Limits:** the times have a resolution of one frame (32 ms). The rule is close to the Silero `VADIterator` rule, but the end comes one frame earlier (16 whole frames, not 17).

### 2.3 `asr`

- **Adapter** `asr/nemo_rnnt.py` (`NemoRnntTranscriber`, D-037): `nvidia/stt_hy_fastconformer_hybrid_large_pc`, NeMo 3.0.0, RNNT decoder (`change_decoding_strategy(decoder_type="rnnt")`), on `cuda` (D-014).
- **Load:** the constructor `NemoRnntTranscriber(repo, filename)` checks CUDA, then loads the `.nemo` file from the Hugging Face cache, with `local_files_only=True`. Nothing downloads at runtime. The defaults are the module constants `ASR_REPO` and `ASR_FILE`. They are model locations, not parameters (D-037).
- **Warm-up (D-022, D-037, D-062):** the adapter has no warm-up method. At startup, the text step calls `transcribe` with `WARMUP_AUDIO_S` of zeros (§2.6, §2.9).
- **Contract:** `transcribe(audio)` takes float32, mono, 16 kHz audio and returns the Armenian text. The text can be empty. NeMo shows no progress bar (`verbose=False`).
- **Errors:** `asr: CUDA is not available` (no CPU fallback, R10); `asr: model file not in the Hugging Face cache: <name>`; `asr: unexpected output type <type>`.
- **Limits:** one segment for each call (batch size 1). [RUN] 0.027–0.036 s for each call after the warm-up, 987 MiB VRAM (T-INSTALL-02). The model writes commas where a person writes "։" (Q-06).

### 2.4 `mt`

- **Adapter** `mt/ct2_nllb.py` (`Ct2NllbTranslator`, D-037): `facebook/nllb-200-distilled-600M`, converted to CTranslate2 in `models/nllb-200-distilled-600M-ct2-float16`, on `cuda`, `compute_type = mt_compute_type` (D-015). Tokenizer: Transformers `AutoTokenizer` from the Hugging Face cache, source `hye_Armn`, target `eng_Latn`.
- **CUDA 12 cuBLAS (D-030):** before `import ctranslate2`, the adapter loads `libcublasLt.so.12` and then `libcublas.so.12` from the package `nvidia-cublas-cu12` (`ctypes`, `RTLD_GLOBAL`). The file paths come from `importlib.metadata`. The program needs no `LD_LIBRARY_PATH`.
- **Load:** the constructor `Ct2NllbTranslator(params, model_dir)` loads the model and the tokenizer. It reads `mt_compute_type` and `mt_beam_size` from `Params`. The default of `model_dir` is a module constant. It is a model location, not a parameter (D-037). The default is relative to the current folder, so the program must start in the project folder. The adapter checks for `model_dir/model.bin` before the load.
- **Warm-up (D-022, D-037, D-062):** the adapter has no warm-up method. At startup, the text step calls `translate(WARMUP_TEXT)` (§2.6, §2.9).
- **Contract:** `translate(text)` takes a non-empty Armenian text and returns the English text.
- **Errors:** `mt: CTranslate2 model not found: <path>` (the message gives the conversion command of C2: `HF_HUB_OFFLINE=1 uv run --no-sync ct2-transformers-converter --model facebook/nllb-200-distilled-600M --output_dir models/nllb-200-distilled-600M-ct2-float16 --quantization float16`); `mt: <file> not found in the package nvidia-cublas-cu12` (`<file>` is `libcublasLt.so.12` or `libcublas.so.12`); `mt: empty input text`.
- **Limits:** each segment is translated alone, with no context (known limit: «նա» = he or she). [RUN] 0.066–0.132 s for each call after the warm-up (T-INSTALL-03). CTranslate2 limits the output to 256 tokens (library default) [UNVERIFIED].

### 2.5 `output`

- **Core** `output.py` (D-024, D-040):
  - `format_block(line, session_start) -> str` gives the text of one block.
  - `write_block(line, session_start, stream)` writes the full block with one `write` call, then calls `flush`. One call for each block, so that the lines of two sources do not mix.
  - Each block ends with an empty line, so that the blocks have a blank line between them.

  ```
  [00:01:12] Me
   HY: Լավ եմ, շնորհակալություն։
   EN: I'm fine, thank you.
   [Latency: vad 0.53s, asr 0.41s, mt 0.18s, out 0.00s | Total 1.12s]
  ```

- **Time:** `Segment.start` minus the session start, as `hh:mm:ss`. The seconds are cut, not rounded (D-040). The session starts when the program prints "Listening".
- **Latency steps (D-023, D-024):** two decimals; the steps add up to the total.

  | Step | From | To |
  |---|---|---|
  | `vad` | `speech_end` | `closed` |
  | `asr` | `closed` | ASR end (includes the queue wait) |
  | `mt` | ASR end | MT end |
  | `spk` | MT end | speaker step end (system side only, D-059) |
  | `out` | MT end, or the speaker step end | the moment before the write |
  | Total | `speech_end` | the moment before the write |

- **Names of the text steps (D-063 part 2):** `Line.steps` comes from the `STEPS` of the text step (§2.9). P1 has two names, `asr` and `mt`, as in the table. P4 has one name, `s2t`: one step from `closed` to the end of both texts (the MT end), because one call gives both texts. A P4 block: `[Latency: vad 0.53s, s2t 0.59s, out 0.00s | Total 1.12s]`; with the speaker step, `vad, s2t, spk, out`. An empty text of P4 gives `vad` and `s2t` (from `closed` to the ASR end).

- **System side (D-059, D-060):** a block of the system side with a text has the label `"Speaker N"` (or `"Unidentified"`, §2.8) and the steps `vad, asr, mt, spk, out`: `[Latency: vad 0.53s, asr 0.41s, mt 0.18s, spk 0.01s, out 0.01s | Total 1.14s]`. A "Me" block does not change.
- **Empty ASR text (D-031):** in C2 to C6, a short block with no MT call: the time, the label, `HY: (no text)`, and a latency line with `vad`, `asr`, and the total. On the system side, this block keeps the label `"System"`: it gets no speaker step (D-059 point 3). C7 removes this block for the delivery; the shutdown line still counts the empty texts.
- **Rounding:** the program adds the raw step values. The printed steps can differ from the printed total by rounding (maximum 0.02 s for 4 steps).
- **Limit:** `out` does not include the time that the terminal needs to show the text.

### 2.6 `pipeline`

- **Core** `pipeline.py` (D-042, D-054, D-059, D-062). `run(sources, text_step, params, clock, out, err, labelers=None) -> int` takes a list of `(source, vad)` pairs, one for each audio source, the text step (§2.9; the program: P1, `CascadeTextStep`), and a mapping from a source label to a `Labeler` (the program: `{"System": …}`). A source with no labeler keeps its source label. It builds one `Endpointer` for each pair, starts the threads (§4), and returns the exit code. Each capture thread has the name `capture <label>` (the `label` of its source). All capture threads put their segments in one queue, and the worker writes the blocks in the order in which the segments close. Thus the `[hh:mm:ss]` times of two sources are not always in sequence: a long segment of one source can come after a later, short segment of the other source. The clock is `time.monotonic` in the program and a fake clock in unit tests. `out` gets the blocks and the shutdown line; `err` gets the error line.
- **Warm-up (D-022, D-037, D-042, D-059, D-062):** `warm_up(text_step, embedder, clock) -> (asr_s, mt_s, spk_s)` calls `text_step.warm_up` with `WARMUP_AUDIO_S` of zeros (P1: `transcribe` with the zeros, then `translate(WARMUP_TEXT)`, §2.9), then `embed` with the same zeros, and returns the three times. It gets the embedder, not the labeler, so it cannot change a clusterer. The caller prints them. It is separate from `run()`, so that the counts of the model calls in T-PIPE-03 stay correct.
- **Session start (D-042):** `run()` takes the session start from the clock, prints "Listening. Press Ctrl+C to stop.", and only then starts the threads. Each source opens its stream at its first block (D-041). Thus no block time is before the session start.
- **Worker:** for each segment, `text_step.process(segment.audio, clock)` gives the Armenian text, the English text, the ASR end, and the MT end (§2.9). The text step reads the clock: after the Armenian step, and after the English step if the text is not empty. An empty text gets no English step, and the MT end is the ASR end (D-031). Then, if the source has a labeler and the text is not empty: `label(segment)`, then the speaker step end from the clock (D-059); else the line keeps the source label and has no speaker step. Then the write time from the clock, and `write_block` (§2.5).
- **Stop (D-042):**
  - Ctrl+C: the shutdown line, then exit code 0. Ctrl+C takes effect within `STOP_POLL_S` (0.5 s, D-044). The open segments, the segments in the queue, and a segment in ASR or MT are not processed. "Not processed" in the shutdown line counts the segments in the queue and in ASR or MT; it does not count the open segments of the `Endpointer`s. Aren accepted this risk: a Ctrl+C right after the last phrase can lose that line. T-PIPE-11 (unit test), T-E2E-02 (model test), and L-02 check this path.
  - End of the sources (tests and the WAV source only, D-025): each capture thread puts an end mark in the queue at the end of its source. The worker continues until it has the end mark of each source (D-054, T-PIPE-07), and then the shutdown line comes, with exit code 0.
  - Shutdown line: `Stopped. Segments: <n>, short segments: <n>, empty texts: <n>, not processed: <n>.` "Segments" counts the written blocks. The counts are the sums of all sources. An output lock makes the shutdown line the last line.
  - **Clean stop (D-061):** at each end (Ctrl+C, the end of the sources, an error), the main thread sets the stop event under the output lock, writes the shutdown line or the error line, and then waits for all threads, with one time limit `STOP_JOIN_S` (2.0 s) for all of them. Only then does `run()` return. Each capture thread stops at its next block (it does not push that block) and closes its block iterator, so the `with` blocks of the adapter close the audio stream. A wake-up mark in the segment queue makes the worker stop when it waits for a segment; a worker in ASR, MT, or the speaker step stops before it writes. A thread that does not stop in `STOP_JOIN_S` gives `tir-asr: stop: thread <name> did not stop in <s> s` on `err` (R10); the exit code does not change. A second Ctrl+C during the wait makes `run()` return at once. T-PIPE-11 to T-PIPE-13 and T-E2E-02 check the stop.
  - **Reason (D-061):** [SOURCE] `soundcard` 0.4.6 registers an `atexit` function that stops and frees the PulseAudio main loop (`pulseaudio.py`, lines 125–132 and 291), and each `record()` call locks that main loop. [RUN] Python runs the `atexit` functions while daemon threads still run (workspace test, Python 3.13). Before D-061, `run()` returned while the capture threads still recorded, so the exit could stop the process: `Assertion 'pthread_mutex_lock(&m->mutex) == 0' failed … pa_mutex_lock(). Aborting.`, exit code 134 (exit check, L-02).
- **Errors (D-042):** the first exception in a thread stops the program. `run()` writes the error line to `err`, does the clean stop (D-061), and returns 1, with no shutdown line. A `TirError` gives `tir-asr: <module>: <cause>`. Any other exception gives its traceback, then `tir-asr: <thread>: <type>: <message>` (the thread is `capture <label>` or `worker`, T-PIPE-08).

### 2.7 `cli` and `app`

- **Launcher (D-045):** `./run.sh` in the project folder. It goes to the project folder (so it works from any folder), sets `HF_HUB_OFFLINE=1` (nothing downloads, K2), and starts `.venv/bin/tir-asr` with `exec` (so Ctrl+C goes straight to the program). The arguments go to the program. If `.venv/bin/tir-asr` is missing, it stops with a message to run `uv sync`.
- **Command:** `tir-asr`, from `[project.scripts]` in `pyproject.toml` (`tir_asr.cli:main`). After a change to `pyproject.toml`, `uv sync` installs the command.
- **Flags (F1, D-054):**
  - `--mic ID`: the exact source id of the microphone (label `"Me"`). With no flag: the default microphone (`default_microphone_id()`, §2.1).
  - `--system ID`: the exact source id of the system audio (label `"System"`), normally a monitor. With no flag: the monitor of the default output (`default_system_id()`, §2.1).
  - `--list-devices`: `app.list_devices()` prints the text of `format_source_list` (§2.1) and returns 0. It loads no model. A `TirError` gives `tir-asr: <message>` and exit code 1.
  - The same id for `--mic` and `--system` gives an `argparse` error: `tir-asr: error: --mic and --system select the same source <id>`, exit code 2 (T-CLI-02).
  - A change of the default output during a run does not move the `"System"` source (§2.1).
- **`cli.py` (core, D-037, D-043, D-054):** only the `argparse` interface. After the parse, it imports `app` and returns `app.list_devices()` (with `--list-devices`) or `app.main(mic=…, system=…)`. Thus `--help` imports no model and no audio-device package (T-CLI-01).
- **`app.py` (D-042, D-043, D-054):** it selects the two sources, loads the adapters, prints the startup log, and calls the pipeline with one `(source, vad)` pair for each source. It imports the adapters inside its functions, in the load order below. Each startup line starts with `startup: `.
- **Startup sequence:**

  | Step | Place | Startup line |
  |---|---|---|
  | 1. Versions and parameters | `app.log_versions` | `startup: tir-asr …; torch …; nemo-toolkit …; ctranslate2 …; silero-vad …; soundcard …` (from `importlib.metadata`; no import), then one `startup: parameter <name> = <value>` line for each parameter (`config.parameter_lines`, T-CFG-02) |
  | 2. Sources (§2.1; the streams open later) | `app.select_sources` | `startup: source Me: <name> (<id>)`, then `startup: source System: <name> (<id>)`. A wrong id stops the program here, before the model load (D-054, point 6). |
  | 3. ASR load, with the CUDA check (§2.3) | `app.load_models` | `startup: GPU <name>; CUDA (torch) <version>`, then `startup: ASR loaded in <s> s; GPU memory used <MiB> MiB` |
  | 4. MT load (the cuBLAS preload, D-030) | `app.load_models` | `startup: MT loaded in <s> s; GPU memory used <MiB> MiB (<±MiB> MiB)` |
  | 5. VAD load: one Silero instance for each source (D-054, point 7) | `app.load_models` | `startup: VAD loaded in <s> s (Me, System); torch CPU threads <n>` |
  | 6. Speaker model load (§2.8, D-057 part 6) | `app.load_models` | `startup: speaker model loaded in <s> s; GPU memory used <MiB> MiB (<±MiB> MiB)` |
  | 7. Warm-up (§2.6) | `pipeline.warm_up`, called by `app.main` | `startup: warm-up ASR <s> s, MT <s> s, speaker <s> s` |
  | 8. "Listening" and the session start | `pipeline.run` (§2.6) | `Listening. Press Ctrl+C to stop.` |

- **Load order (D-043, point 2a, D-057 part 6):** ASR first, so that a missing CUDA gives `asr: CUDA is not available` before any other GPU call. Then MT, then VAD, then the speaker model. `load_models(params, log, labels)` returns `(vads, text_step, embedder)`; the text step is `CascadeTextStep(transcriber, translator)` (P1, §2.9, D-062). `app.speaker_labeler(embedder, params)` builds the labeler of `"System"`: `SpeakerLabeler(embedder, CentroidClusterer(params.spk_threshold, params.spk_min_new_s))` (D-058). `soundcard` loads before `torch` (step 2); [RUN] T-E2E-02 and T-SIM-01 pass with this order. The MT adapter loads the CUDA 12 cuBLAS before its own `import ctranslate2`; no other module imports `ctranslate2`. [RUN] torch and NeMo before the MT adapter in one process: T-MODEL-MT-01 passes with no `LD_LIBRARY_PATH` (c2d-pipeline model run).
- **GPU memory:** `torch.cuda.mem_get_info()` gives the used memory of the full device, so the MT line also counts CTranslate2. The change in brackets has its sign (`+1664`, `-256`). [RUN] The device value can go down at a later load: in the program it goes down by 256 MiB at the speaker model load. The probe of C5 (`test-results/c5-probe-spk-load.txt`) shows that the TitaNet load takes 196 MiB from the torch cache that is already reserved (918 MiB before and after), so the device value does not grow; the cause of the −256 MiB is [UNVERIFIED] (probably CTranslate2 after its load). The TitaNet load does not change the torch CPU threads (1 before and after).
- **NeMo lines (D-043, point 3):** NeMo prints about 185 lines at its load. M1 does not hide them (R10). C7 decides again.
- **Errors and Ctrl+C during the startup (D-043, point 4):** a `TirError` gives `tir-asr: <message>` and exit code 1. Any other exception gives its traceback, then `tir-asr: startup: <type>: <message>`, and exit code 1. Ctrl+C before "Listening" gives `Stopped during the startup.` and exit code 0.
- **Stop:** §2.6 (Ctrl+C, the shutdown line, the exit codes).

### 2.8 `speakers`

- **Purpose (F4, D-057):** each line of the system side gets `"Speaker 1"`, `"Speaker 2"`, and so on. One person keeps the same label for the full session. The microphone side stays `"Me"`. A short segment before the first speaker gets `"Unidentified"` (D-060).
- **Core** `speakers/labeler.py` (branch `c5-pipeline`, D-059, D-060): `SpeakerLabeler(embedder, clusterer)`. `label(segment)` calls `embedder.embed(segment.audio)`, then `clusterer.assign(embedding, segment.speech_end - segment.start)`. When `assign` gives `None`, `label` gives `UNIDENTIFIED` (`"Unidentified"`). Thus `label` always gives a text, and the pipeline and the output do not change. The pipeline calls it after MT, only for `"System"` and only for a text that is not empty (§2.6).
- **Adapter** `speakers/titanet.py` (`TitanetEmbedder`, branch `c5-pipeline`, D-058): `nvidia/speakerverification_en_titanet_large` (TitaNet-large, SPK-3), NeMo 3.0.0 `EncDecSpeakerLabelModel`, on `cuda`. The constructor checks CUDA, then loads `speakerverification_en_titanet_large.nemo` from the Hugging Face cache with `local_files_only=True` (nothing downloads). `repo` and `filename` are model locations, not parameters (as D-037). `embed(audio)` calls `infer_segment` and returns a float32 vector. No warm-up method: the pipeline makes the warm-up call. [RUN] 200 MiB VRAM, load 3.34 s, at most 28.3 ms for each segment (C5 sweep).
- **Core** `speakers/cluster.py` (branch `c5-cluster`):
  - `OnlineClusterer(threshold, min_new_s)` is an abstract class with the shared steps (Template Method). A subclass gives only `_add` (a new speaker), `_similarities` (the cosine similarity to each speaker), and `_update` (one more embedding for a speaker).
  - `CentroidClusterer` (rule A, D-057 part 4) is the program rule: the similarity to the centroid of each speaker. The centroid is the mean of the speaker's embeddings (each with length 1), scaled to length 1.
  - `assign(embedding, duration_s) -> str | None` gives the label of one segment. `duration_s` is the speech time of the segment. The steps:
    1. Check the embedding, and make its length 1 (L2 norm).
    2. With no speaker yet, a segment with `duration_s < min_new_s` gets `None` (no label) and starts no speaker (D-060: in L-06, a cough as the first segment started "Speaker 1"). A longer segment starts `"Speaker 1"`.
    3. A segment with `duration_s < min_new_s` gets the label of the most similar speaker. It starts no new speaker and changes no speaker (D-057 part 5B).
    4. Else, if the highest similarity is `threshold` or more, the segment gets that speaker, and the speaker is updated. If not, it starts a new speaker.
  - On equal similarities, the speaker that came first wins. The labels are in the order of the first segment of each speaker. A label never changes after `assign` gives it.
  - The attribute `count` gives the number of speakers so far.
- **Errors:** `speakers: CUDA is not available` (no CPU fallback, R10); `speakers: model file not in the Hugging Face cache: <repo>/<file>`; `speakers: threshold <t> is not in [-1, 1]`; `speakers: min_new_s <s> is negative`; `speakers: embedding has shape <shape>, expected one dimension`; `speakers: embedding has <n> values, expected <m>` (the size of the first embedding); `speakers: embedding has values that are not finite`; `speakers: embedding has zero length`. `SpeakerError` is in `speakers/cluster.py`.
- **Parameters (§6, D-058, D-060):** `spk_threshold` = 0.50 and `spk_min_new_s` = 1.0 s. L-06 kept both: 0.50 gave no wrong label on clean turns, and L-06 gave no fact for `spk_min_new_s` (the output shows no segment length). C7 checks them again with a diagnostic line (D-060).
- **Limits:**
  - One embedding for each segment, so a segment with two voices gets one label: the label of the voice with more speech. The VAD cuts only after `vad_min_silence_ms` (500 ms) of silence, so a fast change of speaker or an interruption gives such a segment. Its embedding also updates the centroid of that speaker. [RUN] L-06 (Q-04). C7 measures a shorter `vad_min_silence_ms` (D-060).
  - An embedding from a noise can start a new speaker when the noise is `min_new_s` or longer, after the first speaker (Q-14). C7 measures the VAD options for noises (D-060).

### 2.9 `text`

- **Purpose (D-053, D-062):** the text step gives the Armenian text and the English text of one segment. P1 (the default) and P4 (the flag `--seamless`, branch `c6-cli`) are two subclasses of one abstract class, so that the pipeline is the same for both.
- **Core** `text/step.py` (branch `c6-textstep`, D-062 part 2): the abstract class `TextStep`, with the Template Method pattern.
  - `process(audio, clock) -> TextResult` is a template method: `state = _prepare(audio)`; `hy = _armenian(state)`; then the clock gives `asr_end`. If `hy` is empty, there is no `_english` call: `en` is `""` and `mt_end` is `asr_end` (D-031). Else `en = _english(state, hy)`, and then the clock gives `mt_end`. Thus a text gives two clock reads, and an empty text gives one.
  - `warm_up(audio, clock) -> TextResult` is a template method (D-022, D-037): the same steps, but `_english(state, WARMUP_TEXT)` always runs, also when `hy` is empty (zeros normally give no text). P1 translates `WARMUP_TEXT`; P4 does not use it.
  - The hooks: `_prepare(audio)` (default: the audio, with no work), `_armenian(state) -> str` (abstract), and `_english(state, hy) -> str` (abstract). `_armenian` and `_english` get the state of the same `_prepare` call. A subclass defines only the hooks, not `process` or `warm_up` (T-TEXT-04).
  - An exception of a hook goes up with no change (R10), and the pipeline stops (§2.6).
  - `CascadeTextStep(transcriber, translator)` is P1: `_armenian` is `transcriber.transcribe(audio)` (§2.3), and `_english` is `translator.translate(hy)` (§2.4). The adapters do not change.
  - `STEPS` (class attribute) gives the names of the text steps on the latency line (§2.5, D-063 part 2): `("asr", "mt")` in `TextStep` (P1), `("s2t",)` in the P4 adapter. The pipeline puts it into `Line.steps`.
  - `TextError(TirError)`, with the message `text: <cause>`, is in this module.
- **Adapter** `text/seamless.py` (P4, `SeamlessTextStep`, branch `c6-seamless`, D-063): `facebook/seamless-m4t-v2-large`, `SeamlessM4Tv2ForSpeechToText`, float16, on `cuda` (D-053).
  - **Load:** the constructor `SeamlessTextStep(repo)` checks CUDA, then checks the Hugging Face cache with `hf_hub_download(repo, "config.json", local_files_only=True)`, then loads the processor and the model with `local_files_only=True`. Nothing downloads at runtime. The default `repo` is the module constant `S2T_REPO`; it is a model location, not a parameter (as D-037). [SOURCE: huggingface_hub 2.3.0] `snapshot_download(local_files_only=True)` can raise `IncompleteSnapshotError` for a cache that `from_pretrained` can use, so the adapter does not use it.
  - **Variant V2 (D-063 part 1):** `_prepare(audio)` makes the features, does one encoder pass, and calls the base `GenerationMixin.generate` one time with two decoder rows: the `hye` code and the `eng` code (the base `generate` adds the decoder start token). The state is `(Armenian text, English text)`; `_armenian` and `_english` give its two parts. The Seamless `generate` is not used, because with no `tgt_lang` it writes a warning at each call. Each call gets a new `BaseModelOutput`, because `generate` changes the given encoder output in place for the beams [SOURCE: transformers 5.20.2, `_expand_dict_for_generation`].
  - **Generate values (D-063 part 6):** the defaults of the model: greedy (the model files set no `num_beams`) and `max_new_tokens` 256. The attributes `num_beams` and `max_new_tokens` give them to the startup log. No parameter (R10).
  - **`STEPS`:** `("s2t",)` (D-063 part 2).
  - **Errors:** `text: CUDA is not available` (no CPU fallback and no CPU mode, R10, D-063 part 4); `text: model not in the Hugging Face cache: <repo>`.
  - **Limits:** [RUN, probe, 34 segments of S1–S3] WER 7.1 %, chrF 59.0, line time 0.337 s mean and 0.443 s maximum, 2884 MiB VRAM. The adapter calls the base `generate` directly, which is a detail of the transformers code: a transformers update can break it (T-MODEL-P4-01). In float16, the batch of two gives a small difference from one call for each language (2 of 34 Armenian texts differ by one character). Each segment is translated alone, with no context. The program does not run P4 on the CPU; the probe numbers for the CPU are in `docs/eval/results.md` (D-063 part 4).
- **Latency line:** the names of `STEPS` (§2.5, D-063 part 2; D-062 part 3 had kept `asr` and `mt` for P4).
- **Weak point (D-062 part 2):** the hooks of P4 share the state of `_prepare`, so the hooks have a fixed order.

## 3. Data types (core, `types.py`)

All times are `time.monotonic()` values in seconds. All audio is float32, mono, 16 kHz, normally in [−1, 1]. A loud input can give values a little outside (probe B: −1.0496, D-041).

| Type | Field | Type | Meaning |
|---|---|---|---|
| `AudioBlock` | `source` | `str` | Source label: `"Me"` (C2) or `"System"` (C4, D-054). |
| | `samples` | `np.ndarray` (512,) | One VAD frame. |
| | `arrival` | `float` | Arrival time of the block. |
| `Segment` | `source` | `str` | From the blocks. |
| | `audio` | `np.ndarray` | Speech with the pads (§2.2 rule 6). |
| | `start` | `float` | Start of speech (no pad). |
| | `speech_end` | `float` | True end of speech (D-023). |
| | `closed` | `float` | Time when the `Endpointer` closed the segment. |
| | `cut` | `bool` | True for a hard cut (§2.2 rule 5). |
| `Line` | `label` | `str` | `"Me"`; on the system side `"Speaker N"` or `"Unidentified"` (C5, D-060), or `"System"` for an empty text (D-059). |
| | `start` | `float` | `Segment.start`. |
| | `hy`, `en` | `str` | Armenian text, English text. |
| | `speech_end`, `closed`, `asr_end`, `mt_end`, `write` | `float` | The times of §2.5. |
| | `spk_end` | `float \| None` | The end of the speaker step; `None` with no speaker step (D-059). Default `None`. |
| | `steps` | `tuple[str, ...]` | The names of the text steps: `("asr", "mt")` (default, P1) or `("s2t",)` (P4), from `TextStep.STEPS` (§2.5, D-063 part 2). |
| `TextResult` (D-062) | `hy`, `en` | `str` | Armenian text (`""` for no text), English text (`""` when the Armenian text is empty). |
| | `asr_end`, `mt_end` | `float` | The end of the Armenian step and of the English step; `mt_end` = `asr_end` for an empty text (D-031). |

Interfaces (core, `typing.Protocol`):

| Interface | Method | Adapter (C2) | Unit-test fake |
|---|---|---|---|
| `AudioSource` | attribute `label: str`; `blocks() -> Iterator[AudioBlock]` | `SoundcardSource` (microphone or monitor) | a list of blocks |
| `SpeechProbability` | `__call__(samples) -> float` | Silero VAD | a list of numbers |
| `Transcriber` | `transcribe(audio) -> str` | NeMo RNNT | a fixed text |
| `Translator` | `translate(text) -> str` | CTranslate2 NLLB | a fixed text |
| `SpeakerEmbedder` | `embed(audio) -> np.ndarray` (one dimension) | TitaNet (D-058) | a fixed vector |
| `Labeler` | `label(segment) -> str` (`"Speaker N"` or `"Unidentified"`) | `SpeakerLabeler` (core, §2.8) | a list of labels |

The text step is an abstract class, not a Protocol, because it holds the template methods: `TextStep` in `text/step.py` (§2.9). The unit tests use `CascadeTextStep` with the fake transcriber and the fake translator, or a recorder subclass.

The WAV file source is test code only (D-025). It is in `tests/support/`, not in the package. It plays the clips at real-time speed and gives only whole frames; it drops the last part of a clip that is shorter than one frame. It adds no silence (D-032): a clip must end with at least 512 ms of silence, or the test fails.

## 4. Data flow, threads, and queues

| Thread | Work | Blocks on |
|---|---|---|
| Main | Startup (§2.7), then it waits for Ctrl+C, for "done", or for an error from a thread. | the event queue |
| Capture (one for each source, name `capture <label>`) | Reads the blocks of its source, calls the `Endpointer.push` of its source (which calls the `SpeechProbability` of its source), puts each `Segment` in the segment queue. At the end of its source (tests only), it puts an end mark. | `record()` |
| Worker (one) | Gets a `Segment`, calls the text step (§2.9; P1: ASR, then MT if the text is not empty), then the speaker step (`"System"`, text not empty), then writes the block. After the end mark of each source, it puts "done" in the event queue. | the segment queue |

- **Segment queue:** one `queue.Queue` for all sources, with no size limit (D-029). A slow worker shows as a larger `asr` step on each line.
- **One worker thread** uses the GPU, so the GPU models run one at a time.
- **Main-thread wait (D-044):** the main thread waits on the event queue with a time limit of `STOP_POLL_S` (0.5 s), in a loop. The time limit changes nothing except that the main thread wakes up. [RUN] With no time limit, Ctrl+C did nothing: the process has 75–79 native threads, and Python handles a signal only when the main thread wakes up (L-02, probe C). T-E2E-02 checks Ctrl+C on the real program.
- **Errors:** each thread puts its exception in the event queue. The main thread stops the program (§2.6). The threads are daemon threads, so that they do not keep the program alive after the main thread returns. At each end, `run()` first waits for them with the limit `STOP_JOIN_S` (clean stop, D-061, §2.6).
- **No parallel GPU work.** One worker runs ASR, then MT, then the speaker model (C5). [RUN] This takes 0.10–0.17 s for each segment, and a new segment comes at most once in 0.76 s (calc). Two GPU threads would share the GPU, so each call would be slower; the gain is only when segments wait in the queue. C4 and C5 measure the queue wait before a change (R6).
- **No `asyncio`.** `soundcard`, NeMo, and CTranslate2 have blocking APIs. With `asyncio`, they would run in threads anyway. Threads and queues are simpler.
- **GIL:** the worker and the capture threads share the Python interpreter lock. A long Python step in the worker can delay a capture thread; PulseAudio then keeps the audio in its buffer [UNVERIFIED buffer size]. Q-10 checks it in the live run; T-SIM-01 measures the arrival gaps of two sources (C4).

## 5. Configuration

C2 has no configuration file and no flags except `--help`. The parameters (§6) are the default values of the frozen dataclass `Params` in `config.py`. The program uses `Params()`. Only tests build a `Params` with other values. The startup log shows all of them.

Constants (fixed by a model or a test, not tunable):

| Name | Value | Reason |
|---|---|---|
| `SAMPLE_RATE` | 16000 Hz | The ASR model and Silero VAD need 16 kHz. |
| `VAD_FRAME` | 512 samples | The only frame size that Silero VAD accepts at 16 kHz [SOURCE]. |
| `WARMUP_AUDIO_S` | 2.0 s of zeros | Synthetic ASR warm-up input (no audio file in git, R11). |
| `WARMUP_TEXT` | «Բարև, ինչպե՞ս ես։» | Synthetic MT warm-up input. |
| `MT_SRC_LANG`, `MT_TGT_LANG` | `hye_Armn`, `eng_Latn` | NLLB language codes. |
| `STOP_POLL_S` (`pipeline.py`) | 0.5 s | The main thread waits for an event with this time limit, in a loop. It only wakes the main thread, so that Python can handle Ctrl+C (D-044). |
| `STOP_JOIN_S` (`pipeline.py`) | 2.0 s | At each end of `run()`, the main thread waits this time in total for all threads (clean stop, D-061). A thread stops within one block (32 ms) and the worker within one segment [RUN: ASR, MT, and the speaker step take at most 0.2 s on the GPU, P1]. A thread that does not stop gives an error line (R10). |

## 6. Parameters

Only Aren adds a parameter (RULES.md R10). The startup log shows each parameter.

| Name | Value | Unit | Reason | Approved by Aren (date) |
|---|---|---|---|---|
| `mt_compute_type` | `float16` | — | `auto` selects `int8_float16`, which fails on RTX 50-series GPUs; float16 was the fastest mode in the CTranslate2 benchmark (D-015). | 2026-10-24 |
| `vad_threshold` | 0.5 | probability | Silero default (D-026). | 2026-10-25 |
| `vad_end_threshold` | 0.35 | probability | Silero rule: threshold − 0.15 (D-026). | 2026-10-25 |
| `vad_min_silence_ms` | 500 | ms | Start value; pauses at phrase ends; no sentence split on the T-INSTALL-04 clips (D-027). | 2026-10-25 |
| `vad_speech_pad_ms` | 30 | ms | Silero default; no latency cost (D-026). | 2026-10-25 |
| `vad_min_speech_ms` | 250 | ms | Silero default; removes clicks (D-026). | 2026-10-25 |
| `vad_max_speech_s` | 10 | s | Limits the wait during a long speech (D-026). | 2026-10-25 |
| `mt_beam_size` | 2 | — | CTranslate2 default. Beam sizes 1 and 2 gave the same texts and the same times (T-INSTALL-03, D-033). | 2026-10-25 |
| `spk_threshold` | 0.50 | cosine | The middle of the zero-error range 0.40–0.60 of TitaNet with rule A in the C5 sweep (D-058). [RUN] L-06: no wrong label on clean turns; kept (D-060). C7 checks it again. | 2026-10-27 |
| `spk_min_new_s` | 1.0 | s | Start value: a shorter segment starts no speaker and changes no speaker (D-057 part 5B, D-058); before the first speaker, it gets `Unidentified` (D-060). No source and no eval segment under 2.40 s; L-06 gave no fact (no segment length in the output); kept. C7 sets it with the diagnostic line (D-060). | 2026-10-27 |

## 7. Error behaviour

| Module | Message | Program |
|---|---|---|
| `asr` (startup) | `asr: CUDA is not available` | Stops before the MT load and before the microphone opens (exit code 1). |
| `asr`, `mt`, `speakers`, `text` | model file or folder not found | Stops at startup (exit code 1). |
| `text` (startup, P4) | `text: CUDA is not available` | Stops at startup (exit code 1). |
| `mt` | `libcublas.so.12 not found …` | Stops at startup (exit code 1). |
| `audio` | cannot connect to PulseAudio; no default microphone; no default output; no monitor source for the default output; no source with the exact id | Stops at startup (exit code 1). |
| `audio` | recording failed | Stops (exit code 1). |
| any thread | a `TirError` (each module error) | Stops with `tir-asr: <module>: <cause>` (exit code 1). |
| any thread | any other exception | Stops with its traceback, then `tir-asr: <thread>: <type>: <message>` (exit code 1). |
| `segment` | segment under `vad_min_speech_ms` | No output; counted in the shutdown line. |
| `app` (startup) | any exception that is not a `TirError` | Stops with its traceback, then `tir-asr: startup: <type>: <message>` (exit code 1). |
| `app` (startup) | Ctrl+C before "Listening" | `Stopped during the startup.` (exit code 0). |
| `pipeline` (stop) | `stop: thread <name> did not stop in <s> s` | Written after the shutdown line or the error line; the exit code does not change (D-061). |

No module retries, waits with a timeout, or changes to another device or model (R10). The only time limit is the clean stop (`STOP_JOIN_S`, D-061), and it is not silent.

## 8. Tools that the program does not use

The program (`cli`, `app`, `pipeline`) does not use these tools. §8.1 is outside the `tir_asr` package. §8.2 is in the package (`tir_asr.eval`), so that the unit tests can import it.

### 8.1 `scripts/export_chats.py`: chat export to Markdown (D-012)

- **Purpose:** deliverable D3. The tool changes chats from the Claude data export into one Markdown file for each chat. It changes only the format. It does not change the text.
- **Command:** `uv run python scripts/export_chats.py <EXPORT> chats/manifest.toml`
- **Input:**
  - `EXPORT`: the conversations JSON file from the Claude data export. The file stays outside the repository. The tool only reads it.
  - `chats/manifest.toml`: one `[[chat]]` table for each chat, with two keys:
    - `title`: the chat title in the app.
    - `file`: the output file name, for example `00-kickoff.md`.
- **Output:** for each manifest entry, the file `<file>` in the folder of the manifest. The tool replaces a file that exists. Git shows each change.
  - **Header:** the chat title, the chat ID, `created_at`, `updated_at`, and the number of messages in the file.
  - **Note:** the file has only the text blocks of the main branch, with no change. The note gives the number of messages in side branches, and the number of blocks of each other type in the main branch. The original chat in the app has all blocks.
  - **Messages:** each message of the main branch, in tree order. A heading gives the number, the sender, and `created_at`. Then each `text` block of `content` follows:
    - `human`: in a code fence. The fence has more backticks than the longest backtick sequence in the text.
    - `assistant`: as Markdown, with no change.
    - A message with no text block gets the line "(This message has no text blocks.)".
  - **Terminal:** one line for each file, with the file name and the number of messages.
- **Main branch:** the path from the root to the leaf message with the newest `created_at`. The root is the parent ID `00000000-0000-4000-8000-000000000000` (**[RUN]** in C0).
- **Not used:** `message.text` (it has a placeholder in place of the tool calls), `account`, `attachments`, `files`, and all blocks that are not `text`.
- **Errors (fail loudly, R10):** the tool stops with exit code 1 and the message `export_chats: <cause>`. If one chat has an error, the tool writes no file. Causes:
  1. The export is not valid JSON, or the manifest is not valid TOML.
  2. A key is missing, or a value has the wrong type (for example, a chat has no `chat_messages`).
  3. A manifest `file` is not a plain file name that ends in `.md`.
  4. Two manifest entries have the same `title` or the same `file`.
  5. A manifest `title` matches no chat, or two or more chats.
  6. A chat has no messages.
  7. A parent message ID is not in the chat and is not the root ID, or the parent chain has a loop.
  8. Two leaf messages have the same newest `created_at`.
  9. A sender is not `human` or `assistant`.
- **Limits:**
  - Only the Python standard library (`json`, `tomllib`). No new dependency.
  - The tool does not show tool calls, tool results, thinking summaries, injected prompts, documents, or side branches (D-012, option B).
  - **[RUN]** The format facts come from one chat (C0). The final export after C8 can have a different format.

### 8.2 `tir_asr.eval`: eval tools for the bake-off (C3, D-046, D-047)

- **Purpose:** the bake-off of the ASR and MT candidates (PLAN C3). The rules of the core modules apply: no `laptop` import (T-IMPORT-01).
- **Eval data (D-046):**
  - Audio: `data/eval/raw/<s>.mic.wav` (Aren, "Me") and `data/eval/raw/<s>.call.wav` (Speaker 1 and Speaker 2), 48 kHz, mono, float32. `data/` is not in git.
  - Labels: `data/eval/raw/<s>.labels.txt`, exported from Audacity: start (s), tab, end (s), tab, line ID.
  - References: the Armenian and English columns of `docs/eval/scripts.md`.
- **`normalize.py`** (branch `c3-normalize`, D-047): `normalize_hy(text: str) -> str`.
  - Rules, in this order: (1) Unicode NFKC; (2) lowercase; (3) delete «՜» U+055C, «՛» U+055B, «՟» U+055F, and «՚» U+055A, with no space, and keep «՞» U+055E (P1); (4) «եւ» → «եվ», which also covers «և»; (5) one space for each other punctuation mark or symbol (Unicode categories P and S); (6) one space between words, and no space at the start or at the end.
  - Digits do not change (N1).
  - Only the Python standard library (`unicodedata`). No error: each `str` is a valid input.
  - Limit: an ASCII «?» in place of «՞» becomes a space.
- **`metrics.py`** (branch `c3-metrics`, D-047, D-049):
  - `edit_distance(ref, hyp) -> int`: the minimum number of substitutions, deletions, and insertions; each costs 1.
  - `wer(refs, hyps)` and `cer(refs, hyps) -> float`: `normalize_hy` on each text, then words (WER) or characters with the spaces (CER). The result is the total edits divided by the total reference length, for the full list.
  - `chrf(refs, hyps) -> float`: `sacrebleu` `CHRF()` with its default values (character order 6, word order 0, beta 2), for the full list, 0 to 100. The English text gets no normalization.
  - `digit_words(texts) -> int`: the number of normalized words with a digit (D-047, N1).
  - `label_accuracy(truths, labels, weights) -> float` (branch `c5-cluster`, D-057 part 2): the label accuracy after the best one-to-one mapping of the labels to the true speakers (`scipy.optimize.linear_sum_assignment`, maximum matched weight). The weight of a segment is its speech time, or 1 for a count. A label with no true speaker, and a true speaker with no label, count as errors. A segment with no label (`None`, D-060) is always an error. The result is the matched weight divided by the total weight.
  - Errors of `label_accuracy`: `metrics: <n> true speakers, <m> labels, and <k> weights`; `metrics: no segments`; `metrics: weight <w> is not positive`.
  - Errors: `MetricError(TirError)`: `metrics: <n> references and <m> hypotheses`; `metrics: the references have no words`.
  - Dependency: `sacrebleu` in the dev group (CI installs it).
- **`data.py`** (branch `c3-data`, D-046, D-048, D-049):
  - `load_wav_16k(path)`: a mono float32 WAV file at 48 kHz (resampled with `scipy.signal.resample_poly(x, 1, 3)`) or at 16 kHz (no change). Returns float32 audio at 16 kHz.
  - `with_end_silence(audio)`: adds `END_SILENCE_S` = 1.0 s of zeros, so that the last segment of a file closes (D-048).
  - `read_references(scripts_md, script) -> list[ScriptLine]`: `ScriptLine(id, speaker, side, hy, en)`, in table order; the ID has no "†"; the side is "mic" for "Me" and "call" for the other speakers.
  - `read_labels(path, lines) -> list[Label]`: `Label(id, start, end)` from an Audacity label file; each line of the script has exactly one label.
  - `assign_segments(segments, labels)`: for each segment, the ID of the label with the largest time overlap; on equal overlaps, the label that starts first; `None` with no overlap (the line view of D-046).
  - Errors: `DataError(TirError)`, `data: <file>: <cause>`: channels, sample format, sample rate, columns, no lines for a script, label fields, a time that is not a number, end before start, unknown, missing, or repeated ID.
  - Dependency: `scipy` in the dev group (CI installs it).
- **`run.py`** (branch `c3-run`, D-046, D-048, D-051), core with no `laptop` import:
  - `segment_file(audio, vad, params)`: adds the end rule (`with_end_silence`), then sends each 512-sample frame into the program's `Endpointer`. Frame k gets the arrival time (k + 1) × 0.032 s, so all segment times are audio times, the same as the label times.
  - `transcribe_all(segments, transcriber, clock)` and `translate_all(texts, translator, clock)`: one call for each segment, with its time (`Timed(text, seconds)`). An empty ASR text gets no MT call: "" and 0.0 s (D-031).
  - `score_side(lines, labels, segments, hy, en, asr_s, mt_s) -> SideScore`: WER, CER, and chrF of the joined texts (D-046 point 2); the digit words; the line view with `assign_segments` (D-046 point 3) and the number of segments outside each label; the audio time, the ASR RTF, and the mean and maximum time of the ASR calls and of the MT calls.
- **`scripts/bakeoff.py`** (model level, D-051): `--asr <name> --mt <name> [--mt-input asr|reference]`.
  - It runs S1–S3, both sides, and writes `test-results/bakeoff/<asr>+<mt>.json` (with `--mt-input reference`: `none+<mt>+ref.json`, the MT of the reference Armenian lines, with no ASR).
  - The JSON holds the versions, the GPU, the parameters, the load time, the VRAM (`torch.cuda.mem_get_info()`, before and after each load), the warm-up time, the texts and times of each segment, the scores of each file, and the totals for "mic", "call", and "all".
  - Load order ASR, MT, VAD (D-043). One new `SileroSpeechProbability` for each file, because the VAD keeps its state.
  - Command: `env -u LD_LIBRARY_PATH HF_HUB_OFFLINE=1 uv run python scripts/bakeoff.py --asr nemo-rnnt --mt nllb-ct2` (D-030).
- **Candidate adapters** (branch `c3-candidates`, D-014, D-015, D-049, D-051). Each is in `ADAPTERS` of T-IMPORT-01. The runner selects them by name. The program does not import them.
  - `nemo-ctc` (`nemo_ctc.py`, `NemoCtcTranscriber`): the `.nemo` file of the program adapter, with `change_decoding_strategy(decoder_type="ctc")`.
  - `opus-ct2` (`opus_ct2.py`, `OpusCt2Translator`): `Helsinki-NLP/opus-mt-hy-en`, converted to CTranslate2 in `models/opus-mt-hy-en-ct2-float16` (float16), on `cuda`, with `mt_compute_type` and `mt_beam_size`. Its `ctranslate2` import comes after the cuBLAS preload of `tir_asr.mt.ct2_nllb` (D-030).
  - `buzz-whisper` (`buzz_whisper.py`, `BuzzWhisperTranscriber`): `BuzzASR/armenian` (Whisper-large-v3, full fine-tune) on Transformers, float16, `cuda`. `generate(num_beams=1, no_repeat_ngram_size=3, repetition_penalty=1.2)`, from the model card.
  - `seamless` (`seamless.py`): `facebook/seamless-m4t-v2-large` on Transformers, float16, `cuda`, with the default generate values. `SeamlessSpeech` (`SeamlessM4Tv2ForSpeechToText`) gives the ASR (`tgt_lang="hye"`) and the end-to-end English (`"eng"`, runner name `seamless-s2tt`, with `--asr seamless` and no second load). `SeamlessText` (`SeamlessM4Tv2ForTextToText`) gives the MT (`src_lang="hye"`, `tgt_lang="eng"`).
- **`nearest.py`** (branch `c5-cluster`, D-057 part 4): `NearestClusterer(threshold, min_new_s)`, rule B-max, for the threshold sweep only. It subclasses `OnlineClusterer` (§2.8) and keeps all embeddings of each speaker. The similarity to a speaker is the highest cosine similarity to one of its embeddings. The program keeps only one rule (D-057).
- **`streams.py`** (branch `c5-embed`, D-057 part 1), core:
  - `Turn(start, end, speaker)` and `Stream(name, audio, turns)`. The true speaker is `<script>/<speaker>`, for example `s1/Speaker 1`, because the speakers of different scripts are different people.
  - `call_stream(script, audio, lines, labels)`: the call side of one script. Only the call-side lines become turns (the call file has no echo of "Me", D-046).
  - `cut(stream, start_s, end_s, name)` (`end_s` None: to the end) and `join(streams, name)`: the turn times shift with the audio. A cut inside a turn gives `data: <stream>: the cut at <t> s is inside a turn (<start>–<end> s)`.
  - `stream_d(s1, s2, s3)`: S1 from 0 to `STREAM_D_CUT_S` (34.0 s, in the 7.3 s silence after s1-06), S2, S1 from 34.0 s to the end, S3.
- **`spk_run.py`** (branch `c5-embed`, D-057 parts 2 to 4), core:
  - `truth_of(start, end, turns)`: the speaker of the turn with the largest overlap; on equal overlaps, the earlier turn; None with no overlap.
  - `embed_all(segments, turns, embedder, clock) -> list[Embedded]`: one embedding call for each segment, with its time, the speech time (`speech_end - start`), and the true speaker.
  - `sweep(items, rule, thresholds, min_new_s) -> list[SweepPoint]`: for each threshold, a new clusterer gets all segments in time order (a segment with no turn too, as in the program). Only the segments with a true speaker get a score: `accuracy_time`, `accuracy_count`, `wrong` (count), `scored`, and `speakers` (the speaker count of the clusterer).
  - `pairwise(items) -> Pairwise`: the lowest and the mean cosine of two segments of one speaker, the highest and the mean cosine of two segments of two speakers (None with no such pair).
  - `pass_range(points) -> (lowest, highest) | None`: the longest run of thresholds where each stream has `MAX_WRONG` (1) or fewer wrong segments; on equal runs, the first. The pass rule of D-057 part 3 also needs a width of `MIN_RANGE` (0.10) or more. `THRESHOLDS` are 0.20 to 0.90 in steps of 0.05.
- **Speaker candidates** (branch `c5-embed`, D-017, D-057 part 3, D-058), in `ADAPTERS` of T-IMPORT-01. Each has `embed(audio) -> np.ndarray` (one dimension, float32) on `cuda`, checks CUDA and the Hugging Face cache in the constructor, and raises `SpeakerError` (`speakers: CUDA is not available`; `speakers: model not in the Hugging Face cache: <repo>`). No separate model test: the sweep run is their model-level check (D-057).
  - TitaNet: D-058 selected this model. In `c5-pipeline`, its adapter moved to `speakers/titanet.py` (§2.8, D-057 part 3, point 3); `spk_bakeoff.py` imports it from there.
  - Removed after the sweep (D-058): `spk_ecapa.py` (SpeechBrain ECAPA, `speechbrain/spkrec-ecapa-voxceleb`) and `spk_wespeaker.py` (pyannote.audio WeSpeaker, `pyannote/wespeaker-voxceleb-resnet34-LM`, with the telemetry switch `PYANNOTE_METRICS_ENABLED=false`), and the dependency group `spk-eval`. The `c5-embed` commits keep them; `docs/eval/results.md` has their numbers.
- **`scripts/spk_bakeoff.py`** (model level, branch `c5-embed`): `--model titanet` (the other two choices left with D-058). It loads the model (with one warm-up call of `WARMUP_AUDIO_S` zeros), then the VAD (D-043), and builds the four streams (S1, S2, S3 call sides, and D). For each stream: the segments of the program's `Endpointer` (`segment_file`, `Params()`), `embed_all`, `pairwise`, and `sweep` with both rules (`CentroidClusterer`, `NearestClusterer`) and `min_new_s` = 1.0 s. It prints a table for each rule and `pass_range`, and writes `test-results/bakeoff/spk-<model>.json` (versions, GPU, parameters, load time, VRAM, warm-up time, the segments, the pairwise values, the sweep, and the pass result).
  - Command: `env -u LD_LIBRARY_PATH HF_HUB_OFFLINE=1 uv run --no-sync python scripts/spk_bakeoff.py --model titanet`.
- The next branches add their contracts here.

## 9. Open points for Aren (C2)

No open points. Accepted on 2026-10-25: D-029 (queue with no size limit), D-030 (CUDA 12 cuBLAS), D-031 (empty ASR text), D-032 (end of a test WAV clip), D-033 (`mt_beam_size`), D-034 (no keys in the MVP; decide after M3).

## 10. Change log

| Version | Date | Change |
|---|---|---|
| 0.0 | 2026-10-23 | Template. |
| 0.1 | 2026-10-23 | New §8: contract of `scripts/export_chats.py` (S1, D-012). The change log is now §9. |
| 0.2 | 2026-10-25 | C2 draft: overview, contracts of `audio`, `segment`, `asr`, `mt`, `output`, `pipeline`, `cli`; data types; threads; constants; parameters (D-015, D-026, D-027); error behaviour; open points. The change log is now §10. |
| 0.3 | 2026-10-25 | Aren's review: D-029 to D-034 accepted; no parallel GPU work and no `asyncio` (§4); rounding note (§2.5). |
| 0.4 | 2026-10-25 | C2b: `Params` dataclass (§5) and `Endpointer.short_segments` (§2.2), agreed by Aren in C2b. Not yet agreed: `Endpointer(params, vad)` calls the VAD itself (§2.2, §4); lengths counted in frames (§2.2); `SegmentError` location. |
| 0.5 | 2026-10-25 | C2c, D-037: adapter class names `NemoRnntTranscriber` and `Ct2NllbTranslator`; the constructors load the models (§2.3, §2.4); no warm-up method in the adapters, the pipeline makes the warm-up calls (§2.6); `cli.py` is only the `argparse` interface (§2.7); `verbose=False` for NeMo (§2.3). Status line: the v0.4 changes apply D-036. |
| 0.6 | 2026-10-25 | C2c, branch `c2c-mt` (§2.4): the default `model_dir` is relative to the project folder; the check for `model.bin`; the conversion command in the error message; the cuBLAS error names the missing file. |
| 0.7 | 2026-10-25 | C2d, branch `c2d-output` (§2.5), D-040: `format_block(line, session_start)` and `write_block(line, session_start, stream)`; a blank line after each block; the seconds of the block time are cut. |
| 0.8 | 2026-10-26 | C2d, branch `c2d-audio` (§2.1, §3, §7), D-041: `SoundcardMicrophone(device=None)` with an exact device id; the stream opens in `blocks()`; blocks of shape (512,); the error for a missing exact id; the probe B numbers in the limits; audio "normally in [−1, 1]". |
| 0.9 | 2026-10-26 | C2d, branch `c2d-pipeline` (§2, §2.6, §4, §7), D-042: `run()` and `warm_up()`; the session start before the capture; the stop, the shutdown line, and the exit codes; `TirError` in `errors.py`; the error line for other exceptions. |
| 0.10 | 2026-10-26 | C2d, branch `c2d-cli` (§2, §2.7, §7), D-043: `cli.py` and `app.py`; the startup sequence with its lines and places; the load order ASR, MT, VAD; the GPU memory; the NeMo lines; the errors and Ctrl+C during the startup; the `tir-asr` command. |
| 0.11 | 2026-10-26 | C2d, branch `c2d-cli` (§2.6, §4, §5), D-044: the main thread waits with the time limit `STOP_POLL_S` (0.5 s) in a loop, so that Ctrl+C works; T-E2E-02. |
| 0.12 | 2026-10-26 | C2d, branch `c2d-cli` (§2.7), D-045: the launcher `run.sh`. |
| 0.13 | 2026-10-26 | C3, branch `c3-normalize` (§8), D-046 and D-047: §8 is now "Tools that the program does not use"; new §8.2 with the eval data and `normalize_hy`. |
| 0.14 | 2026-10-26 | C3, branch `c3-metrics` (§8.2), D-049: the contract of `metrics.py`. |
| 0.15 | 2026-10-26 | C3, branch `c3-data` (§8.2), D-046, D-048, D-049: the contract of `data.py`. |
| 0.16 | 2026-10-26 | C3, branch `c3-run` (§8.2), D-051: the contracts of `run.py` and `scripts/bakeoff.py`. |
| 0.17 | 2026-10-26 | C3, branch `c3-candidates` (§8.2), D-051: the candidates `nemo-ctc` and `opus-ct2`. |
| 0.18 | 2026-10-26 | C3, branch `c3-candidates` (§8.2), D-051: the candidates `buzz-whisper` and `seamless` (ASR, MT, end to end). |
| 0.19 | 2026-10-26 | C4, branch `c4-audio` (§2.1, §3, §7), D-054: `SoundcardSource(label, device)` in `audio/soundcard_source.py` replaces `SoundcardMicrophone`; the device id is required; the adapter functions `list_sources`, `default_microphone_id`, and `default_system_id`; the core module `audio/devices.py` (`SourceInfo`, `format_source_list`); the source label `"System"`; new errors. |
| 0.20 | 2026-10-26 | C4, branch `c4-pipeline` (§1, §2.6, §3, §4), D-054: `run(sources, …)` with one `(source, vad)` pair, one `Endpointer`, and one capture thread `capture <label>` for each source; one queue and one worker; "done" after the end mark of each source; the sums in the shutdown line; the attribute `label` of `AudioSource`; the text of "not processed" agrees with the code. |
| 0.21 | 2026-10-26 | C4, branch `c4-cli` (§2.7), D-054: the flags `--mic`, `--system`, and `--list-devices`; `app.log_versions`, `app.select_sources`, and `app.list_devices`; the sources before the model load; one VAD for each source; the new startup sequence. |
| 0.22 | 2026-10-27 | C5, branch `c5-cluster` (§2, §2.8, §3, §8.2), D-057: the core module `speakers/cluster.py` (`OnlineClusterer`, `CentroidClusterer`, `SpeakerError`); the interface `SpeakerEmbedder`; `label_accuracy` in `metrics.py`; the eval rule `NearestClusterer` in `nearest.py`. |
| 0.23 | 2026-10-27 | C5, branch `c5-embed` (§8.2), D-057: `streams.py`, `spk_run.py`, the three speaker candidates, the group `spk-eval`, and `scripts/spk_bakeoff.py`. |
| 0.24 | 2026-10-27 | C5, branch `c5-embed` (§8.2), D-058: TitaNet selected; the ECAPA and WeSpeaker candidates and the group `spk-eval` removed; `spk_bakeoff.py` has only `--model titanet`. |
| 0.25 | 2026-10-27 | C5, branch `c5-pipeline` (§1, §2, §2.5–§2.8, §3, §4, §6, §7, §8.2), D-058, D-059: the speaker step in the worker (`SpeakerLabeler`, `labelers` in `run()`, no step for an empty text); the `spk` latency step; `Line.spk_end`; `warm_up` with the embedder; the speaker model load; the TitaNet adapter in `speakers/titanet.py`; the parameters `spk_threshold` and `spk_min_new_s`. |
| 0.26 | 2026-10-27 | C5, branch `c5-pipeline` (§2.5, §2.8, §3, §6, §8.2), D-060: a short first segment gets no label (`assign` gives `None`) and the labeler gives `"Unidentified"`; `label_accuracy` counts a segment with no label as an error; the L-06 limits (two voices in one segment, noise); the parameters kept after L-06. |
| 0.27 | 2026-10-27 | C5, branch `c5-stop` (§2.6, §4, §5, §7), D-061: the clean stop: `run()` waits for all threads with the limit `STOP_JOIN_S` (2.0 s) before it returns; the capture threads close their audio streams; the error line for a thread that does not stop. |
| 0.28 | 2026-10-27 | C6, branch `c6-textstep` (§1, §2, §2.3, §2.4, §2.6, §2.7, new §2.9, §3, §4), D-062: the text step `TextStep` (Template Method) with `CascadeTextStep` (P1); `TextResult`; `run()` and `warm_up()` get one text step; `load_models` returns `(vads, text_step, embedder)`. No change of behaviour. |
| 0.29 | 2026-10-27 | C6, branch `c6-seamless` (§2, §2.5, §2.9, §3, §7), D-063: the P4 adapter `SeamlessTextStep` (variant V2: one encoder pass and one decode of the rows `hye` and `eng`); `TextError`; `TextStep.STEPS` and `Line.steps`; the one latency step `s2t` of P4. |
