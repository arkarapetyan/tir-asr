# ARCHITECTURE.md

**Project:** tir-asr · **Version:** 0.12 · **Date:** 2026-10-26
**Status:** v0.3 APPROVED by Aren on 2026-10-25. The v0.4 changes (C2b) apply D-036, ACCEPTED on 2026-10-25. The v0.5 and v0.6 changes (C2c) apply D-037, ACCEPTED on 2026-10-25; Aren reviews the text (see §10). The v0.7 changes (C2d) apply D-040, ACCEPTED on 2026-10-25. The v0.8 changes (C2d) apply D-041, ACCEPTED on 2026-10-26. The v0.9 changes (C2d) apply D-042, ACCEPTED on 2026-10-26. The v0.10 changes (C2d) apply D-043, ACCEPTED on 2026-10-26. The v0.11 changes (C2d) apply D-044, ACCEPTED on 2026-10-26. The v0.12 change (C2d) applies D-045. C2 contracts for the walking skeleton (microphone → VAD → ASR → MT → terminal). C4 adds the system audio, C5 adds the speakers. §8 is complete (S1, D-012).

---

## 1. Overview

The program captures the microphone, cuts the audio into speech segments, transcribes each segment to Armenian text, translates the text to English, and prints one block for each segment.
Core modules have no model import and no audio-device import. Adapter modules hold the model and device code (D-021). Unit tests give fakes to the core modules.

```
 microphone ──► audio (adapter) ──AudioBlock──► segment: Endpointer (core) ◄── SpeechProbability (Silero adapter, CPU)
                capture thread                          │
                                                        ▼ Segment
                                                 segment queue (unbounded)
                                                        │
                                   worker thread        ▼
                                   asr: Transcriber (NeMo adapter, GPU) ──► Armenian text
                                   mt:  Translator (CTranslate2 adapter, GPU) ──► English text
                                   output: format_block (core) ──► terminal (one write for each block)
```

## 2. Modules and contracts

| Module | Kind | Input | Output | Errors (fail loudly, R10) | Limits |
|---|---|---|---|---|---|
| `audio` | adapter | microphone (C2), system audio (C4) | `AudioBlock` stream | `AudioError` | §2.1 |
| `segment` | core + adapter | `AudioBlock` | `Segment` | `SegmentError` | §2.2 |
| `asr` | adapter | `Segment.audio` | Armenian text (`str`) | `AsrError` | §2.3 |
| `mt` | adapter | Armenian text | English text (`str`) | `MtError` | §2.4 |
| `speakers` | (C5) | | | | |
| `output` | core | `Line` | one text block | none | §2.5 |
| `pipeline` | core | the modules above | threads, queue, stop, exit code | the first error of a thread | §2.6 |
| `errors` | core | — | `TirError`, the base class of the module errors | — | §2.6 |
| `cli` | core | command line | calls `app.main()`; its exit code | — (`argparse` stops on a wrong argument) | §2.7 |
| `app` | loads the adapters (in `ADAPTERS` of T-IMPORT-01) | the adapters | startup log, exit code | the error line (§7) | §2.7 |

Each error class has the module name in its message: `<module>: <cause>`. Each error class inherits from `TirError` in `errors.py` (D-042).

### 2.1 `audio`

- **C2 source:** the default microphone of PulseAudio (PipeWire). The startup log gives its name. Device selection flags come in C4 (F1).
- **Adapter** `audio/soundcard_mic.py` (`SoundcardMicrophone(device=None)`, D-041): `soundcard` 0.4.6 recorder with `samplerate=16000`, `channels=1`, `blocksize=512`. Each `record(numframes=512)` gives one `AudioBlock`.
  - **Constructor:** it imports `soundcard` and selects the source, so that the errors come at startup. With no `device`, it uses the default microphone. A `device` must be an exact source id among all sources, monitors included (for example `<sink>.monitor`). The adapter checks the exact id first, because `soundcard.get_microphone` also accepts a part of the name or a regex match [SOURCE: `soundcard` 0.4.6], which can select a different device with no error (R10).
  - **`blocks()`:** it opens the stream, then gives blocks until the caller closes the iterator. The stream keeps all audio from the moment it opens, with no limit [SOURCE], so it must not open before "Listening".
  - The attribute `name` gives the device name for the startup log.
- **Contract:** each block has exactly 512 float32 samples in an array of shape (512,) (32 ms at 16 kHz, mono), the label `"Me"`, and the `time.monotonic()` value at its arrival. `soundcard` gives (512, 1); the adapter makes it flat.
- **Errors:**
  - `audio: cannot connect to the PulseAudio server` (the `soundcard` import fails with an `AssertionError`) [RUN]. T-AUDIO-02.
  - `audio: no default microphone`.
  - `audio: no source with the exact id <id>`. T-AUDIO-03.
  - `audio: recording failed: <cause>` (`soundcard` raises `RuntimeError` when the stream fails) [SOURCE].
  - `audio: block has <n> samples, expected 512`.
- **Limits:**
  - PulseAudio converts the device format to 16 kHz mono. [RUN] A 440 Hz tone through a null sink (2 channels, 48 kHz) keeps its frequency and its level (probe B, T-AUDIO-01). C4 tests the call path.
  - [RUN] The arrival gaps alternate between about 21 ms and 43 ms, with a mean of 32 ms (probe B). Thus an arrival time can be up to about 11 ms late against an even 32 ms grid.
  - [RUN] A monitor with no audio gives blocks of zeros (probe B). Thus the `Endpointer` can close a segment during a silence on the system side (C4).
  - [RUN] The samples can be a little outside [−1, 1]: the default microphone gave −1.0496 (probe B, Q-11). The adapter does not clip them (D-041).
  - The sim tests do not cover the default-microphone line; L-01 covers it.
  - When PulseAudio reports lost audio, `soundcard` fills the gap with zeros and gives no warning [SOURCE: `soundcard` 0.4.6]. The program cannot see this loss. C4 tests for drift and loss.
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
- **Warm-up (D-022, D-037):** the adapter has no warm-up method. The pipeline calls `transcribe` with `WARMUP_AUDIO_S` of zeros at startup (§2.6).
- **Contract:** `transcribe(audio)` takes float32, mono, 16 kHz audio and returns the Armenian text. The text can be empty. NeMo shows no progress bar (`verbose=False`).
- **Errors:** `asr: CUDA is not available` (no CPU fallback, R10); `asr: model file not in the Hugging Face cache: <name>`; `asr: unexpected output type <type>`.
- **Limits:** one segment for each call (batch size 1). [RUN] 0.027–0.036 s for each call after the warm-up, 987 MiB VRAM (T-INSTALL-02). The model writes commas where a person writes "։" (Q-06).

### 2.4 `mt`

- **Adapter** `mt/ct2_nllb.py` (`Ct2NllbTranslator`, D-037): `facebook/nllb-200-distilled-600M`, converted to CTranslate2 in `models/nllb-200-distilled-600M-ct2-float16`, on `cuda`, `compute_type = mt_compute_type` (D-015). Tokenizer: Transformers `AutoTokenizer` from the Hugging Face cache, source `hye_Armn`, target `eng_Latn`.
- **CUDA 12 cuBLAS (D-030):** before `import ctranslate2`, the adapter loads `libcublasLt.so.12` and then `libcublas.so.12` from the package `nvidia-cublas-cu12` (`ctypes`, `RTLD_GLOBAL`). The file paths come from `importlib.metadata`. The program needs no `LD_LIBRARY_PATH`.
- **Load:** the constructor `Ct2NllbTranslator(params, model_dir)` loads the model and the tokenizer. It reads `mt_compute_type` and `mt_beam_size` from `Params`. The default of `model_dir` is a module constant. It is a model location, not a parameter (D-037). The default is relative to the current folder, so the program must start in the project folder. The adapter checks for `model_dir/model.bin` before the load.
- **Warm-up (D-022, D-037):** the adapter has no warm-up method. The pipeline calls `translate(WARMUP_TEXT)` at startup (§2.6).
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
  | `out` | MT end | the moment before the write |
  | Total | `speech_end` | the moment before the write |

- **Empty ASR text (D-031):** in C2 to C6, a short block with no MT call: the time, the label, `HY: (no text)`, and a latency line with `vad`, `asr`, and the total. C7 removes this block for the delivery; the shutdown line still counts the empty texts.
- **Rounding:** the program adds the raw step values. The printed steps can differ from the printed total by rounding (maximum 0.02 s for 4 steps).
- **Limit:** `out` does not include the time that the terminal needs to show the text.

### 2.6 `pipeline`

- **Core** `pipeline.py` (D-042). `run(source, vad, transcriber, translator, params, clock, out, err) -> int` builds the `Endpointer`, starts the threads (§4), and returns the exit code. The clock is `time.monotonic` in the program and a fake clock in unit tests. `out` gets the blocks and the shutdown line; `err` gets the error line.
- **Warm-up (D-022, D-037, D-042):** `warm_up(transcriber, translator, clock) -> (asr_s, mt_s)` calls `transcribe` with `WARMUP_AUDIO_S` of zeros, then `translate(WARMUP_TEXT)`, and returns the two times. The caller prints them. It is separate from `run()`, so that the counts of the model calls in T-PIPE-03 stay correct.
- **Session start (D-042):** `run()` takes the session start from the clock, prints "Listening. Press Ctrl+C to stop.", and only then starts the threads. The source opens its stream at its first block (D-041). Thus no block time is before the session start.
- **Worker:** for each segment, `transcribe`, then the ASR end from the clock. If the text is not empty: `translate`, then the MT end from the clock. If the text is empty: no MT call, and the MT end is the ASR end (D-031). Then the write time from the clock, and `write_block` (§2.5).
- **Stop (D-042):**
  - Ctrl+C: the shutdown line, then exit code 0. Ctrl+C takes effect within `STOP_POLL_S` (0.5 s, D-044). The open segment, the segments in the queue, and a segment in ASR or MT are not processed; the shutdown line gives their number. Aren accepted this risk: a Ctrl+C right after the last phrase can lose that line. T-E2E-02 (model test) and L-02 check this path; it has no unit test.
  - End of the source (tests and the WAV source only, D-025): the capture thread puts an end mark in the queue. The worker finishes the segments in the queue, and then the shutdown line comes, with exit code 0.
  - Shutdown line: `Stopped. Segments: <n>, short segments: <n>, empty texts: <n>, not processed: <n>.` "Segments" counts the written blocks. An output lock makes the shutdown line the last line.
- **Errors (D-042):** the first exception in a thread stops the program. `run()` writes the error line to `err` and returns 1, with no shutdown line. A `TirError` gives `tir-asr: <module>: <cause>`. Any other exception gives its traceback, then `tir-asr: <thread>: <type>: <message>` (the thread is `capture` or `worker`).

### 2.7 `cli` and `app`

- **Launcher (D-045):** `./run.sh` in the project folder. It goes to the project folder (so it works from any folder), sets `HF_HUB_OFFLINE=1` (nothing downloads, K2), and starts `.venv/bin/tir-asr` with `exec` (so Ctrl+C goes straight to the program). The arguments go to the program. If `.venv/bin/tir-asr` is missing, it stops with a message to run `uv sync`.
- **Command:** `tir-asr`, from `[project.scripts]` in `pyproject.toml` (`tir_asr.cli:main`). After a change to `pyproject.toml`, `uv sync` installs the command. C2 has no flags except `--help`. C4 adds the device flags.
- **`cli.py` (core, D-037, D-043):** only the `argparse` interface. After the parse, it imports `app` and returns `app.main()`. Thus `--help` imports no model and no audio-device package (T-CLI-01).
- **`app.py` (D-042, D-043):** it loads the adapters, prints the startup log, and calls the pipeline. It imports the adapters inside its functions, in the load order below. Each startup line starts with `startup: `.
- **Startup sequence:**

  | Step | Place | Startup line |
  |---|---|---|
  | 1. Versions and parameters | `app.load_models` | `startup: tir-asr …; torch …; nemo-toolkit …; ctranslate2 …; silero-vad …; soundcard …; CUDA (torch) …` (from `importlib.metadata`), then one `startup: parameter <name> = <value>` line for each parameter (`config.parameter_lines`, T-CFG-02) |
  | 2. ASR load, with the CUDA check (§2.3) | `app.load_models` | `startup: GPU <name>`, then `startup: ASR loaded in <s> s; GPU memory used <MiB> MiB` |
  | 3. MT load (the cuBLAS preload, D-030) | `app.load_models` | `startup: MT loaded in <s> s; GPU memory used <MiB> MiB (+<MiB> MiB)` |
  | 4. VAD load | `app.load_models` | `startup: VAD loaded in <s> s; torch CPU threads <n>` |
  | 5. Warm-up (§2.6) | `pipeline.warm_up`, called by `app.main` | `startup: warm-up ASR <s> s, MT <s> s` |
  | 6. Microphone (§2.1; the stream opens later) | `app.main` | `startup: microphone <name>` |
  | 7. "Listening" and the session start | `pipeline.run` (§2.6) | `Listening. Press Ctrl+C to stop.` |

- **Load order (D-043, point 2a):** ASR first, so that a missing CUDA gives `asr: CUDA is not available` before any other GPU call. Then MT, then VAD. The MT adapter loads the CUDA 12 cuBLAS before its own `import ctranslate2`; no other module imports `ctranslate2`. [RUN] torch and NeMo before the MT adapter in one process: T-MODEL-MT-01 passes with no `LD_LIBRARY_PATH` (c2d-pipeline model run).
- **GPU memory:** `torch.cuda.mem_get_info()` gives the used memory of the full device, so the MT line also counts CTranslate2.
- **NeMo lines (D-043, point 3):** NeMo prints about 185 lines at its load. M1 does not hide them (R10). C7 decides again.
- **Errors and Ctrl+C during the startup (D-043, point 4):** a `TirError` gives `tir-asr: <message>` and exit code 1. Any other exception gives its traceback, then `tir-asr: startup: <type>: <message>`, and exit code 1. Ctrl+C before "Listening" gives `Stopped during the startup.` and exit code 0.
- **Stop:** §2.6 (Ctrl+C, the shutdown line, the exit codes).

## 3. Data types (core, `types.py`)

All times are `time.monotonic()` values in seconds. All audio is float32, mono, 16 kHz, normally in [−1, 1]. A loud input can give values a little outside (probe B: −1.0496, D-041).

| Type | Field | Type | Meaning |
|---|---|---|---|
| `AudioBlock` | `source` | `str` | Source label: `"Me"` (C2). |
| | `samples` | `np.ndarray` (512,) | One VAD frame. |
| | `arrival` | `float` | Arrival time of the block. |
| `Segment` | `source` | `str` | From the blocks. |
| | `audio` | `np.ndarray` | Speech with the pads (§2.2 rule 6). |
| | `start` | `float` | Start of speech (no pad). |
| | `speech_end` | `float` | True end of speech (D-023). |
| | `closed` | `float` | Time when the `Endpointer` closed the segment. |
| | `cut` | `bool` | True for a hard cut (§2.2 rule 5). |
| `Line` | `label` | `str` | `"Me"` (C2); `"Speaker N"` (C5). |
| | `start` | `float` | `Segment.start`. |
| | `hy`, `en` | `str` | Armenian text, English text. |
| | `speech_end`, `closed`, `asr_end`, `mt_end`, `write` | `float` | The times of §2.5. |

Interfaces (core, `typing.Protocol`):

| Interface | Method | Adapter (C2) | Unit-test fake |
|---|---|---|---|
| `AudioSource` | `blocks() -> Iterator[AudioBlock]` | `soundcard` microphone | a list of blocks |
| `SpeechProbability` | `__call__(samples) -> float` | Silero VAD | a list of numbers |
| `Transcriber` | `transcribe(audio) -> str` | NeMo RNNT | a fixed text |
| `Translator` | `translate(text) -> str` | CTranslate2 NLLB | a fixed text |

The WAV file source is test code only (D-025). It is in `tests/support/`, not in the package. It plays the clips at real-time speed and gives only whole frames; it drops the last part of a clip that is shorter than one frame. It adds no silence (D-032): a clip must end with at least 512 ms of silence, or the test fails.

## 4. Data flow, threads, and queues

| Thread | Work | Blocks on |
|---|---|---|
| Main | Startup (§2.7), then it waits for Ctrl+C, for "done", or for an error from a thread. | the event queue |
| Capture (one for each source) | Reads the blocks, calls `Endpointer.push` (which calls `SpeechProbability`), puts each `Segment` in the segment queue. At the end of the source (tests only), it puts an end mark. | `record()` |
| Worker (one) | Gets a `Segment`, calls ASR, then MT (if the text is not empty), then writes the block. At the end mark, it puts "done" in the event queue. | the segment queue |

- **Segment queue:** `queue.Queue` with no size limit (D-029). A slow worker shows as a larger `asr` step on each line.
- **One worker thread** uses the GPU, so the GPU models run one at a time.
- **Main-thread wait (D-044):** the main thread waits on the event queue with a time limit of `STOP_POLL_S` (0.5 s), in a loop. The time limit changes nothing except that the main thread wakes up. [RUN] With no time limit, Ctrl+C did nothing: the process has 75–79 native threads, and Python handles a signal only when the main thread wakes up (L-02, probe C). T-E2E-02 checks Ctrl+C on the real program.
- **Errors:** each thread puts its exception in the event queue. The main thread stops the program (§2.6). The threads are daemon threads, so that they do not keep the program alive after the main thread returns.
- **No parallel GPU work.** One worker runs ASR and then MT. [RUN] This takes 0.10–0.17 s for each segment, and a new segment comes at most once in 0.76 s (calc). Two GPU threads would share the GPU, so each call would be slower; the gain is only when segments wait in the queue. C4 and C5 measure the queue wait before a change (R6).
- **No `asyncio`.** `soundcard`, NeMo, and CTranslate2 have blocking APIs. With `asyncio`, they would run in threads anyway. Threads and queues are simpler.
- **GIL:** the worker and the capture thread share the Python interpreter lock. A long Python step in the worker can delay the capture thread; PulseAudio then keeps the audio in its buffer [UNVERIFIED buffer size]. Q-10 checks it in the live run.

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

## 7. Error behaviour

| Module | Message | Program |
|---|---|---|
| `asr` (startup) | `asr: CUDA is not available` | Stops before the MT load and before the microphone opens (exit code 1). |
| `asr`, `mt` | model file or folder not found | Stops at startup (exit code 1). |
| `mt` | `libcublas.so.12 not found …` | Stops at startup (exit code 1). |
| `audio` | cannot connect to PulseAudio; no default microphone; no source with the exact id | Stops at startup (exit code 1). |
| `audio` | recording failed | Stops (exit code 1). |
| any thread | a `TirError` (each module error) | Stops with `tir-asr: <module>: <cause>` (exit code 1). |
| any thread | any other exception | Stops with its traceback, then `tir-asr: <thread>: <type>: <message>` (exit code 1). |
| `segment` | segment under `vad_min_speech_ms` | No output; counted in the shutdown line. |
| `app` (startup) | any exception that is not a `TirError` | Stops with its traceback, then `tir-asr: startup: <type>: <message>` (exit code 1). |
| `app` (startup) | Ctrl+C before "Listening" | `Stopped during the startup.` (exit code 0). |

No module retries, waits with a timeout, or changes to another device or model (R10).

## 8. Tools outside the package

These tools are not part of the `tir_asr` package. The program does not use them.

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
