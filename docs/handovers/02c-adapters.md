# Handover 02c → 02d (C2c `asr` + `mt` adapters → C2d `audio` + `output` + `pipeline` + `cli`)

**Date:** 2026-10-25

## Goal of the next chat

Do chat C2d (`PLAN.md` §5.2 C2d): the microphone adapter, the line format, the threads and the queue, the startup, and the stop (`ARCHITECTURE.md` §2.1, §2.5–§2.7, §4). Then M1: the walking skeleton works on Aren's laptop, and each line shows its latency (K1).

1. Branch `c2d-output` first (core, unit tests only). Then `c2d-audio`, `c2d-pipeline`, `c2d-cli`, each from the new `main`.
2. Select the T-AUDIO-01 option (1: live, 2: sim with a null sink) with Aren before `c2d-audio`.
3. Each branch adds its core modules to the `REQUIRED` set in `tests/unit/test_imports.py` (T-IMPORT-01). `tir_asr.audio.soundcard_mic` is already in `ADAPTERS`.

## Branches and tests for each component (R3, Aren 2026-10-25)

Each component has its own branch and its own tests, also inside one chat. Aren merges a branch into `main` only when its tests pass on their own and CI is green. The next branch starts from the new `main`.

| Chat | Branch | Component (files) | Tests (`TESTS.md` §2.4) |
|---|---|---|---|
| C2b | `c2b-segment` | `segment/endpoint.py`, `segment/silero.py`, `types.py`, `config.py` | T-SEG-01–09, T-CFG-01, T-IMPORT-01; T-MODEL-VAD-01 (all PASS) |
| C2c | `c2c-asr` | `asr/nemo_rnnt.py` | T-MODEL-ASR-01, T-MODEL-ERR-01, T-MODEL-ERR-03, T-IMPORT-01 (all PASS) |
| C2c | `c2c-mt` | `mt/ct2_nllb.py` | T-MODEL-MT-01, T-MODEL-ERR-02, T-MODEL-ERR-04, T-IMPORT-01 (all PASS) |
| C2d | `c2d-output` | `output.py` | T-OUT-01–03, T-IMPORT-01 |
| C2d | `c2d-audio` | `audio/soundcard_mic.py` | T-AUDIO-01 (DESIGNED; select option 1 or 2 with Aren) |
| C2d | `c2d-pipeline` | `pipeline.py` | T-PIPE-01–04, T-IMPORT-01 |
| C2d | `c2d-cli` | `cli.py` | T-CLI-01, T-CFG-02, T-IMPORT-01; T-E2E-01; L-01–L-03 |

## Current state

- **Code on `main`:** `types.py`, `config.py`, `segment/` (C2b); `asr/` (merge `b8871a0`); `mt/` (branch `c2c-mt`; Aren gives the merge hash).
- **Tests:** unit 49 pass; model T-MODEL-VAD-01, T-MODEL-ASR-01, T-MODEL-MT-01, T-MODEL-ERR-01 to T-MODEL-ERR-04 pass (Aren's laptop, 2026-10-25; files `test-results/c2c-*.txt`). CI: Aren reports.
- **Documents:** `ARCHITECTURE.md` v0.6, `RULES.md` v0.5, `DECISIONS.md` to D-039, `TESTS.md` with the C2c results.

## Decisions made in C2c

| ID | Subject | Summary |
|---|---|---|
| D-037 | Interface of `asr` and `mt` | Class names `NemoRnntTranscriber`, `Ct2NllbTranslator`; the constructors load the models; no warm-up method; **the pipeline makes the warm-up calls**; **`cli.py` is only the `argparse` interface**. |
| D-038 | Test runs in C2c | No workspace copy; Aren runs `ruff` and the unit tests. For C2c only: Aren decides again at the start of C2d. |
| D-039 | Commits | No bulk commits: one logical change in each commit. Claude gives the full `git add … && git commit -m … && git push` command. No co-author line (`RULES.md` R12). |

Aren also said: tests must not use a private attribute of an adapter.

## Facts that C2d needs

- **Adapter interfaces** (`ARCHITECTURE.md` §2.3, §2.4):
  - `NemoRnntTranscriber(repo=ASR_REPO, filename=ASR_FILE)`; `transcribe(audio) -> str` (the text can be empty); `AsrError`.
  - `Ct2NllbTranslator(params, model_dir=MT_MODEL_DIR)`; `translate(text) -> str`; `MtError`; `translate("")` raises `mt: empty input text`, so the pipeline must not call MT for an empty text (D-031, T-PIPE-03).
  - `config.py` has `WARMUP_AUDIO_S = 2.0` and `WARMUP_TEXT`, `MT_SRC_LANG`, `MT_TGT_LANG`.
- **`Endpointer`** (C2b): `Endpointer(params, vad)`; `push(block) -> Segment | None`; public integer `short_segments`.
- **Startup (D-037):** §2.7 still lists six startup steps under `cli`. Aren decided that `cli.py` is only the `argparse` interface. Propose the new place of each step to Aren before the code.
- **Warm-up numbers [RUN]:** ASR warm-up 0.412 s, then 0.021–0.028 s for each call (ratio 1.00). MT warm-up 0.126 s, then 0.066–0.076 s (ratio 1.09). Load: ASR 1.47 s, MT 1.31 s.
- **GPU memory [RUN]:** ASR 897 MiB peak (torch); MT +1800 MiB (`nvidia-smi`).
- **The MT adapter loads cuBLAS 12 at import** (D-030). `env -u LD_LIBRARY_PATH` in the test command proves it. It is [UNVERIFIED] whether an earlier `import ctranslate2` in another module breaks the preload. Import the MT adapter first.
- **The default `model_dir` is relative** (`models/…`): the program must start in the project folder.
- **NeMo output:** the NeMo load prints about 185 lines of warnings and configuration. `transcribe` uses `verbose=False`, so there is no progress bar for each segment. The startup log design must handle the load lines.
- **Q-07 [RUN]:** the first CTranslate2 call took 0.126 s in T-MODEL-MT-01, but 5.1 s in T-INSTALL-03. The cause is not known.

## Open questions

- **Aren (PLAN §10.2):** Q15 (a longer `vad_max_speech_s`), Q16 (CPU-only and limited-resource modes).
- **QA (`TESTS.md` §3):** Q-06, Q-07, Q-09, Q-10.
- **C2d:** the place of each startup step (D-037); the T-AUDIO-01 option; the owner of the exit codes in T-PIPE-02 and T-PIPE-04 (pipeline or `cli.py`).
- **Time (R16):** C0 to C2b took 7.53 h. C2c started at 13:32. Aren writes the C2c time in the `PLAN.md` time log.
- **For the README (C8):** NeMo prints "No exporters were provided…" and about 185 load lines; `int8_float16` fails on RTX 50-series GPUs; the Silero load prints a `torch.jit.load` deprecation warning; start the program in the project folder.

## Read list for the next chat

1. `docs/handovers/02c-adapters.md` (this file)
2. `ARCHITECTURE.md`: §2.1, §2.5–§2.7, §3, §4, §7
3. `TESTS.md`: §2.4
4. `PLAN.md`: §5.2 C2d
5. `src/tir_asr/types.py`

`RULES.md` and `DECISIONS.md` (D-029, D-031, D-034, D-037, D-039) are Project documents. Read them with the Projects tool.

## First task in the next chat

1. Check the access to `/home/aren/dev/armenian-asr`. If it is not connected, ask for it.
2. Do the chat start checklist (`RULES.md` §5.1).
3. Ask Aren if D-038 (no workspace copy) applies to C2d too.
4. Ask Aren for the merge hash of `c2c-mt` and the state of CI. Check that the branch `c2d-output` exists.
5. Write T-OUT-01 to T-OUT-03.

## Do not

- **Remote writes:** use a new staged path for each write (for example `/mnt/user-data/outputs/c2d-r1/`). After each write, stage the files back and compare the checksums. To refresh a staged file, delete the old copy in the workspace first.
- **File times after git:** a branch change or a merge rewrites the file times. `device_commit_files` then rejects a write with an old `expectedMtimeMs`. Stage the file again, check that the content is the same, and write with the new time.
- **ruff cache:** the sort of an import of `tir_asr.<module>` depends on whether the module exists, and the `ruff` cache does not see this. Use `ruff check --no-cache` and `ruff format --no-cache --check`. The workspace has `ruff` 0.16.9; the laptop has 0.17.2 or newer.
- **Import blocks in model tests:** with `import torch` and an import of `tir_asr.<new module>` in one function, `ruff` wants no blank line while the module does not exist, and one blank line after it exists. Fix the block in the green step.
- **MT model tests:** always run them with `env -u LD_LIBRARY_PATH` (D-030).
- **Model test files:** import the `laptop` packages inside the test functions, because CI collects the file. Command: `HF_HUB_OFFLINE=1 uv run --no-sync pytest <file> -m model -s -v 2>&1 | tee test-results/<name>.txt`.
- **CI-style runs:** `uv sync --locked --no-group laptop`, then `uv run --no-sync …`. A plain `uv run` installs the `laptop` group (4 GB).
- `import soundcard` fails with no PulseAudio server, and with `python -c` (it reads `sys.argv[1]`). Use a script file or stdin.
- Do not use a private attribute of an adapter in a test (Aren).
- Do not commit red tests: CI runs T-IMPORT-01, and a red `REQUIRED` set breaks CI.
- Do not try to write into `.github/workflows/`.
- Do not put two components on one branch. Do not tell Aren to merge a branch before its own tests pass (R3).
- Do not start sub-agents (R15). Do not make decisions without the R7 steps.
