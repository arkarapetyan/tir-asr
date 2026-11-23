# Handover 09b → 10 (C10: OhanASR + Google as the program default)

**Date:** 2026-11-23

## Goal of the next chat

Make OhanASR (ASR) + Google Translate through `googletrans` (MT) the default pipeline of the program (D-080). OhanASR runs in its own process, because it cannot share the main environment (D-073). Then remove P1 and P4 (D-072 part 4), and do the test changes for tuning (D-072 part 5).

## Current state

- **Branches:** `c9-eval` has the eval tools (D-072 to D-075). `c9-ayb` starts from `c9-eval` and has D-076 to D-080: the Ayb work and its removal, the Google adapter, and the results. Aren merges `c9-eval` into `main`, then `c9-ayb`, when CI is green. Claude does not know the commit hashes.
- **Program:** no change in C9. P1 is the default; P4 is behind `--seamless`.
- **C9 results** (`docs/eval/results.md`, "C9"), all [RUN] on Aren's laptop:

| Pipeline | WER S1–S3 / S5 | chrF S1–S3 / S5 | Model s per audio s (S5) | VRAM |
|---|---|---|---|---|
| **OhanASR + Google** (D-080) | 5.3 % [calc, D-075] / 6.3 % | **67.5 / 69.3** | 0.429 | 4,994 MiB [calc, with TitaNet and the base] |
| P4 (Seamless, audio to English) | 7.1 % / 13.0 % | 59.0 / 65.3 | 0.092 | 3,082 MiB |
| P1 (`nemo-rnnt` + NLLB) | 10.6 % / 10.0 % | 51.7 / 57.8 | 0.026 | 952 + 1,932 MiB |

- **Tests:** unit 255 passed, 27 deselected (`test-results/c9-unit-6.txt`).
- **Documents:** `RULES.md` v0.6, `PLAN.md` v0.25, `DECISIONS.md` to D-080, `ARCHITECTURE.md` v0.43, `TESTS.md` §2.10.
- **Dependencies:** the group `c9-eval` has only `googletrans>=4.0.2` (not in `default-groups`).
- **Models (`models/`, not in git):** `ohanasr-v0.1` (in use); `ayb-0.5-4b` (9.3 GB, not in use after D-078; Aren can delete it).

## Facts for the C10 design (no decision yet)

- **Two environments (D-073):** the OhanASR environment is Python 3.11, torch 2.8.0, fairseq2 0.5.2, and omnilingual-asr 0.2.0 (`scripts/ohanasr_transcribe.py`, with its inline metadata and its lock). The main environment is Python 3.12, torch 2.14.1, NeMo 3.0.0 (TitaNet), and silero-vad. Thus the program needs a second process for OhanASR: a worker that loads the model one time, gets each segment (float32, 16 kHz), and gives back the text. The form of the connection (for example stdin and stdout with a length prefix, or a local socket) is open.
- **`googletrans` (D-079):**
  - It is async only. The eval adapter uses one event loop for all calls.
  - `raise_exception=True` is necessary. With the default, a failed call gives the input text as the "translation".
  - The timeout is 5 s, explicit. There are no retries.
  - In the program, a failed call must stop the program or show the error clearly (R10). Do not change silently to another translator.
- **Speed:** OhanASR 0.164 + Google 0.265 = 0.429 model s per audio s on S5 [RUN]. The limit is 0.5 (K1, D-071). The Google time is network wait, not GPU time. Thus the ASR of the next segment can maybe run during the MT of the last segment [inference].
- **VRAM:** 4,646 (OhanASR) + 200 (TitaNet) + 148 (base) = 4,994 MiB [calc]. Only a run with both processes is a measurement.
- **Text:** OhanASR writes punctuation, case, and digits (D-075). The output rules of `text/clean.py` (D-066) apply.
- **Removal (D-072 part 4):** the `nemo-rnnt` adapter, NLLB (`mt/ct2_nllb.py`, CTranslate2, the cuBLAS preload), and the Seamless pipeline (`text/seamless.py`, `--seamless`). NeMo stays, because TitaNet uses it (D-058). Check each test that uses a removed part.
- **Description and K2:** "Local models only" in `pyproject.toml` and `README.md`, and constraint K2 in `PLAN.md` §1.2 ("No cloud speech or translation APIs"), change in C10, because the MT of the program then uses the network (D-079). In C9 only the eval tool used Google, so K2 is still true for the program.
- **Consent:** Aren uses the program only with the consent of the other people, in familiar circles (D-079).

## Open questions for C10

1. The form of the OhanASR worker and its contract (`ARCHITECTURE.md` §2.3), with options (R7).
2. Do any flags for the old pipelines stay? D-072 part 4 says that they go.
3. `googletrans` moves from the group `c9-eval` to the group `laptop` (R11). Do the eval tools (`scripts/c9_run.py`, `eval/google_mt.py`) stay, or does the adapter move into `mt/`?
4. The time box of C10.

## Read list for the next chat

1. `docs/handovers/10-integration.md` (this file)
2. `DECISIONS.md`: D-073, D-079, D-080 (at the end of the file in the project folder)
3. `ARCHITECTURE.md` §2 (modules and contracts) and §4 (data flow, threads, and queues)
4. `scripts/ohanasr_transcribe.py`
5. `src/tir_asr/eval/google_mt.py`

Read `RULES.md` with the Projects tool (`claude/RULES.md`, v0.6).

## First task in the next chat

1. Ask for the access to `/home/aren/dev/armenian-asr`. Do the chat start checklist (`RULES.md` §5.1).
2. Ask Aren for the CI state and the merge state, and ask the open questions.
3. Propose the design of the OhanASR worker (options, weak points, R7). Then write the tests in `TESTS.md` (R5) before the code.

## Do not

- Do not load OhanASR in the main environment (D-073).
- Do not set `raise_exception=False`, and do not add retries or a fallback to another translator (R10).
- **`uv remove` and `uv sync`** without `--group c9-eval` uninstall `googletrans` (C9). Until C10 moves it, use `uv run --group c9-eval` for a Google run.
- **The report and condition 1:** `scripts/c9_run.py report` uses N1 for the WER. For a comparison between models, use the substitution of the checked digit groups (D-075).
- **Remote writes:** write each output file one time into a new folder, write it to the laptop with the mtime guard, then stage it again and compare. After a `git switch` or a merge, stage the files again before a write.
- **`ruff` in the workspace:** only `--no-cache`, with `--config pyproject.toml`, in a scratch tree that has an empty file for each module of `tir_asr`.
- **From the earlier handovers:** measure before a change (R6); no parameter without Aren's approval (R10); Claude does not run tests in the workspace (D-038); the full `git add`, `git commit -m`, and `git push` commands, with no co-author line (D-039); no sub-agents (R15).
