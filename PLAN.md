# PLAN.md: Plan of Completion

**Project:** Live Armenian Transcription to English Translation (Mathrix AI coding challenge)
**Version:** 0.4 · **Date:** 2026-10-23
**Status:** APPROVED by Aren on 2026-10-23 (v0.4).

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
| M1 Skeleton | Microphone → speech segments → Armenian text → English text → terminal, label "Me". | F2, F3, part of F5 | C2 |
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
│   ├── cli.py              # flags, device list, startup log
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
| C2 | Walking skeleton | Module contracts; microphone → VAD → ASR → MT → terminal | M1 | 3 h |
| C3 | Evaluation set and bake-off | Eval scripts and metrics; numbers for the ASR and MT shortlists | — | 2.5 h |
| C4 | Two audio sources | Device list, flags, system audio capture, virtual devices for sim tests, setup guide | M2 | 2 h |
| C5 | Speaker labels | Speaker embeddings, online clustering, stable labels | **M3 (MVP)** | 3 h |
| C6 | Weakest link | One improvement, chosen with numbers after M3 | — | 2 h |
| C7 | Live test and reliability | Live test with two or more people; error behaviour check; latency report | M4 | 1.5 h |
| C8 | Delivery | Full README, `chats/`, rehearsal checklist | M5 | 1 h |
| — | Buffer | — | — | 1 h |
| | **Total** | | | **20 h** |

ASR: automatic speech recognition. MT: machine translation.

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
  9. Aren does a test export of this chat to Markdown. This removes the export risk early.
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

#### C2. Walking skeleton

- **Goal:** The thinnest end-to-end path: microphone → VAD → ASR → MT → terminal, label "Me".
- **Steps:**
  1. **Install check first** (mitigation for D-002): install the first candidates on Aren's laptop with GPU support. A model test loads each model and runs one known clip.
  2. Write the module contracts and the data types in `ARCHITECTURE.md`.
  3. Design the tests in `TESTS.md`. Aren reviews them.
  4. Write the tests, then the thin modules, then connect them.
  5. Add an end-to-end model test that feeds a WAV file through the same pipeline at real-time speed.
  6. Aren runs the program live with his microphone.
- **Decisions needed:**
  - The WAV file source is for tests and eval only. It is not a user feature. Tip T8 warns about extra features, so we log this decision.
  - How the program shows or logs the measured latency of each line (necessary for K1).
- **Done when:** M1 works on Aren's laptop. We have the latency of each line.

#### C3. Evaluation set and bake-off

- **Goal:** Make a small eval set. Compare the ASR and MT shortlists with numbers on Aren's laptop. Change the skeleton models only if a different candidate wins.
- **Steps:**
  1. Design and write the tests for the metric code (TDD).
  2. Write the scripts that make the eval set. The data stays local (`data/`, in `.gitignore`).
  3. Write the metrics: CER/WER, chrF, latency, RTF (real-time factor: processing time divided by audio duration), and VRAM use.
  4. Aren records about 10 short Armenian phrases with the microphone and writes the reference text.
  5. Aren runs the bake-off. Claude makes the results table.
  6. We decide the ASR model and the MT model.
- **Eval set (proposal; final in C1):**
  - about 30 short public Armenian clips with Armenian reference text and English reference text,
  - about 10 recordings from Aren's microphone,
  - 1–2 audio streams with 3 or more speakers, made from clips of different speakers (for C5).
- **Done when:** The results table exists. D-ASR and D-MT are ACCEPTED.

#### C4. Two audio sources

- **Goal:** Capture the microphone and the system audio at the same time, with device selection.
- **Steps:**
  1. Write the setup guide for the system audio capture on Ubuntu (from the C1 research).
  2. Write the script that makes the virtual devices for sim tests.
  3. Design the tests:
     - unit: device list output, flag parsing, a clear error for a missing device (no fallback),
     - sim: two eval streams play into two virtual devices; check the source labels and the time order of the lines.
  4. Write the tests, then the code.
  5. Aren does a live check with a video call.
- **Done when:** M2 works: lines from both sources appear at the same time, with the correct source.

#### C5. Speaker labels

- **Goal:** Label different people on the system side as "Speaker 1", "Speaker 2", and so on. Each person keeps the same label for the full session.
- **Steps:**
  1. Design the tests with the multi-speaker eval streams. Metric: label accuracy after the best mapping of labels to true speakers.
  2. Compare the speaker shortlist with numbers (model tests).
  3. Write the code: speaker embedding for each segment, then online clustering.
  4. Aren sets the clustering threshold from the eval numbers (R10: parameters need Aren's approval).
  5. Sim test: a multi-speaker stream plays into the virtual call device.
  6. Aren does a live check.
- **Done when:** M3 works. All required features F1–F5 work live. **This is the MVP.**

#### C6. Weakest link

- **Goal:** One improvement. We choose it after M3 with numbers: ASR errors, MT quality, latency, or speaker confusion.

#### C7. Live test and reliability

- **Goal:** A full live test with two or more people on the call side.
- **Steps:**
  1. Run all sim tests. Then run the live checklist in `TESTS.md`.
  2. Write the latency report.
  3. Check the error behaviour: a missing device and a missing model must give a clear error.
  4. Fix the problems that we find.
- **Done when:** M4 works.

#### C8. Delivery

- **Goal:** Complete D1–D3.
- **Steps:**
  1. Write the README from `DECISIONS.md`, `ARCHITECTURE.md`, and the measured numbers.
  2. Write the known limits honestly.
  3. Aren exports all chats to `chats/`.
  4. Check each item in §1 against the result.
  5. Aren does a rehearsal of the interview start: install, audio setup, run.
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
| RK8 | The chat export method is not known. | D3 is late or incomplete. | Test export in C0. Export at the end of each chat, not only at the end of the project. |
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

None at the end of C0.

---

## 11. Time log

| Chat | Time box | Actual | Notes |
|---|---|---|---|
| C0 | 1.5 h | 2.5 h | 14:00–16:30 (Aren). 1.0 h over the time box. |
| C1 | 2.5 h | | |
| C2 | 3 h | | |
| C3 | 2.5 h | | |
| C4 | 2 h | | |
| C5 | 3 h | | |
| C6 | 2 h | | |
| C7 | 1.5 h | | |
| C8 | 1 h | | |
| Buffer | 1 h | 1.0 h | Used by C0. No buffer is left. |
| **Total** | **20 h** | 2.5 h | |

---

## 12. Change log

| Version | Date | Change |
|---|---|---|
| 0.1 | 2026-10-23 | First draft. |
| 0.2 | 2026-10-23 | Aren's answers: target hardware (§1.6); Aren owns the repository; option B phase order (skeleton is now C2, eval and bake-off is C3); no calendar; sim test level; new risks RK13 and RK14; new research questions §6.6 and §6.8; open questions Q6–Q11. |
| 0.3 | 2026-10-23 | Laptop facts from Aren's commands (§1.6). Project folder on the laptop is Claude's only place to read and write (D-005). Aren runs all tests; results go to `test-results/` (D-006). Tool baseline approved (D-007). Name decision added (D-008). |
| 0.4 | 2026-10-23 | Name `tir-asr` (D-008). Claude runs `ruff` and unit tests on a copy before Aren's official run (D-006, Q13). |
