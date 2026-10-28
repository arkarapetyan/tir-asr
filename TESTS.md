# TESTS.md

**Project:** tir-asr · **Date:** 2026-10-28
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
- **T-NORM-08** reads `docs/eval/scripts.md`. A change of the script table can change the result of this test. C7: the test reads only the rows of S1 to S4 (its approved input); S5 has hyphen words («շաբաթ-կիրակի»), which rule 5 splits by design. The first S5 commit broke CI here, because the regex of the test read all scripts.
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
| T-SPK-06 | D-057 part 1, §8.2: the stream builder. | Audio whose sample k has the value k. (a) `call_stream` with a "Me" line and two call lines. (b) A 10 s stream with turns 1–3 s and 5–7 s: `cut` at 0–4 s and 4 s to the end, then `join` in the order second, first. (c) A cut at 2.0 s. (d) `stream_d`: S1 40 s (turns 10–12 s, 36–38 s), S2 and S3 5 s (turn 1–2 s). (e) `truth_of` with turns 1–3 s and 3.5–6 s. | (a) Only the two call turns, `s1/Speaker 1` and `s1/Speaker 2`, in time order. (b) 4 s with the turn 1–3 s; 6 s that starts at sample 64000 with the turn 1–3 s; the join has 10 s and the turns 1–3 s and 7–9 s. (c) `data: s1: the cut at 2.00 s is inside a turn (1.00–3.00 s)`. (d) 50 s; turns 10–12, 35–36, 41–43, 46–47 s; the sample at 39 s is the S1 sample at 34 s. (e) 2.5–4.0 s: the earlier turn (equal overlaps); 3.2–5.0 s: the second turn; 7–8 s: None. | unit | PASSES |
| T-SPK-08 | D-057 parts 2 and 4, §8.2: `sweep`. **New.** Both rules. | Vectors at 0° (4 s, A), 30° (2 s, A), 100° (3 s, B), 130° (1 s, B), 200° (3 s, no turn). Thresholds 0.5 and 0.95, `min_new_s` 1.0. | 0.5: accuracy 1.0 (time and count), 0 wrong, 4 scored, 3 speakers (the segment with no turn starts a speaker). 0.95: accuracy 0.7 (time) and 0.5 (count), 2 wrong, 4 scored, 5 speakers. | unit | PASSES |
| T-SPK-09 | §8.2: `pairwise`. **New.** | (a) A at 0°, A at 60° (length 2), B at 90°, and a vector with no turn. (b) Two vectors of one speaker. | (a) 1 same pair, lowest and mean 0.5; 2 different pairs, highest cos 30° = 0.866, mean 0.433. (b) 0 different pairs; highest and mean None. | unit | PASSES |
| T-SPK-10 | D-057 part 3, §8.2: `pass_range`. **New.** | Thresholds 0.20–0.40. (a) Wrong counts S: 3, 1, 0, 0, 2 and T: 2, 0, 1, 0, 0. (b) S: 0, 2, 0, 2, 0. (c) All 2. | (a) (0.25, 0.35). (b) (0.2, 0.2), the first of equal runs. (c) None. | unit | PASSES |
| T-IMPORT-01 | D-021, D-057. | `tir_asr.eval.streams` and `tir_asr.eval.spk_run` in `REQUIRED`; the three candidates in `ADAPTERS`; `speechbrain` and `pyannote` in `FORBIDDEN`. | It passes. | unit | PASSES |
| Sweep | D-057 parts 1–4. | Each candidate model, both rules, thresholds 0.20–0.90 in steps of 0.05, the four streams. | Report (not pass or fail): the accuracy of each stream (time and count), the speaker count, the pairwise similarities, and the time of each embedding call. Aren sets `spk_threshold`. | model | PASSES |

**Results (branch `c5-embed`, Aren's laptop, 2026-10-27):** no red run (D-057 part 8).

- **Unit:** `ruff check --no-cache` and `ruff format --no-cache --check` pass; 218 passed, 17 deselected (`test-results/c5-embed-unit.txt`).
- **Install (`spk-eval`):** 31 new packages, no version change of the existing packages; torch 2.14.1+cu130 and torchaudio 2.11.0+cu130 import together; `speechbrain` and `pyannote.audio` import (`test-results/c5-add-spk.txt`). Downloads with no token: TitaNet 5 files, ECAPA 10 files, WeSpeaker 4 files (`test-results/c5-downloads.txt`).
- **Sweep** (`test-results/c5-spk-*.txt`, `test-results/bakeoff/spk-*.json`; table in `docs/eval/results.md`, "Speaker labels (C5)"): all three models ran on the GPU and pass the rule of D-057.
  - Passing ranges, rule A / rule B-max: TitaNet 0.40–0.65 / 0.40–0.65; ECAPA 0.35–0.55 / 0.35–0.60; WeSpeaker 0.50–0.65 / 0.50–0.65.
  - Stream D margin (lowest same-speaker − highest different-speaker cosine): TitaNet +0.170, ECAPA −0.017, WeSpeaker +0.124.
  - TitaNet, rule A, 0.50: 100 % on all four streams (9/9, 5/5, 5/5, 19/19), by count and by speech time. Embedding time at most 28.3 ms.
  - Library messages, no error: SpeechBrain "Falling back to device 0" (the GPU); pyannote turned TF32 off; NeMo "no telemetry data will be collected"; the WAV chunk warning of C4.
- **D-058:** TitaNet with rule A; `spk_threshold` = 0.50 and `spk_min_new_s` = 1.0 s as start values for L-06. After the sweep, the ECAPA and WeSpeaker adapters and the group `spk-eval` are removed. T-IMPORT-01 then has only `tir_asr.eval.spk_titanet` of the three candidates in `ADAPTERS`, and `speechbrain` and `pyannote` leave `FORBIDDEN`.

**Branch `c5-pipeline`** (D-059). T-SPK-11 is new: it tests the core labeler, which T-PIPE-09 replaces with a fake. Aren approved it on 2026-10-27. T-SIM-01 changes only for the new signatures of `load_models` and `warm_up`; it runs with no labeler, so its labels stay `Me` and `System`.

| ID | Requirement | Input | Expected result | Level | Status |
|---|---|---|---|---|---|
| T-SPK-11 | §2.8, D-059 point 1: `SpeakerLabeler`. **New.** | A fake embedder (vectors at 0°, 90°, 80°) and `CentroidClusterer(0.9, 1.0)`. Segments 1.0–4.0 s, 5.0–8.0 s, 9.0–9.5 s; the audio of each shows its start. | `Speaker 1`, `Speaker 2`, `Speaker 2` (the third segment has 0.5 s of speech, so it is short: the most similar speaker, cos 10°). The embedder got the audio of the three segments in order. | unit | PASSES |
| T-MODEL-SPK-01 | §2.8, the selected adapter. | `TitanetEmbedder()`, one warm-up call with 2 s of zeros, then clip 1, clip 2, clip 1 (`data/eval/c2-check{1,2}.16k.wav`). | Each embedding is 1-D, float32, finite, with norm > 0; clip 1 two times gives cos ≥ 0.999. Report: the load time, the call times, the cosine of the two clips of Aren, the peak VRAM. | model | PASSES |
| T-MODEL-SPK-02 | §2.8, §7. | (a) `TitanetEmbedder(filename="no-such-model.nemo")`. (b) `torch.cuda.is_available` patched to False. | (a) `SpeakerError` that starts with `speakers: model file not in the Hugging Face cache: ` and names the file. (b) `speakers: CUDA is not available`. | model | PASSES |
| T-PIPE-05 (changed) | §2.6, D-022, D-059 point 5. | `warm_up(transcriber, translator, embedder, clock)` with fakes; a `SpeakerLabeler` holds the same fake embedder. Clock 10.0, 10.4, 10.5, 10.53. | One ASR call with 2 s of zeros, one MT call with `WARMUP_TEXT`, one embedding call with the same zeros; the clusterer has 0 speakers; times 0.4, 0.1, 0.03 s. | unit | PASSES |
| T-PIPE-09 | F4, F5, D-059 points 2 to 4. | Me (50 frames, speech 5–24) and System (140 frames: short 30–36, speech 60–79, speech 100–119 with an empty text), System after Me; a fake labeler for `"System"` that gives `Speaker 2`. Clock 0.0; 1.400, 1.500, 1.510; 3.200, 3.300, 3.320, 3.330; 4.500, 4.510. | `[00:00:00] Me` with `vad 0.51s, asr 0.09s, mt 0.10s, out 0.01s \| Total 0.71s`; `[00:00:01] Speaker 2` with `vad 0.51s, asr 0.13s, mt 0.10s, spk 0.02s, out 0.01s \| Total 0.77s`; `[00:00:03] System`, `HY: (no text)`, `vad 0.51s, asr 0.15s \| Total 0.67s`; `Stopped. Segments: 3, short segments: 1, empty texts: 1, not processed: 0.`; one labeler call, for the System segment that starts at 1.92 s. | unit | PASSES |
| T-PIPE-10 | §2.6, §7, R10. | One System source (speech 5–24); a fake labeler that raises `speakers: test` (a `TirError`). Clock 0.0, 1.400, 1.500. | Exit code 1; the error output `tir-asr: speakers: test`; the output is only "Listening". | unit | PASSES |
| T-OUT-05 | D-024, D-059 point 4. | The T-OUT-01 line with the label `Speaker 1`, `mt_end` 1076.12, `spk_end` 1076.13, `write` 1076.14. | `[00:01:12] Speaker 1`; `[Latency: vad 0.53s, asr 0.41s, mt 0.18s, spk 0.01s, out 0.01s \| Total 1.14s]`. | unit | PASSES |
| T-CFG-01 (changed) | R10, D-058. | `asdict(Params())`. | The §6 table, now with `spk_threshold` 0.50 and `spk_min_new_s` 1.0. | unit | PASSES |
| T-IMPORT-01 (changed) | D-021. | `tir_asr.speakers.labeler` in `REQUIRED`; `tir_asr.speakers.titanet` in `ADAPTERS` (in place of `tir_asr.eval.spk_titanet`). | It passes. | unit | PASSES |
| T-E2E-01 (changed) | K1, F2, F3, F5, D-059. | As in §2.6, with `load_models(…)` that returns the embedder too, and `warm_up(…, embedder, …)`. | As in §2.6, and a `startup: speaker model loaded in` line. | model | PASSES |
| T-SIM-01 (changed) | D-054, D-059. | As in §2.6, with the new signatures. | As in §2.6. | sim, model | PASSES |
| T-SIM-02 | F4, F5, K1, D-057, D-059 point 8. | Two null sinks. "Me" plays `s1.mic.wav`; "System" plays stream D (a 16-bit copy at 16 kHz). The program labeler of `"System"` (`app.speaker_labeler`) in a wrapper that records the start, the speech end, and the label of each call. Time 0 of stream D: the start of the System player. | (1) Exit code 0, no error output. (2) Each block has `Me`, `Speaker N`, or `System` with `(no text)` only; one `Speaker N` block for each labeler call. (3) Label accuracy after the best mapping: at most 1 wrong segment (D-057 part 3); exactly 4 speaker labels. (4) Each total < 5 s. (5) No arrival gap over 64 ms on each source (Q-10). Report: each segment with its label and true speaker, the accuracy by count and by time. | sim, model | PASSES |
| L-06 | F4, K1 (§4). | A call with 2 or more people on the call side, `./run.sh` with no flags. | Each person keeps one label; the count of extra labels (noise, Q-14) and of merged people; each total < 5 s. The values of `spk_threshold` and `spk_min_new_s` are checked (D-058). | live | FAILS on one point (D-060) |

**Results (branch `c5-pipeline`, Aren's laptop, 2026-10-27):** no red run (D-057 part 8).

- **Unit:** `ruff check --no-cache` and `ruff format --no-cache --check` pass; 223 passed, 21 deselected (`test-results/c5-pipeline-unit.txt`).
- **Model** (`test-results/c5-pipeline-model.txt`): 5 passed in 32.87 s.
  - T-MODEL-SPK-01: shape (192,), float32; load 0.34 s, warm-up 0.388 s, each call 6–10 ms; the same audio gives cosine 1.000000; two clips of Aren give 0.788; peak torch VRAM 254 MiB.
  - T-MODEL-SPK-02: `speakers: model file not in the Hugging Face cache: nvidia/speakerverification_en_titanet_large/no-such-model.nemo`; `speakers: CUDA is not available`.
  - T-E2E-01: totals 0.64 s and 0.62 s; the line `startup: speaker model loaded in 0.20 s`. T-E2E-02: exit code 0, 1.17 s after SIGINT; `torch CPU threads 1`.
- **Sim** (`test-results/c5-pipeline-sim.txt`): 2 passed in 278.46 s.
  - T-SIM-01: the same result as in C4: 14 blocks (5 `Me`, 9 `System`), WER `Me` 0.085 and `System` 0.205 on their own references, totals at most 0.66 s, gaps at most 48.7 ms.
  - T-SIM-02: 24 blocks (5 `Me`, 19 `Speaker N`); 19 labelled segments, 19 scored, **0 wrong**; accuracy 1.000 by count and by time; 4 labels: `Speaker 1` = s1/Speaker 1 (5 segments), `Speaker 2` = s1/Speaker 2 (4), `Speaker 3` = s2/Speaker 1 (5), `Speaker 4` = s3/Speaker 1 (5). The two S1 people kept their labels after the S2 voice (from 1:37). The `spk` step took 0.01–0.02 s; totals 0.59–0.68 s; the largest arrival gap 43.3 ms (`Me`) and 50.5 ms (`System`).
  - Not errors of the speaker step: the labels `Speaker 3` and `Speaker 4` (each script calls its first remote person "Speaker 1", but stream D is one session with four people); one `Me` block before an earlier `Speaker 3` block (a long segment closes later, D-054); "Me" plays all of S1 while "System" plays stream D, so the two sides do not make one conversation after 34 s; ASR word errors (P1).
- **Probe** (`test-results/c5-probe-spk-load.txt`, after ASR and the Silero import): the TitaNet load adds 196 MiB of torch memory (458 → 654 MiB allocated) from the reserved torch cache (918 MiB before and after), so the device value does not change; the torch CPU threads stay 1. Two consequences:
  - The startup line showed `(+-256 MiB)` for the speaker model: a sign format error in `app.py`, corrected to `(-256 MiB)` (also for the MT line). The cause of the −256 MiB of the full device is [UNVERIFIED] (probably CTranslate2 after its load).
  - In T-SIM-02, the VAD line showed `torch CPU threads 4`: the second model load in the same test process changed it [UNVERIFIED cause]. The program loads each model one time, and T-E2E-01/02 show 1.
- **L-06** (`test-results/c5-l06.txt`, 2026-10-27, Bluetooth buds, about 1 min 15 s; the protocol asked for 5 min): **fails on one point** (D-060).
  - 2 people on the call side (A, B); 9 `System` lines, 8 `Me` lines; totals 0.57–0.70 s; `spk` 0.01–0.02 s (K1 passes).
  - Clean turns: A kept `Speaker 2` (00:00:06, 00:00:30), B kept `Speaker 3` (00:00:16, 00:00:46); no two people got one label.
  - The failure: the first segment was a cough of A («Լա։» → "What is it?"). It started `Speaker 1` (D-057 part 5B), so A had two labels. D-060 part 2 changes the rule.
  - Two segments had two voices (00:00:40: A, then B for longer, label `Speaker 3`; 00:00:55: A, then B shortly after, label `Speaker 2`). Aren: "No interruptions were correctly registered" (Q-04).
  - 3 of 9 `System` lines were noises with one letter or a fragment: «Լա։», «Հովհ.» (`Speaker 3`), «Հ։» (`Speaker 2`) (Q-14).
  - After `Stopped.`: `terminate called without an active exception`. The pipe hid the exit code (L-02).
  - The startup line: `speaker model loaded in 0.20 s; GPU memory used 2508 MiB (-256 MiB)`.

**Changes after L-06 (branch `c5-pipeline`, D-060).** Aren: "proceed" (2026-10-27).

| ID | Requirement | Input | Expected result | Level | Status |
|---|---|---|---|---|---|
| T-SPK-03 (changed) | §2.8 steps 2 and 3, D-060 part 2. Both rules. | Threshold 0.9, `min_new_s` 1.0. 0° (0.5 s), then the old inputs: 0° (long), 90° (long), 40° (0.5 s), 35° (long), 180° (1.0 s). | `None` and `count` = 0 (a short first segment starts no speaker); then `Speaker 1`, `Speaker 2`, `Speaker 1` (short: the most similar, `count` = 2), `Speaker 3`, `Speaker 4`; `count` = 4. | unit | PASSES |
| T-SPK-05 (one more case) | §8.2, D-060 part 2. | (f) Truths A A B, labels None S1 S2, weights 1. (g) Truths A B, labels None None. | (f) 2/3 (no label is always an error). (g) 0.0. | unit | PASSES |
| T-SPK-11 (one more case) | §2.8, D-060 part 2. | A fake embedder (0°, 0°), `CentroidClusterer(0.9, 1.0)`. Segments 1.0–1.5 s (0.5 s of speech), then 2.0–5.0 s. | `Unidentified`, then `Speaker 1`. `UNIDENTIFIED` is `"Unidentified"`. | unit | PASSES |

**Results (D-060 changes, Aren's laptop, 2026-10-27):** no red run (D-057 part 8). `ruff check --no-cache` and `ruff format --no-cache --check` pass; 226 passed, 21 deselected (`test-results/c5-d060-unit.txt`): 223 as before, 2 new cases of T-SPK-05, and the new T-SPK-11 function.

**Branch `c5-stop`** (D-061, the clean stop). Aren approved T-PIPE-11, T-PIPE-12, the change of T-E2E-02, and the live exit check on 2026-10-27 ("approved, proceed"). T-PIPE-13 is new: R10 does not allow a silent time limit, so a thread that does not stop gives an error line. Aren approved it on 2026-10-27 ("ci is green, continue").

| ID | Requirement | Input | Expected result | Level | Status |
|---|---|---|---|---|---|
| T-PIPE-11 | §2.6 clean stop, D-061: Ctrl+C. **New.** | One `Me` source that gives silence blocks with no end (1 ms between blocks). A helper thread calls `_thread.interrupt_main()` after the first block. Clock 0.0. | Exit code 0. The output is only `Listening` and `Stopped. Segments: 0, short segments: 0, empty texts: 0, not processed: 0.`; no error output. When `run()` returns, the block iterator of the source is closed, and no thread of `run()` runs. | unit | PASSES |
| T-PIPE-12 | §2.6 clean stop, D-061: an error. **New.** | The same endless source, with speech in frames 5–24. The transcriber raises `asr: test`. Clock 0.0. | Exit code 1. The error output is `tir-asr: asr: test`; the output is only `Listening`; one ASR call. When `run()` returns, the iterator is closed, and no thread of `run()` runs. | unit | PASSES |
| T-PIPE-13 | §2.6 clean stop, §7, D-061, R10. **New.** | `STOP_JOIN_S` patched to 0.1 s. A `Me` source that gives one block and then no block until the test releases it. Ctrl+C as in T-PIPE-11. | Exit code 0; the shutdown line; the error output `tir-asr: stop: thread capture Me did not stop in 0.1 s`. After the release, the source ends. | unit | PASSES |
| T-E2E-02 (changed) | L-02, D-061. | As before (SIGINT 2 s after "Listening"). | Also: the output has no line with `Aborting` and no line with `terminate called`. | model | PASSES |
| L-02 (exit check) | D-061. | 3 runs of `./run.sh`, each with `echo "exit code ${PIPESTATUS[0]}"`: 2 runs with `pw-play` on the System side, 1 run with only the microphone; Ctrl+C one time. | Exit code 0 and no abort line in each run. | live | PASSES |

**Results (branch `c5-stop`, Aren's laptop, 2026-10-27):** no red run (D-057 part 8).

- **Unit:** `ruff check --no-cache` and `ruff format --no-cache --check` pass; 229 passed, 21 deselected (`test-results/c5-stop-unit.txt`).
- **Model** (`test-results/c5-stop-model.txt`): T-E2E-01 and T-E2E-02 pass in 32.07 s. T-E2E-01: totals 0.63 s and 0.61 s. T-E2E-02: exit code 0, 1.12 s after SIGINT, no abort line.
- **Sim** (`test-results/c5-stop-sim2.txt`): 2 passed in 280.01 s.
  - T-SIM-01: 14 blocks (5 `Me`, 9 `System`); WER `Me` 0.068 and `System` 0.196 on their own references (c5-pipeline: 0.085 and 0.205; the segments can differ a little from run to run [UNVERIFIED]); totals at most 0.65 s; arrival gaps at most 45.6 ms.
  - T-SIM-02: 19 of 19 labels correct, 4 labels; totals at most 0.70 s; arrival gaps at most 47.9 ms.
  - The first sim run (`test-results/c5-stop-sim.txt`) stopped before the model load and has no result.
- **Live exit check:** 3 runs, each with exit code 0 and no abort line. `c5-exit2.txt`: S2 call on the System side, 5 `Speaker 1` lines and 1 `Me` line. `c5-exit3.txt`: S3 call, 5 `Speaker 1` lines. `c5-exit4.txt`: only the microphone, 6 `Me` lines. Before D-061, `c5-exit1.txt` gave exit code 134.

### 2.8 P4: Seamless end to end (C6)

Contracts: `ARCHITECTURE.md` §2.6, §2.7, and the new §2.9 (`text`, branch `c6-textstep`). Decisions: D-062; D-063 selects the P4 variant and gives the limits of T-PERF-P4-01. Aren approved the tests on 2026-10-27 ("agree on the tests"). D-062 part 10: no separate red run; Claude writes the tests and the code in one step, and Aren does only the green run.

**Branch `c6-probe`** (research, R8, D-062 part 1): no tests. `scripts/probe_p4.py` is a model-level script, as `scripts/bakeoff.py` and `scripts/probe_cpu.py`. Its numbers go into D-063 and `docs/eval/results.md`.

**Results (branch `c6-probe`, Aren's laptop, 2026-10-27):** `test-results/c6-probe-gpu.txt`, `test-results/c6-probe-cpu.txt`, `test-results/bakeoff/p4-probe-{gpu,cpu}.json`. The GPU part reproduces C3 with V0 (WER 6.8 %, chrF 59.0, maximum 0.83 s). V2 (one call for both lines): WER 7.1 %, chrF 59.0, line mean 0.337 s, maximum 0.443 s. The model is greedy (`num_beams` not set). A decode step with a batch of two takes 1.02 times a step with a batch of one. CPU: 24 threads 5.2–50.5 s for each line; 8 threads (the fast cores) V2 2.7–3.9 s; INT8 with 8 threads V2 1.18–1.76 s. Table and details: `docs/eval/results.md`, "P4 variants (C6)"; D-063.

**Branch `c6-textstep`** (D-062 part 2). Core `text/step.py`. In T-TEXT-01 to T-TEXT-05, a recorder subclass of `TextStep` records each hook call; its `_prepare` gives a new state object at each call.

| ID | Requirement | Input | Expected result | Level | Status |
|---|---|---|---|---|---|
| T-TEXT-01 | §2.9, D-062 part 2: the template order and the clock reads. | The recorder: `_armenian` gives "բարև", `_english` gives "hi". `process(audio, clock)`; clock 1.0, 2.0. | The hook calls in this order: `_prepare(audio)` with the same array, `_armenian(state)`, `_english(state, "բարև")`, both with the state of `_prepare`. The result is `TextResult("բարև", "hi", 1.0, 2.0)`. The clock has no values left (2 reads). | unit | PASSES |
| T-TEXT-02 | §2.9, D-031 for P1 and P4. | The recorder with `_armenian` = "". `process(audio, clock)`; clock 1.0. | No `_english` call. The result is `TextResult("", "", 1.0, 1.0)`. 1 clock read. | unit | PASSES |
| T-TEXT-03 | §2.9, D-022, D-037: the warm-up of each path. | The recorder with `_armenian` = "" (zeros give no text). `warm_up(zeros, clock)`; clock 10.4, 10.5. | `_prepare(zeros)`, `_armenian(state)`, then `_english(state, WARMUP_TEXT)`, also with the empty HY text. The result is `TextResult("", "hi", 10.4, 10.5)`. | unit | PASSES |
| T-TEXT-04 | §2.9, D-062 part 2: P1 in the template. | `CascadeTextStep(FakeTranscriber(["բարև"]), FakeTranslator("hi"))`: `process(audio, clock)`, clock 1.0, 2.0. Then a new one with `FakeTranscriber([""])`: `warm_up(zeros, clock)`, clock 10.4, 10.5. | `process`: the transcriber gets the same audio array, the translator gets "բարև", and the result is `TextResult("բարև", "hi", 1.0, 2.0)`. `warm_up`: the transcriber gets the zeros, the translator gets `WARMUP_TEXT`, and the result is `TextResult("", "hi", 10.4, 10.5)`. `CascadeTextStep` does not define `process` or `warm_up`: the template stays in `TextStep`. | unit | PASSES |
| T-TEXT-05 | §2.9, §7, R10: an error goes up with no change. | (a) The recorder with an `_armenian` that raises `FakeAsrError("asr: test")`. (b) The recorder with an `_english` that raises `KeyError("x")`; clock 1.0. | (a) The same exception object; no `_english` call; no clock read. (b) The same `KeyError` object; 1 clock read. | unit | PASSES |
| T-PIPE-01 to T-PIPE-13 (changed) | §2.6, D-062 part 2: no change of behaviour. | `run(sources, text_step, …)` and `warm_up(text_step, embedder, clock)`, with `CascadeTextStep(FakeTranscriber, FakeTranslator)`. All other inputs and all clock values as before. | The same expected results as before (§2.4, §2.6, §2.7). | unit | PASSES |
| T-IMPORT-01 (changed) | D-021. | `tir_asr.text` and `tir_asr.text.step` in `REQUIRED`. | It passes. | unit | PASSES |
| T-E2E-01, T-E2E-02, T-SIM-01, T-SIM-02 (changed) | D-062 part 2. | As before, with the new signatures: `load_models` returns `(vads, text_step, embedder)`; `warm_up(text_step, embedder, clock)`; `run(sources, text_step, …)`. | As before. | model; sim, model | PASSES |

**Results (branch `c6-textstep`, Aren's laptop, 2026-10-27):** no separate red run (D-062 part 10).

- **Unit:** `ruff check --no-cache` and `ruff format --no-cache --check` pass; 237 passed, 21 deselected (`test-results/c6-textstep-unit.txt`): 229 as before, the 6 functions of `test_text.py`, and 2 more core modules in T-IMPORT-01.
- **Model** (`test-results/c6-textstep-model.txt`): 2 passed in 31.81 s. T-E2E-01: totals 0.64 s and 0.62 s, the same as in C5 (0.63 s, 0.61 s); the warm-up ASR 0.284 s, MT 0.105 s, speaker 0.048 s. T-E2E-02: exit code 0, 1.12 s after SIGINT.

**Branch `c6-seamless`** (D-062 parts 2, 3, and 9; D-063). D-063 part 2 (the step name `s2t` for P4) adds T-OUT-06 and T-PIPE-14; D-063 part 4 (no CPU mode) removes T-PERF-P4-01 part (b) and T-MODEL-P4-02 part (c); D-063 part 5 gives the limits of T-PERF-P4-01.

| ID | Requirement | Input | Expected result | Level | Status |
|---|---|---|---|---|---|
| T-MODEL-P4-01 | §2.9, D-053, D-063: the P4 adapter. | `SeamlessTextStep()` on `cuda`. `warm_up` with 2 s of zeros, then `process` on clip 1, clip 2, and clip 1 (`data/eval/c2-check{1,2}.16k.wav`). | Each HY text is not empty and has Armenian letters (U+0531 to U+0587). Each EN text is not empty and has Latin letters. Clip 1 two times gives the same two texts. `SeamlessTextStep` does not define `process` or `warm_up`, and its `STEPS` is `("s2t",)`. Report: the load time, the warm-up time, the time of each call, the peak VRAM. | model | PASSES |
| T-MODEL-P4-02 | §2.9, §7, R10. | (a) A model id that is not in the Hugging Face cache. (b) `torch.cuda.is_available` patched to False. Part (c) left the test (D-063 part 4: no CPU mode). | (a) `TextError` that starts with `text: model not in the Hugging Face cache: ` and names the id. (b) `text: CUDA is not available`; the model does not load. | model | PASSES |
| T-PERF-P4-01 | D-056 part 2.4 (the performance test of P4 alone), K1, R6, D-063 part 5. | The program's VAD cuts S1–S3 with `Params()` (34 segments, as in C3); `SeamlessTextStep.process` on each segment, after its warm-up. Part (b) (CPU) left the test (D-063 part 4). | WER ≤ 7.6 %, chrF ≥ 58.5 (joined texts, as in C3), line mean ≤ 0.40 s, line maximum ≤ 0.55 s. Report: CER, VRAM, the empty Armenian texts. | model | PASSES |
| T-OUT-06 | D-024, D-063 part 2: one text step for P4. **New.** | The T-OUT-01 line with `steps=("s2t",)`: (a) as in T-OUT-01; (b) with the label `Speaker 1`, `spk_end` 1076.13, `write` 1076.14; (c) an empty text: `hy` and `en` "", `mt_end` 1075.94, `write` 1075.97. | (a) `[Latency: vad 0.53s, s2t 0.59s, out 0.00s \| Total 1.12s]`. (b) `[Latency: vad 0.53s, s2t 0.59s, spk 0.01s, out 0.01s \| Total 1.14s]`. (c) `HY: (no text)` and `[Latency: vad 0.53s, s2t 0.41s \| Total 0.97s]`. The T-OUT-01 to T-OUT-05 lines keep the default `steps` `("asr", "mt")` and their results. | unit | PASSES |
| T-PIPE-14 | §2.6, D-063 part 2: the line gets the step names of the text step. **New.** | One `Me` source (speech in frames 5–24) and a fake text step with `STEPS = ("s2t",)` that gives "բարև" and "hi". Clock 0.0, 1.400, 1.500, 1.510. | `[00:00:00] Me`, `HY: բարև`, `EN: hi`, `[Latency: vad 0.51s, s2t 0.19s, out 0.01s \| Total 0.71s]`; then the shutdown line; exit code 0. | unit | PASSES |
| T-IMPORT-01 (changed) | D-021. | `tir_asr.text.seamless` in `ADAPTERS`. | It passes. | unit | PASSES |

**Results (branch `c6-seamless`, Aren's laptop, 2026-10-27):** no separate red run (D-062 part 10). Aren approved T-OUT-06 and T-PIPE-14 on 2026-10-27 ("tests confirmed").

- **Unit:** `ruff check --no-cache` and `ruff format --no-cache --check` pass; 241 passed, 24 deselected (`test-results/c6-seamless-unit.txt`): 237 as before, the 3 functions of T-OUT-06, and T-PIPE-14.
- **Model** (`test-results/c6-seamless-model.txt`): 5 passed in 49.54 s.
  - T-MODEL-P4-01: load 2.78 s, VRAM +2884 MiB; greedy (`num_beams` 1), `max_new_tokens` 256; warm-up 0.697 s; clip 1 0.328 s, clip 2 0.336 s, clip 1 0.321 s with the same texts; peak torch memory 2941 MiB. On the 2 s of zeros of the warm-up, P4 wrote «ՄԱՐԻԿ - Այո։» and "The first thing we do is we make a little bit of a noise." (Seamless invents text for audio with no speech).
  - T-MODEL-P4-02: `text: model not in the Hugging Face cache: facebook/no-such-model`; `text: CUDA is not available`.
  - T-PERF-P4-01: 34 segments, none with an empty Armenian text; WER 7.1 %, CER 2.3 %, chrF 59.0, line mean 0.334 s, maximum 0.426 s (limits 7.6 %, 58.5, 0.40 s, 0.55 s); peak torch memory 2955 MiB.
  - T-E2E-01 and T-E2E-02 pass again: totals 0.63 s and 0.62 s; exit code 0, 1.22 s after SIGINT. After T-PERF-P4-01 in the same process, the VAD line of T-E2E-01 showed `torch CPU threads 4` (the C5 note: a second model load in one test process changes it [UNVERIFIED cause]); the program process of T-E2E-02 shows 1.

**Branch `c6-cli`** (D-062 parts 4 and 5).

| ID | Requirement | Input | Expected result | Level | Status |
|---|---|---|---|---|---|
| T-CLI-03 | D-062 part 4: the flag. | The fake `app` of T-CLI-02. `cli.main(["--seamless"])`; `cli.main(["--seamless", "--mic", "a"])`; `cli.main(["--help"])`. | `app.main` gets `seamless=True` (with `mic=None`, `system=None`), then `seamless=True` with `mic="a"`. The help text has `--seamless`. T-CLI-02 changes: each call of `app.main` also has `seamless=False`. | unit | PASSES |
| T-E2E-03 | K1, F2, F3, F5, D-062 parts 4 and 5: the program with P4. | (a) As T-E2E-01, with the load function of the program for P4 (`seamless=True`). (b) As T-E2E-02, with `tir-asr --seamless`. | (a) The results of T-E2E-01. The startup log has the text step line and a Seamless load line, and no `ASR loaded` and no `MT loaded` line. (b) The results of T-E2E-02: exit code 0, no abort line, the shutdown line last. | model | PASSES |
| T-SIM-03 | F4, F5, K1, Q-10, D-062. | As T-SIM-02, with the P4 text step. | The results (1) to (5) of T-SIM-02. Report: the line times and the `s2t` step. | sim, model | FAILS on point (5) (D-064); PASSES after D-067 (C7, §2.9) |
| L-07 | F1 to F5, K1, D-053 (revisit), D-062 (§4). | A call with 1 or more people on the call side, `./run.sh --seamless`, about 5 min. `nvidia-smi` logs the GPU power and temperature. | Lines with `Me` and `Speaker N`; each total < 5 s; the totals do not grow during the call; the startup log shows the text step; at the stop, the shutdown line, exit code 0, and no abort line. Report: the GPU power and temperature. | live | RUN, NOT RECORDED (D-064); RECORDED in C7 (§2.9, §4) |

**Results (branch `c6-cli`, Aren's laptop, 2026-10-27):** no separate red run (D-062 part 10).

- **Unit:** `ruff check --no-cache` and `ruff format --no-cache --check` pass; 243 passed, 27 deselected (`test-results/c6-cli-unit.txt`): 241 as before and the 2 functions of T-CLI-03.
- **Model** (`test-results/c6-cli-model.txt`): 4 passed in 59.20 s.
  - T-E2E-01 (P1): the line `startup: text step cascade (P1): …`; totals 0.63 s and 0.62 s; the versions line has `transformers 5.20.2`.
  - T-E2E-03 (a) (P4): `startup: text step seamless (P4): …`, `startup: Seamless loaded in 2.43 s; … generate num_beams 1, max_new_tokens 256`; no ASR and no MT load line; the latency lines `vad 0.51s, s2t 0.35s, out 0.00s | Total 0.86s` and `… s2t 0.34s … | Total 0.85s`.
  - T-E2E-02 and T-E2E-03 (b): exit code 0, 1.22 s after SIGINT, no abort line; the P4 warm-up line `startup: warm-up s2t 0.69 s, speaker 0.20 s`.
- **Sim** (`test-results/c6-cli-sim.txt`): 1 failed, 2 passed in 476.07 s. T-SIM-01 and T-SIM-02 (P1) pass: T-SIM-01 WER `Me` 0.068 and `System` 0.205 on their own references, totals at most 0.65 s, gaps at most 43.3 ms; T-SIM-02 19 of 19 labels correct, totals at most 0.68 s, gaps at most 49.5 ms. **T-SIM-03 (P4) fails on point (5):** the capture thread `Me` had an arrival gap of 145.0 ms (limit 64 ms, Q-10). Its points (1) to (4) pass: 24 blocks (5 `Me`, 19 `Speaker N`), 19 of 19 labels correct, 4 labels, totals 0.76–0.99 s, the step `s2t` 0.25–0.48 s. The P4 lines have correct Armenian text, with no `#err` and no English text in an HY line. The VAD line of the P4 load showed `torch CPU threads 4` (a second model load in the test process; the program has 1).
- **L-07** (live, 2026-10-27 and 2026-10-28): run, with no output file. Aren, 2026-10-27: P1 was "miles better" than P4; "the text of both normal, as well as slightly 'artificially clarified' speech, seamless was constantly failing"; "no not really invented lines on noise or silence"; "also seamless gave some #err symbols for some reason". Aren, 2026-10-28 (more tests): "it worked a bit better this time, but I still get #err symbol, as well as english text in armenian transcription". The checks of the row (the totals, their growth, the GPU power) are not recorded. D-064: no run of unoptimized P4 (the probe shows the same texts for V0 and V2); the next chat finds the cause and does a full live test of P1 and P4 with the output in files.

### 2.9 C7: live test and P4 fixes (C7)

Decisions: D-065 (plan), D-066 (the P4 fixes), D-067 (the GIL switch interval). D-065: no separate red run; Claude writes the tests and the code in one step, and Aren does only the green run.

**Part A (the cause search, D-065 point 3):**

- A1 (`test-results/c7-a1-vocab.txt`): `#err` is two normal tokens of the Seamless vocabulary, `▁#` (5134) and `err` (38634).
- A1b (`test-results/c7-a1b-marks.txt`): «՞» is in 25 tokens, «։» in 3, «՝» in 8; «և» is in no token.
- A2 (`test-results/c7-a2-sim03.txt`): T-SIM-03 alone, `torch CPU threads 1`: FAILS on point (5), gap 134.4 ms on `Me`. Thus the 4 threads of the C6 test process were not the cause.

**Live calls (L-07 again, D-065 point 4):** script S5 (`docs/eval/scripts.md`), Me and Speaker 1, first P1 (`test-results/c7-live-p1.txt`), then P4 (`test-results/c7-live-p4.txt`); the audio in `data/c7/`; GPU logs `test-results/c7-live-p{1,4}-gpu.csv`. Scores from `scripts/score_live.py` (the joined texts of each side against S5, as in C3): table and findings in D-066 and `docs/eval/results.md`, "Live calls (C7)". In short: P1 WER 7.1 % (Me) and 12.7 % (call), chrF 56.0 and 59.6; P4 WER 8.3 % and 18.1 %, chrF 64.2 and 65.5; one `#err` (P4, s5-43, for «Հը»); no English text in an HY line; totals P1 0.57–0.67 s, P4 0.70–0.94 s, no growth; GPU at most 24.2 W and 50 °C.

**Branch `c7-p4`** (D-066, D-067).

| ID | Requirement | Input | Expected result | Level | Status |
|---|---|---|---|---|---|
| T-TEXT-06 | §2.9, D-066 parts 1 and 3: the output rules of `text/clean.py`. | HY: the P4 line of s5-43 (`իսկապես #err ոնց էր, դուր եկավ։`), `#err`, `#err, լավ եմ։`, a text with no change (spaces at the start and the end), a text with «՞», «՜», `:`, digits, and «», an English line, `լավ, OK Google, գնանք`, `Привет բարև`, `համար #1`. EN: `Really? #Hmm, how was it? Did you like it?`, a text with no change, typographic punctuation, `Hello Սոնա, how are you?`, `Hi Сона Սոնա!`, `A café`. | HY: the mark and its comma go; `""`; `լավ եմ։`; the same texts; `[?]`; `լավ, [?] գնանք`; `[?] բարև`; `համար [?]`. EN: `Hmm` stays without `#`; the same texts; `Hello [?] how are you?`; `Hi [?]`; `A [?]`. | unit | PASSES |
| T-TEXT-07 | §2.9, D-066: the place of the rules in the template. | (a) The recorder with HY `բարև OK` and EN `hi Привет`, clock 1.0, 2.0. (b) The recorder with HY `#err` and EN `#Hmm`, clock 1.0. | (a) `_english` gets `բարև [?]` (P1 translates the clean text); the result is `TextResult("բարև [?]", "hi [?]", 1.0, 2.0)`. (b) No `_english` call; `TextResult("", "", 1.0, 1.0)` (D-031). | unit | PASSES |
| T-IMPORT-01 (changed) | D-021. | `tir_asr.text.clean` in `REQUIRED`. | It passes. | unit | PASSES |
| T-PIPE-15 | §2.6, §4, D-067. | A text step that records `sys.getswitchinterval()` in `_armenian`: (a) with a text, clock 0.0, 1.400, 1.500, 1.510; (b) with a `TirError`, clock 0.0. | During `run()`, the interval is `GIL_SWITCH_S` (0.001 s); after `run()`, it has its old value; exit code (a) 0, (b) 1. | unit | PASSES |
| T-SIM-02, T-SIM-03 (changed) | Q-10, D-066 part 2: the diagnostic. | As before; a test wrapper on the text step records the times of its calls, and a `gc.callbacks` function records the GC passes. | Report only, no new assert: the GC passes, the text step calls, and each gap over 64 ms with its time, the text step call in it, and the GC passes in it. | sim, model | PASSES (T-SIM-03, after D-067) |

**Results (branch `c7-p4`, Aren's laptop, 2026-10-28):** no separate red run (D-065).

- **`feat(text)` (D-066):** ruff passes; unit 261 passed, 27 deselected (`test-results/c7-p4-unit.txt`): 243 as before, 15 cases of T-TEXT-06, 2 of T-TEXT-07, and 1 more core module in T-IMPORT-01. Model (`test-results/c7-p4-model.txt`): 7 passed in 75.80 s; T-PERF-P4-01 does not change (WER 7.1 %, chrF 59.0, line mean 0.330 s, maximum 0.418 s); T-E2E-01 to T-E2E-03 pass.
- **Diagnostic (D-066 part 2, before D-067)** (`test-results/c7-p4-sim03.txt`): T-SIM-03 FAILS on point (5). 522 GC passes, none of generation 2, longest 0.6 ms. 24 text step calls, longest 0.451 s. Gaps over 64 ms: 17 on `Me` (largest 135.0 ms), 18 on `System` (largest 146.2 ms); each came during a text step call, and no full GC pass came in a gap.
- **`fix(pipeline)` (D-067):** ruff passes; unit 263 passed (`test-results/c7-gil-unit.txt`): 261 and the 2 cases of T-PIPE-15. **T-SIM-03 PASSES** (`test-results/c7-gil-sim03.txt`): 0 gaps over 64 ms, largest 61.0 ms (`Me`) and 55.0 ms (`System`); 19 of 19 labels correct, 4 labels; totals max 0.96 s, mean 0.88 s; 523 GC passes, none of generation 2. Model (`test-results/c7-gil-model.txt`): T-E2E-01 to T-E2E-03, 4 passed; exit code 0, 1.22 s after SIGINT.

## 3. QA questions

We add a question here when we find it during the work (tip T4).

| ID | Question | Source | Answer / test ID |
|---|---|---|---|
| Q-01 | Which branch does the app show when a chat has edited messages? | S1, C0 export | The branch to the newest message. Aren confirmed it for C0 (2026-10-23). T-EXPORT-03. |
| Q-02 | Does the final export after C8 have the same format as the C0 export? | S1, D-012 | Open. T-EXPORT-11, run 2. |
| Q-03 | Is the first model call slower for each new input length, also after one warm-up run? | C2, D-022 | [RUN] No, for these inputs: after call 1, new lengths (2.78–12.17 s of audio, 25–52 tokens) are as fast as old lengths. T-INSTALL-02, T-INSTALL-03. |
| Q-04 | Does the minimum silence put two remote speakers into one segment when they change turns fast? | C2, D-027 | [RUN] Yes. L-06: an interruption and a fast change each gave one segment with two voices; the segment got the label of the voice with more speech (§2.7, D-060). C7 measures a shorter `vad_min_silence_ms` (from 250 ms) and the speaker sweep on a stream with fast changes. |
| Q-05 | Does `vad_min_speech_ms = 250` remove short answers such as "ոչ" or "հա"? | C2, D-026 | Open. C3 recordings with short answers. |
| Q-06 | ASR writes commas where the reference has "։" (T-INSTALL-02). Does the MT quality drop with this ASR text? | C2 | [RUN] C3 bake-off: the opposite. Where the ASR writes «։» between two sentences, NLLB leaves out the second sentence (Q-13); a comma keeps it. `docs/eval/results.md`, finding 2. |
| Q-07 | Is the first CTranslate2 call (5.1 s) a compile step that the driver keeps between program starts [UNVERIFIED]? | C2, D-022 | Open. Run T-INSTALL-03 two times in two processes. [RUN] Data point (T-MODEL-MT-01, 2026-10-25): in a new process, with the cuBLAS preload and no `LD_LIBRARY_PATH`, the first call took 0.126 s. The cause of the 5.1 s in T-INSTALL-03 is not known. |
| Q-08 | A clip can end with less silence than `vad_min_silence_ms` (clip 1: 150 ms). How does the last segment end? | C2, D-027 | D-032: no added silence; the test plays clip 1, then clip 2 (gap 632 ms). T-E2E-01. |
| Q-09 | Is the first segment after a long silence or a pause slower, because the GPU clocks down [UNVERIFIED]? | C2, Aren's warm-up question | [RUN] No, for 76 s of silence: the first total after the silence was 0.61 s, the same as before (L-03, 2026-10-26). |
| Q-10 | Does a long Python step in the worker delay the capture thread (GIL)? | C2, Aren's thread question | [RUN] No, for P1 with two sources: in T-SIM-01, the largest arrival gap was 43.2 ms (`Me`) and 47.8 ms (`System`), under the 64 ms limit, while the worker ran ASR and MT. In L-05, the latency did not grow in 6 min. P4 (C6) and the speaker model (C5) add worker time: check again. [RUN] C5, T-SIM-02: at most 49.5 ms with the speaker model. **C6, T-SIM-03 (P4): 145.0 ms on `Me`, over the 64 ms limit** (P1 in the same run: 49.5 ms). The cause (possibly the Python loop of `generate`, or the 4 torch CPU threads of the test process) and the effect on the audio are [UNVERIFIED]; C7 (D-064).  **C7 [RUN]:** T-SIM-03 alone with 1 torch thread: 134.4 ms, so the threads are not the cause (A2). The diagnostic (D-066 part 2): no full GC pass in a gap; each gap over 64 ms came during a P4 text step call. With `GIL_SWITCH_S` = 1 ms during `run()` (D-067): largest gap 61.0 ms (`Me`), 55.0 ms (`System`); T-SIM-03 passes. No audio was lost in the live P4 call (all 49 lines of S5 are in the output). |
| Q-11 | The default microphone gave 22 samples outside [−1, 1] (min −1.0496) at a source volume of 24 % (probe B). Does the input clip, and does a clipped input change the ASR text? | C2d, probe B | The volume is not over 100 % [RUN]. Possible cause [UNVERIFIED]: a full-scale input and the 48 → 16 kHz conversion. [RUN] C3: `s1.mic.wav` has 500 samples at full scale, the other 5 eval files none; the S1 mic WER (6.8 %, `nemo-rnnt`) is close to the other mic files. D-041 part 4. |
| Q-12 | Do Bluetooth headphones change to the headset mode when an application opens their microphone, and does the call audio then lose quality? | C2d, Aren's recordings | Open [UNVERIFIED]. C4 setup guide: select the laptop microphone in the call application. [RUN] L-05: Bluetooth buds as the output and the laptop microphone as the input worked; the quality of the call audio was not measured. |
| Q-13 | Does NLLB leave out a sentence when one segment has two or more sentences? In the first live run, the EN line of the last block has no translation of «Լավ Սոնա, հետո կզանգեմ, հիմա պիտի գնամ։». | C2d, live run | [RUN] C3: yes. With the ASR text: s1-05, s3-07; with the reference text: also s2-06, s2-07, s3-04. Seamless does not leave out these sentences. D-053 (P4). |
| Q-14 | Noises (coughs, short sounds) of 250 ms or more pass the VAD. Then the ASR gives one letter or a fragment, and NLLB invents a sentence. What can stop these blocks? | C4, L-05 (Aren) | Open. [RUN] L-05: about 11 of 84 blocks have only one letter or a fragment, for example «Հ։» → "A: What is it?" and «Հովհ.» → "John: What is it?"; 10 shorter sounds were removed as short segments. Possible changes (no decision): `vad_threshold`, `vad_min_speech_ms`, a rule for texts with one letter, or P4 (C6). C7 decides with numbers (R6). [RUN] L-06: 3 of 9 `System` lines; a cough as the first segment started a speaker (D-060 part 2). Aren: longer coughs do not pass the VAD. D-060 part 4: C7 measures `vad_threshold`, `vad_min_speech_ms`, and the short-text rule with a new recording of noises and short words. |

## 4. Live checklist (manual)

Only the checks that a sim test cannot do. (C7)

| ID | Check | Expected result | Result |
|---|---|---|---|
| L-01 | Aren says 5 Armenian sentences into the microphone, with a pause after each. | One block for each sentence, label "Me", each total < 5 s (K1). | PASSES (2026-10-26): Script 4, s4-01 to s4-05: 5 blocks, label "Me", totals 0.61–0.64 s. |
| L-02 | Aren presses Ctrl+C. | The shutdown line with the counts. Exit code 0. | Run 1 FAILED (2026-10-26): no reaction (D-044). Run 2 PASSES (2026-10-26, after D-044): the shutdown line, exit code 0. C5, open: in L-06, `terminate called without an active exception` came after the shutdown line; the exit code is not known (exit check, D-060). **FAILS** (exit check, `test-results/c5-exit1.txt`, 2026-10-27, only `Me` lines, no speaker call): the shutdown line, then `Assertion 'pthread_mutex_lock(&m->mutex) == 0' failed at ../src/pulsecore/mutex-posix.c:92, function pa_mutex_lock(). Aborting.`, exit code 134. Cause: the `atexit` function of `soundcard` frees the PulseAudio main loop while the capture threads still record. The fix comes in branch `c5-stop` (D-061). After D-061: **PASSES** (2026-10-27): 3 runs (`c5-exit2.txt` to `c5-exit4.txt`), each with the shutdown line, exit code 0, and no abort line. |
| L-03 | Aren is silent for 60 s, then says one sentence; then he says 3 sentences with short pauses (Q-09). | The total of the first sentence is compared with the next ones. || PASSES (2026-10-26): after 76 s of silence, the total of s4-06 was 0.61 s, the same as before (Q-09). |
| L-04 | `./run.sh --list-devices` (C4, D-054). | The list shows the microphone and the output monitor; the defaults have a `*`; exit code 0; no model load. | Not run in C4. PASSES (2026-10-28, `test-results/c7-l04.txt`): the laptop microphone, two output monitors (analog and Bluetooth), the defaults with `*`, exit code 0, no model load. |
| L-05 | A video call with one person, wired headphones, `./run.sh` with no flags (C4, D-054). | Lines with `Me` and `System` at the same time; Aren still hears the call; each total < 5 s (K1); the two `startup: source` lines name the correct devices. | PASSES (2026-10-26, Bluetooth buds in place of wired headphones): 84 blocks in about 6 min, totals 0.11–0.68 s, no growth; Aren heard the call (§2.6 results). |
| L-06 | A call with 2 or more people on the call side, `./run.sh` with no flags (C5, D-058, D-059). | Each person keeps one label for the full call; no label for two people; count the extra labels from noise (Q-14); each total < 5 s (K1). The result decides `spk_threshold` and `spk_min_new_s`. | FAILS on one point (2026-10-27, D-060): 2 people, about 1 min 15 s; clean turns correct; a first cough gave person A a second label; two segments had two voices (Q-04); totals 0.57–0.70 s. Both parameters kept. C7 runs it again with the D-060 changes. |
| L-07 | A call with 1 or more people on the call side, `./run.sh --seamless`, about 5 min (C6, D-062); `nvidia-smi` logs the GPU power and temperature. | Lines with `Me` and `Speaker N`; each total < 5 s (K1); the totals do not grow during the call; the startup log shows the text step; at the stop, the shutdown line, exit code 0, and no abort line. Report: the GPU power and temperature. | Run (2026-10-27 and 2026-10-28), with no output file. Aren, 2026-10-27: P1 was "miles better" than P4; "the text of both normal, as well as slightly 'artificially clarified' speech, seamless was constantly failing"; "no not really invented lines on noise or silence"; "also seamless gave some #err symbols for some reason". Aren, 2026-10-28 (more tests): "it worked a bit better this time, but I still get #err symbol, as well as english text in armenian transcription". Not recorded; the next chat runs it again with the output in files (D-064).  **C7 (2026-10-28, recorded, D-065):** two calls with script S5, first P1, then P4 (`test-results/c7-live-p1.txt`, `c7-live-p4.txt`, §2.9). P4: lines with `Me` and `Speaker 1`; totals 0.70–0.94 s, no growth; the startup log shows the text step; the shutdown line and no abort line (the pipe hid the exit code); GPU mean 14.1 W, max 24.2 W, max 50 °C. One `#err` (for «Հը», D-066), no English text in an HY line. Scores in D-066. The fixes: D-066 (output rules) and D-067 (GIL). |
