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
| T-INSTALL-05 | D-021: CI installs no `laptop` package. | CI on the next push. | The CI log shows no `torch` install. All CI steps pass. | unit (CI) | APPROVED (waits for the CI run) |

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
| Q-07 | Is the first CTranslate2 call (5.1 s) a compile step that the driver keeps between program starts [UNVERIFIED]? | C2, D-022 | Open. Run T-INSTALL-03 two times in two processes. |
| Q-08 | A clip can end with less silence than `vad_min_silence_ms` (clip 1: 150 ms). How does the last segment end? | C2, D-027 | Open. `segment` contract (C2). |

## 4. Live checklist (manual)

Only the checks that a sim test cannot do. (C7)

| ID | Check | Expected result | Result |
|---|---|---|---|
| | | | |
