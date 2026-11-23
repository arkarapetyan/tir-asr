# tir-asr

Live Armenian speech transcription and English translation in the terminal, with speaker labels.
The VAD, the speech recognition (OhanASR), and the speaker model run locally on the GPU. The English translation uses Google Translate over the network: the Armenian text of each line goes to Google (§7). Use the program only with the consent of the other people in the call.

The program captures your microphone (`Me`) and the other side of a call (`Speaker 1`, `Speaker 2`, …) at the same time. For each speech segment, it prints the time, the speaker, the Armenian text, the English translation, and the latency of each step:

```
[00:01:44] Speaker 2
 HY: Ես համաձայն եմ, միայն թե ուզում եմ կիրակի օրը վաղ վերադառնալ, որովհետև երկուշաբթի հանդիպում ունեմ։
 EN: I agree, except I want to come back early on Sunday because I have a meeting on Monday.
 [Latency: vad 0.50s, asr 1.01s, mt 0.48s, spk 0.01s, out 0.00s | Total 2.01s]
```

The total is the time from the end of the speech to the print. In our simulated call with 4 voices (24 lines), the totals were 1.08–4.71 s, mean 2.02 s. In a run with slow Google answers, one total was 5.97 s (§6). The `mt` step is the Google network time.

The name comes from Tir. In Armenian mythology, Tir is the god of written language and wisdom, the scribe of the chief god Aramazd, and an interpreter of dreams ([source](https://en.wikipedia.org/wiki/Tir_(god))).

## Contents

1. [Requirements](#1-requirements)
2. [Setup](#2-setup)
3. [Run](#3-run)
4. [Models: choices, alternatives, and reasons](#4-models-choices-alternatives-and-reasons)
5. [Architecture](#5-architecture)
6. [Measured results](#6-measured-results)
7. [Known limits](#7-known-limits)
8. [Possible improvements](#8-possible-improvements)
9. [How we worked](#9-how-we-worked)
10. [Development and tests](#10-development-and-tests)

---

## 1. Requirements

| Item | Tested with |
|---|---|
| OS | Ubuntu 26.04 LTS, PipeWire 1.6 with PulseAudio (`pipewire-pulse`) |
| GPU | NVIDIA GPU with CUDA (tested: RTX 5070 Laptop GPU, 8 GB). The program uses about 4.9 GB, and it needs this much free GPU memory at the start. |
| NVIDIA driver | 595.99 (supports CUDA 13.2) |
| uv | 0.12.21 exactly (pinned in `pyproject.toml`, D-009). uv installs Python 3.11 (D-081). |
| Network | An internet connection for Google Translate. With no network, the program stops at the startup. |
| Disk | the OhanASR model is 9.1 GB (`model.pt`), plus the environment and the speaker model |

The program has **no CPU mode** (§7).

## 2. Setup

### 2.1 Environment

```bash
git clone https://github.com/arkarapetyan/tir-asr.git
cd tir-asr
uv sync --locked          # installs the environment (.venv) from uv.lock
```

### 2.2 Models (one time, needs the network)

The program reads the models only from the local disk (`run.sh` sets `HF_HUB_OFFLINE=1`). Get them one time:

1. **OhanASR (ASR):** `Metric-AI/OhanASR-v0.1` is a gated model. On its Hugging Face page, ask for access and accept the conditions. Then log in and download it into `models/ohanasr-v0.1` (the folder is in `.gitignore`):

   ```bash
   uv run --no-sync hf auth login
   uv run --no-sync hf download Metric-AI/OhanASR-v0.1 --local-dir models/ohanasr-v0.1
   ```

   The folder must have `model.pt`, `ohanasr.py`, and `ohanasr_tokenizer.model`. The program loads the model with the model's own `ohanasr.py`.

2. **TitaNet (speaker labels):**

   ```bash
   uv run --no-sync hf download nvidia/speakerverification_en_titanet_large
   ```

The Silero VAD model comes with the `silero-vad` package. The translation needs no model and no key (Google Translate, §4).

### 2.3 Audio

The program captures two sources:

| Label | Source | Flag | Default (no flag) |
|---|---|---|---|
| `Me` | your microphone | `--mic ID` | the default microphone |
| `System` | the sound that the computer plays (the other side of the call) | `--system ID` | the **monitor** of the default output |

On Ubuntu, each output device has a monitor source. The monitor copies the sound that plays, and you still hear it. This is the Ubuntu equivalent of BlackHole and a Multi-Output Device on macOS. No extra software is necessary.

Before the call:

1. Connect **headphones** before you start the program. With loudspeakers, the microphone also captures the other side (echo handling is out of scope).
2. In the call application, select the laptop microphone as the input and the headphones (the default output) as the output.
3. Do not change the output device during a run. The program does not follow a change. If you change it, stop and start the program again.

The full guide, with the error messages, is in [`docs/setup-audio.md`](docs/setup-audio.md).

## 3. Run

```bash
./run.sh --list-devices        # show the sources, their exact ids, and the defaults (*); load no model
./run.sh                       # start with the defaults
./run.sh --mic <id> --system <monitor id>   # start with selected devices (exact ids from the list)
```

- The startup loads the models and makes one warm-up call for each model. The MT warm-up is the first call to Google, so a missing network stops the program here. Each startup line starts with `startup: `; NeMo shows only its errors (D-068). Check the two `startup: source …` lines: they must show the devices of the call.
- When `Listening. Press Ctrl+C to stop.` appears, the program is ready.
- Push **Ctrl+C one time** to stop. The program prints a shutdown line with the counts, and exits with code 0.
- A wrong device id, a missing model, no CUDA, too little free GPU memory, or a failed Google call stops the program with a clear message (for example `tir-asr: audio: no source with the exact id <id>` or `tir-asr: mt: Google Translate failed: …`) and exit code 1. The program has no silent fallback and no retry.

## 4. Models: choices, alternatives, and reasons

We chose each model with numbers on our own Armenian recordings (R6), not from a reputation. The eval set: 3 conversation scripts (S1–S3), 34 lines, 397 words, several voices, both sides of real Google Meet and Telegram calls (`docs/eval/`). The full tables are in [`docs/eval/results.md`](docs/eval/results.md). Each decision, with its options and reasons, is in `DECISIONS.md`.

### 4.1 The program

| Step | Model and runtime | Why | Licence |
|---|---|---|---|
| VAD (speech segments) | Silero VAD 6.2.3, CPU | MIT, under 1 ms for each 32 ms frame, no telemetry (D-018). | MIT |
| ASR (speech → Armenian) | `Metric-AI/OhanASR-v0.1` (omniASR LLM 1B v2 with the OhanASR checkpoint), fairseq2, bfloat16, GPU | The lowest WER on our sets: 5.3 % (S1–S3) and 6.3 % (S5, recorded calls). It writes punctuation, case, and digits (D-075, D-080). | CC-BY-NC-4.0 |
| MT (Armenian → English) | Google Translate through `googletrans` 4.0.2 (unofficial client), over the network | The highest chrF on the OhanASR text: 67.5 (S1–S3) and 69.3 (S5) (D-079, D-080). | Google service (see §4.4) |
| Speaker labels | `nvidia/speakerverification_en_titanet_large` (TitaNet-large) embeddings, with our own online centroid clustering | 0 wrong labels on 4 Armenian voices over the widest threshold range (0.40–0.60); no new package (D-057, D-058). | CC-BY-4.0 |

All models run in one process and one environment: Python 3.11 and torch 2.8.0, the versions that OhanASR needs (D-081).

### 4.2 The decision rule of C9

In C9, a new pipeline had to pass four conditions, fixed before the runs (D-072 part 3): a WER not higher than the old pipelines, a chrF not lower than P4, 8 GB and 0.5 model s per audio s, and no added text in the English lines. OhanASR + Google passed all four (D-080):

| Pipeline | WER S1–S3 / S5 | chrF S1–S3 / S5 | Model s per audio s (S5) |
|---|---|---|---|
| **OhanASR + Google (the program)** | 5.3 % / 6.3 % | **67.5 / 69.3** | 0.429 |
| P4: SeamlessM4T v2, audio to English (until C9: `--seamless`) | 7.1 % / 13.0 % | 59.0 / 65.3 | 0.092 |
| P1: NeMo FastConformer RNNT + NLLB-200 (until C9: the default) | 10.6 % / 10.0 % | 51.7 / 57.8 | 0.026 |

P1 and P4 left the program in C10 (D-072 part 4, D-081). The git history keeps them.

### 4.3 Alternatives that we measured

| Candidate | Result on our set | Why not in the program |
|---|---|---|
| `Metric-AI/Ayb-0.5-4B` (Armenian LLM) as the MT | chrF 63.4 / 63.6 on the OhanASR text | Too slow and too large with OhanASR in 8 GB, and it added text to some lines (D-078). |
| SeamlessM4T v2 or NLLB, text to text, on the OhanASR text | chrF 56.0 / 62.9 (Seamless) | Lower chrF than Google (D-080). |
| Google Cloud Translation API (the official API) | Not measured | It needs a Google Cloud account with billing and a key (D-079). |
| ASR-1 with the CTC decoder (and its ONNX export) | WER 12.7 % | Higher WER than RNNT (D-052). |
| `BuzzASR/armenian` (Whisper fine-tune) | WER 19.0 %, 0.26 s for each segment | Higher WER, slower (D-053). |
| `Helsinki-NLP/opus-mt-hy-en` | chrF 42.7 | Much lower chrF (D-053). |
| ECAPA (SpeechBrain), WeSpeaker (pyannote) | Both pass, with narrower ranges or a negative margin | 5 and 27 new packages; removed after the sweep (D-058). |
| Streaming Sortformer, diart | Not measured | Max. 4 speakers and English-only training; diart does not install with pyannote 4 (D-017). |

### 4.4 Licences and terms

- OhanASR is **CC-BY-NC-4.0 (non-commercial)**.
- `googletrans` uses the servers of the Google Translate website. It is not an official Google API, and it can stop to work at any time (D-079). A product needs the official Cloud Translation API and a check of its terms.

## 5. Architecture

```
 microphone ──► capture thread "Me" ─────► Endpointer + Silero VAD ─┐
 call audio ──► capture thread "System" ─► Endpointer + Silero VAD ─┤  Segment
 (monitor)                                                          ▼
                                                    one segment queue (unbounded)
                                                                    │
                                     worker thread (all GPU work)   ▼
                                       text step (Template Method), CascadeTextStep:
                                         OhanASR ASR (GPU) → Google Translate MT (network)
                                         output rules: only Armenian in HY, only English in EN
                                       speaker step ("System" only): TitaNet → online centroids
                                       output: one write for each block
```

- **Core and adapters (D-021):** core modules have no model or device import, so CI runs their unit tests with fakes. Adapters hold the model and device code.
- **Threads (D-029, D-054):** one capture thread for each source, one worker for all GPU work. The GPU models run one at a time.
- **Segments (D-027, D-069):** a segment ends after 500 ms of silence (`vad_min_silence_ms`), or at 15 s of continuous speech (`vad_max_speech_s`).
- **Speaker labels (D-057 to D-060):** each `System` segment gets an embedding. It joins the nearest speaker centroid when the cosine similarity is 0.50 or more (`spk_threshold`); else it starts a new speaker. A segment under 1.0 s (`spk_min_new_s`) cannot start a new speaker. Labels stay the same for the full session.
- **Text step (D-062, D-081):** one abstract `TextStep` with the empty-text rule, the clock reads, and the output rules (D-066). `CascadeTextStep` gives the two hooks: OhanASR, then Google Translate.
- **Fail loudly (R10):** each error stops the program with the module name and the cause. No fallback, no retry. A Google call has a timeout of 10 s (D-082). Each tuned parameter is in `config.Params` and in the startup log.
- **Clean stop (D-044, D-061, D-067):** Ctrl+C stops the threads in order, so the audio library does not abort at exit.

All modules, contracts, parameters, and error messages are in [`ARCHITECTURE.md`](ARCHITECTURE.md).

## 6. Measured results

All numbers are from Aren's laptop (RTX 5070 Laptop GPU, 8 GB). The numbers of P1 and P4 (until C9) are in [`docs/eval/results.md`](docs/eval/results.md).

| Measurement | Result | Source |
|---|---|---|
| WER, eval sets S1–S3 / S5 | 5.3 % / 6.3 % (digits counted as correct, D-075) | C9 eval (D-080) |
| chrF, eval sets S1–S3 / S5 | 67.5 / 69.3 | C9 eval (D-080) |
| Model time for each second of audio (S5) | 0.429 s: OhanASR 0.164 s, Google 0.265 s (limit 0.5, K1) | C9 eval (D-080) |
| Google time for each line | 0.99 s mean, 3.02 s max (C9); one call of 4.75 s (C10) | C9 eval, T-SIM-01 (D-082) |
| Line totals, simulated call with 4 voices (24 lines) | 1.08–4.71 s, mean 2.02 s | T-SIM-02 (C10) |
| Line totals, simulated call S1 (14 lines) | run 1: 1.19–2.50 s; run 2: 1.40–5.97 s (slow Google answers) | T-SIM-01 (C10) |
| Arrival gaps of the audio blocks (GIL check) | max 47.4 ms with OhanASR in the worker (limit 64 ms) | T-SIM-02 (C10) |
| The program adapter against the C9 eval run | the same 136 texts, the same WER, 0.164 model s per audio s (S5) | T-MODEL-ASR-02 (C10) |
| GPU memory | 4,894 MiB after all loads | startup log, T-E2E-01 (C10) |
| Speaker labels, 4 voices (stream D) | 19 of 19 correct, 4 labels | T-SIM-02 (C10) |

## 7. Known limits

- **Interruptions:** a segment ends only after 0.5 s of silence. When a person starts to speak less than 0.5 s after another person, or interrupts, both voices are in one line, with the label of the person who spoke more (D-060). A shorter silence (300 ms) split a sentence at a normal pause in our tests, so it is not in the program (D-069).
- **Two people at the same time** on the call side give one line with one label (D-017).
- **Extra speaker labels from noise:** in the final live test (2 people on the call side, bad connection), short fragments such as «Օի։» or «Խ։» got 5 extra labels (Speakers 3–7, 1–2 lines each). Speaker 1 and Speaker 2 (the two people) had 47 of the 52 call-side lines (D-069).
- **Noises:** a cough or a short sound can pass as speech. The line then has one letter or a fragment, and the translation can be an invented sentence. A short sound before the first speaker gets the label `Unidentified` (D-060).
- **Short phrases:** a phrase under 250 ms (for example a fast «հա») is removed as noise (`vad_min_speech_ms`).
- **Long speech:** after 15 s of speech with no pause, the program cuts the segment, and a word can be split (Q15, D-069).
- **Maximum length not measured on the eval set:** the eval numbers (§6) used a maximum length of 10 s (no eval segment reached it). The C8 live test had 4 hard cuts at 10 s, so the program uses 15 s (D-069). A 15 s line comes up to 5 s later than a 10 s line.
- **Translation:** each segment is translated alone, with no context. Armenian «նա» is "he" or "she", and the translation must guess.
- **Network and privacy:** the Armenian text of all people in the call goes to Google. With no network, or when a Google call fails or takes more than 10 s, the program stops with an `mt` error (D-079, D-082). The Google time changes from call to call (0.1–4.75 s measured), so some lines come later.
- **Unofficial client:** `googletrans` is not an official Google API, and it can stop to work at any time (D-079).
- **Invented text:** on 2 s of silence (the warm-up), OhanASR wrote a full invented sentence. Thus a noise that passes the VAD can give an invented line (C10, Q-14).
- **GPU memory:** the program needs about 4.9 GB of free GPU memory at the start. If the call application or a browser uses a large part of the GPU, the program stops at the startup with `OutOfMemoryError` (D-082).
- **Output rules:** the Armenian line shows only Armenian script, and the English line only Latin script. A word in another script, for example a Latin name in the Armenian line, shows as `[?]` (D-066).
- **Dialect:** Eastern Armenian only. We did not measure Western Armenian (D-013).
- **Hardware:** an NVIDIA GPU with CUDA is necessary; the program has no CPU mode.
- **Pinned versions:** OhanASR needs Python 3.11, torch 2.8.0, and numpy 1.26 (fairseq2 0.5.2). All packages of the program stay at versions that work with these pins (D-081).
- **Devices:** the program does not follow a change of the default output during a run (D-054). Echo handling is out of scope: use headphones.
- **Eval size:** the eval set is small (34 lines and 2 recorded calls, 4 call-side voices). The speaker result of C5 (0 errors in 19 segments) has an approximate 95 % upper limit of about 15 % for the error rate.
- **Not done yet (C11, D-072):** the measurements of a shorter minimum silence and of the VAD settings for noises, a speaker diagnostic line, and a live test with OhanASR + Google.

## 8. Possible improvements

In the order of the measured need:

1. **Interruptions and segment values:** measure `vad_min_silence_ms` (250–500 ms) and `vad_max_speech_s` on WER, chrF, and speaker accuracy, maybe with a separate value for the `System` side (C11).
2. **Noises:** a measured `vad_threshold` and `vad_min_speech_ms`, and a rule for invented or very short texts, with a recording of coughs and short words (C11).
3. **Speed:** the ASR of the next segment can run during the network wait of the last Google call (D-080), if a live test shows lines that come later and later.
4. **Translation context:** give the MT the previous segment of the same speaker, so that pronouns and cut sentences get a better translation.
5. **An official MT API:** the Google Cloud Translation API, with a key, in place of `googletrans` (D-079, option A).
6. **A commercial licence:** replace OhanASR with a model that allows commercial use, measured on the same eval set.
7. **A larger eval set:** more voices, devices, and call applications, with casual speech.

## 9. How we worked

The project was built with Claude (Anthropic) in one Claude Project, by the rules in [`RULES.md`](RULES.md):

- **Plan first:** `PLAN.md` (phases C0–C11, milestones, time log) was approved before any code.
- **One module, one chat:** each phase had its own chat, with a handover file in `docs/handovers/`.
- **Decisions:** each choice of a model, a parameter, or a design is in `DECISIONS.md` (D-001 to D-082), with the options, the weak points, and Aren's reason. Both sides questioned each proposal.
- **Tests first:** each test in `TESTS.md` comes from a requirement, not from the code. Four levels: unit (CI), model, sim (virtual audio devices), and live.
- **Measure, do not guess:** each model choice comes from the bake-off numbers in `docs/eval/results.md`.
- **The human owns the repository:** Aren ran all tests and did all git operations. Claude wrote only in the project folder.

The chats are in the Claude Project in the Claude app, not in the repository (D-071). Until C8, the repository had a Markdown copy of each chat in `chats/`; the git history keeps those files.

## 10. Development and tests

```bash
uv sync --locked                                   # install the environment
uv run ruff check . && uv run ruff format --check . # lint and format
uv run pytest                                      # unit tests (also in CI)
HF_HUB_OFFLINE=1 uv run pytest -m model tests/model --ignore=tests/model/test_e2e.py    # model tests (GPU)
HF_HUB_OFFLINE=1 uv run pytest -m model tests/model/test_e2e.py::test_e2e_01_full_pipeline_with_the_real_models
HF_HUB_OFFLINE=1 uv run pytest -m model tests/model/test_e2e.py::test_e2e_02_ctrl_c_stops_the_program
HF_HUB_OFFLINE=1 uv run pytest -m "sim and model" tests/sim/test_audio_sim.py::test_sim_02_speaker_labels_on_the_system_side
```

One program load needs about 4.9 GB of the 8 GB GPU. Thus each end-to-end test and each sim test runs in its own pytest process (D-082). The model, end-to-end, and sim tests send Armenian text to Google.

CI (GitHub Actions) runs `ruff` and the unit tests without the GPU packages (`--no-group laptop`, D-021).

| File | Contents |
|---|---|
| `RULES.md` | How we worked: the rules of engagement. |
| `PLAN.md` | Requirements, phases, milestones, risks, time log. |
| `DECISIONS.md` | Each decision, with its options and reasons. |
| `ARCHITECTURE.md` | Modules, contracts, data flow, threads, parameters, errors. |
| `TESTS.md` | Each test, with the requirement that it checks, and the results. |
| `docs/research/RESEARCH.md` | The research of the candidate models, with sources. |
| `docs/eval/` | The eval scripts and the measured results. |
| `docs/setup-audio.md` | The audio setup on Ubuntu. |
