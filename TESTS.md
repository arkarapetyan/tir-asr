# TESTS.md

**Project:** tir-asr · **Date:** 2026-10-25
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
| T-PIPE-01 | F2, F3, F5, §2.6, D-042: end-to-end with fakes. | 111 fake frames: p = 0.9 for frames 5–24 and 60–79, else 0.1. Fake ASR ("բարև"), fake MT ("hi"). Fake clock: session start 0.0; then ASR end, MT end, and write for each segment: 1.400, 1.500, 1.510 and 3.200, 3.300, 3.310. | `run` returns 0. The output is the "Listening" line, then two exact blocks (`[00:00:00]`: `vad 0.51s, asr 0.09s, mt 0.10s, out 0.01s \| Total 0.71s`; `[00:00:01]`: `vad 0.51s, asr 0.13s, mt 0.10s, out 0.01s \| Total 0.75s`), then the shutdown line with 2 segments. The error output is empty. | unit | APPROVED (exact values: D-042, Aren reviews) |
| T-PIPE-02 | R10, §2.6, D-042: an error in a thread. | Three cases: (a) the fake ASR raises a `TirError` subclass with `asr: test`; (b) the fake MT raises `KeyError("x")`; (c) the fake VAD gives 1.2 (capture thread). | `run` returns 1. No block and no shutdown line. The error output is (a) `tir-asr: asr: test`; (b) a traceback, then `tir-asr: worker: KeyError: 'x'`; (c) `tir-asr: segment: probability 1.2 is not in [0, 1]`. | unit | APPROVED (cases b and c are new: D-042, Aren reviews) |
| T-PIPE-03 | D-031: no MT call for an empty text. | The input of T-PIPE-01 with only the first region. The fake ASR returns "". Clock: 0.0, then ASR end 1.400 and write 1.410. | The fake MT gets no call. One exact block: `HY: (no text)` and `vad 0.51s, asr 0.09s \| Total 0.61s`. The shutdown line has 1 segment and 1 empty text. | unit | APPROVED |
| T-PIPE-04 | §2.7, D-042: shutdown line. | 150 fake frames: a normal region (frames 5–24), a short region (frames 60–66, 224 ms), and a region with an empty text (frames 100–119). The fake ASR returns "բարև", then "". Then the source ends. | `run` returns 0. The last output line is exactly `Stopped. Segments: 2, short segments: 1, empty texts: 1, not processed: 0.` | unit | APPROVED (exact text: D-042, Aren reviews) |
| T-PIPE-05 | D-022, D-037, D-042: warm-up. | `warm_up(transcriber, translator, clock)` with a fake clock 10.0, 10.4, 10.5. | The fake ASR gets one call: 32000 zeros, float32. The fake MT gets one call: `WARMUP_TEXT`. The result is (0.4 s, 0.1 s). | unit | APPROVED |
| T-CFG-01 | R10, §6: approved parameters. | `config.py`. | Each value is equal to the §6 table. | unit | PASSES |
| T-CFG-02 | R10, §2.7: parameters in the startup log. | The startup log function. | The startup log has one line for each parameter, with its name and value. | unit | APPROVED |
| T-CLI-01 | §2.7: help. | `tir-asr --help`. | Exit code 0, a usage text, and no model or device import. | unit | APPROVED |
| T-IMPORT-01 | D-021: core modules have no `laptop` import. | Import each core module that exists in the branch, in a new Python process. | `torch`, `nemo`, `ctranslate2`, `silero_vad`, `soundcard`, and `transformers` are not in `sys.modules`. | unit | PASSES (C2b modules, `tir_asr.asr`, `tir_asr.mt`, `tir_asr.output`, and `tir_asr.audio`; later branches add theirs) |

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
| T-E2E-01 | K1, F2, F3, F5, D-025, D-032: full pipeline with the real models. | The test WAV source plays clip 1 and then clip 2 at real-time speed. | 2 blocks in time order, label "Me", no empty text, each total < 5.0 s. | model | APPROVED |

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

## 3. QA questions

We add a question here when we find it during the work (tip T4).

| ID | Question | Source | Answer / test ID |
|---|---|---|---|
| Q-01 | Which branch does the app show when a chat has edited messages? | S1, C0 export | The branch to the newest message. Aren confirmed it for C0 (2026-10-23). T-EXPORT-03. |
| Q-02 | Does the final export after C8 have the same format as the C0 export? | S1, D-012 | Open. T-EXPORT-11, run 2. |
| Q-03 | Is the first model call slower for each new input length, also after one warm-up run? | C2, D-022 | [RUN] No, for these inputs: after call 1, new lengths (2.78–12.17 s of audio, 25–52 tokens) are as fast as old lengths. T-INSTALL-02, T-INSTALL-03. |
| Q-04 | Does the minimum silence put two remote speakers into one segment when they change turns fast? | C2, D-027 | Open. C5 speaker purity of the segments. |
| Q-05 | Does `vad_min_speech_ms = 250` remove short answers such as "ոչ" or "հա"? | C2, D-026 | Open. C3 recordings with short answers. |
| Q-06 | ASR writes commas where the reference has "։" (T-INSTALL-02). Does the MT quality drop with this ASR text? | C2 | Open. End-to-end model test (C2), C3 bake-off. |
| Q-07 | Is the first CTranslate2 call (5.1 s) a compile step that the driver keeps between program starts [UNVERIFIED]? | C2, D-022 | Open. Run T-INSTALL-03 two times in two processes. [RUN] Data point (T-MODEL-MT-01, 2026-10-25): in a new process, with the cuBLAS preload and no `LD_LIBRARY_PATH`, the first call took 0.126 s. The cause of the 5.1 s in T-INSTALL-03 is not known. |
| Q-08 | A clip can end with less silence than `vad_min_silence_ms` (clip 1: 150 ms). How does the last segment end? | C2, D-027 | D-032: no added silence; the test plays clip 1, then clip 2 (gap 632 ms). T-E2E-01. |
| Q-09 | Is the first segment after a long silence or a pause slower, because the GPU clocks down [UNVERIFIED]? | C2, Aren's warm-up question | Open. L-03. |
| Q-10 | Does a long Python step in the worker delay the capture thread (GIL)? | C2, Aren's thread question | Open. Live run (C2 code chat): measure the gaps between block arrivals. |
| Q-11 | The default microphone gave 22 samples outside [−1, 1] (min −1.0496) at a source volume of 24 % (probe B). Does the input clip, and does a clipped input change the ASR text? | C2d, probe B | Open. The volume is not over 100 % [RUN]. Possible cause [UNVERIFIED]: a full-scale input and the 48 → 16 kHz conversion. C3: count the full-scale samples in each eval recording. D-041 part 4. |
| Q-12 | Do Bluetooth headphones change to the headset mode when an application opens their microphone, and does the call audio then lose quality? | C2d, Aren's recordings | Open [UNVERIFIED]. C4 setup guide: select the laptop microphone in the call application. |

## 4. Live checklist (manual)

Only the checks that a sim test cannot do. (C7)

| ID | Check | Expected result | Result |
|---|---|---|---|
| L-01 | Aren says 5 Armenian sentences into the microphone, with a pause after each. | One block for each sentence, label "Me", each total < 5 s (K1). | |
| L-02 | Aren presses Ctrl+C. | The shutdown line with the counts. Exit code 0. | |
| L-03 | Aren is silent for 60 s, then says one sentence; then he says 3 sentences with short pauses (Q-09). | The total of the first sentence is compared with the next ones. | |
