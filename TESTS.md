# TESTS.md

**Project:** tir-asr · **Date:** 2026-10-27
**Rules:** RULES.md R5 (test-driven development) and D-006 (test runs).

Each test comes from a requirement in the brief (F, K, D in `PLAN.md` §1) or from a module contract in `ARCHITECTURE.md`.
Aren reviews each test before Claude writes it.

Test levels:

- **unit:** no model and no audio device. CI runs them.
- **model:** loads a real model. Aren runs them on the laptop.
- **sim:** the program captures from virtual audio devices. Aren runs them on the laptop.
- **live:** real devices and real people. Aren does the checklist in §4.

Status values: DESIGNED, APPROVED, WRITTEN (it fails), PASSES.

---

## 1. How to run the tests (D-006)

Claude gives the exact commands for each run. Each run writes its result into `test-results/`. Claude reads that file.
`test-results/` is in `.gitignore`.

## 2. Test list

### 2.1 Setup (C0)

| ID | Requirement | Input | Expected result | Level | Status |
|---|---|---|---|---|---|
| T-SETUP-01 | D-007: the package installs with uv and imports. | `uv sync --locked`, then `import tir_asr` | The import works. The installed version is `0.1.0`. | unit | PASSES (workspace and Aren's laptop, 2026-10-23) |

Note: T-SETUP-01 checks the setup only, not a module. Claude wrote it together with the setup, before Aren's review. Aren chose not to review the setup tests ("I wont check the setup tests", 2026-10-23).

### 2.2 Chat export tool (S1)

Contract: `ARCHITECTURE.md` §8.1. Decision: D-012 (option B). Aren approved the tests on 2026-10-23.
The unit tests run the tool as a command (`python scripts/export_chats.py`) on test data that each test makes. The test data is not real chat text.

| ID | Requirement | Input | Expected result | Level | Status |
|---|---|---|---|---|---|
| T-EXPORT-01 | D3: the text does not change. | One chat with both senders. The text blocks have Armenian letters, Markdown, HTML, `\r\n`, spaces at the line end, no last newline, and backtick sequences of length 3 and 4. | Each text block of the main branch is in the output file, with no change. | unit | PASSES (workspace and Aren's laptop, 2026-10-23) |
| T-EXPORT-02 | §8.1: a human text is in one code fence. | A human text with lines `` ``` `` and `` ```` `` in it. | A check with the CommonMark fence rule finds the fence end after the full text. The fence content is equal to the text. | unit | PASSES (workspace and Aren's laptop, 2026-10-23) |
| T-EXPORT-03 | §8.1: main branch. | A chat with 2 roots and 1 edit (two messages with the same parent). The list order is not the tree order. | Only the messages on the path to the newest leaf are in the file, in tree order. The text of the side-branch messages is not in the file. | unit | PASSES (workspace and Aren's laptop, 2026-10-23) |
| T-EXPORT-04 | §8.1: the note tells what is not in the file. | The chat of T-EXPORT-03 with `tool_use`, `tool_result`, `thinking`, `injected_prompt_block`, and `document` blocks, a `message.text` placeholder, and an `account.uuid`. | The note gives the number of side-branch messages and the number of blocks of each other type in the main branch. No text from those blocks, from `message.text`, or from `account` is in the file. | unit | PASSES (workspace and Aren's laptop, 2026-10-23) |
| T-EXPORT-05 | R4, §8.1: only the manifest chats. | An export with 3 chats. The manifest names 1 chat. | The tool writes 1 file. The text of the other 2 chats is in no output file. | unit | PASSES (workspace and Aren's laptop, 2026-10-23) |
| T-EXPORT-06 | §8.1: header and message headings. | One chat. | The header has the title, the chat ID, `created_at`, `updated_at`, and the number of messages. Each message heading has the number, the sender, and `created_at`. The terminal line gives the file name and the number of messages. | unit | PASSES (workspace and Aren's laptop, 2026-10-23) |
| T-EXPORT-07 | §8.1: a message with no text block. | An assistant message with only tool blocks. | Its heading is in the file, with the line "(This message has no text blocks.)". | unit | PASSES (workspace and Aren's laptop, 2026-10-23) |
| T-EXPORT-08 | §8.1: the same input gives the same output. | Run the tool two times. Before the second run, change the output file. | The second run replaces the file. The two outputs are equal, byte for byte. | unit | PASSES (workspace and Aren's laptop, 2026-10-23) |
| T-EXPORT-09 | §8.1: the input does not change. | One run. | The SHA-256 checksums of the export and of the manifest are the same before and after the run. | unit | PASSES (workspace and Aren's laptop, 2026-10-23) |
| T-EXPORT-10 | R10, §8.1: errors. | One case for each error cause 1–9 in §8.1. One more case: a manifest with 2 chats, and only the second chat has an error. | Exit code 1. The error output starts with `export_chats:` and names the cause. No output file exists. | unit | PASSES (workspace and Aren's laptop, 2026-10-23) |
| T-EXPORT-11 | D3 on real data. | Run 1: Aren runs the tool on the C0 export of 2026-10-23. Run 2: the final export after C8. | Exit code 0. Each manifest file exists. GitHub shows each file. The messages are the same as in the app. | live (manual) | Run 1 PASSES (Aren's laptop, 2026-10-23): exit code 0, 22 messages. The file is byte-equal to the workspace run, which found 25 of 25 text blocks unchanged and in order. Aren read `chats/00-kickoff.md` on the laptop: "dont see any changes to it" (2026-10-23). Aren read it on GitHub: "its fine" (2026-10-23). Open: run 2 after C8. |

### 2.3 Install check (C2)

Decisions: D-014, D-015, D-016, D-021, D-022, D-026, D-027. These tests measure. They have no quality limit: C3 sets the quality with the eval set.
Input from Aren: `data/eval/c2-check1.wav` (3 sentences) and `data/eval/c2-check2.wav` (2 sentences), 44.1 kHz stereo, with their `.hy.txt` and `.en.txt` reference texts.
Claude converted the two clips in the workspace to 16 kHz mono (`soxr`, quality VHQ, mean of the two channels): `data/eval/c2-check{1,2}.16k.wav`. C3 and C4 decide the resample step of the program, with a test.
Test file: `tests/model/test_install_check.py`.

**Change after Aren's approval (2026-10-25, Aren ran the changed tests the same day):** T-INSTALL-02 and T-INSTALL-03 show each output next to its reference text. They give no CER and no chrF. Reason: the metric code and the Armenian normalization rules are C3 work with their own tests (PLAN C3, step 1), and a number with no normalization can mislead (R6). T-INSTALL-03 also measures the beam sizes 1 and 2, for the `mt_beam_size` proposal.

| ID | Requirement | Input | Expected result | Level | Status |
|---|---|---|---|---|---|
| T-INSTALL-01 | D-016, RK13: PyTorch and CTranslate2 use the RTX 5070. | The environment check (`test-results/c2-install.txt`). | `torch.cuda.is_available()` is True. The capability is (12, 0). A float16 matrix product runs on the GPU. CTranslate2 finds 1 CUDA device and lists `float16`. | model | PASSES (Aren's laptop, 2026-10-25): torch 2.14.1+cu130, capability (12, 0), `sm_120` in the arch list; CTranslate2 4.8.3 finds 1 device. |
| T-INSTALL-02 | D-014, F2: ASR-1 on NeMo (RNNT) runs on the GPU. | The two clips and their Armenian text. | The model loads on `cuda`. No text is empty. The result file shows each text next to the reference, the load time, the peak VRAM, and the time of each call: clip 1, clip 1 again, clip 2, the first half of clip 1, clip 1 + clip 2, clip 1 again (D-022). | model | PASSES (Aren's laptop, 2026-10-25): load 1.85 s; call 1 0.458 s; the next calls 0.027–0.036 s for 2.78–12.17 s of audio; 987 MiB VRAM (nvidia-smi). |
| T-INSTALL-03 | D-015, F3: NLLB-600M on CTranslate2 (`mt_compute_type = float16`) runs on the GPU. | The Armenian reference texts: text 1, text 1 again, text 2, text 1 + text 2. | No English text is empty. The result file shows each text next to the reference, the load time, the VRAM, and the time of each call, for the beam sizes 1 and 2. The same inputs on PyTorch (Transformers, float16, GPU) give the times for D-016. | model | PASSES (Aren's laptop, 2026-10-25): CTranslate2 call 1 5.104 s, the next calls 0.066–0.132 s, +1930 MiB VRAM; PyTorch call 1 0.136 s, the next calls 0.082–0.174 s, +1196 MiB VRAM; beam sizes 1 and 2 give the same texts. One run for each value. |
| T-INSTALL-04 | D-018, D-026, D-027: Silero VAD runs on the CPU. | The two clips. | The result file gives each speech region and each pause, with its length in ms, and the segments for a minimum silence of 300, 500, and 800 ms. | model | PASSES (Aren's laptop, 2026-10-25): 0.10–0.30 ms of CPU for each 32 ms frame; pauses at sentence ends 64, 448, and 96 ms, at a comma 64 ms; 500 ms gives 1 segment for each clip; 300 ms splits clip 1 only at a sentence end. |
| T-INSTALL-05 | D-021: CI installs no `laptop` package. | CI on the next push. | The CI log shows no `torch` install. All CI steps pass. | unit (CI) | PASSES (CI on GitHub, 2026-10-25; Aren: "CI passed") |

### 2.4 Walking skeleton (C2)

Contracts: `ARCHITECTURE.md` v0.3. Decisions: D-022 to D-033. Unit tests use fakes for the four interfaces and build the frames in code. In the unit tests, frame `k` arrives at `(k + 1) × 0.032` s, so its start time is `k × 0.032` s.

**Unit (CI):**

| ID | Requirement | Input | Expected result | Level | Status |
|---|---|---|---|---|---|
| T-SEG-01 | §2.2 rule 1: start. | p = 0.1 for frames 0–4, 0.9 for frames 5–24, 0.1 after. | One segment. `start` = 0.160 s (start of frame 5). | unit | PASSES |
| T-SEG-02 | §2.2 rules 2–3, D-023, D-027: true end and close. | The input of T-SEG-01. | `speech_end` = 0.800 s (start of frame 25). The segment closes at frame 40 (the 16th silent frame): `closed` = 1.312 s. No segment before frame 40. | unit | PASSES |
| T-SEG-03 | §2.2 rule 2: speech after a short silence. | Speech, then 10 frames at 0.1, then speech again, then 20 frames at 0.1. | One segment, not two. `speech_end` = the start of the second silence. | unit | PASSES |
| T-SEG-04 | §2.2 rules 1–2: two thresholds. | Speech with frames at 0.4 inside; a silence with frames at 0.4 inside. | A frame at 0.4 in speech does not start a silence. A frame at 0.4 in a silence counts as silence: the close comes after 16 frames that are not ≥ 0.5. | unit | PASSES |
| T-SEG-05 | §2.2 rule 4, D-026: minimum length. | Speech of 7 frames (224 ms); speech of 8 frames (256 ms). | 7 frames: no segment, the short-segment count is 1. 8 frames: one segment. | unit | PASSES |
| T-SEG-06 | §2.2 rule 5, D-026: hard cut. | p = 0.9 for 11 s from frame 0. | The first segment closes at frame 312 (end 10.016 s): `cut` = True, `speech_end` = `closed` = 10.016 s, no end pad. A second segment starts at frame 313. | unit | PASSES |
| T-SEG-07 | §2.2 rule 5: maximum length with an open silence. | Speech to 9.9 s, then silence. The 10 s limit comes during the silence. | `cut` = False. `speech_end` = the start of the silence. | unit | PASSES |
| T-SEG-08 | §2.2 rule 6: audio and pads. | The input of T-SEG-01, audio = sample index (a ramp). | The segment audio is samples 2080 to 13279 (start − 480, end + 480). A start at frame 0 gives no start pad. | unit | PASSES |
| T-SEG-09 | §2.2 errors, R10. | A block of 500 samples; a probability of 1.2. | `SegmentError`: `segment: frame has 500 samples, expected 512`; `segment: probability 1.2 is not in [0, 1]`. | unit | PASSES |
| T-OUT-01 | F5, D-024: line format. | A `Line` with `start` 72.4 s after the session start, label "Me", Armenian and English text, fixed times. | The exact block of §2.5, with `[00:01:12]`, the four steps, two decimals, and the total. | unit | PASSES |
| T-OUT-02 | §2.5: latency arithmetic. | Times with steps 0.534, 0.413, 0.177, 0.004 s. | The total comes from the raw values (1.13 s). Each printed step is the rounded raw step. | unit | PASSES |
| T-OUT-03 | D-031: empty ASR text. | A `Line` with an empty `hy`. | `HY: (no text)`, no `EN` line, a latency line with `vad`, `asr`, and the total only. | unit | PASSES |
| T-OUT-04 | D-024, §2.5: one write for each block. | `write_block(line, session_start, stream)` with a fake stream. | The stream gets exactly one `write` call with the full block, then one `flush` call. | unit | PASSES |
| T-PIPE-01 | F2, F3, F5, §2.6, D-042: end-to-end with fakes. | 111 fake frames: p = 0.9 for frames 5–24 and 60–79, else 0.1. Fake ASR ("բարև"), fake MT ("hi"). Fake clock: session start 0.0; then ASR end, MT end, and write for each segment: 1.400, 1.500, 1.510 and 3.200, 3.300, 3.310. | `run` returns 0. The output is the "Listening" line, then two exact blocks (`[00:00:00]`: `vad 0.51s, asr 0.09s, mt 0.10s, out 0.01s \| Total 0.71s`; `[00:00:01]`: `vad 0.51s, asr 0.13s, mt 0.10s, out 0.01s \| Total 0.75s`), then the shutdown line with 2 segments. The error output is empty. | unit | PASSES |
| T-PIPE-02 | R10, §2.6, D-042: an error in a thread. | Three cases: (a) the fake ASR raises a `TirError` subclass with `asr: test`; (b) the fake MT raises `KeyError("x")`; (c) the fake VAD gives 1.2 (capture thread). | `run` returns 1. No block and no shutdown line. The error output is (a) `tir-asr: asr: test`; (b) a traceback, then `tir-asr: worker: KeyError: 'x'`; (c) `tir-asr: segment: probability 1.2 is not in [0, 1]`. | unit | PASSES |
| T-PIPE-03 | D-031: no MT call for an empty text. | The input of T-PIPE-01 with only the first region. The fake ASR returns "". Clock: 0.0, then ASR end 1.400 and write 1.410. | The fake MT gets no call. One exact block: `HY: (no text)` and `vad 0.51s, asr 0.09s \| Total 0.61s`. The shutdown line has 1 segment and 1 empty text. | unit | PASSES |
| T-PIPE-04 | §2.7, D-042: shutdown line. | 150 fake frames: a normal region (frames 5–24), a short region (frames 60–66, 224 ms), and a region with an empty text (frames 100–119). The fake ASR returns "բարև", then "". Then the source ends. | `run` returns 0. The last output line is exactly `Stopped. Segments: 2, short segments: 1, empty texts: 1, not processed: 0.` | unit | PASSES |
| T-PIPE-05 | D-022, D-037, D-042: warm-up. | `warm_up(transcriber, translator, clock)` with a fake clock 10.0, 10.4, 10.5. | The fake ASR gets one call: 32000 zeros, float32. The fake MT gets one call: `WARMUP_TEXT`. The result is (0.4 s, 0.1 s). | unit | PASSES |
| T-CFG-01 | R10, §6: approved parameters. | `config.py`. | Each value is equal to the §6 table. | unit | PASSES |
| T-CFG-02 | R10, §2.7, D-043: parameters in the startup log. | `parameter_lines(Params())` in `config.py`. | One line `parameter <name> = <value>` for each field of `Params`, in the field order. | unit | PASSES |
| T-CLI-01 | §2.7, D-043: help. | (a) A new Python process calls `cli.main(["--help"])`. (b) The installed command `tir-asr --help`. | (a) Exit code 0, a text that starts with `usage: tir-asr`, and none of the `laptop` packages and not `tir_asr.app` in `sys.modules`. (b) Exit code 0 and the same usage line. | unit | PASSES |
| T-IMPORT-01 | D-021: core modules have no `laptop` import. | Import each core module that exists in the branch, in a new Python process. | `torch`, `nemo`, `ctranslate2`, `silero_vad`, `soundcard`, and `transformers` are not in `sys.modules`. | unit | PASSES (C2b modules, `tir_asr.asr`, `tir_asr.mt`, `tir_asr.output`, `tir_asr.audio`, `tir_asr.errors`, `tir_asr.pipeline`, and `tir_asr.cli` |

**Model (Aren's laptop):**

| ID | Requirement | Input | Expected result | Level | Status |
|---|---|---|---|---|---|
| T-MODEL-VAD-01 | §2.2, D-026, D-027: Silero adapter and `Endpointer`. | Clip 1 and clip 2 (16 kHz), frame by frame. | Each probability is in [0, 1]. Clip 1 + clip 2 give 2 segments (T-INSTALL-04 shows the pauses). | model | PASSES |
| T-MODEL-ASR-01 | §2.3, D-022: NeMo adapter with the synthetic warm-up. | Warm-up (2 s of zeros), then clip 1, clip 2, clip 1, clip 2. | No text is empty. The first real call takes no more than 3 times the median of the next 3 calls. | model | PASSES |
| T-MODEL-MT-01 | §2.4, D-022, D-030: CTranslate2 adapter with the cuBLAS preload. | The command sets no `LD_LIBRARY_PATH`. Warm-up, then text 1, text 2, text 1, text 2. | CTranslate2 runs on `cuda`. No text is empty. The first real call takes no more than 3 times the median of the next 3 calls. | model | PASSES |
| T-MODEL-ERR-01 | §7, R10: missing ASR model file. | A wrong `.nemo` name. | `asr: model file not in the Hugging Face cache: …` | model | PASSES |
| T-MODEL-ERR-02 | §7, R10: missing MT model folder. | A missing CTranslate2 folder. | `mt: CTranslate2 model not found: …` with the conversion command. | model | PASSES |
| T-MODEL-ERR-03 | §2.3, §7, R10: no CUDA, no CPU fallback. | `torch.cuda.is_available` returns False (`monkeypatch`). | `AsrError`: `asr: CUDA is not available`. The model does not load. | model | PASSES (approved by Aren, 2026-10-25) |
| T-MODEL-ERR-04 | §2.4, §7, R10: empty MT input. | `translate("")` after the load. | `MtError`: `mt: empty input text`. | model | PASSES (approved by Aren, 2026-10-25) |
| T-AUDIO-01 | §2.1, D-020, D-041: microphone adapter (sim). | A null sink. `SoundcardMicrophone(device="<sink>.monitor")` gives 200 blocks. After block 29, `pw-play` plays a 4 s, 440 Hz tone (peak 0.25) into the sink. | Each block: `samples` (512,) float32, `source` "Me". The arrival times increase. Span ÷ (n − 1) = 32 ms ± 0.5 ms. No gap > 64 ms. Blocks 0–29: max \|x\| < 1e-6. Tone: 440 ± 1 Hz, RMS 0.1768 ± 10 %, no run of 16 or more exact zeros. The playback stream is on the null sink. The default sink and source do not change. | sim | PASSES |
| T-AUDIO-02 | §2.1, §7, R10: no PulseAudio server. | A new Python process with `PULSE_SERVER` set to a socket that does not exist. It builds `SoundcardMicrophone()`. | `AudioError`: `audio: cannot connect to the PulseAudio server`. | sim | PASSES |
| T-AUDIO-03 | §2.1, R10, D-041: exact device id, no fuzzy match. | A null sink `<sink>`. `SoundcardMicrophone(device="<sink>")`: the id is only a part of the monitor name. | `AudioError`: `audio: no source with the exact id <sink>`. The test first shows that `soundcard.get_microphone("<sink>", include_loopback=True)` selects the monitor. | sim | PASSES |
| T-E2E-01 | K1, F2, F3, F5, D-025, D-032, D-043: full pipeline with the real models. | `app.load_models()` (the function of the program), `warm_up()`, then `run()` with the test WAV source (`tests/support/wav_source.py`): clip 1, then clip 2, at real-time speed. | Exit code 0 and no error output. 2 blocks in time order, label "Me", no `(no text)`, each total < 5.0 s. Fewer blocks give the message "a clip ends with less than 512 ms of silence (D-032)". | model | PASSES |
| T-E2E-02 | L-02, §2.6, D-044: Ctrl+C stops the program. | The installed command `tir-asr` in a new process (real models, default microphone), output in a pipe. After "Listening" (at most 120 s), wait 2 s, then send SIGINT. | The process ends within 10 s, with exit code 0. The last line of the program starts with `Stopped. Segments: `. | model | PASSES |

**Live (manual, §4):** L-01 to L-03.

Aren approved the tests of §2.4 and §4 on 2026-10-25 ("agree on the tests"). After that, Claude split T-CFG-01 (now T-CFG-01 and T-CFG-02) and T-MODEL-ERR-01 (now T-MODEL-ERR-01 and T-MODEL-ERR-02), so that each component branch has its own tests (D-035, R3). The content is the same. T-AUDIO-01 is new, because the microphone adapter had no test. Aren agreed to the split of T-MODEL-ERR-01 in C2c ("Agree on split", 2026-10-25).

**Changes in C2c (Aren, 2026-10-25):**

- T-MODEL-ERR-03 is new. It tests the error `asr: CUDA is not available` of §2.3 ("yes on both of the untested error points").
- The error `asr: unexpected output type <type>` (§2.3) has no test, because the test needs a fake NeMo model.
- T-MODEL-ASR-01 has one more check: `torch.cuda.memory_allocated() > 0` after the load (§2.3: on `cuda`). Aren: "its fine".
- T-MODEL-ERR-04 is new. It tests the error `mt: empty input text` of §2.4.
- The error `mt: <file> not found in the package nvidia-cublas-cu12` (§2.4) has no test, because the test needs a missing package ("dont add the missing package test").
- T-MODEL-MT-01 checks "CTranslate2 runs on `cuda`" with `nvidia-smi`: the GPU memory must grow by more than 1000 MiB at the load, because the float16 weights are 1175 MiB. The tests use no private attribute of an adapter ("refrain from using private attribut").
- The MT model tests run with `env -u LD_LIBRARY_PATH` (D-030).

**Changes in C2d (Aren, 2026-10-25, D-040):**

- T-OUT-04 is new. It tests the one write for each block of §2.5 (D-024). Aren: "approve the test".
- Each block ends with an empty line, so that the blocks have a blank line between them (D-040). T-OUT-01, T-OUT-03, and T-OUT-04 expect this line.
- T-OUT-01 has two test functions: the full block, and the block time. The seconds are cut, not rounded: 3671.9 s gives `[01:01:11]`.
- T-OUT-03: the write comes 0.03 s after the ASR end. Thus the total (0.97 s) is more than `vad` + `asr` (0.94 s), and the test shows that the total counts the time to the write.
- T-AUDIO-01: Aren selected the sim option ("no let's simulate", 2026-10-25). The limits come from the probe B numbers (D-041).
- T-AUDIO-02 and T-AUDIO-03 are new. They test the errors of §2.1 that a sim test can make. Aren: "I approve the tests" (2026-10-26).
- T-PIPE-01 to T-PIPE-04 now give the exact input values and the exact output (D-042). T-PIPE-02 has two new cases: an exception that is not a `TirError`, and an error in the capture thread. T-PIPE-05 is new (D-042 point 4).
- The Ctrl+C path (D-042 point 3) has no unit test. L-02 covers it.
- Aren approved the exact T-PIPE-01 to T-PIPE-05 texts: "accept the tests" (2026-10-26).
- T-CFG-02, T-CLI-01, and T-E2E-01 now give the exact input and output (D-043). T-CLI-01 has two cases: the function in a new process, and the installed command. Aren: "agree" (2026-10-26).
- T-E2E-02 is new. It is the automatic form of L-02, after L-02 failed in the first live run (D-044). Aren: "I approve the test" (2026-10-26).

**C2c results (branch `c2c-asr`, Aren's laptop, 2026-10-25):**

- **Red runs:** T-IMPORT-01 failed (no `tir_asr.asr`); T-MODEL-ASR-01, T-MODEL-ERR-01, and T-MODEL-ERR-03 failed with `ModuleNotFoundError` (files `test-results/c2c-asr-unit-red.txt`, `c2c-asr-model-red.txt`, `c2c-asr-model-red-err03.txt`).
- **Unit:** 48 passed. `ruff check --no-cache` and `ruff format --no-cache --check` pass. File: `test-results/c2c-asr-unit.txt`.
- **Model (file `test-results/c2c-asr-model.txt`):** 3 passed.
  - Load 1.47 s. Warm-up with 2 s of zeros: 0.412 s, empty text.
  - The four real calls: 0.025, 0.028, 0.021, 0.025 s for 5.56–6.61 s of audio. First call / median of the next 3 = 1.00. Thus the synthetic warm-up is enough for the ASR (D-022).
  - Peak torch VRAM: 897 MiB. The same clip gives the same text in both calls.
  - T-MODEL-ERR-01 message: `asr: model file not in the Hugging Face cache: nvidia/stt_hy_fastconformer_hybrid_large_pc/no-such-model.nemo`.
  - T-MODEL-ERR-03: the error comes before the model load (0.000 s).
- **For C2d:** the NeMo load prints about 185 lines of warnings and configuration to the terminal. The startup log design must handle this.

**C2c results (branch `c2c-mt`, Aren's laptop, 2026-10-25):**

- **Red runs:** T-IMPORT-01 failed (no `tir_asr.mt`); T-MODEL-MT-01, T-MODEL-ERR-02, and T-MODEL-ERR-04 failed with `ModuleNotFoundError` (files `test-results/c2c-mt-unit-red.txt`, `c2c-mt-model-red.txt`, `c2c-mt-model-red2.txt`).
- **Unit:** 49 passed. `ruff check --no-cache` and `ruff format --no-cache --check` pass. File: `test-results/c2c-mt-unit.txt`.
- **Model (file `test-results/c2c-mt-model.txt`, run with `env -u LD_LIBRARY_PATH`):** 3 passed.
  - `LD_LIBRARY_PATH` was empty. The cuBLAS preload works (D-030).
  - Load 1.31 s. The GPU memory grew by 1800 MiB (`nvidia-smi`).
  - Warm-up (`WARMUP_TEXT`): 0.126 s, "Hello, how are you?".
  - The four real calls: 0.076, 0.070, 0.066, 0.070 s. First call / median of the next 3 = 1.09.
  - The same text gives the same translation in both calls. Text 2 has "truck" where the reference has "trunk" (MT quality, C3).
  - T-MODEL-ERR-02 message: `mt: CTranslate2 model not found: <tmp>/no-such-model. Convert it with: HF_HUB_OFFLINE=1 uv run --no-sync ct2-transformers-converter …`.
- **Q-07 data point:** the first CTranslate2 call in this process took 0.126 s. In T-INSTALL-03, it took 5.104 s.

**C2d results (branch `c2d-output`, Aren's laptop, 2026-10-25):**

- **Red run:** 1 failed (T-IMPORT-01: no `tir_asr.output`), 1 collection error (`test_output.py`: `No module named 'tir_asr.output'`), 48 passed. File: `test-results/c2d-output-unit-red.txt`.
- **Green run:** 55 passed. `ruff check --no-cache` and `ruff format --no-cache --check` pass. File: `test-results/c2d-output-unit.txt`.
- [RUN] With the project layout and no `output.py`, `ruff` reports I001 on the import block of `test_output.py`. With `output.py`, the block passes. Thus a red run of a new module can show I001; the green run is the check.

**C2d results (branch `c2d-cli`, Aren's laptop, 2026-10-26):**

- **Red runs:** unit: 1 collection error (`test_config.py`: no `parameter_lines`), 3 failed (both T-CLI-01 cases, T-IMPORT-01), 63 passed; model: T-E2E-01 failed with `No module named 'tir_asr.app'`. Files: `test-results/c2d-cli-unit-red.txt`, `c2d-cli-e2e-red.txt`.
- **Green runs:** `uv lock --check` passed, so `uv.lock` did not change with `[project.scripts]`. Unit: 69 passed; `ruff` passes (`test-results/c2d-cli-unit.txt`, and `c2d-cli-unit2.txt` after D-044).
- **T-E2E-01** (`test-results/c2d-cli-e2e.txt`, again in `c2d-e2e-green.txt`): 2 blocks, totals 0.64 s and 0.62 s (then 0.63 s and 0.62 s). Steps: `vad` 0.51 s (the silence wait, D-027), `asr` 0.03–0.05 s, `mt` 0.08–0.09 s, `out` 0.00 s. The first line is not slower than the second, so the synthetic warm-up is enough (D-022). Startup: ASR 1.52 s (1100 MiB used), MT 1.10 s (+1664 MiB), VAD 0.02 s; warm-up ASR 0.29 s, MT 0.13 s. The load order ASR → MT → VAD works with no `LD_LIBRARY_PATH` (D-043, point 2a).
- **L-02 failed in the first live run** (`test-results/c2d-live.txt`): Ctrl+C did nothing, and Aren closed the terminal. Probe C (`scripts/probe_sigint.py`, `test-results/c2d-probe-sigint.txt`) found the cause (D-044). T-E2E-02 was red with the old code (`test-results/c2d-e2e02-red.txt`: no stop within 10 s).
- **After the fix (D-044):** T-E2E-02 passed: exit code 0, 1.17 s after SIGINT, with the shutdown line (`test-results/c2d-e2e-green.txt`). L-02 passed in the terminal (`test-results/c2d-live2.txt`).
- **The first live run** (Script 4, s4-01 to s4-09, `docs/eval/scripts.md`) gave 8 blocks. Totals 0.21–0.64 s (K1). Data for later chats:
  - s4-07, s4-08, and the start of s4-09 came in one segment, with a hard cut at `vad_max_speech_s` = 10 s (`vad 0.00s`): the pauses were shorter than 512 ms. The cut split the word «լսել» (the D-026 weak point, now [RUN]). Data for Q15 (PLAN §10.2) and C3.
  - MT gave no English for the last sentence of the last block (Q-13).
  - ASR errors: «Ալոս Սորա» for «Ալո, Սոնա», «երեք» for «Երեկ» (MT then gave "three football games"). C3 measures the WER.

**C2d results (branch `c2d-pipeline`, Aren's laptop, 2026-10-26):**

- **Red run:** 1 collection error (`test_pipeline.py`: `No module named 'tir_asr.errors'`), 1 failed (T-IMPORT-01: no `tir_asr.errors` and no `tir_asr.pipeline`), 55 passed. File: `test-results/c2d-pipeline-unit-red.txt`.
- **Green run:** unit: 65 passed (T-PIPE-02 has three test functions); `ruff check --no-cache` and `ruff format --no-cache --check` pass (`test-results/c2d-pipeline-unit.txt`).
- **Check of the adapters after the `TirError` base class:** sim: 3 passed (`test-results/c2d-pipeline-sim.txt`); model: T-MODEL-VAD-01, T-MODEL-ASR-01, T-MODEL-MT-01, and T-MODEL-ERR-01 to T-MODEL-ERR-04 pass, with `env -u LD_LIBRARY_PATH` (`test-results/c2d-pipeline-model.txt`). Thus the new import in the MT adapter does not change the cuBLAS preload.

**C2d results (branch `c2d-audio`, Aren's laptop, 2026-10-26):**

- **Red runs:** unit: 1 failed (T-IMPORT-01: no `tir_asr.audio`), 54 passed; sim: 3 failed with `No module named 'tir_asr.audio'`. The fixture loaded and unloaded the null sink with no teardown error. Files: `test-results/c2d-audio-unit-red.txt`, `c2d-audio-sim-red.txt`.
- **Green runs:** unit: 56 passed; `ruff check --no-cache` and `ruff format --no-cache --check` pass (`test-results/c2d-audio-unit.txt`). Sim: 3 passed in 6.75 s (`test-results/c2d-audio-sim.txt`).
  - T-AUDIO-01: span ÷ (n − 1) 32.054 ms; gaps 20.7–43.4 ms (median 42.1 ms); silent phase max \|x\| 0; tone in blocks 32 to 157, first tone block 0.076 s after the player start; 440.02 Hz, RMS 0.1768 (played 0.1768), no holes; the playback stream was on the null sink.
  - T-AUDIO-02: `audio: cannot connect to the PulseAudio server`.
  - T-AUDIO-03: `soundcard.get_microphone("tir_t_audio")` gave `tir_t_audio.monitor`, so the name match is a real risk. The adapter gave `audio: no source with the exact id tir_t_audio`.
- The sim tests do not cover the default-microphone line of the adapter (D-041 part 2); L-01 covers it.

**C2d audio probes (`scripts/probe_audio.py`, Aren's laptop, 2026-10-25):**

- **Probe A** (`test-results/c2d-probe-a.txt`): `pactl` 17.0, `pw-play` (PipeWire 1.6.2), server "PulseAudio (on PipeWire 1.6.2)", default format float32le 2ch 48000 Hz. `module-null-sink` loads in 0.008 s. Its monitor has the exact id `<sink>.monitor` (float32le, 2 channels, 48 kHz). The default sink and source do not change at the load or after the unload.
- **Probe B** (`test-results/c2d-probe-b.txt`), recorded in the same way as the adapter (16 kHz, 1 channel, 512 samples):

  | Measure | Null-sink monitor | Default microphone |
  |---|---|---|
  | Shape, type | (512, 1) float32 | (512, 1) float32 |
  | Stream latency (`recorder.latency`) | 21.4–21.5 ms | 43.5 ms at the end (0.2 ms at the open: no timing data yet) |
  | First block after the open | 45 ms | 125 ms (the device was suspended) |
  | Gaps | 20.1–43.3 ms, mean 32.05 ms | 20.4–43.6 ms, mean 32.12 ms |
  | Span ÷ real time | 1.0017 (199 gaps) | 1.0037 (99 gaps) |
  | Content | silent phase: exact zeros; tone 440.02 Hz, RMS 0.1768 (played 0.1768), no holes | 22 samples outside [−1, 1], min −1.0496 (Q-11) |

  - The gaps alternate between about 21 ms and 43 ms. This agrees with a PipeWire cycle of 1024 frames at 48 kHz (21.33 ms, calc); the cycle size is [UNVERIFIED]. One block is 1.5 cycles.
  - The tone came 75 ms after the `pw-play` start (an upper limit: it includes the start of `pw-play`).
  - A monitor with no audio gives blocks of zeros. Thus the `Endpointer` can close a segment during a silence on the system side (C4).

**Component branches (D-035, R3):** each branch has its own tests (`PLAN.md` §5.2 C2b, C2c, C2d). T-PIPE-02 and T-PIPE-04 check exit codes: if the exit code belongs to `cli.py`, C2d moves that part of the test to the `c2d-cli` branch, with Aren's approval.

**C2b results (branch `c2b-segment`, Aren's laptop, 2026-10-25):**

- **Unit:** 47 passed (26 from before and 21 new). `ruff` passes. File: `test-results/c2b-unit.txt`.
- **Test functions for one ID:**
  - T-SEG-04 has two (inside speech, inside a silence). The first one ends the speech with frames at 0.4, so that it fails if 0.4 starts a silence.
  - T-SEG-08 has four: the ramp of T-SEG-01, a start at frame 0, a pad of 100 ms (longer than one frame) at the start of the stream, and a segment that starts right after a close. The last two protect the buffer of the start pad.
  - T-SEG-09 has two (frame length, probability). The frame-length test also shows that the VAD is not called.
- **T-IMPORT-01:** the test imports each module of the package except the four adapters, each in a new process. A second test checks a `REQUIRED` set of core modules, because the first test passes with no code. Each component branch adds its modules to `REQUIRED`.
- **T-MODEL-VAD-01 (file `test-results/c2b-model-vad.txt`):** clip 1 has 173 frames (5.536 s) and clip 2 has 206 frames (6.592 s). The result is 2 segments, 0 short segments, and probabilities from 0.005 to 1.000. The model and the `Endpointer` need 0.19 ms for each frame on the CPU, with 1 PyTorch thread.

  | Segment | `start` | `speech_end` | `closed` | Audio |
  |---|---|---|---|---|
  | 1 | 0.224 s | 5.408 s | 5.920 s | 5.244 s |
  | 2 | 6.016 s | 11.232 s | 11.744 s | 5.276 s |

  - Segment 1 closes in the silence at the start of clip 2. The silence between the two segments is 608 ms (19 frames), which is 3 frames more than the 16 frames of the rule. The pause of 448 ms inside clip 1 did not split it.
  - The VAD silence after the speech of clip 2 is 896 ms, so segment 2 closes inside the clip.

### 2.5 Eval tools (C3)

Decisions: D-046 (labels and their use), D-047 (Armenian normalization: option P1 for «՞», option N1 for numbers). Aren approved T-NORM-01 to T-NORM-09 on 2026-10-26.
Module: `src/tir_asr/eval/normalize.py`, function `normalize_hy(text) -> str`. Test file: `tests/unit/test_normalize.py`. The program does not import `tir_asr.eval`.

| ID | Requirement | Input | Expected result | Level | Status |
|---|---|---|---|---|---|
| T-NORM-01 | D-047 rule 1: NFKC. | «ﬓա» (U+FB13 + «ա»), and U+FB14 to U+FB17 | «մնա», «մե», «մի», «վն», «մխ» | unit | PASSES (Aren's laptop, 2026-10-26) |
| T-NORM-02 | D-047 rule 2: lowercase. | «Բարև ԵՐԵՎԱՆ OK» | «բարեվ երեվան ok» | unit | PASSES (Aren's laptop, 2026-10-26) |
| T-NORM-03 | D-047 rule 4: one form for «և». | «և», «եւ», «Եվ», «ԵՎ», «ԵՒ»; «Երևան», «Երեւան», «Երեվան»; «ուր», «Լսում» | «եվ» five times; «երեվան» three times; «ուր», «լսում» (no change to «ու») | unit | PASSES (Aren's laptop, 2026-10-26) |
| T-NORM-04 | D-047 rule 3 (P1): the marks inside a word go, except «՞». | «Լսո՞ւմ», «ԼՍՈ՞ՒՄ»; «Վա՜յ»; «ե՛ս»; one test word with U+055F and one with U+055A; «լսում ՞» | «լսո՞ւմ» two times; «վայ»; «ես»; the mark goes, with no space; «լսում ՞» («՞» alone stays as its own word) | unit | PASSES (Aren's laptop, 2026-10-26) |
| T-NORM-05 | D-047 rule 5: each other mark becomes a space. | «Բարև, տղերք։ Լսո՞ւմ եք ինձ։»; «այսօր՝ մինչև»; «երկու-մեկ», «երկու֊մեկ»; «Նռնենի» in the quotes « and »; each of the marks `.` `,` `:` `;` `?` `!` `"` «…» «—» «։» «՝» « » between two letters | «բարեվ տղերք լսո՞ւմ եք ինձ»; «այսօր մինչեվ»; «երկու մեկ» two times; «նռնենի»; one space for each mark | unit | PASSES (Aren's laptop, 2026-10-26) |
| T-NORM-06 | D-047 rule 6: one space between words. | tabs, new lines, several spaces, and spaces at the ends; «։ ,»; an empty text | «ա բ գ»; an empty text; an empty text | unit | PASSES (Aren's laptop, 2026-10-26) |
| T-NORM-07 | D-047 N1: digits do not change. | «ժամը 8-ին» | «ժամը 8 ին» | unit | PASSES (Aren's laptop, 2026-10-26) |
| T-NORM-08 | D-047 rules 3 and 5: a word stays one word. | each Armenian line of S1–S4 in `docs/eval/scripts.md` (44 lines) | The same number of words as the words with a letter in the input. Only lowercase Armenian letters (U+0561–U+0586), «՞», and single spaces. | unit | PASSES (Aren's laptop, 2026-10-26) |
| T-NORM-09 | D-047: a stable result. | each line of T-NORM-08 | A second run changes nothing. | unit | PASSES (Aren's laptop, 2026-10-26) |

Notes:

- **Results (Aren's laptop, 2026-10-26):** red run 47 failed, each with `NotImplementedError`, and 15 passed (T-IMPORT-01) (`test-results/c3-norm-red.txt`). Green run: `ruff check` and `ruff format --check` pass; 118 unit tests pass (`test-results/c3-norm-green.txt`).
- **Red state:** a stub `normalize_hy` raises `NotImplementedError`, so that each test runs and fails alone. T-IMPORT-01 adds `tir_asr.eval` and `tir_asr.eval.normalize` to `REQUIRED`.
- **T-NORM-08** reads `docs/eval/scripts.md`. A change of the script table can change the result of this test.
- **Known limit (P1):** an ASCII «?» in place of «՞» becomes a space. Then the word does not match the reference word, and WER counts an error.

**`metrics.py`** (branch `c3-metrics`, D-047, D-049). Aren approved T-MET-01 to T-MET-08 on 2026-10-26. Test file: `tests/unit/test_metrics.py`. WER and CER use `normalize_hy`. chrF uses `sacrebleu` with its default values (character order 6, word order 0, beta 2) and no normalization. Each score is for the full list: the total edits divided by the total reference length.

| ID | Requirement | Input | Expected result | Level | Status |
|---|---|---|---|---|---|
| T-MET-01 | Edit distance: substitution, deletion, and insertion cost 1 each. | words `a b c`/`a b c`; `a b c`/`a x c`; `a b c`/`a c`; `a b`/`a b c`; empty/`a b`; `a b`/empty; empty/empty; characters `kitten`/`sitting` | 0; 1; 1; 1; 2; 2; 0; 3 | unit | PASSES (Aren's laptop, 2026-10-26) |
| T-MET-02 | WER uses the D-047 normalization. | ref «Բարև, տղերք։», hyp «բարև տղերք» | 0.0 | unit | PASSES (Aren's laptop, 2026-10-26) |
| T-MET-03 | WER is for the full list. | refs «ա բ», «գ դ ե զ»; hyps «ա», «գ դ ե զ» | 1/6 (not 0.25, the mean of the lines) | unit | PASSES (Aren's laptop, 2026-10-26) |
| T-MET-04 | WER keeps «՞» (D-047 P1). | ref «Լսո՞ւմ եք», hyp «լսում եք» | 0.5 | unit | PASSES (Aren's laptop, 2026-10-26) |
| T-MET-05 | CER counts the spaces. | ref «աբ գդ», hyp «աբ գե» | 1/5 | unit | PASSES (Aren's laptop, 2026-10-26) |
| T-MET-06 | chrF on the English text. | the same text; «abc» and «xyz»; «Hello there» and «hello there» | 100.0; 0.0; less than 100 (no lowercase) | unit | PASSES (Aren's laptop, 2026-10-26) |
| T-MET-07 | Digit words (D-047 N1). | «ժամը 8-ին», «15 000 դրամ» | 3 | unit | PASSES (Aren's laptop, 2026-10-26) |
| T-MET-08 | Errors (R10). | `wer`, `cer`, `chrf` with 2 refs and 1 hyp; `wer`, `cer` with the ref «։ ,» | `MetricError` `metrics: 2 references and 1 hypotheses`; `MetricError` `metrics: the references have no words` | unit | PASSES (Aren's laptop, 2026-10-26) |

T-IMPORT-01 adds `tir_asr.eval.metrics` to `REQUIRED`. Red state: a stub raises `NotImplementedError` in each function.

**Results (Aren's laptop, 2026-10-26):** red run 21 failed, each with `NotImplementedError`, and 16 passed (`test-results/c3-met-red.txt`). Green run: `ruff check` and `ruff format --check` pass; 140 unit tests pass; `sacrebleu` 2.6.0 (`test-results/c3-met-green.txt`).

**`data.py`** (branch `c3-data`, D-046, D-048, D-049). Aren approved T-DATA-01 to T-DATA-11 on 2026-10-26. Test file: `tests/unit/test_data.py`. D-050: Claude wrote the tests and the code in one step, with no red run.

| ID | Requirement | Input | Expected result | Level | Status |
|---|---|---|---|---|---|
| T-DATA-01 | Resample 48 → 16 kHz. | 1.0 s, 440 Hz, amplitude 0.5, float32, 48 kHz | 16000 samples, float32; spectrum peak at 440 ± 1 Hz; RMS 0.3536 ± 2 % (without the first and last 2000 samples) | unit | PASSES (Aren's laptop, 2026-10-26) |
| T-DATA-02 | No aliasing. | 1.0 s, 11 kHz tone, 48 kHz | output RMS at least 40 dB below the input RMS | unit | PASSES (Aren's laptop, 2026-10-26) |
| T-DATA-03 | 16 kHz is not changed. | float32, 16 kHz | the same samples | unit | PASSES (Aren's laptop, 2026-10-26) |
| T-DATA-04 | Errors (R10). | stereo; 44100 Hz; int16 | `data: <file>: 2 channels, expected 1`; `data: <file>: sample rate 44100 Hz, expected 48000 or 16000`; `data: <file>: sample format int16, expected float32` | unit | PASSES (Aren's laptop, 2026-10-26) |
| T-DATA-05 | End rule (D-048). | 100 samples | 16100 samples; the first 100 do not change; the last 16000 are 0.0 | unit | PASSES (Aren's laptop, 2026-10-26) |
| T-DATA-06 | References. | a small table with 2 scripts, one "†" ID, "Me", "Speaker 1", "Speaker 2" | only the lines of `s1`, in order; ID with no "†"; side "mic" or "call"; Armenian and English text | unit | PASSES (Aren's laptop, 2026-10-26) |
| T-DATA-07 | References in the real file. | `docs/eval/scripts.md`: s1, s2, s3 | 14, 10, 10 lines; 5 "mic" lines in each | unit | PASSES (Aren's laptop, 2026-10-26) |
| T-DATA-08 | References error. | script `s9` | `data: no lines for s9 in <file>` | unit | PASSES (Aren's laptop, 2026-10-26) |
| T-DATA-09 | Labels. | 3 Audacity lines | 3 labels with the start, the end, and the ID | unit | PASSES (Aren's laptop, 2026-10-26) |
| T-DATA-10 | Label errors (R10). | 2 fields; a time that is not a number; end before start; an unknown ID; a missing ID; a repeated ID | one `DataError` for each, with the line number or the ID | unit | PASSES (Aren's laptop, 2026-10-26) |
| T-DATA-11 | Line view (D-046). | labels a 0–5 s, b 6–10 s; segments 0.2–4.8, 4.9–6.5, 11–12, 4.5–6.5 | a; b; none; a (equal overlaps: the label that starts first) | unit | PASSES (Aren's laptop, 2026-10-26) |

T-IMPORT-01 adds `tir_asr.eval.data` to `REQUIRED`.

**Results (Aren's laptop, 2026-10-26):** no red run (D-050). Green run: `ruff check` and `ruff format --check` pass; 161 unit tests pass (`test-results/c3-data-green.txt`).

**`run.py`** (branch `c3-run`, D-046, D-048, D-051). Aren approved T-RUN-01 to T-RUN-05 on 2026-10-26. Test file: `tests/unit/test_run.py`. D-050: tests and code in one step, with no red run.

| ID | Requirement | Input | Expected result | Level | Status |
|---|---|---|---|---|---|
| T-RUN-01 | Segments in audio time, with the end rule (D-048). | 3.0 s of audio; a fake VAD gives 1.0 for a frame with a peak over 0.1; loud frames 10–39, and loud from frame 80 to the end of the audio | 2 segments; the first has start 0.320 s and speech end 1.280 s; the second (start 2.560 s) closes because of the 1.0 s of zeros | unit | PASSES (Aren's laptop, 2026-10-26) |
| T-RUN-02 | ASR and MT calls (D-031). | 3 fake segments; ASR «ա», «», «բ»; MT "A"; a fake clock that each model call moves by 0.1 s | ASR texts in order; English "A", "", "A"; 2 MT calls only; times 0.1, 0.0, 0.1 s | unit | PASSES (Aren's laptop, 2026-10-26) |
| T-RUN-03 | Main numbers on the joined text (D-046 point 2). | refs «ա բ» (0–2 s) and «գ դ» (3–5 s); segment texts «ա բ գ» (0–3.5 s) and «դ» (4–5 s) | WER 0.0; line view: line 1 WER 0.5, line 2 WER 0.5 | unit | PASSES (Aren's laptop, 2026-10-26) |
| T-RUN-04 | Segment outside each label. | the labels of T-RUN-03; a third segment 6–7 s with «ե» | 1 segment outside; the main WER is 1/4 | unit | PASSES (Aren's laptop, 2026-10-26) |
| T-RUN-05 | Time numbers. | segment audio 2.0 s and 3.0 s; ASR 0.1 s and 0.3 s; MT 0.2 s and 0.4 s | audio 5.0 s; ASR RTF 0.08; ASR mean 0.2 s, maximum 0.3 s; MT mean 0.3 s, maximum 0.4 s | unit | PASSES (Aren's laptop, 2026-10-26) |

T-IMPORT-01 adds `tir_asr.eval.run` to `REQUIRED`.

**Results (Aren's laptop, 2026-10-26):** no red run (D-050). Green run: `ruff check` and `ruff format --check` pass; 167 unit tests pass (`test-results/c3-run-green.txt`). The first bake-off runs (`nemo-rnnt` + `nllb-ct2`, and `nllb-ct2` on the reference text) ran with no error (`test-results/c3-bake-rnnt-nllb.txt`, `test-results/c3-bake-ref-nllb.txt`). The results table comes at the end of C3.

**Bake-off runs (model level, D-049, D-051, D-052).** No separate model test for the candidate adapters: each bake-off run is their model-level check, and it stops at an error (R10). All runs passed on Aren's laptop on 2026-10-26: `nemo-rnnt`, `nemo-ctc`, `buzz-whisper`, and `seamless` (ASR); `nllb-ct2`, `opus-ct2`, and `seamless` (MT, also with the reference text); `seamless-s2tt` (end to end). ONNX-CTC was not run (D-052). Unit tests after the candidates: 167 pass (`test-results/c3-cand2-green.txt`). The numbers are in `docs/eval/results.md`. The CPU probe (`scripts/probe_cpu.py`) is in the same file.

### 2.6 Two audio sources (C4)

Contracts: `ARCHITECTURE.md` §2.1, §2.6, §2.7. Decisions: D-054, D-055. Aren approved the tests on 2026-10-26 ("I approve"). D-055: no separate red run; Claude writes the tests and the code in one step, and Aren does only the green run. C4 changes some tests of §2.4; this table gives their C4 form.

**Branch `c4-audio`:**

| ID | Requirement | Input | Expected result | Level | Status |
|---|---|---|---|---|---|
| T-DEV-01 | F1, §2.1, D-054: the text of `--list-devices`. | (a) `format_source_list(sources, "mic-a", "out-b.monitor")` with the records `mic-a` "Laptop microphone", `out-a.monitor` "Monitor of HDMI", `mic-b` "USB microphone", `out-b.monitor` "Monitor of Headphones" (monitors: the two `.monitor` ids). (b) The same, with no monitor. | (a) The exact text of §2.1: the heading `Microphones (--mic):`, `* mic-a  Laptop microphone`, `  mic-b  USB microphone`, the heading `System audio (--system):`, `  out-a.monitor  Monitor of HDMI`, `* out-b.monitor  Monitor of Headphones`, then `* = the default, used when the flag is not given`. (b) The line `  (none)` under the system heading. | unit | PASSES |
| T-AUDIO-01 | §2.1, D-041, D-054 (changed in C4). | As in §2.4, with `SoundcardSource("System", "<sink>.monitor")`. | As in §2.4, but each block has the source `"System"`. | sim | PASSES |
| T-AUDIO-02 | §2.1, §7 (changed in C4). | No server. One process calls `SoundcardSource("Me", "x")`, then `list_sources()`. | Each call gives `AudioError`: `audio: cannot connect to the PulseAudio server`. | sim | PASSES |
| T-AUDIO-03 | §2.1, D-041 (changed in C4). | `SoundcardSource("Me", "<sink>")`. | As in §2.4. | sim | PASSES |
| T-AUDIO-04 | F1, §2.1, D-054: the device list and the default ids. | A null sink. `list_sources()`, `default_microphone_id()`, `default_system_id()`. | No id occurs two times. `<sink>.monitor` is in the list with `monitor = True`. `default_microphone_id()` = `pactl get-default-source`. `default_system_id()` = `pactl get-default-sink` + `.monitor`, and the list has it with `monitor = True`. | sim | PASSES |
| T-IMPORT-01 | D-021. | `tir_asr.audio.devices` in `REQUIRED`; `tir_asr.audio.soundcard_source` in `ADAPTERS` (in place of `tir_asr.audio.soundcard_mic`). | It passes. | unit | PASSES |

No test: `audio: no default microphone`, `audio: no default output`, `audio: no monitor source for the default output <id>`. A test must change the system defaults.

**Results (branch `c4-audio`, Aren's laptop, 2026-10-26):** no red run (D-055).

- **Unit:** `ruff check --no-cache` and `ruff format --no-cache --check` pass; 170 passed (`test-results/c4-audio-unit.txt`).
- **Sim:** 4 passed in 6.82 s (`test-results/c4-audio-sim.txt`).
  - T-AUDIO-01: gaps 20.8–43.3 ms (median 42.1 ms); span ÷ (n − 1) 32.054 ms; tone 440.02 Hz, RMS 0.1768, no holes; each block has the source `"System"`.
  - T-AUDIO-02: the constructor and `list_sources()` each give `audio: cannot connect to the PulseAudio server`.
  - T-AUDIO-04: the server has 3 sources: the laptop microphone `alsa_input.pci-0000_80_1f.3.analog-stereo`, the output monitor `alsa_output.pci-0000_80_1f.3.analog-stereo.monitor`, and the test monitor. [RUN] The rule `<output id>.monitor` is true for the real output of the laptop, not only for a null sink (D-054). `default_microphone_id()` and `default_system_id()` agree with `pactl`.
- `scripts/probe_sigint.py` (C2d probe) uses `SoundcardSource("Me", default_microphone_id())` in place of `SoundcardMicrophone()` (Aren approved the change).

**Branch `c4-pipeline`** (frame k arrives at (k + 1) × 0.032 s, as in §2.4):

| ID | Requirement | Input | Expected result | Level | Status |
|---|---|---|---|---|---|
| T-PIPE-01 to T-PIPE-05 | §2.6, D-054 (changed in C4). | `run([(source, vad)], …)`; the fake source has `label = "Me"`. | The same exact output as in §2.4. | unit | PASSES |
| T-PIPE-06 | F1, F5, §2.6, D-054: two sources. | Me: 50 frames, speech in frames 5–24. System: 100 frames, a short region in frames 30–36, speech in frames 60–79; it gives its first block only after Me ends. Clock: 0.0; 1.400, 1.500, 1.510; 3.200, 3.300, 3.310. | Exit code 0. "Listening"; `[00:00:00] Me` with `vad 0.51s, asr 0.09s, mt 0.10s, out 0.01s \| Total 0.71s`; `[00:00:01] System` with `vad 0.51s, asr 0.13s, mt 0.10s, out 0.01s \| Total 0.75s`; `Stopped. Segments: 2, short segments: 1, empty texts: 0, not processed: 0.` | unit | PASSES |
| T-PIPE-07 | §2.6, D-054: "done" after the end of each source. | Me: 20 silent frames. System: waits for a release event, then 50 frames with speech in frames 5–24. `run()` runs in a thread. Clock: 0.0; 1.400, 1.500, 1.510. | 0.3 s after the end of Me, `run()` has not returned. After the release: exit code 0, one block `[00:00:00] System` (Total 0.71s), and `Segments: 1`. | unit | PASSES |
| T-PIPE-08 | §2.6, D-042, D-054: the thread name in the error line. | Me: 10 silent frames. The `blocks()` of System raises `KeyError("x")`. | Exit code 1. The error output is a traceback, then `tir-asr: capture System: KeyError: 'x'`. The output is only "Listening". | unit | PASSES |

**Results (branch `c4-pipeline`, Aren's laptop, 2026-10-26):** no red run (D-055).

- **Unit:** `ruff check --no-cache` and `ruff format --no-cache --check` pass; 173 passed (`test-results/c4-pipeline-unit.txt`). `test_pipeline.py` has 10 test functions: T-PIPE-02 has three, and T-PIPE-06 to T-PIPE-08 have one each.
- **Model** (`test-results/c4-pipeline-e2e.txt`, with `env -u LD_LIBRARY_PATH`): T-E2E-01 and T-E2E-02 pass with the new `run()` call, in 32.02 s. T-E2E-01: 2 blocks, label "Me" (one test source), totals 0.64 s and 0.62 s. T-E2E-02: exit code 0, 1.17 s after SIGINT, with the shutdown line. The C4 form of T-E2E-01 and T-E2E-02 (the labels in `load_models`, the `startup: source` lines) comes in `c4-cli`.

**Branch `c4-cli`:**

| ID | Requirement | Input | Expected result | Level | Status |
|---|---|---|---|---|---|
| T-CLI-01 | §2.7, D-043. | As in §2.4. | As in §2.4. | unit | PASSES |
| T-CLI-02 | F1, §2.7, D-054: the flags. | (a) `--mic a --system b`; (b) no flags; (c) `--list-devices`; (d) `--mic x --system x`. A fake replaces `app.main` and `app.list_devices`. | (a) `app.main` gets `mic="a"`, `system="b"`, and `cli` returns its value. (b) `mic=None`, `system=None`. (c) one call of `app.list_devices`, no call of `app.main`, and `cli` returns its value. (d) Exit code 2; the error output ends with `tir-asr: error: --mic and --system select the same source x`. | unit | PASSES |
| T-E2E-01 | K1, F2, F3, F5 (changed in C4). | `load_models(params, log, ["Me"])`, then `run([(WavSource(CLIPS), vads[0])], …)`. | As in §2.4. | model | PASSES |
| T-E2E-02 | L-02, D-044, D-054 (changed in C4). | As in §2.4 (no flags: the default microphone and the default output monitor). | As in §2.4, and two `startup: source` lines before "Listening". | model | PASSES |
| T-SIM-01 | F1, F4 (source labels), F5, K1, D-020, D-054, Q-10: two sources at the same time. | Two null sinks `tir_t_me` and `tir_t_system`. `load_models(…, ["Me", "System"])`, `warm_up()`, then `run()` with `SoundcardSource("Me", "tir_t_me.monitor")` and `SoundcardSource("System", "tir_t_system.monitor")`. A test wrapper on each source records the arrival times and stops the source after the length of S1 + 2.0 s. At the first block of each source, `pw-play --target` plays 16-bit copies of `data/eval/raw/s1.mic.wav` into `tir_t_me` and `s1.call.wav` into `tir_t_system`. | (1) Exit code 0, no error output. (2) Each block has the label `Me` or `System`; each label has one or more blocks; for each label, the block times do not go back. (3) The `Me` text has a lower WER against the S1 mic references than against the call references; the `System` text has the opposite result. (4) Each total < 5.0 s (K1). (5) No arrival gap over 64 ms on each source. (6) The two playback streams are on the two test sinks (else the test stops the players); the default sink and source do not change. Report: the WER of each side, the mean gap, and the span ÷ real time of each source (D-020). | sim, model | PASSES |
| L-04 | F1 (§4). | `./run.sh --list-devices` on the laptop. | The list shows the microphone and the output monitor; the defaults have a `*`; exit code 0; no model load. | live | APPROVED (not run in C4) |
| L-05 | F1, F5, K1 (§4). | A video call with one person, wired headphones, `./run.sh` with no flags. | Lines with `Me` and `System` at the same time; Aren still hears the call; each total < 5 s; the two `startup: source` lines name the correct devices. | live | PASSES |

**Results (branch `c4-cli`, Aren's laptop, 2026-10-26):** no red run (D-055).

- **Unit:** `ruff check --no-cache` and `ruff format --no-cache --check` pass; 177 passed (`test-results/c4-cli-unit.txt`).
- **Model** (`test-results/c4-cli-e2e.txt`): 2 passed in 31.10 s. T-E2E-01: totals 0.64 s and 0.62 s. T-E2E-02: `startup: source Me: … (alsa_input.pci-0000_80_1f.3.analog-stereo)` and `startup: source System: … (alsa_output.pci-0000_80_1f.3.analog-stereo.monitor)` before "Listening"; exit code 0, 1.12 s after SIGINT.
- **Sim** (`test-results/c4-cli-sim.txt`): 5 passed in 88.87 s (T-AUDIO-01 to T-AUDIO-04, T-SIM-01).
  - T-SIM-01: S1 has 70.656 s on each side; each source stopped after 2271 blocks. 14 blocks (5 `Me`, 9 `System`), 1 short segment, no error. Both playback streams were on the test sinks.
  - Label check (WER): `Me` 0.085 against the mic references, 0.938 against the call references; `System` 0.205 against the call references, 1.627 against the mic references.
  - Totals: maximum 0.66 s, mean 0.62 s (K1).
  - Arrival gaps: `Me` 20.8–43.2 ms, `System` 16.3–47.8 ms (limit 64 ms, Q-10). Span ÷ real time 1.0000 for each source: no drift between the two sources in 72.7 s (D-020).
  - One warning: `scipy` `WavFileWarning: Chunk (non-data) not understood` for an S1 file. `scipy` skips that chunk; the audio is read.
- **L-04:** not run in C4 (no result file).
- **L-05** (`test-results/c4-l05.txt`, about 6 min, video call with one person): PASSES. The `System` source was the monitor of Bluetooth buds (`bluez_output.E0:08:71:6B:2A:A2.monitor`, "Redmi Buds 3 Lite"), the `Me` source the laptop microphone. 84 blocks (38 `Me`, 46 `System`); totals 0.11–0.68 s, mean 0.57 s; mean of the first 10 blocks 0.589 s, of the last 10 blocks 0.583 s; 2 hard cuts at `vad_max_speech_s`; 10 short segments; no empty text; no error. Aren's words: "The system and mic listening works superb. every interruption caught"; "latency is very small and does not increase over time"; "voice activation detects small coughs or sounds between intervals as speech" (Q-14); "10s limit for speech sometimes is not enough for long sentences" (Q15); "Overall P1 isnt bad, but it fails frequently, especially on translation".

### 2.7 Speaker labels (C5)

Contracts: `ARCHITECTURE.md` §2.8, §3, §8.2. Decisions: D-057. Aren approved the tests on 2026-10-27 ("agree on the tests"). D-057 part 8: no separate red run; Claude writes the tests and the code in one step, and Aren does only the green run. T-SPK-07 is new: it comes from Aren's decision to measure both rules (D-057 part 4). Aren approved it on 2026-10-27 ("agree").

Eval streams (D-057 part 1): S1 call, S2 call, S3 call, and stream D (S1 call 0–34.0 s, S2 call, S1 call 34.0 s to the end, S3 call; 4 voices, 192.5 s). Metric (part 2): label accuracy after the best mapping, weighted by the speech time; the count of segments too.

**Branch `c5-cluster`** (2-D test vectors at an angle a: the cosine of two vectors is cos(a1 − a2); "long" = 3.0 s):

| ID | Requirement | Input | Expected result | Level | Status |
|---|---|---|---|---|---|
| T-SPK-01 | F4, §2.8 steps 2 and 4. Both rules. | Threshold 0.5. Vectors (1, 0, 0), (0.9, 0.1, 0), (0, 1, 0), (0.05, 1, 0), (0, 0, 1), all long. | `Speaker 1`, `Speaker 1`, `Speaker 2`, `Speaker 2`, `Speaker 3`; `count` = 3. | unit | PASSES |
| T-SPK-02 | §2.8, rule A: the centroid moves. | Threshold 0.7. `CentroidClusterer`: 0°, 40°, 60°. Control: a new clusterer with 0°, 60°. | `Speaker 1` three times (the centroid of 0° and 40° is at 20°; cos 40° = 0.77). Control: `Speaker 1`, `Speaker 2` (cos 60° = 0.5). | unit | PASSES |
| T-SPK-03 | §2.8 step 3, D-057 part 5B. Both rules. | Threshold 0.9, `min_new_s` 1.0. 0° (0.5 s), 90° (long), 40° (0.5 s), 35° (long), 180° (1.0 s). | `Speaker 1` (a short first segment starts a speaker); `Speaker 2`; `Speaker 1` (short: the most similar, no new speaker, `count` = 2); `Speaker 3` (Speaker 1 did not change: cos 35° = 0.82 < 0.9); `Speaker 4` (1.0 s counts as long); `count` = 4. | unit | PASSES |
| T-SPK-04 | §2.8 errors. Both rules. | (a) Threshold 1.5; `min_new_s` −0.1. (b) An embedding of shape (1, 3); one with NaN; one with inf; zeros. (c) (1, 0, 0), then (1, 0). | (a) `speakers: threshold 1.5 is not in [-1, 1]`; `speakers: min_new_s -0.1 is negative`. (b) `speakers: embedding has shape (1, 3), expected one dimension`; `speakers: embedding has values that are not finite` (two times); `speakers: embedding has zero length`; `count` stays 0. (c) `speakers: embedding has 2 values, expected 3`. | unit | PASSES |
| T-SPK-05 | D-057 part 2, §8.2: `label_accuracy`. | (a) Truths A A B B, labels S2 S2 S1 S1, weights 1. (b) A A A B; S1 S1 S2 S3; 1. (c) A B; S1 S1; 3.0, 1.0. (d) A B C; S1 S1 S1; 1, 2, 1. (e) 3 truths and 2 labels; no segments; weight 0.0; weight NaN. | (a) 1.0. (b) 0.75 (the extra label is an error). (c) 0.75. (d) 0.5. (e) `metrics: 3 true speakers, 2 labels, and 3 weights`; `metrics: no segments`; `metrics: weight 0.0 is not positive`; `metrics: weight nan is not positive`. | unit | PASSES |
| T-SPK-07 | D-057 part 4: the two rules differ. **New.** | Threshold 0.7. 0°, 40°, 80°, all long, for each rule. | Rule A: `Speaker 1`, `Speaker 1`, `Speaker 2` (centroid at 20°; cos 60° = 0.5). Rule B-max: `Speaker 1` three times (nearest stored vector 40°; cos 40° = 0.77). | unit | PASSES |
| T-IMPORT-01 | D-021. | `tir_asr.speakers`, `tir_asr.speakers.cluster`, and `tir_asr.eval.nearest` in `REQUIRED`. | It passes. | unit | PASSES |

**Results (branch `c5-cluster`, Aren's laptop, 2026-10-27):** no red run (D-057 part 8). `ruff check --no-cache` and `ruff format --no-cache --check` pass; 206 passed, 17 deselected (`test-results/c5-cluster-unit.txt`). `test_speakers.py` has 26 test functions (T-SPK-01, T-SPK-03, and T-SPK-04 run for both rules); T-IMPORT-01 checks 3 more core modules.

**Branch `c5-embed`** (D-057 part 3, points 1 to 3). T-SPK-08 to T-SPK-10 are new: they test the sweep core. Aren approved them on 2026-10-27 ("agree").

| ID | Requirement | Input | Expected result | Level | Status |
|---|---|---|---|---|---|
| T-SPK-06 | D-057 part 1, §8.2: the stream builder. | Audio whose sample k has the value k. (a) `call_stream` with a "Me" line and two call lines. (b) A 10 s stream with turns 1–3 s and 5–7 s: `cut` at 0–4 s and 4 s to the end, then `join` in the order second, first. (c) A cut at 2.0 s. (d) `stream_d`: S1 40 s (turns 10–12 s, 36–38 s), S2 and S3 5 s (turn 1–2 s). (e) `truth_of` with turns 1–3 s and 3.5–6 s. | (a) Only the two call turns, `s1/Speaker 1` and `s1/Speaker 2`, in time order. (b) 4 s with the turn 1–3 s; 6 s that starts at sample 64000 with the turn 1–3 s; the join has 10 s and the turns 1–3 s and 7–9 s. (c) `data: s1: the cut at 2.00 s is inside a turn (1.00–3.00 s)`. (d) 50 s; turns 10–12, 35–36, 41–43, 46–47 s; the sample at 39 s is the S1 sample at 34 s. (e) 2.5–4.0 s: the earlier turn (equal overlaps); 3.2–5.0 s: the second turn; 7–8 s: None. | unit | WRITTEN |
| T-SPK-08 | D-057 parts 2 and 4, §8.2: `sweep`. **New.** Both rules. | Vectors at 0° (4 s, A), 30° (2 s, A), 100° (3 s, B), 130° (1 s, B), 200° (3 s, no turn). Thresholds 0.5 and 0.95, `min_new_s` 1.0. | 0.5: accuracy 1.0 (time and count), 0 wrong, 4 scored, 3 speakers (the segment with no turn starts a speaker). 0.95: accuracy 0.7 (time) and 0.5 (count), 2 wrong, 4 scored, 5 speakers. | unit | WRITTEN |
| T-SPK-09 | §8.2: `pairwise`. **New.** | (a) A at 0°, A at 60° (length 2), B at 90°, and a vector with no turn. (b) Two vectors of one speaker. | (a) 1 same pair, lowest and mean 0.5; 2 different pairs, highest cos 30° = 0.866, mean 0.433. (b) 0 different pairs; highest and mean None. | unit | WRITTEN |
| T-SPK-10 | D-057 part 3, §8.2: `pass_range`. **New.** | Thresholds 0.20–0.40. (a) Wrong counts S: 3, 1, 0, 0, 2 and T: 2, 0, 1, 0, 0. (b) S: 0, 2, 0, 2, 0. (c) All 2. | (a) (0.25, 0.35). (b) (0.2, 0.2), the first of equal runs. (c) None. | unit | WRITTEN |
| T-IMPORT-01 | D-021, D-057. | `tir_asr.eval.streams` and `tir_asr.eval.spk_run` in `REQUIRED`; the three candidates in `ADAPTERS`; `speechbrain` and `pyannote` in `FORBIDDEN`. | It passes. | unit | WRITTEN |
| Sweep | D-057 parts 1–4. | Each candidate model, both rules, thresholds 0.20–0.90 in steps of 0.05, the four streams. | Report (not pass or fail): the accuracy of each stream (time and count), the speaker count, the pairwise similarities, and the time of each embedding call. Aren sets `spk_threshold`. | model | APPROVED |

**Branch `c5-pipeline`:**

| ID | Requirement | Input | Expected result | Level | Status |
|---|---|---|---|---|---|
| T-MODEL-SPK-01 | §2.8, the selected adapter. | A real segment. | The embedding is 1-D, float32, finite, with norm > 0; the same audio two times gives cos ≥ 0.999. | model | APPROVED |
| T-MODEL-SPK-02 | §2.8, §7. | No CUDA; a missing model file. | `speakers: CUDA is not available`; `speakers: model file not in the Hugging Face cache: <name>`. | model | APPROVED |
| T-PIPE-05 (changed) | §2.6, D-022. | `warm_up` with a fake embedder. | One embedding call; the clusterer state does not change. | unit | APPROVED |
| T-PIPE-09 | F4, F5, D-057 part 6. | Two sources; a fake labeler for `"System"`. | System lines get `Speaker N` and `spk` in the latency line; `"Me"` lines do not change. | unit | APPROVED |
| T-PIPE-10 | §2.6, R10. | The labeler raises an error. | `tir-asr: speakers: …` and exit code 1. | unit | APPROVED |
| T-OUT-05 | D-024, D-057 part 6. | A system line with a `spk` step. | `[Latency: vad …, asr …, mt …, spk …, out … \| Total …]`. | unit | APPROVED |
| T-CFG-01/02, T-IMPORT-01, T-E2E-01 (changed) | R10, D-021, K1. | The new parameters and modules; the speaker model load. | They pass. | unit, model | APPROVED |
| T-SIM-02 | F4, F5, K1, D-057. | Stream D into the system null sink. | The pass rule of D-057 part 3; 4 speakers; `"Me"` lines stay `"Me"`; each total < 5 s. | sim | APPROVED |
| L-06 | F4, K1 (§4). | A call with 2 or more people on the call side. | Each person keeps one label; the count of extra labels from noise; each total < 5 s. | live | APPROVED |

## 3. QA questions

We add a question here when we find it during the work (tip T4).

| ID | Question | Source | Answer / test ID |
|---|---|---|---|
| Q-01 | Which branch does the app show when a chat has edited messages? | S1, C0 export | The branch to the newest message. Aren confirmed it for C0 (2026-10-23). T-EXPORT-03. |
| Q-02 | Does the final export after C8 have the same format as the C0 export? | S1, D-012 | Open. T-EXPORT-11, run 2. |
| Q-03 | Is the first model call slower for each new input length, also after one warm-up run? | C2, D-022 | [RUN] No, for these inputs: after call 1, new lengths (2.78–12.17 s of audio, 25–52 tokens) are as fast as old lengths. T-INSTALL-02, T-INSTALL-03. |
| Q-04 | Does the minimum silence put two remote speakers into one segment when they change turns fast? | C2, D-027 | Open. C5 speaker purity of the segments. |
| Q-05 | Does `vad_min_speech_ms = 250` remove short answers such as "ոչ" or "հա"? | C2, D-026 | Open. C3 recordings with short answers. |
| Q-06 | ASR writes commas where the reference has "։" (T-INSTALL-02). Does the MT quality drop with this ASR text? | C2 | [RUN] C3 bake-off: the opposite. Where the ASR writes «։» between two sentences, NLLB leaves out the second sentence (Q-13); a comma keeps it. `docs/eval/results.md`, finding 2. |
| Q-07 | Is the first CTranslate2 call (5.1 s) a compile step that the driver keeps between program starts [UNVERIFIED]? | C2, D-022 | Open. Run T-INSTALL-03 two times in two processes. [RUN] Data point (T-MODEL-MT-01, 2026-10-25): in a new process, with the cuBLAS preload and no `LD_LIBRARY_PATH`, the first call took 0.126 s. The cause of the 5.1 s in T-INSTALL-03 is not known. |
| Q-08 | A clip can end with less silence than `vad_min_silence_ms` (clip 1: 150 ms). How does the last segment end? | C2, D-027 | D-032: no added silence; the test plays clip 1, then clip 2 (gap 632 ms). T-E2E-01. |
| Q-09 | Is the first segment after a long silence or a pause slower, because the GPU clocks down [UNVERIFIED]? | C2, Aren's warm-up question | [RUN] No, for 76 s of silence: the first total after the silence was 0.61 s, the same as before (L-03, 2026-10-26). |
| Q-10 | Does a long Python step in the worker delay the capture thread (GIL)? | C2, Aren's thread question | [RUN] No, for P1 with two sources: in T-SIM-01, the largest arrival gap was 43.2 ms (`Me`) and 47.8 ms (`System`), under the 64 ms limit, while the worker ran ASR and MT. In L-05, the latency did not grow in 6 min. P4 (C6) and the speaker model (C5) add worker time: check again. |
| Q-11 | The default microphone gave 22 samples outside [−1, 1] (min −1.0496) at a source volume of 24 % (probe B). Does the input clip, and does a clipped input change the ASR text? | C2d, probe B | The volume is not over 100 % [RUN]. Possible cause [UNVERIFIED]: a full-scale input and the 48 → 16 kHz conversion. [RUN] C3: `s1.mic.wav` has 500 samples at full scale, the other 5 eval files none; the S1 mic WER (6.8 %, `nemo-rnnt`) is close to the other mic files. D-041 part 4. |
| Q-12 | Do Bluetooth headphones change to the headset mode when an application opens their microphone, and does the call audio then lose quality? | C2d, Aren's recordings | Open [UNVERIFIED]. C4 setup guide: select the laptop microphone in the call application. [RUN] L-05: Bluetooth buds as the output and the laptop microphone as the input worked; the quality of the call audio was not measured. |
| Q-13 | Does NLLB leave out a sentence when one segment has two or more sentences? In the first live run, the EN line of the last block has no translation of «Լավ Սոնա, հետո կզանգեմ, հիմա պիտի գնամ։». | C2d, live run | [RUN] C3: yes. With the ASR text: s1-05, s3-07; with the reference text: also s2-06, s2-07, s3-04. Seamless does not leave out these sentences. D-053 (P4). |
| Q-14 | Noises (coughs, short sounds) of 250 ms or more pass the VAD. Then the ASR gives one letter or a fragment, and NLLB invents a sentence. What can stop these blocks? | C4, L-05 (Aren) | Open. [RUN] L-05: about 11 of 84 blocks have only one letter or a fragment, for example «Հ։» → "A: What is it?" and «Հովհ.» → "John: What is it?"; 10 shorter sounds were removed as short segments. Possible changes (no decision): `vad_threshold`, `vad_min_speech_ms`, a rule for texts with one letter, or P4 (C6). C7 decides with numbers (R6). |

## 4. Live checklist (manual)

Only the checks that a sim test cannot do. (C7)

| ID | Check | Expected result | Result |
|---|---|---|---|
| L-01 | Aren says 5 Armenian sentences into the microphone, with a pause after each. | One block for each sentence, label "Me", each total < 5 s (K1). | PASSES (2026-10-26): Script 4, s4-01 to s4-05: 5 blocks, label "Me", totals 0.61–0.64 s. |
| L-02 | Aren presses Ctrl+C. | The shutdown line with the counts. Exit code 0. | Run 1 FAILED (2026-10-26): no reaction (D-044). Run 2 PASSES (2026-10-26, after D-044): the shutdown line, exit code 0. |
| L-03 | Aren is silent for 60 s, then says one sentence; then he says 3 sentences with short pauses (Q-09). | The total of the first sentence is compared with the next ones. || PASSES (2026-10-26): after 76 s of silence, the total of s4-06 was 0.61 s, the same as before (Q-09). |
| L-04 | `./run.sh --list-devices` (C4, D-054). | The list shows the microphone and the output monitor; the defaults have a `*`; exit code 0; no model load. | Not run in C4. |
| L-05 | A video call with one person, wired headphones, `./run.sh` with no flags (C4, D-054). | Lines with `Me` and `System` at the same time; Aren still hears the call; each total < 5 s (K1); the two `startup: source` lines name the correct devices. | PASSES (2026-10-26, Bluetooth buds in place of wired headphones): 84 blocks in about 6 min, totals 0.11–0.68 s, no growth; Aren heard the call (§2.6 results). |
