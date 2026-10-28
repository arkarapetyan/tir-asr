# PLAN.md: Plan of Completion

**Project:** Live Armenian Transcription to English Translation (Mathrix AI coding challenge)
**Version:** 0.19 · **Date:** 2026-10-28
**Status:** APPROVED by Aren on 2026-10-23 (v0.4). v0.5 applies D-011. v0.6 applies the C1 decisions (D-013 to D-020). v0.7 logs the C1 time. v0.8 applies the C2 decisions (D-021 to D-035) and splits the C2 code work into C2b, C2c, and C2d (D-035). v0.9 logs the C2b time. v0.10 gives the C2c status (D-037 to D-039) and logs the C2c time. v0.11 gives the C2d status (D-040, D-041) and the C2d time so far. v0.12 closes C2d (M1, D-040 to D-045) and logs the C2d time. v0.13 closes C3 (D-046 to D-053) and gives C6 the P4 implementation. v0.14 closes C4 (D-054, D-055; M2 reached) and logs the C4 time. v0.15 applies D-056 (Q16 closed; the C6 scope; C5 before C6). v0.16 closes C5 (D-057 to D-061; M3 reached), adds the C7 work from D-060, and logs the C5 time. v0.17 starts C6 (D-062: the order, the design, the flag, the tests, and the C6 time box). v0.18 closes C6 (D-062 to D-064), gives C7 a first part for P4 (D-064), and logs the C6 time. v0.19 closes C7 (D-065 to D-067).

---

## 1. Goal and requirements

The brief asks for a Python program that listens to a live conversation, transcribes spoken Armenian, and shows an English translation in the terminal.
Each line must show the speaker. Each line must appear within 5 seconds.

### 1.1 Required features

| ID | Feature (from the brief) |
|---|---|
| F1 | Capture two audio sources at the same time: the microphone and the system audio output (the other side of a call). The user selects the devices, with a printed device list or with command-line flags. macOS: BlackHole plus a Multi-Output Device, so that the user still hears the call. Other OS: the equivalent. |
| F2 | Armenian transcription: speech to Armenian text. |
| F3 | English translation of each transcribed segment. |
| F4 | Speaker labels. Microphone: "Me". System audio: "Speaker 1", "Speaker 2", and so on. One person keeps the same label for the full session. |
| F5 | Live terminal output for each segment: time, speaker, Armenian original, English translation. |

### 1.2 Constraints

| ID | Constraint |
|---|---|
| K1 | Latency: maximum 5 s from the end of a spoken phrase to its English line. |
| K2 | Local models only. No cloud speech or translation APIs. |
| K3 | Python. Any local libraries and models. |
| K4 | The program runs on Aren's own laptop at the interview (§1.6). |
| K5 | We choose the models deliberately. The README explains the choices. |

### 1.3 Deliverables

| ID | Deliverable |
|---|---|
| D1 | Source code in a Git repository. |
| D2 | README: setup and run (with the audio device setup); chosen models, alternatives, and reasons; architecture; known limits and improvements. |
| D3 | `chats/`: each chat session, complete and unedited, as one `.md` file per session. |
| — | Do not commit model weights, audio recordings, or API keys. |

### 1.4 Out of scope (binding, RULES.md R15)

GUI, installer, echo handling, speaker names, speaker memory across sessions, transcript files, and input languages other than Armenian.
If we finish early, we make the core more reliable. We do not add features.

### 1.5 Interview

1. Aren starts the program. The interviewers hold a live Armenian conversation with two or more people on the call side.
2. We examine the output together.
3. Aren explains the code and the decisions.
4. Aren opens the original chats in the Claude app.

### 1.6 Target hardware (from Aren, 2026-10-23)

| Item | Value |
|---|---|
| Laptop | Lenovo Legion 5i |
| CPU | Intel Core Ultra 9 275HX |
| GPU | NVIDIA GeForce RTX 5070 Laptop GPU, 8 GB VRAM |
| RAM | 32 GB |
| OS | Ubuntu 26.04.1 LTS **[RUN]** |
| Audio server | PulseAudio on PipeWire 1.6.2 **[RUN]** |
| NVIDIA driver | 595.99.02. The driver supports CUDA up to 13.2. VRAM: 8151 MiB. **[RUN]** |

**[RUN]** means: Aren ran the commands on 2026-10-23. Note: the "CUDA Version" in `nvidia-smi` is the highest CUDA version that the driver supports. It is not an installed CUDA toolkit.

Effects on the plan:

- **F1 on Linux:** the equivalent of BlackHole is the "monitor" source of the audio output device (PipeWire or PulseAudio). The user still hears the call. **[UNVERIFIED]** C1 checks this.
- **GPU:** the RTX 5070 is a Blackwell GPU. **[UNVERIFIED]** It needs recent CUDA builds of PyTorch and of other runtimes. C1 checks each candidate.
- **VRAM:** all models together must fit in 8 GB VRAM, or some models must run on the CPU. C1 and C3 measure this.

---

## 2. MVP and milestones

**MVP:** F1–F5 work end-to-end, live, on Aren's laptop. We measure the latency against K1. A minimal README exists.

| Milestone | What works | Features | Chat |
|---|---|---|---|
| M1 Skeleton | Microphone → speech segments → Armenian text → English text → terminal, label "Me". | F2, F3, part of F5 | C2–C2d |
| M2 Two sources | Microphone and system audio at the same time. Device selection. Lines show "Me" or the system side. | F1 | C4 |
| M3 **MVP** | Speaker labels on the system side. All required features work. | F4, F5 | C5 |
| M4 Reliable | The weakest links are better. A live test with two or more people passes. Latency is measured. | — | C7 |
| M5 Delivered | README complete. All chats exported. Rehearsal done. | D1–D3 | C8 |

---

## 3. Where things are

| Place | Contents | Who uses it |
|---|---|---|
| GitHub repository (**source of truth**, owned by Aren) | Code, tests, all project `.md` files, handovers, `chats/` | Aren (all git operations), CI. Claude does not use it (D-005). |
| Project folder on Aren's laptop: `/home/aren/dev/armenian-asr` | The git working copy. Test result files in `test-results/` (D-006). | Aren. Claude reads and writes **only in this folder** (D-005). |
| Claude Project "armenian asr", documents | Copies of `RULES.md`, `PLAN.md`, `DECISIONS.md`, `ARCHITECTURE.md` | Each new chat in the Project |
| Claude cloud workspace (one for each chat) | Claude's scratch space. Claude runs `ruff` and unit tests on a copy before Aren's official run (D-006). | Claude |
| Aren's laptop | git, models, audio devices, all official test runs, live tests, the interview | Aren |

Facts that affect this setup (checked on 2026-10-23 in chat C0):

- **[RUN]** The cloud workspace can reach PyPI. It cannot reach `huggingface.co` (the proxy returns HTTP 403). Thus Claude cannot download models in the workspace.
- **Result:** The tests run on Aren's laptop. Aren runs them, and the result goes into a file that Claude reads (D-006).
- **[RUN]** Aren granted this chat access to the project folder on 2026-10-23. A grant is for one chat only. Thus each new chat must ask for access again (§7.2).
- The workspace of each chat is separate. A new chat gets the code from the project folder.

---

## 4. Repository layout (D-007, D-008)

```
tir-asr/                    # local folder: /home/aren/dev/armenian-asr
├── pyproject.toml          # uv project, ruff and pytest configuration
├── uv.lock
├── README.md               # D2
├── RULES.md  PLAN.md  DECISIONS.md  ARCHITECTURE.md  TESTS.md
├── .github/workflows/ci.yml
├── .gitignore              # blocks weights, audio, .env, data/
├── src/tir_asr/
│   ├── cli.py              # argparse only (D-037, D-043)
│   ├── app.py              # loads the adapters, startup log (D-042, D-043)
│   ├── errors.py           # TirError, the base class of the module errors (D-042)
│   ├── config.py  types.py # parameters and constants; data types
│   ├── audio/              # capture of microphone and system audio
│   ├── segment/            # VAD (voice activity detection) → speech segments
│   ├── asr/                # segment → Armenian text
│   ├── mt/                 # Armenian text → English text
│   ├── speakers/           # segment → speaker label (system side)
│   ├── pipeline.py         # connects the modules: threads and queues
│   └── output.py           # terminal lines
├── eval/                   # scripts that make the eval set and compute metrics
├── data/                   # local only, in .gitignore
├── tests/{unit,model,sim}/ # the live checklist is in TESTS.md
├── tests/support/          # test code only: the WAV source (D-025)
├── scripts/                # tools outside the package: export_chats.py, probe_audio.py, probe_sigint.py
├── run.sh                  # the launcher (D-045)
├── docs/research/RESEARCH.md
├── docs/handovers/NN-<phase>.md
└── chats/NN-<phase>.md     # D3
```

---

## 5. Phases and chats

Phase order: option B, skeleton first (D-002).

### 5.1 Overview

| Chat | Name | Main output | Milestone | Time box |
|---|---|---|---|---|
| C0 | Kickoff and repository setup (this chat) | Approved RULES and PLAN; repository with uv, ruff, pytest, CI; document templates | — | 1.5 h |
| C1 | Research | `RESEARCH.md`; first candidates and shortlists in `DECISIONS.md` | — | 2.5 h |
| C2 | Walking skeleton: install check and design | Install check; module contracts; test design | — | 3 h |
| C2b | Skeleton code: `types` + `segment` | `Endpointer` and Silero adapter, with their tests | — | 1 h |
| C2c | Skeleton code: `asr` + `mt` adapters | NeMo and CTranslate2 adapters (warm-up, cuBLAS preload), with their tests | — | 1 h |
| C2d | Skeleton code: `audio` + `output` + `pipeline` + `cli` | Microphone → terminal; end-to-end test; live run | M1 | 1.5 h |
| C3 | Evaluation set and bake-off | Eval scripts and metrics; numbers for the ASR and MT shortlists | — | 2.5 h |
| C4 | Two audio sources | Device list, flags, system audio capture, virtual devices for sim tests, setup guide | M2 | 2 h |
| C5 | Speaker labels | Speaker embeddings, online clustering, stable labels | **M3 (MVP)** | 3 h |
| C6 | Weakest link: P4 | Seamless end to end in the program behind a flag, P1 the default; P4 optimizations; P4 performance and live tests (D-053, D-056) | — | 3.5 h (D-062) |
| C7 | Live test and reliability | Live test with two or more people; error behaviour check; latency report; the D-060 measurements (VAD for fast changes and noises) and the speaker diagnostic line | M4 | 1.5 h |
| C8 | Delivery | Full README, `chats/`, rehearsal checklist | M5 | 1 h |
| S1 | Side chat: export format | Format of the full data export; converter decision, if necessary (D-011) | — | 0.5 h |
| — | Buffer | — | — | 1 h |
| | **Total** | | | **25.5 h** |

ASR: automatic speech recognition. MT: machine translation.

**Note (C2 to C2d, R16):** D-035 adds 3.5 h. With the actual times of C0 to C2d, the expected total is about 23.9 h, or 24.6 h with the buffer (calc: C2c 0.97 h and C2d 2.92 h, against 1.0 h and 1.5 h), which is more than the "about 20 hours" of the brief. R16: we cut the scope back to the MVP. C6 (weakest link, after the MVP) is the first item to cut. Aren decides.

**Note (after C5, R16):** C5 took about 4.4 h, 1.4 h over its time box (§11). C0 to C5 took about 19.4 h (calc: 14.95 + 4.4). With the time boxes of C6 to C8 (4.5 h), the expected total is about 23.9 h, more than the "about 20 hours" of the brief. C6 is still the first item to cut. Aren decides.

**Note (C6 start, R16):** Aren keeps C6 with a time box of 3.5 h for the full D-056 scope (D-062 part 11). The expected total is now about 25.4 h (calc: 19.35 + 3.5 + 1.5 + 1.0).

**Note (C7 end, R16):** C7 took about 1.7 h (Aren confirmed), about 0.1 h over its time box (1.5 h, plus 10 min for the calls). C0 to C7 took about 22.5 h (calc: 20.77 + 1.7). With C8 (1 h), the expected total is about 23.5 h.

**Note (C6 end, R16):** C6 took about 1.4 h, under its time box (§11). C0 to C6 took about 20.8 h (calc: 19.35 + 1.42). With C7 and C8 (2.5 h), the expected total is about 23.3 h. Aren wants to wrap up the project; C7 first settles P4 (D-064), and Aren decides the rest of the C7 scope.

### 5.2 Details for each chat

#### C0. Kickoff and repository setup (this chat)

- **Goal:** Agree on the rules and the plan. Set up the repository.
- **Steps:**
  1. Claude writes the drafts of `RULES.md` and `PLAN.md`. *(done)*
  2. Aren reviews them. Claude writes the changes. Aren approves RULES v0.3 and PLAN v0.4. *(done)*
  3. We decide D-005, D-006, D-007, and the name of the application (D-008). *(done)*
  4. Aren makes the GitHub repository with the chosen name, and connects it to the project folder.
  5. Claude writes the setup files into the project folder: uv project, ruff, pytest markers, `.gitignore`, CI workflow, and templates for `ARCHITECTURE.md`, `TESTS.md`, and `README.md`. *(done; Aren added `ci.yml`, because the remote tools cannot write into `.github/workflows/`)*
  6. Claude gives Aren the commands to run (`uv sync`, `ruff`, `pytest`) and the commit message.
  7. Aren runs the commands. The result goes into `test-results/`. Claude reads it. *(done: all checks pass)*
  8. Aren reads `git diff`, commits, and pushes. CI must be green. *(done after the D-010 fix)*
  9. Aren requests the full data export, to learn its format (D-011). The format check is in the side chat S1. *(changed)*
  10. Claude writes handover H0 and copies the documents into the Project. *(done)*
- **Decisions:** D-001 to D-008.
- **Done when:** RULES and PLAN v0.2 are confirmed. CI is green on the first commit. The export method is known.

#### C1. Research

- **Goal:** Collect facts about candidate models, libraries, and data. No decisions during research (R8).
- **Read list:** H0, `PLAN.md` §1 and §6, `DECISIONS.md`.
- **Steps:**
  1. Research each question in §6. Mark each fact [SOURCE], [RUN], or [UNVERIFIED].
  2. Write `docs/research/RESEARCH.md`: one table for each component, with sources.
  3. Discuss the facts.
  4. Decide for each component:
     - the **first candidate** for the skeleton (C2),
     - the **shortlist** for the bake-off (C3): max. 3 ASR, max. 3 MT, max. 3 speaker models, 1–2 VAD options,
     - the eval data, the audio capture library, and the virtual device method for sim tests.
- **Done when:** `RESEARCH.md` has a table with sources for each component. The decisions are ACCEPTED in `DECISIONS.md`.

#### C2. Walking skeleton: install check and design

- **Goal:** Install check of the first candidates. Module contracts and test design for the thinnest end-to-end path: microphone → VAD → ASR → MT → terminal, label "Me".
- **Steps:**
  1. **Install check first** (mitigation for D-002). *(done: T-INSTALL-01 to T-INSTALL-05 pass)*
     - ASR: ASR-1 on NeMo (RNNT). If NeMo does not install, ASR-1 on ONNX Runtime with the CTC head (D-014). *(NeMo works)*
     - MT: NLLB-200-distilled-600M on CTranslate2 with `mt_compute_type = float16`, with the CUDA 12 libraries next to the CUDA 13 build of PyTorch (D-015, D-016). Also time the same sentences on PyTorch. *(done)*
     - Aren downloads the model weights before C2 into the normal Hugging Face cache (C1 commands). *(done)*
  2. Write the module contracts and the data types in `ARCHITECTURE.md`. *(done: v0.3, approved)*
  3. Design the tests in `TESTS.md`. Aren reviews them. *(done: §2.4, approved)*
  4. Steps 4 to 6 of the first plan (code, end-to-end test, live run) moved to C2b, C2c, and C2d (D-035).
- **Decisions:** D-021 to D-035. The two "decisions needed" of the first plan are D-025 (WAV source only for tests) and D-024 (latency on each line).
- **Done when:** the install check passes, and Aren approves the contracts and the tests. *(done)*

#### C2b. Skeleton code: `types` + `segment`

- **Goal:** `types.py` (`ARCHITECTURE.md` §3), the core `Endpointer` and the Silero adapter (§2.2).
- **Read list:** `docs/handovers/02-skeleton-design.md`, `RULES.md`, `ARCHITECTURE.md` (§2.2, §3, §5, §6), `TESTS.md` (§2.4).
- **Branches (R3, Aren 2026-10-25):** one branch for each component, with its own tests. Aren merges a branch into `main` only when its tests pass on their own and CI is green. The next branch starts from the new `main`.

  | Branch | Component (files) | Tests |
  |---|---|---|
  | `c2b-segment` | `segment/endpoint.py`, `segment/silero.py`, with the shared `types.py` and `config.py` (first user) | T-SEG-01 to T-SEG-09, T-CFG-01, T-IMPORT-01 (unit); T-MODEL-VAD-01 (model) |

- **Done when:** the tests pass on Aren's laptop and in CI, and the branch is merged. *(The tests pass on Aren's laptop, 2026-10-25. Aren merges the branch at the end of C2b.)*

#### C2c. Skeleton code: `asr` + `mt` adapters

- **Goal:** the NeMo RNNT adapter and the CTranslate2 NLLB adapter (§2.3, §2.4): warm-up (D-022), cuBLAS preload (D-030), error messages (§7).
- **Branches (R3, Aren 2026-10-25):** one branch for each component, with its own tests. Aren merges a branch into `main` only when its tests pass on their own and CI is green. The next branch starts from the new `main`.

  | Branch | Component (files) | Tests |
  |---|---|---|
  | `c2c-asr` | `asr/nemo_rnnt.py` | T-MODEL-ASR-01, T-MODEL-ERR-01, T-MODEL-ERR-03 (model); T-IMPORT-01 (unit) |
  | `c2c-mt` | `mt/ct2_nllb.py` | T-MODEL-MT-01, T-MODEL-ERR-02, T-MODEL-ERR-04 (model); T-IMPORT-01 (unit) |

- **Done when:** the tests pass on Aren's laptop, and both branches are merged. T-MODEL-MT-01 runs with no `LD_LIBRARY_PATH`. *(The tests pass on Aren's laptop, 2026-10-25; `c2c-asr` is merged (`b8871a0`). Decisions: D-037 to D-039. Aren merges `c2c-mt` at the end of C2c.)*

#### C2d. Skeleton code: `audio` + `output` + `pipeline` + `cli`

- **Goal:** the microphone adapter, the line format, the threads and the queue, the startup and the stop (§2.1, §2.5–§2.7, §4). Then M1.
- **Branches (R3, Aren 2026-10-25):** one branch for each component, with its own tests. Aren merges a branch into `main` only when its tests pass on their own and CI is green. The next branch starts from the new `main`.

  | Branch | Component (files) | Tests |
  |---|---|---|
  | `c2d-output` | `output.py` | T-OUT-01 to T-OUT-04, T-IMPORT-01 (unit) |
  | `c2d-audio` | `audio/soundcard_mic.py` | T-AUDIO-01 to T-AUDIO-03 (sim, D-041); T-IMPORT-01 (unit) |
  | `c2d-pipeline` | `pipeline.py` | T-PIPE-01 to T-PIPE-04, T-IMPORT-01 (unit) |
  | `c2d-cli` | `cli.py` | T-CLI-01, T-CFG-02, T-IMPORT-01 (unit); T-E2E-01 (model); L-01 to L-03 (live) |

- **Done when:** M1 works on Aren's laptop, and all four branches are merged. Each line shows its latency (K1).
- **Status (2026-10-26): done, M1 reached.** `c2d-output` merged (`ab0820f`, D-040); `c2d-audio` merged (`b363fed`, D-041: T-AUDIO-01 became a sim test with a null sink, after two probes); `c2d-pipeline` merged (`2bfd7b3`, D-042); `c2d-cli` merged at the end of C2d (D-043 to D-045). T-E2E-01: each total about 0.6 s (K1). L-01 to L-03 pass; L-02 passed after the fix D-044 (Ctrl+C). The launcher is `./run.sh` (D-045).

#### C3. Evaluation set and bake-off

- **Goal:** Make a small eval set. Compare the ASR and MT shortlists with numbers on Aren's laptop. Change the skeleton models only if a different candidate wins.
- **Steps:**
  1. Design and write the tests for the metric code (TDD). First write the Armenian text normalization rules for WER/CER (punctuation, case, numbers, and orthographic variants) and their tests.
  2. Write the scripts that make the eval set. The data stays local (`data/`, in `.gitignore`).
  3. Write the metrics: CER/WER, chrF, latency, RTF (real-time factor: processing time divided by audio duration), and VRAM use.
  4. Aren records 20 short Armenian phrases with the microphone and writes the Armenian and the English reference text (D-019).
  5. Aren runs the bake-off. Claude makes the results table.
  6. We decide the ASR model and the MT model.
- **Eval set (D-019 with its amendment):**
  - ASR and MT: at least 20 recordings with several voices and several devices, from 4 conversation scripts. Aren's Armenian and English reference text. No public eval set.
  - Some recordings go through a real call and come from the monitor source (call-path audio). The resample step to 16 kHz mono has a test.
  - C5: the 3-person script and other recordings that Aren makes with other people.
- **Shortlists:** ASR (D-014), MT (D-015).
- **Done when:** The results table exists. D-ASR and D-MT are ACCEPTED.
- **Result (2026-10-26):** done. The eval tools are `tir_asr.eval` (normalize, metrics, data, run) and `scripts/bakeoff.py` (D-046 to D-051). The eval set is S1–S3 (34 lines, two sides each), with Aren's labels. The results table is `docs/eval/results.md`. D-ASR and D-MT: D-053, P4 (Seamless end to end) on the GPU. ONNX-CTC was not run (D-052).

#### C4. Two audio sources

- **Goal:** Capture the microphone and the system audio at the same time, with device selection.
- **Steps:**
  1. Write the setup guide for the system audio capture on Ubuntu (from the C1 research). The guide says: use wired headphones (echo handling is out of scope, §1.4).
  2. Write the script that makes the virtual devices for sim tests.
  3. Design the tests:
     - unit: device list output, flag parsing, a clear error for a missing device (no fallback),
     - sim: two eval streams play into two virtual devices; check the source labels and the time order of the lines.
  4. Write the tests, then the code.
  5. Aren does a live check with a video call.
- **Done when:** M2 works: lines from both sources appear at the same time, with the correct source.
- **Status (2026-10-26): done, M2 reached.** Branches `c4-audio`, `c4-pipeline`, `c4-cli` (D-054; no red run, D-055). The flags `--mic`, `--system`, `--list-devices`; the source labels `Me` and `System`; one capture thread for each source. T-SIM-01 (S1 into two null sinks) and L-05 (a video call, about 6 min, 84 blocks, totals 0.11–0.68 s with no growth) pass. L-04 was not run. Setup guide: `docs/setup-audio.md`.
- **Data from L-05 for later chats:** noises of 250 ms or more give blocks with one letter, and NLLB invents a sentence (Q-14, C7); 2 hard cuts at 10 s (Q15); Aren: P1 "fails frequently, especially on translation" (D-053, C6).

#### C5. Speaker labels

- **Goal:** Label different people on the system side as "Speaker 1", "Speaker 2", and so on. Each person keeps the same label for the full session.
- **Steps:**
  1. Design the tests with the multi-speaker eval streams. Metric: label accuracy after the best mapping of labels to true speakers.
  2. Compare the speaker shortlist with numbers (model tests).
  3. Write the code: speaker embedding for each segment, then online clustering.
  4. Aren sets the clustering threshold from the eval numbers (R10: parameters need Aren's approval).
  5. Sim test: a multi-speaker stream plays into the virtual call device.
  6. Aren does a live check.
- **Order (D-056):** C5 comes before C6, because C5 does not depend on P4.
- **Rule (D-056):** the speaker step is its own component, with its own interface and one call in the worker, separate from the text step (ASR and MT). Then C6 changes only the text step.
- **Done when:** M3 works. All required features F1–F5 work live. **This is the MVP.**
- **Status (2026-10-27): done, M3 reached** (D-060 part 7). Branches `c5-d056`, `c5-cluster`, `c5-embed`, `c5-pipeline`, `c5-stop` (D-056 to D-061; no red run, D-057 part 8).
  - Speaker model and rule (D-058): TitaNet-large with online centroids (rule A); `spk_threshold` = 0.50, `spk_min_new_s` = 1.0 s. The sweep on S1, S2, S3, and stream D: 0 wrong labels from 0.40 to 0.60. ECAPA and WeSpeaker also passed; their packages left the project.
  - Program (D-059, D-060): the speaker step in the worker after MT, only for `System` lines with a text; the latency step `spk`; a short first segment gets `Unidentified`.
  - Tests: T-SIM-02 (stream D with 4 people) 19 of 19 labels correct. L-06 (a call with 2 people, about 1 min 15 s) fails on one point: a first cough gave a person a second label (fixed by D-060). Clean turns were correct; totals 0.57–0.70 s.
  - Stop (D-061): the exit check found an abort at the stop (exit code 134, PulseAudio). Cause: the `atexit` function of `soundcard` and the capture threads that still recorded. Fix: the clean stop in `run()`.
- **Data from C5 for later chats:**
  - A fast change of speaker or an interruption (less than 0.5 s of silence) gives one line with two voices and the label of the voice with more speech (Q-04). C7 measures a shorter `vad_min_silence_ms` (D-060 part 3).
  - Noises: 3 of 9 `System` lines in L-06 (Q-14). C7 measures the VAD options with a new recording (D-060 part 4).
  - The speaker step stays its own component (D-056 rule): C6 changes only the text step. The clean stop waits `STOP_JOIN_S` (2.0 s) for the worker: C6 checks this limit against the P4 call times.

#### C6. Weakest link

- **Goal (D-053):** implement P4 in the program: one Seamless model (`SeamlessM4Tv2ForSpeechToText`, float16, GPU) gives the HY line and the EN line from the audio of each segment. The P1 code stays. The C3 numbers chose this improvement: WER 10.6 → 6.8 %, chrF 51.7 → 59.0, no left-out sentences (Q-13).
- **Order (D-056):** after C5 (M3).
- **Design (Aren, 2026-10-26):** one pipeline that is suitable for both P1 and P4, with OOP abstraction and the Template Method pattern.
- **Scope (D-056):**
  1. P4 in the program, mainly for the GPU. P1 stays the default; a flag starts the program with P4 (name and form: C6, R10).
  2. All possible optimizations of P4 for the CPU and for the GPU, for example one encoder pass for the HY line and the EN line, and INT8 if the quality drop is acceptable (measured, R6).
  3. A separate performance test of P4 alone, and a live test of P4.
  4. No custom ONNX implementation of P4 for now.
- **Open for C6 (D-056, questions 1 to 5):** a CPU mode of P1; INT8 on the GPU; the reuse of the encoder output; the 36.4 s line of the CPU probe; a new time box.
- **Status (2026-10-28): done** (D-062 to D-064). Branches `c6-d062`, `c6-probe`, `c6-textstep`, `c6-seamless`, `c6-cli`.
  - Result: P4 is in the program behind `--seamless` (variant V2, one latency step `s2t`), as experimental; P1 stays the default. T-PERF-P4-01: WER 7.1 %, chrF 59.0, line time 0.334 s mean, 0.426 s maximum on the GPU. No INT8 on the GPU (a batch of two costs 1.02 times a batch of one); no CPU mode (D-063 part 4).
  - T-SIM-03 (P4) fails on its point (5): a capture gap of 145 ms (Q-10). The P4 lines through the capture path are correct.
  - L-07 (live, no output files): P4 fails on normal and clear speech, with `#err` symbols and English text in the HY line; P1 is much better. The optimization is not the cause (the probe shows the same texts for V0 and V2). The next chat finds the cause, does a recorded live test of P1 and P4, and makes the final P4 decision (D-064).
  - The plan items below are the original C6 plan.
  - Order: measure first (R6), then build. Branches `c6-d062`, `c6-probe` (`scripts/probe_p4.py`; then D-063 selects the P4 variant), `c6-textstep`, `c6-seamless`, `c6-cli`. No separate red run.
  - Design: a Template Method text step (`TextStep`) with `CascadeTextStep` (P1) and `SeamlessTextStep` (P4); the latency line keeps `asr` and `mt`; the flag `--seamless`; with P4, NeMo ASR and NLLB do not load; the speaker step and `STOP_JOIN_S` do not change.
  - INT8 on the GPU: no measurement, if the probe shows that a batch of two costs little more than a batch of one. CPU mode: a device flag only if the CPU numbers meet K1; else the README states the limits.
  - Tests: `TESTS.md` §2.8. Time box: 3.5 h.

#### C7. Live test and reliability

- **Goal:** A full live test with two or more people on the call side.
- **First part (D-064):** find the cause of the P4 problems (the `#err` text, English text in the HY line, the capture gap of T-SIM-03); a full live test of P1 and P4 with the output in files; then the final decision on P4 (keep, fix, or remove). Then the rest of C7 in the scope that Aren decides (R16).
- **Steps:**
  1. Run all sim tests. Then run the live checklist in `TESTS.md`.
  2. Write the latency report.
  3. Check the error behaviour: a missing device and a missing model must give a clear error.
  4. Fix the problems that we find.
  5. The work from D-060 (C5), with numbers (R6):
     - the speaker diagnostic line (a flag; one line on stderr for each `System` segment: the speech length, the similarities, the decision), before the live test;
     - `vad_min_silence_ms` from 250 to 500 ms on S1–S3 (WER, chrF, segment count and lengths), and the speaker sweep on a new stream with fast changes (made from the S1–S3 turns); a separate value for the System side is possible;
     - `vad_threshold`, `vad_min_speech_ms`, and a rule for texts with one or two letters, with a new recording of noises and short words;
     - L-06 again with 2 or more people, about 5 min; `spk_threshold` and `spk_min_new_s` again.
- **Done when:** M4 works.
- **Result (C7, D-065 to D-067):** scope A (D-065). Two recorded calls with the new script S5 (P1, then P4) and `scripts/score_live.py`. `#err` is the hesitation mark of the model; the output rules of `text/clean.py` remove it and show only Armenian text in the HY line and only English text in the EN line, with `[?]` for a word in another script (D-066). The capture gap of P4 came from the GIL; `GIL_SWITCH_S` (1 ms) during `run()` fixes it, and T-SIM-03 passes (D-067). No block for an empty text (D-031). L-04 passes. Not done (R16): the speaker diagnostic line, the D-060 VAD measurements, and L-06 again; the README states these limits. P1 stays the default. **M4:** the weakest links are better and the latency is measured, but the live test had one person on the call side (the goal says two or more), and L-06 did not run again; Aren decides if M4 counts as reached.

#### S1. Side chat: export format

- **Goal:** Learn the format of the full data export. Decide if a converter to one `.md` file for each chat is necessary (D-011).
- **Read list:** `docs/handovers/00b-export-format.md`, `RULES.md` R15, `DECISIONS.md` D-011.
- **Input from Aren:** the file names in the export and the keys of one conversation. Not the content of other chats.
- **Done when:** we know the export method for C8. If a converter is necessary, it exists and has tests.

#### C8. Delivery

- **Goal:** Complete D1–D3.
- **Steps:**
  1. Write the README from `DECISIONS.md`, `ARCHITECTURE.md`, and the measured numbers.
  2. Write the known limits honestly. Known limits found so far:
     - Eastern Armenian only (D-013).
     - Each segment is translated alone. Armenian "նա" can be "he" or "she", and the MT must guess. Context, or a fixed "he/she" output, is a possible C6 item.
     - When two remote people speak at the same time, the segment gets one label (D-017).
  3. Check each item in §1 against the result.
  4. Aren does a rehearsal of the interview start: install, audio setup, run.
  5. **Last step, after Claude's last message:** Aren requests the full data export and puts each project chat into `chats/` as one `.md` file (with the converter from S1, if necessary). Then Aren commits and pushes.
- **Done when:** M5. Aren sends the repository link.

---

## 6. Research questions for C1

### 6.1 ASR (speech → Armenian text)

- **Candidates from Aren:** `nvidia/stt_hy_fastconformer_hybrid_large_pc`; the ArmBench-ASR leaderboard (`Metric-AI/ArmBench-ASR`).
- **Other candidates to examine:** the Whisper family and Armenian fine-tunes of it, Meta MMS, Meta Omnilingual ASR, SeamlessM4T v2, and newer models that the research finds.
- **Questions:**
  1. What is the WER/CER on Armenian test data (ArmBench, FLEURS, Common Voice)? Which test sets did each model see in training?
  2. Does the model run on an RTX 5070 (Blackwell) with Ubuntu? What is the install path, the RTF, and the VRAM use?
  3. Does the model add punctuation? Does the MT model need it?
  4. What is the licence?

### 6.2 MT (Armenian text → English text)

- **Candidate from Aren:** `Helsinki-NLP/opus-mt-hy-en`.
- **Other candidates to examine:** NLLB-200 (distilled sizes), M2M-100, MADLAD-400, SeamlessM4T v2 (text input), and small local LLMs with Armenian support.
- **Questions:**
  1. What is the chrF/BLEU on FLORES-200 (Armenian → English)?
  2. What is the speed and the VRAM use on Aren's GPU? Can CTranslate2 or a similar runtime make it faster? Does that runtime support Blackwell?
  3. How does the model handle ASR errors and missing punctuation?
  4. What is the licence?

### 6.3 Architecture option: cascade or end-to-end

- **Cascade:** ASR → MT, two models.
- **End-to-end:** one model that translates speech directly (for example SeamlessM4T v2).
- **Note:** The brief also requires the Armenian text. Thus an end-to-end model must also do ASR.
- **Question:** Compare the quality, the latency, and the memory of the two options.

### 6.4 Speaker labels (system side only)

- **Problem statement:** The microphone side is "Me" because of the channel. The system side needs online speaker clustering: a new segment gets an existing label or a new label. Offline diarization of separate chunks gives labels that are not stable across chunks.
- **Candidates to examine:** pyannote (embedding models and pipelines), SpeechBrain ECAPA-TDNN, WeSpeaker, NVIDIA TitaNet, NVIDIA Sortformer (streaming), and diart (online diarization).
- **Hypothesis H-S1 (Aren's point; D-003):** Speaker embedding models trained on other languages can lose accuracy on Armenian speech. Fine-tuning can help.
  - **Claude's current view [UNVERIFIED]:** Speaker embeddings depend more on the voice and the audio channel than on the language. A language mismatch can still cause some loss. C1 must find sources for both sides.
  - **Test:** Measure the label accuracy on the Armenian multi-speaker eval streams in C5. Fine-tune only if the numbers fail and time allows.
- **Questions:**
  1. Is there published evidence on the cross-lingual loss of speaker embeddings? Are there Armenian results?
  2. Is there Armenian speech data with speaker IDs (for example, Common Voice `client_id`), for evaluation and, if necessary, for fine-tuning?
  3. What is the minimum segment length for a reliable embedding?
  4. Do the models need a Hugging Face token or the acceptance of terms (gated models)? What is the licence?

### 6.5 VAD and segmentation

- **Candidates:** Silero VAD, WebRTC VAD, pyannote segmentation.
- **Questions:** Which settings (minimum silence, maximum segment length) give the best balance between latency (K1) and complete phrases? (Aren approves the final values, R10.)

### 6.6 Audio capture on Ubuntu

- **System audio:** the monitor source of the output device (PipeWire or PulseAudio).
- **Python libraries to examine:** `sounddevice`, `soundcard`, and others.
- **Questions:**
  1. Which library can read two devices at the same time on Ubuntu, with one clock for the timestamps?
  2. Can we make virtual devices for sim tests (for example, a null sink and its monitor source), and play audio into them from a script?
  3. Do the virtual devices behave like real devices for the capture library?

### 6.7 Eval data

- **Candidates:** FLEURS `hy_am` (parallel English text through FLORES), Common Voice `hy-AM` (speaker IDs), the ArmBench test sets.
- **Questions:** What are the licence, the size, and the access method? Do the parallel English references exist for each clip?

### 6.8 GPU and memory budget

- **Questions:**
  1. Which PyTorch and CUDA versions support the RTX 5070?
  2. Do NeMo, pyannote, CTranslate2, and the other candidate runtimes work with those versions?
  3. What is the total VRAM use of ASR + MT + VAD + speaker model at the same time?

---

## 7. Context between chats

### 7.1 Handover template: `docs/handovers/NN-<phase>.md`

```markdown
# Handover NN → NN+1  (<phase name>)
Date:
Goal of the next chat:
Current state: what works, test status (unit / model / sim), last commit hash on main.
Decisions made in this chat: IDs in DECISIONS.md.
Open questions:
Read list for the next chat (max. 5 files):
First task in the next chat:
Do not: known traps and failed approaches.
```

### 7.2 Start of a new chat

1. Aren opens a new chat in the Project "armenian asr".
2. Aren pastes the handover text as the first message.
3. Claude asks for access to the project folder `/home/aren/dev/armenian-asr` (D-005). Aren approves the prompt.
4. Claude does the chat start checklist (RULES.md §5.1). Claude reads only the files in the Read list.

### 7.3 Project documents

- The Project holds copies of `RULES.md`, `PLAN.md`, `DECISIONS.md`, and `ARCHITECTURE.md`.
- Git is the source of truth. At the end of each chat, Claude copies the changed files into the Project.
- We keep these files short, because each chat in the Project can see them (T6).

### 7.4 Project instructions

Aren added the Project instructions on 2026-10-23. *(done)*

---

## 8. Calendar

No calendar (Aren's decision, 2026-10-23). We record the time only (RULES.md R16, §11).

---

## 9. Risks

| ID | Risk | Effect | Mitigation |
|---|---|---|---|
| RK1 | Armenian ASR quality is low. | The English text is not understandable. | Bake-off with numbers in C3. Honest limits in the README. |
| RK2 | Latency is more than 5 s on Aren's hardware. | K1 fails. | Measure RTF in C2 and C3. Smaller models. Tune the segment parameters with numbers. |
| RK3 | A model or library does not install on Aren's laptop (for example NeMo or pyannote). | Lost time. | Install check is the first step of C2. Keep a second candidate on each shortlist. |
| RK4 | System audio capture on Ubuntu does not work as expected. | F1 fails or is late. | Research in C1. Sim and live checks in C4. |
| RK5 | Speaker labels are not stable for short segments. | F4 fails. | Measure the minimum segment length in C5. Document the limit. |
| RK6 | Gated models need a Hugging Face token. | Setup fails at the interview. | The token stays in a local `.env` file, never in git. The README gives the setup steps. |
| RK7 | The cloud workspace cannot download models (§3). | Claude cannot run model tests. | Model and sim tests run automatically on Aren's laptop (D-006). Aren pastes the result. |
| RK8 | The chat export method is not known. | D3 is late or incomplete. | Learn the export format early, in S1. Final export after the last message of C8 (D-011). |
| RK9 | The brief names "Claude Cowork". The Cowork capabilities are now a part of the Claude app. | An interviewer can ask about the tool. | We do all work in this Project in the Claude app. Aren can confirm with Mathrix if he is not sure. |
| RK10 | Time overrun. The brief gives one week from receipt, and we have no calendar. | Missing features or a late delivery. | Time boxes and a time log. Cut back to the MVP. Respect the "Out of scope" list. |
| RK11 | Context loss between chats. | Decisions are made again; work is done again. | Handovers, `DECISIONS.md`, Project documents. |
| RK12 | Some model licences are non-commercial. | A question at the interview. | Record each licence in `RESEARCH.md` and in the README. |
| RK13 | A runtime does not support the Blackwell GPU (RTX 5070). | A model runs only on the CPU, or does not run. | Research in C1 (§6.8). Install check in C2. |
| RK14 | All models together need more than 8 GB VRAM. | Out-of-memory error, or a model must run on the CPU. | Measure the VRAM use in C2 and C3. Choose the device for each model with numbers. |

---

## 10. Open questions

### 10.1 Answered on 2026-10-23

| ID | Question | Answer (Aren) |
|---|---|---|
| Q1 | Interview laptop | See §1.6. |
| Q2 | GitHub repository | Aren runs the repository. Claude tells Aren when to commit and push (D-004). |
| Q3 | Dates | No calendar. Record the time only. |
| Q4 | Phase order | Option B, skeleton first, because it follows tip T2 more closely (D-002). |
| Q5 | Rules C1–C3 (now R14–R16) | Approved. |
| Q7 | D-005: change transfer | Claude reads and writes only in `/home/aren/dev/armenian-asr`. Claude does not need the GitHub repository. |
| Q8 | D-006: model and sim tests | Aren runs all tests. The results go into files in the project folder. Claude reads them. |
| Q9 | D-007: tool baseline | Approved. Some items are provisional. |
| Q10 | Repository access | Not necessary (D-005). |
| Q11 | Laptop facts | See §1.6. |
| Q12 | Name | `tir-asr` (D-008). |
| Q13 | Claude's own test runs | Yes. Claude runs `ruff` and unit tests on a copy in the workspace. Aren's run is the official result (D-006). |
| Q6 | Confirm RULES and PLAN | Confirmed: `RULES.md` v0.3 and `PLAN.md` v0.4. |
| Q14 | uv version | Pin Aren's uv 0.12.21 (D-009). |

### 10.2 Open

| ID | Question | Source | Claude's notes (for the decision later) |
|---|---|---|---|
| Q15 | Change `vad_max_speech_s` from 10 s to a longer value? | Aren, C2 (2026-10-25) | A longer limit gives fewer cut words, but a long speech gives its line later, and the ASR and MT time grows with the length. C3 can measure the cut words and the time for each length. [RUN] C2d live run: three phrases with short pauses came in one segment, the 10 s hard cut split the word «լսել», and the MT left out a sentence (TESTS.md, Q-13). [RUN] C3: no segment of S1–S3 had a hard cut. [RUN] C4 L-05 (live, about 6 min): 2 hard cuts in 84 segments; Aren: "10s limit for speech sometimes is not enough for long sentences". |
| Q16 | Add a CPU-only mode and a limited-resource mode? | Aren, C2 (2026-10-25): the brief can mean < 5 s on weaker hardware | K4 says that the program runs on Aren's laptop at the interview. A mode is a new feature (T8) and needs a decision; it must be a flag, not a fallback (R10). Before a decision, C3 can measure the CPU latency of the ASR and the MT models (data only). [RUN] C3 CPU probe (24 threads): P1 0.38–0.43 s for each line; P4 (Seamless) 9.9–36.4 s, so P4 does not meet K1 on the CPU (`docs/eval/results.md`). Aren asks the Mathrix team about the laptop (D-053). **Closed (2026-10-27, D-056):** no question to the Mathrix team; the target hardware is Aren's laptop with its GPU; the README states the CPU limits of P4. |

---

## 11. Time log

| Chat | Time box | Actual | Notes |
|---|---|---|---|
| C0 | 1.5 h | 2.5 h | 14:00–16:30 (Aren). 1.0 h over the time box. |
| C1 | 2.5 h | 1.8 h | 2026-10-24, 11:43–13:29 (1 h 46 min). 0.7 h under the time box; added to the buffer. |
| C2 | 3 h | 2.65 h | 2026-10-25, 10:01–12:40 (2 h 39 min). Install check, contracts, test design. The C2 scope changed: the code moved to C2b–C2d (D-035), so the 0.35 h under the time box does not go to the buffer. |
| C2b | 1 h | 0.58 h | 2026-10-25, 12:45–13:20 (35 min). `types`, `config`, and `segment`, with their tests (D-036). 0.42 h under the time box; Aren decides if it goes to the buffer. |
| C2c | 1 h | 0.97 h | 2026-10-25, 13:32–14:30 (58 min, Aren). `asr` and `mt` adapters, with their tests (D-037 to D-039). 0.03 h under the time box. |
| C2d | 1.5 h | 2.92 h | 2026-10-25, 17:44–18:35 (51 min); 19:27–19:40 (about 13 min: recording setup for the eval set, C3 preparation); 2026-10-26, 10:04–10:15 (11 min); 10:46–12:26 (100 min, to the end of the chat). The breaks are not counted (Aren). 1.42 h over the time box: the sim test for T-AUDIO-01 and its two probes (D-041), and the Ctrl+C fix with probe C (D-044). |
| C3 | 2.5 h | 2.5 h | 2026-10-26, 15:14–17:44 (2 h 30 min, from the chat times). On the time box, with the full shortlists (D-049). The P4 implementation moved to C6 (D-053). |
| C4 | 2 h | 1.03 h | 2026-10-26, 20:41–21:28 (47 min, the three branches); 21:53–22:03 (10 min, live test L-05); 22:03–22:08 (5 min, closing). The time 21:28–21:53 is not counted (Aren). Aren adds the time of his last commits if necessary. 0.97 h under the time box; Aren decides if it goes to the buffer. |
| C5 | 3 h | about 4.4 h | 2026-10-26, about 22:32–22:50 (the ONNX question; estimate); 2026-10-27, 13:57–15:56 (D-056 to D-059, three branches); 17:14–17:55 (L-06 and its report); 19:21 to the end of the chat (D-060, D-061, `c5-stop`, the chat end). The breaks are not counted. About 1.4 h over the time box: the L-06 follow-up (D-060) and the abort at the stop (D-061). Estimate from the chat times; Aren confirms or corrects it. |
| C6 | 3.5 h (D-062) | 1.42 h | 2026-10-27, 20:51–22:08 (77 min), and 2026-10-28, 11:12–11:20 (8 min) (Aren). His own P4 tests on 2026-10-28 before 11:12 are not counted. Under the time box: the probe chose the variant quickly, and the CPU mode was not built (D-063 part 4). |
| C7 | 1.5 h + 10 min (the calls, Aren) | about 1.7 h | 2026-10-28, 11:23–11:50 (27 min); the two S5 calls (10 min, Aren); 13:32 to the end of the chat (about 63 min). The break is not counted. Estimate from the chat times; Aren confirmed it. |
| C8 | 1 h | | |
| S1 | 0.5 h | | |
| Buffer | 1 h + 0.7 h (from C1) | 1.0 h | 1.0 h used by C0. C1 added 0.7 h. Buffer left: 0.7 h. |
| **Total** | **25.5 h** | about 22.5 h | C0 to C7. S1 adds 0.5 h over the 20 h of the brief. D-035 adds 3.5 h (C2b–C2d). Expected total about 23.5 h after C8 (R16 notes in §5.1). |

---

## 12. Change log

| Version | Date | Change |
|---|---|---|
| 0.1 | 2026-10-23 | First draft. |
| 0.2 | 2026-10-23 | Aren's answers: target hardware (§1.6); Aren owns the repository; option B phase order (skeleton is now C2, eval and bake-off is C3); no calendar; sim test level; new risks RK13 and RK14; new research questions §6.6 and §6.8; open questions Q6–Q11. |
| 0.3 | 2026-10-23 | Laptop facts from Aren's commands (§1.6). Project folder on the laptop is Claude's only place to read and write (D-005). Aren runs all tests; results go to `test-results/` (D-006). Tool baseline approved (D-007). Name decision added (D-008). |
| 0.4 | 2026-10-23 | Name `tir-asr` (D-008). Claude runs `ruff` and unit tests on a copy before Aren's official run (D-006, Q13). |
| 0.5 | 2026-10-23 | C0 time logged. Side chat S1 for the export format; final export after C8 (D-011). |
| 0.6 | 2026-10-24 | C1 decisions: C2 install check (D-014, D-015, D-016); C3 eval set, normalization rules, and shortlists (D-014, D-015, D-019); setup guide: wired headphones; known limits list in C8. |
| 0.7 | 2026-10-24 | C1 time logged (1.8 h). The 0.7 h saved goes to the buffer (0.7 h left). |
| 0.8 | 2026-10-25 | C2 decisions D-021 to D-035: install check done, contracts and tests approved; the code work moves to C2b, C2c, and C2d, with one branch and its own tests for each component (D-035, R3); open questions Q15 and Q16; R16 note on the total time; C2 time logged (2.65 h). |
| 0.9 | 2026-10-25 | C2b time logged (0.58 h). Expected total now about 22.5 h, or 23.2 h with the buffer (§5.1 note). C2b note: tests pass on Aren's laptop; D-036. |
| 0.10 | 2026-10-25 | C2c status: the tests pass on Aren's laptop; new tests T-MODEL-ERR-03 and T-MODEL-ERR-04 in the C2c table; D-037 to D-039. C2c time logged (0.97 h). |
| 0.11 | 2026-10-26 | C2d status: `c2d-output` and `c2d-audio` merged (D-040, D-041); the C2d branch table; C2d time so far (1.52 h, with no breaks). |
| 0.12 | 2026-10-26 | C2d closed: M1 reached; all four C2d branches; D-042 to D-045; the C2d time (2.92 h, with no breaks, to 12:26); the repository layout (`app.py`, `errors.py`, `tests/support/`, `scripts/`, `run.sh`); the R16 note (expected total about 23.9 h); Q15 data. |
| 0.13 | 2026-10-26 | C3 closed: eval tools, S1–S3 eval set, bake-off, results table (`docs/eval/results.md`); D-046 to D-053; C6 is now the P4 implementation (D-053); Q15 and Q16 data. C3 time logged (2.5 h). C6: P4 after M3, with one pipeline for P1 and P4 (Template Method); C4 is next. |
| 0.14 | 2026-10-26 | C4 closed: M2 reached; D-054 and D-055; the C4 status and the L-05 data; Q15 data; open question on the order of C5 and C6 (Aren, end of C4); C4 time logged (1.03 h). |
| 0.15 | 2026-10-27 | D-056: Q16 closed; the C6 scope (P4 behind a flag, P1 the default, optimizations, P4 tests, no custom ONNX); C5 before C6, with the rule for the speaker step. |
| 0.16 | 2026-10-27 | C5 closed: M3 reached; D-057 to D-061; the C5 status and data; the C7 work from D-060 (step 5); the R16 note after C5; C5 time logged (about 4.4 h, Aren confirms). |
| 0.17 | 2026-10-27 | C6 started: D-062 (the order, the text step design, the flag `--seamless`, INT8, the CPU mode rule, the tests); the C6 time box 3.5 h; the R16 note at the C6 start. |
| 0.18 | 2026-10-28 | C6 closed: D-062 to D-064; the C6 status, T-SIM-03, and the L-07 result; the C7 first part for P4 (D-064); the R16 note at the C6 end; C6 time logged (1.42 h, Aren: to 11:20). |
| 0.19 | 2026-10-28 | C7 closed: D-065 to D-067; the C7 result in §5.2; the R16 note at the C7 end; C7 time logged (about 1.7 h, Aren confirmed). |
