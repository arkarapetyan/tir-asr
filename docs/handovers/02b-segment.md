# Handover 02b → 02c (C2b `types` + `segment` → C2c `asr` + `mt` adapters)

**Date:** 2026-10-25

## Goal of the next chat

Do chat C2c (`PLAN.md` §5.2 C2c): write the NeMo RNNT adapter `asr/nemo_rnnt.py` and the CTranslate2 NLLB adapter `mt/ct2_nllb.py` (`ARCHITECTURE.md` §2.3, §2.4), each on its own branch.

1. Branch `c2c-asr` first: write T-MODEL-ASR-01 and T-MODEL-ERR-01 (model). Aren runs them. They must fail (no adapter yet).
2. Write `asr/nemo_rnnt.py` until they pass. Aren runs them. Aren merges the branch into `main` when its tests pass on their own and CI is green.
3. Branch `c2c-mt` starts from the new `main`: T-MODEL-MT-01 and T-MODEL-ERR-02 (model), then `mt/ct2_nllb.py`. The test command sets no `LD_LIBRARY_PATH` (D-030).
4. Each branch adds its package to the `REQUIRED` set in `tests/unit/test_imports.py` (T-IMPORT-01): `tir_asr.asr` and `tir_asr.mt`. Both `__init__.py` files must not import the adapter.

## Branches and tests for each component (R3, Aren 2026-10-25)

Each component has its own branch and its own tests, also inside one chat. Aren merges a branch into `main` only when its tests pass on their own and CI is green. The next branch starts from the new `main`. Each handover (02b, 02c, 02d) repeats this section.

| Chat | Branch | Component (files) | Tests (`TESTS.md` §2.4) |
|---|---|---|---|
| C2b | `c2b-segment` | `segment/endpoint.py`, `segment/silero.py`, `types.py`, `config.py` | T-SEG-01–09, T-CFG-01, T-IMPORT-01; T-MODEL-VAD-01 (all PASS) |
| C2c | `c2c-asr` | `asr/nemo_rnnt.py` | T-MODEL-ASR-01, T-MODEL-ERR-01, T-IMPORT-01 |
| C2c | `c2c-mt` | `mt/ct2_nllb.py` | T-MODEL-MT-01, T-MODEL-ERR-02, T-IMPORT-01 |
| C2d | `c2d-output` | `output.py` | T-OUT-01–03, T-IMPORT-01 |
| C2d | `c2d-audio` | `audio/soundcard_mic.py` | T-AUDIO-01 (DESIGNED; select option 1 or 2 with Aren) |
| C2d | `c2d-pipeline` | `pipeline.py` | T-PIPE-01–04, T-IMPORT-01 |
| C2d | `c2d-cli` | `cli.py` | T-CLI-01, T-CFG-02, T-IMPORT-01; T-E2E-01; L-01–L-03 |

After Aren's approval of §2.4, Claude split T-CFG-01 and T-MODEL-ERR-01 into two tests each (same content), and added T-AUDIO-01. Tell Aren about T-MODEL-ERR-01 and T-MODEL-ERR-02 at the start of C2c.

## Current state

- **Code (branch `c2b-segment`):**
  - `src/tir_asr/types.py`: `AudioBlock`, `Segment`, `Line`, and the four `Protocol` interfaces.
  - `src/tir_asr/config.py`: `SAMPLE_RATE`, `VAD_FRAME`, and the frozen dataclass `Params` (the §6 values).
  - `src/tir_asr/segment/endpoint.py`: `Endpointer(params, vad)`, `SegmentError`.
  - `src/tir_asr/segment/silero.py`: `SileroSpeechProbability` (the only file that imports `torch` and `silero_vad`).
- **Tests:**
  - Unit: 47 pass (Aren's laptop, 2026-10-25; `test-results/c2b-unit.txt`). CI: Aren pushes the branch and reports.
  - Model: T-INSTALL-01 to T-INSTALL-04 and T-MODEL-VAD-01 pass (`test-results/c2b-model-vad.txt`).
  - C2 tests in `TESTS.md` §2.4: 12 PASS, 14 APPROVED, 1 DESIGNED (T-AUDIO-01).
- **Commits:** three commits on `c2b-segment` after `59b3c3e` (core with unit tests; Silero adapter with the model test; documents). Aren gives the hashes and says if the branch is merged into `main`.
- **Local files (not in git):** `models/nllb-200-distilled-600M-ct2-float16/`; `data/eval/c2-check{1,2}.wav` (44.1 kHz stereo), `.16k.wav` (16 kHz mono), `.hy.txt`, `.en.txt`; `test-results/`.

## Decisions made in C2b

| ID | Subject | Summary |
|---|---|---|
| D-036 | Interface of `segment` | `Params` dataclass; `Endpointer.short_segments`; `push(block)` calls the VAD; lengths counted in frames; `SegmentError` in `segment/endpoint.py`. All ACCEPTED by Aren on 2026-10-25. |

`ARCHITECTURE.md` is v0.4 (§2.2, §4, §5). It had uncommitted changes before C2b (`git status`). Aren commits v0.3 and v0.4 together.

## Facts that C2c needs

- **Reuse the install check:** `tests/model/test_install_check.py` has working code for the ASR (T-INSTALL-02: `hf_hub_download(..., local_files_only=True)`, `restore_from`, `change_decoding_strategy(decoder_type="rnnt")`, `transcribe([audio], batch_size=1)`) and for the MT (T-INSTALL-03: tokenizer, `translate_batch` with `target_prefix`, first target token removed) [SOURCE: the file]. The output of `transcribe` can be a tuple or a list of `Hypothesis` objects.
- **Constants for `config.py`** (`ARCHITECTURE.md` §5): `WARMUP_AUDIO_S`, `WARMUP_TEXT`, `MT_SRC_LANG`, `MT_TGT_LANG`. C2b added only `SAMPLE_RATE` and `VAD_FRAME`. T-CFG-01 checks `Params` only, so new constants do not break it.
- **Errors (D-036, part 5):** each adapter defines its own error class (`AsrError`, `MtError`) with the message `<module>: <cause>`.
- **Silero (for C4, not for C2c):** the model keeps its state between calls. C4 needs one `SileroSpeechProbability` instance for each audio source.
- **VAD margins (T-MODEL-VAD-01 [RUN]):** Silero keeps its probability high for about 150 ms after speech ends. The silence between the two segments of clip 1 + clip 2 is 19 frames (rule: 16). The pause of 448 ms inside clip 1 did not split it. D-027 stays open for C3 and C5.
- **Workspace limits:** a full `torch` install from PyPI works in the workspace (about 5 GB, 5 min), but the workspace has no GPU, and `huggingface.co` is blocked. The ASR and MT tests run on Aren's laptop only. In the workspace, check `ruff`, the unit tests, and the import of the core modules.

## Open questions

- **Aren (PLAN §10.2):** Q15 (a longer `vad_max_speech_s`), Q16 (CPU-only and limited-resource modes). Not for C2c.
- **QA (`TESTS.md` §3):** Q-06 (ASR commas → MT quality), Q-07 (5.1 s first CTranslate2 call), Q-09 (GPU after a long silence), Q-10 (GIL and the capture thread).
- **Time (R16):** C0 to C2b took 7.53 h (C2b: 0.58 h, 12:45–13:20). The expected total is about 22.5 h, or 23.2 h with the buffer (`PLAN.md` §5.1 note). Aren decides what to cut; C6 is the first candidate.
- **For the README (C8):** NeMo prints "No exporters were provided. This means that no telemetry data will be collected."; CTranslate2 lists `int8` on this GPU, but C1 found that `int8_float16` fails on RTX 50-series GPUs; the Silero load prints a `torch.jit.load` deprecation warning.
- **D-016 data point:** CTranslate2 was 16–33 ms faster than PyTorch on the next calls, with 734 MiB more VRAM and a 5.1 s first call (one run). C3 decides with repeated runs.

## Read list for the next chat

1. `docs/handovers/02b-segment.md` (this file)
2. `ARCHITECTURE.md`: §2.3, §2.4, §5, §7
3. `TESTS.md`: §2.4
4. `PLAN.md`: §5.2 C2c
5. `tests/model/test_install_check.py`: the code of T-INSTALL-02 and T-INSTALL-03

`RULES.md` and `DECISIONS.md` (D-022, D-030) are Project documents. Read them with the Projects tool.

## First task in the next chat

1. Check the access to `/home/aren/dev/armenian-asr`. If it is not connected, ask for it.
2. Do the chat start checklist (`RULES.md` §5.1).
3. Ask Aren for the output of `git branch --show-current && git log --oneline -4 && git status --short`. Check that `c2b-segment` is merged and CI is green. Check that the branch `c2c-asr` exists (it starts from the new `main`).
4. Make the workspace copy (ask Aren for the file list, R4). Run `ruff` and the unit tests.
5. Write T-MODEL-ASR-01 and T-MODEL-ERR-01.

## Do not

- **Remote writes:** use a new staged path for each write (for example `/mnt/user-data/outputs/c2c-r1/`). After each write, stage the files back and compare the checksums. To refresh a staged file, delete the old copy in the workspace first. A WAV file gets a `C2PA` chunk after its `data` chunk in the transfer, so compare the `fmt` and `data` bytes, not the file checksum.
- Do not try to write into `.github/workflows/`.
- **uv in the workspace:** `pip install --break-system-packages uv==0.12.21`, then `python3 -m uv`. The workspace copy needs a placeholder `README.md` for the build.
- **CI-style runs:** `uv sync --locked --no-group laptop`, then `uv run --no-sync …`. A plain `uv run` installs the `laptop` group (4 GB) [RUN].
- **Model test files:** import the `laptop` packages inside the test functions, because CI collects the file. Command: `HF_HUB_OFFLINE=1 uv run --no-sync pytest <file> -m model -s -v 2>&1 | tee test-results/<name>.txt` (`-m` on the command line replaces the `addopts` value) [RUN].
- `import soundcard` fails with no PulseAudio server, and with `python -c` (it reads `sys.argv[1]`). Use a script file or stdin.
- Do not use the CTranslate2 compute type `auto`. Until the `mt` adapter has the preload (D-030), CTranslate2 needs `LD_LIBRARY_PATH=$PWD/.venv/lib/python3.12/site-packages/nvidia/cublas/lib`.
- `du` on the Hugging Face cache folders shows only KB (links). Use `ls -laL`.
- **Mutation checks:** two edits of the same file size in the same second keep a stale `.pyc`. Set `PYTHONDONTWRITEBYTECODE=1` and delete `__pycache__` before each run.
- **ruff:** after you add a new module, run `ruff check --fix .`. The sort of the import blocks depends on whether `tir_asr.<module>` exists.
- Do not put two components on one branch. Do not tell Aren to merge a branch before its own tests pass (R3).
- Do not start sub-agents (R15). Do not make decisions without the R7 steps.
