# tir-asr

Live Armenian speech transcription and English translation in the terminal, with speaker labels.
All models run locally on the GPU. No cloud API is used.

The program captures your microphone (`Me`) and the other side of a call (`Speaker 1`, `Speaker 2`, …) at the same time. For each speech segment, it prints the time, the speaker, the Armenian text, the English translation, and the latency of each step:

```
[00:01:12] Speaker 1
 HY: Լավ եմ, շնորհակալություն։
 EN: I'm fine, thank you.
 [Latency: vad 0.53s, asr 0.03s, mt 0.08s, spk 0.01s, out 0.00s | Total 0.65s]
```

The total is the time from the end of the speech to the print. In the recorded live calls, each total was 0.57–0.67 s (limit: 5 s).

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
| GPU | NVIDIA GPU with CUDA (tested: RTX 5070 Laptop GPU, 8 GB; P1 uses about 2.8 GB) |
| NVIDIA driver | 595.99 (supports CUDA 13.2) |
| uv | 0.12.21 exactly (pinned in `pyproject.toml`, D-009). uv installs Python 3.12. |
| Disk | about 10 GB for the environment and the models |

The program has **no CPU mode** (§7).

## 2. Setup

### 2.1 Environment

```bash
git clone https://github.com/arkarapetyan/tir-asr.git
cd tir-asr
uv sync --locked          # installs the environment (.venv) from uv.lock
```

### 2.2 Models (one time, needs the network)

The program reads the models only from the local disk (`run.sh` sets `HF_HUB_OFFLINE=1`). Download them one time:

```bash
uv run --no-sync hf download nvidia/stt_hy_fastconformer_hybrid_large_pc        # ASR (P1)
uv run --no-sync hf download facebook/nllb-200-distilled-600M                    # MT (P1)
uv run --no-sync hf download nvidia/speakerverification_en_titanet_large         # speaker labels
uv run --no-sync hf download facebook/seamless-m4t-v2-large                      # only for --seamless (P4)

# Convert NLLB to CTranslate2 (float16) into models/ (the folder is in .gitignore):
HF_HUB_OFFLINE=1 uv run --no-sync ct2-transformers-converter \
    --model facebook/nllb-200-distilled-600M \
    --output_dir models/nllb-200-distilled-600M-ct2-float16 --quantization float16
```

The Silero VAD model comes with the `silero-vad` package. No model needs a Hugging Face token.

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
./run.sh                       # start with the defaults (P1)
./run.sh --mic <id> --system <monitor id>   # start with selected devices (exact ids from the list)
./run.sh --seamless            # experimental P4: one Seamless model gives both texts (§4)
```

- The startup loads the models and makes one warm-up call for each model. Each startup line starts with `startup: `; NeMo shows only its errors (D-068). Check the two `startup: source …` lines: they must show the devices of the call.
- When `Listening. Press Ctrl+C to stop.` appears, the program is ready.
- Push **Ctrl+C one time** to stop. The program prints a shutdown line with the counts, and exits with code 0.
- A wrong device id, a missing model, or no CUDA stops the program with a clear message (for example `tir-asr: audio: no source with the exact id <id>`) and exit code 1. The program has no silent fallback.

## 4. Models: choices, alternatives, and reasons

We chose each model with numbers on our own Armenian recordings (R6), not from a reputation. The eval set: 3 conversation scripts (S1–S3), 34 lines, 397 words, several voices, both sides of real Google Meet and Telegram calls (`docs/eval/`). The full tables are in [`docs/eval/results.md`](docs/eval/results.md). Each decision, with its options and reasons, is in `DECISIONS.md`.

### 4.1 The program (default pipeline P1)

| Step | Model and runtime | Why | Licence |
|---|---|---|---|
| VAD (speech segments) | Silero VAD 6.2.3, CPU | MIT, under 1 ms for each 32 ms frame, no telemetry (D-018). | MIT |
| ASR (speech → Armenian) | `nvidia/stt_hy_fastconformer_hybrid_large_pc`, RNNT decoder, NeMo, GPU | The best open Armenian WER on the ArmBench leaderboard; on our set, WER 10.6 % at 0.02 s for each segment (D-014, D-053). | CC-BY-4.0 |
| MT (Armenian → English) | `facebook/nllb-200-distilled-600M`, CTranslate2 float16, GPU | chrF 51.7 against 42.7 for OPUS-MT, at 0.07 s for each segment (D-015, D-016). | CC-BY-NC-4.0 |
| Speaker labels | `nvidia/speakerverification_en_titanet_large` (TitaNet-large) embeddings, with our own online centroid clustering | 0 wrong labels on 4 Armenian voices over the widest threshold range (0.40–0.60); no new package (D-057, D-058). | CC-BY-4.0 |

### 4.2 Alternatives that we measured

| Candidate | Result on our set | Why not in the default |
|---|---|---|
| ASR-1 with the CTC decoder (and its ONNX export) | WER 12.7 % | Higher WER than RNNT; the ONNX export has the CTC head only (D-052). |
| `BuzzASR/armenian` (Whisper fine-tune) | WER 19.0 %, 0.26 s for each segment | Higher WER, slower, writes digits (D-053). |
| `Helsinki-NLP/opus-mt-hy-en` | chrF 42.7 | Much lower chrF (D-053). |
| SeamlessM4T v2, text to text | chrF 55.5, 0.25 s | Better English, but P4 is better again (below). |
| **SeamlessM4T v2 end to end (P4)** | WER 7.1 %, chrF 59.0, 0.33 s for each line | In the program behind `--seamless` (below). |
| ECAPA (SpeechBrain), WeSpeaker (pyannote) | Both pass, with narrower ranges or a negative margin | 5 and 27 new packages; removed after the sweep (D-058). |
| Streaming Sortformer, diart | Not measured | Max. 4 speakers and English-only training; diart does not install with pyannote 4 (D-017). |
| Whisper large-v3 (turbo) fine-tunes | Not measured | Higher WER than ASR-1 on all ArmBench sets, about 6 GB VRAM (D-014). |

### 4.3 P1 or P4

P4 (`--seamless`) is one `facebook/seamless-m4t-v2-large` model (float16, GPU). One encoder pass and one decode of two rows give the Armenian line and the English line (D-063). On the eval set, P4 is better on both texts. In the live calls with a casual script, P4 gave the better English, but P4 changes casual spoken Armenian to standard Armenian (for example «էս» → «այս»), so its Armenian WER on the call side was higher:

| Live call (script S5) | WER Me / call | chrF Me / call | Totals |
|---|---|---|---|
| P1 (default) | 7.1 % / 12.7 % | 56.0 / 59.6 | 0.57–0.67 s |
| P4 (`--seamless`) | 8.3 % / 18.1 % | 64.2 / 65.5 | 0.70–0.94 s |

P1 stays the default (D-056, D-066): it is faster, it keeps the words that people say, and it needs less GPU work. Use `--seamless` when the English matters more than an exact Armenian line. P4 is labelled experimental.

### 4.4 Licences

NLLB-200 and SeamlessM4T v2 are **CC-BY-NC-4.0 (non-commercial)**. NLLB is also "not released for production deployment". A commercial product needs a different MT model.

## 5. Architecture

```
 microphone ──► capture thread "Me" ─────► Endpointer + Silero VAD ─┐
 call audio ──► capture thread "System" ─► Endpointer + Silero VAD ─┤  Segment
 (monitor)                                                          ▼
                                                    one segment queue (unbounded)
                                                                    │
                                     worker thread (all GPU work)   ▼
                                       text step (Template Method):
                                         P1 CascadeTextStep:  NeMo ASR → NLLB MT
                                         P4 SeamlessTextStep: Seamless, both texts in one call
                                         output rules: only Armenian in HY, only English in EN
                                       speaker step ("System" only): TitaNet → online centroids
                                       output: one write for each block
```

- **Core and adapters (D-021):** core modules have no model or device import, so CI runs their unit tests with fakes. Adapters hold the model and device code.
- **Threads (D-029, D-054):** one capture thread for each source, one worker for all GPU work. The GPU models run one at a time.
- **Segments (D-026, D-027):** a segment ends after 500 ms of silence (`vad_min_silence_ms`), or at 10 s of continuous speech.
- **Speaker labels (D-057 to D-060):** each `System` segment gets an embedding. It joins the nearest speaker centroid when the cosine similarity is 0.50 or more (`spk_threshold`); else it starts a new speaker. A segment under 1.0 s (`spk_min_new_s`) cannot start a new speaker. Labels stay the same for the full session.
- **Text step (D-062, D-063):** one abstract `TextStep` with the empty-text rule, the clock reads, and the output rules (D-066). P1 and P4 implement only the model hooks.
- **Fail loudly (R10):** each error stops the program with the module name and the cause. No fallback, no hidden retry. Each tuned parameter is in `config.Params` and in the startup log.
- **Clean stop (D-044, D-061, D-067):** Ctrl+C stops the threads in order, so the audio library does not abort at exit.

All modules, contracts, parameters, and error messages are in [`ARCHITECTURE.md`](ARCHITECTURE.md).

## 6. Measured results

All numbers are from Aren's laptop (RTX 5070 Laptop GPU, 8 GB).

| Measurement | Result | Source |
|---|---|---|
| Latency of a line, live (P1) | 0.57–0.67 s total; no growth during a call | C7 live calls |
| Latency of a line, live (P4) | 0.70–0.94 s total | C7 live calls |
| ASR + MT time for each segment (P1) | 0.10 s mean, 0.14 s max | C3 bake-off |
| WER / chrF, eval set (P1) | 10.6 % / 51.7 | C3 bake-off |
| WER / chrF, eval set (P4) | 7.1 % / 59.0 | T-PERF-P4-01 |
| Speaker labels, 4 voices (stream D) | 19 of 19 correct | C5 sweep, T-SIM-02 |
| GPU memory | P1: about 2.8 GB; P4: about 3.1 GB (with the speaker model) | startup log, C6 probe |
| GPU power during a live call | P1: mean 13.4 W, max 20.6 W, max 47 °C | C7 live calls |

## 7. Known limits

- **Interruptions:** a segment ends only after 0.5 s of silence. When a person starts to speak less than 0.5 s after another person, or interrupts, both voices are in one line, with the label of the person who spoke more (D-060).
- **Two people at the same time** on the call side give one line with one label (D-017).
- **Noises:** a cough or a short sound can pass as speech. The line then has one letter or a fragment, and the translation can be an invented sentence. A short sound before the first speaker gets the label `Unidentified` (D-060).
- **Short phrases:** a phrase under 250 ms (for example a fast «հա») is removed as noise (`vad_min_speech_ms`).
- **Long speech:** after 10 s of speech with no pause, the program cuts the segment, and a word can be split (Q15).
- **Translation (P1):** each segment is translated alone, with no context. NLLB sometimes leaves out the second sentence of a segment. Armenian «նա» is "he" or "she", and the model must guess.
- **P4:** it changes casual Armenian to standard Armenian (§4.3). It is experimental.
- **Output rules:** the Armenian line shows only Armenian script, and the English line only Latin script. A word in another script, for example a Latin name in the Armenian line, shows as `[?]` (D-066).
- **Dialect:** Eastern Armenian only. We did not measure Western Armenian (D-013).
- **Hardware:** an NVIDIA GPU with CUDA is necessary; the program has no CPU mode. A probe of P4 on the CPU of the laptop gave 1.2–1.8 s for each line with INT8 and 8 threads, but 5–50 s with float32 and 24 threads (D-063). P1 on the CPU gave about 0.4 s for each line (C3 probe).
- **Devices:** the program does not follow a change of the default output during a run (D-054). Echo handling is out of scope: use headphones.
- **Eval size:** the eval set is small (34 lines, 4 call-side voices). The speaker result (0 errors in 19 segments) has an approximate 95 % upper limit of about 15 % for the error rate.
- **Not done (time budget, D-065):** the measurements of a shorter minimum silence and of the VAD settings for noises, and a speaker diagnostic line.

## 8. Possible improvements

In the order of the measured need:

1. **Interruptions:** a shorter `vad_min_silence_ms` for the `System` side (250–400 ms), measured on WER, chrF, and speaker accuracy; or a speaker-change split inside a segment with embeddings on short windows.
2. **Noises:** a measured `vad_threshold` and `vad_min_speech_ms`, and a rule for texts with one or two letters, with a recording of coughs and short words.
3. **Translation context:** give the MT the previous segment of the same speaker, so that pronouns and cut sentences get a better translation.
4. **A CPU mode:** P1 on the CPU, and P4 with INT8 on the fast cores, behind a `--device cpu` flag (the probe numbers meet the 5 s limit).
5. **A commercial licence:** replace NLLB and Seamless with a model that allows commercial use, measured on the same eval set.
6. **A larger eval set:** more voices, devices, and call applications, with casual speech.

## 9. How we worked

The project was built with Claude (Anthropic) in one Claude Project, by the rules in [`RULES.md`](RULES.md):

- **Plan first:** `PLAN.md` (phases C0–C8, milestones, time log) was approved before any code.
- **One module, one chat:** each phase had its own chat, with a handover file in `docs/handovers/`.
- **Decisions:** each choice of a model, a parameter, or a design is in `DECISIONS.md` (D-001 to D-068), with the options, the weak points, and Aren's reason. Both sides questioned each proposal.
- **Tests first:** each test in `TESTS.md` comes from a requirement, not from the code. Four levels: unit (CI), model, sim (virtual audio devices), and live.
- **Measure, do not guess:** each model choice comes from the bake-off numbers in `docs/eval/results.md`.
- **The human owns the repository:** Aren ran all tests and did all git operations. Claude wrote only in the project folder.

The chats are in [`chats/`](chats/), one Markdown file for each chat. They contain the text messages; the original chats in the Claude app also have the tool calls (D-012).

## 10. Development and tests

```bash
uv sync --locked                                   # install the environment
uv run ruff check . && uv run ruff format --check . # lint and format
uv run pytest                                      # unit tests (also in CI)
env -u LD_LIBRARY_PATH HF_HUB_OFFLINE=1 uv run pytest -m model          # model tests (GPU)
env -u LD_LIBRARY_PATH HF_HUB_OFFLINE=1 uv run pytest -m "sim and model" # sim tests (virtual audio devices)
```

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
