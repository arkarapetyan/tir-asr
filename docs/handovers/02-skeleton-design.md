# Handover 02 → 02b (C2 install check and design → C2b `types` + `segment`)

**Date:** 2026-10-25

## Goal of the next chat

Do chat C2b (`PLAN.md` §5.2 C2b): write `types.py` (`ARCHITECTURE.md` §3), the core `Endpointer` (`segment/endpoint.py`), and the Silero adapter (`segment/silero.py`) (§2.2).

1. Write T-SEG-01 to T-SEG-09, T-CFG-01, and T-IMPORT-01 (unit). Run them. They must fail.
2. Write `types.py`, `config.py`, and `segment/endpoint.py` until the unit tests pass.
3. Write `segment/silero.py` and T-MODEL-VAD-01 (model). Aren runs it.
4. All work is on the branch `c2b-segment`. Aren merges it into `main` when its tests pass on their own and CI is green.

## Branches and tests for each component (R3, Aren 2026-10-25)

Each component has its own branch and its own tests, also inside one chat. Aren merges a branch into `main` only when its tests pass on their own and CI is green. The next branch starts from the new `main`. Each handover (02b, 02c, 02d) repeats this section.

| Chat | Branch | Component (files) | Tests (`TESTS.md` §2.4) |
|---|---|---|---|
| C2b | `c2b-segment` | `segment/endpoint.py`, `segment/silero.py`, with the shared `types.py` and `config.py` (first user) | T-SEG-01–09, T-CFG-01, T-IMPORT-01; T-MODEL-VAD-01 |
| C2c | `c2c-asr` | `asr/nemo_rnnt.py` | T-MODEL-ASR-01, T-MODEL-ERR-01, T-IMPORT-01 |
| C2c | `c2c-mt` | `mt/ct2_nllb.py` | T-MODEL-MT-01, T-MODEL-ERR-02, T-IMPORT-01 |
| C2d | `c2d-output` | `output.py` | T-OUT-01–03, T-IMPORT-01 |
| C2d | `c2d-audio` | `audio/soundcard_mic.py` | T-AUDIO-01 (DESIGNED; select option 1 or 2 with Aren) |
| C2d | `c2d-pipeline` | `pipeline.py` | T-PIPE-01–04, T-IMPORT-01 |
| C2d | `c2d-cli` | `cli.py` | T-CLI-01, T-CFG-02, T-IMPORT-01; T-E2E-01; L-01–L-03 |

After Aren's approval of §2.4, Claude split T-CFG-01 and T-MODEL-ERR-01 into two tests each (same content), and added T-AUDIO-01. Tell Aren about this at the start of each chat that uses them.

## Current state

- **Code:** no product code yet. `tests/model/test_install_check.py` exists (T-INSTALL-02 to T-INSTALL-04).
- **Dependencies:** group `laptop` (torch 2.14.1+cu130, nemo-toolkit 3.0.0, ctranslate2 4.8.3, nvidia-cublas-cu12, silero-vad 6.2.3, soundcard 0.4.6, transformers 5.20.2, sentencepiece, huggingface-hub) in `default-groups`. `numpy` is a main dependency. CI excludes the group (D-021, D-028).
- **Tests:**
  - Unit: 26 pass (Aren's laptop and CI, 2026-10-25).
  - Model: T-INSTALL-01 to T-INSTALL-04 pass (Aren's laptop, 2026-10-25). T-INSTALL-05 passes (CI).
  - C2 tests in `TESTS.md` §2.4: 26 APPROVED and 1 DESIGNED (T-AUDIO-01), none written.
- **Commits:** two C2 commits after `0e127fd` (`build(deps): …`, `test(model): …`) and one design commit at the end of C2. Aren gives the hashes at the start of C2b.
- **Local files (not in git):** `models/nllb-200-distilled-600M-ct2-float16/` (CTranslate2 conversion); `data/eval/c2-check{1,2}.wav` (44.1 kHz stereo), `.16k.wav` (16 kHz mono, converted by Claude with `soxr` VHQ), `.hy.txt`, `.en.txt`; `test-results/c2-*.txt`.

## Decisions made in C2

| ID | Subject | Summary |
|---|---|---|
| D-021 | Dependencies and CI | Group `laptop`; CI runs `uv sync --locked --no-group laptop` and `uv run --no-sync`. |
| D-022 | Warm-up | One warm-up call for each GPU model: ASR with 2 s of zeros, MT with a fixed sentence. |
| D-023 | Latency definition | From the true end of speech: the start of the first silent VAD frame. |
| D-024 | Line format | Brief format plus `[Latency: vad …, asr …, mt …, out … \| Total …]`; time = segment start since the program start. |
| D-025 | WAV source | Test code only (`tests/support/`), no CLI flag. |
| D-026 | VAD parameters | `vad_threshold` 0.5, `vad_end_threshold` 0.35, `vad_speech_pad_ms` 30, `vad_min_speech_ms` 250, `vad_max_speech_s` 10. |
| D-027 | End rule | `vad_min_silence_ms = 500` (start value, open for change). |
| D-028 | Declared imports | Declare each package that our code imports. |
| D-029 | Threads and queue | One capture thread for each source, one worker, a queue with no size limit. |
| D-030 | CUDA 12 cuBLAS | The `mt` adapter preloads it from `nvidia-cublas-cu12`; no `LD_LIBRARY_PATH`. |
| D-031 | Empty ASR text | `HY: (no text)` block until C7; C7 removes it. |
| D-032 | End of a test clip | No added silence; the end-to-end test plays clip 1, then clip 2. |
| D-033 | `mt_beam_size` | 2. |
| D-034 | Keys | No start/pause keys in the MVP; decide after M3. |
| D-035 | Chat split | C2b, C2c, C2d; one branch and its own tests for each component (R3). |

## Facts that C2b needs

- **Silero VAD 6.2.3** [SOURCE: `utils_vad.py`, `model.py`]: only 512-sample frames at 16 kHz; `load_silero_vad()` loads the JIT model; the import sets the PyTorch CPU threads to 1 [RUN].
- **Our rule** (`ARCHITECTURE.md` §2.2) closes after 16 whole silent frames (512 ms). Silero `VADIterator` closes one frame later. A frame in [0.35, 0.5) counts as silence during a silence.
- **Unit-test times:** frame `k` arrives at `(k + 1) × 0.032` s; its start time is `k × 0.032` s (`TESTS.md` §2.4).
- **T-INSTALL-04 pauses:** clip 1: 64 ms (sentence end), 448 ms (sentence end), speech ends 152 ms before the clip end; clip 2: 96 ms (sentence end), 64 ms (comma), speech starts at 0.480 s, ends 914 ms before the clip end. Clip 1 + clip 2 give 2 segments at 500 ms (calc).
- **Core and adapter:** `segment/__init__.py` and `segment/endpoint.py` must not import `torch` or `silero_vad` (T-IMPORT-01, D-021). Only `segment/silero.py` imports them.

## Open questions

- **Aren (PLAN §10.2):** Q15 (a longer `vad_max_speech_s`), Q16 (CPU-only and limited-resource modes). Not for C2b.
- **QA (`TESTS.md` §3):** Q-06 (ASR commas → MT quality), Q-07 (5.1 s first CTranslate2 call), Q-09 (GPU after a long silence), Q-10 (GIL and the capture thread).
- **Time (R16):** C2 took 2.65 h (10:01–12:40). The expected total is about 23 h, or 23.7 h with the buffer (`PLAN.md` §5.1 note). Aren decides what to cut; C6 is the first candidate.
- **For the README (C8):** NeMo prints "No exporters were provided. This means that no telemetry data will be collected."; CTranslate2 lists `int8` on this GPU, but C1 found that `int8_float16` fails on RTX 50-series GPUs.
- **D-016 data point:** CTranslate2 was 16–33 ms faster than PyTorch on the next calls, with 734 MiB more VRAM and a 5.1 s first call (one run). C3 decides with repeated runs.

## Read list for the next chat

1. `docs/handovers/02-skeleton-design.md` (this file)
2. `RULES.md`
3. `ARCHITECTURE.md`: §2.2, §3, §5, §6
4. `TESTS.md`: §2.4
5. `PLAN.md`: §5.2 C2b

## First task in the next chat

1. Check the access to `/home/aren/dev/armenian-asr`. If it is not connected, ask for it.
2. Do the chat start checklist (`RULES.md` §5.1).
3. Ask Aren for the hashes of the C2 commits. Check that the branch `c2b-segment` exists (one branch for each component, see above).
4. Make the workspace copy (ask Aren for the file list, R4). Run `ruff` and the unit tests.
5. Write T-SEG-01 to T-SEG-09.

## Do not

- **Remote writes:** use a new staged path for each write. After each write, compare the checksums. A WAV file gets a `C2PA` chunk after its `data` chunk in the transfer, so compare the `fmt` and `data` bytes, not the file checksum.
- Do not try to write into `.github/workflows/`.
- **uv in the workspace:** `pip install --break-system-packages uv==0.12.21`, then `python3 -m uv`. The workspace copy needs a placeholder `README.md` for the build.
- **CI-style runs:** `uv sync --locked --no-group laptop`, then `uv run --no-sync …`. A plain `uv run` installs the `laptop` group (4 GB) [RUN].
- **Model test files:** import the `laptop` packages inside the test functions, because CI collects the file. Command: `HF_HUB_OFFLINE=1 uv run --no-sync pytest <file> -m model -s -v` (`-m` on the command line replaces the `addopts` value) [RUN].
- `import soundcard` fails with no PulseAudio server, and with `python -c` (it reads `sys.argv[1]`). Use a script file or stdin.
- Do not use the CTranslate2 compute type `auto`. Until C2c adds the preload (D-030), CTranslate2 needs `LD_LIBRARY_PATH=$PWD/.venv/lib/python3.12/site-packages/nvidia/cublas/lib`.
- `du` on the Hugging Face cache folders shows only KB (links). Use `ls -laL`.
- Do not put two components on one branch. Do not tell Aren to merge a branch before its own tests pass (R3).
- Do not start sub-agents (R15). Do not make decisions without the R7 steps.
