# Handover 01 → 02 (C1 Research → C2 Walking skeleton)

**Date:** 2026-10-24

## Goal of the next chat

Do chat C2, Walking skeleton (`PLAN.md` §5.2 C2): microphone → VAD → ASR → MT → terminal, label "Me".

1. Install check first: the first candidates on Aren's laptop with GPU support (D-014, D-015, D-016).
2. Module contracts and data types in `ARCHITECTURE.md`. Add the approved parameter `mt_compute_type = float16` to the parameter table (approved 2026-10-24, D-015).
3. Tests in `TESTS.md` (TDD), then the thin modules.
4. Measure the latency of each line (K1).

## Current state

- **Code:** no code change in C1.
- **Tests:** no new tests in C1. Status as at the end of C0/S1 (see `test-results/`).
- **Last commit on `main`:** `3bf69fd` at the start of C1. Aren gives the hash of the C1 commit at the start of C2.
- **Research:** `docs/research/RESEARCH.md` exists on the laptop only. Aren decided not to commit it.
- **Eval scripts:** `docs/eval/scripts.md` (4 conversation scripts, Armenian and English references, recording rules). Aren records the audio into `data/eval/`.
- **Model weights:** Aren downloads them before C2 into `~/.cache/huggingface/hub`. The log is `test-results/c1-downloads.txt`. Problems with the download are a C2 topic.

## Decisions made in C1

| ID | Subject | Summary |
|---|---|---|
| D-013 | Scope | Eastern Armenian only. |
| D-014 | ASR | C2: `nvidia/stt_hy_fastconformer_hybrid_large_pc` on NeMo, RNNT decoder. Planned second path: the same model on ONNX Runtime with the CTC head (`OpenVoiceOS/stt_hy_fastconformer_hybrid_large_pc_onnx`). C3: ASR-1 (NeMo-RNNT, NeMo-CTC, ONNX-CTC), `facebook/seamless-m4t-v2-large`, `BuzzASR/armenian`. |
| D-015 | MT | C2: `facebook/nllb-200-distilled-600M` on CTranslate2, `mt_compute_type = float16`; the install check also times it on PyTorch. C3: OPUS-MT (CTranslate2), NLLB-600M (CTranslate2), Seamless text-to-text (PyTorch). |
| D-016 | Runtime | PyTorch (CUDA 13 build) and CTranslate2 (MT) from C2. |
| D-017 | Speakers (C5) | Embedding per segment + own online clustering. Shortlist: `pyannote/wespeaker-voxceleb-resnet34-LM`, `speechbrain/spkrec-ecapa-voxceleb`, `nvidia/speakerverification_en_titanet_large`. |
| D-018 | VAD | Silero VAD on the CPU first, WebRTC VAD second. Claude proposes the settings in C2 with numbers; Aren approves (R10). |
| D-019 | Eval data | At least 20 recordings, several voices and devices, from the 4 scripts; some through a real call. No public eval set. C5: recordings with other people. |
| D-020 | Capture | `soundcard` first, `sounddevice` second. Sim tests: `pactl load-module module-null-sink`. |
| D-007 | Python | 3.12 stays (C1 note). |

## Facts that C2 needs (details in `RESEARCH.md` §0)

- PyTorch 2.14.1 on PyPI: the Linux wheel uses CUDA 13.0. Blackwell (sm_120) kernels exist only in the CUDA 13.0 and 13.2 builds, not in the CUDA 12.6 build.
- CTranslate2 4.8.3: wheels built with CUDA 12.8. They need the CUDA 12 cuBLAS (for example `nvidia-cublas-cu12`) and `LD_LIBRARY_PATH`. INT8 is disabled on sm120. The value `auto` for the compute type selects `int8_float16`, which fails on RTX 50-series GPUs with `CUBLAS_STATUS_NOT_SUPPORTED`.
- NeMo 3.0.0 `[asr]` pins `lightning>2.2.1,<=2.4.0`; pyannote.audio 4.0.7 needs `lightning>=2.4`. Only 2.4.0 fits both [RUN: resolution].
- torchaudio is in maintenance (newest 2.11.0); the resolver selects it with torch 2.14.1 [UNVERIFIED that they work together].
- pyannote telemetry is on by default; `PYANNOTE_METRICS_ENABLED=0` stops it.
- `diart` 0.9.2 does not install with `pyannote.audio` 4.0.7 (numpy conflict) [RUN].

## Open questions

- **Latency definition (C2 decision in `PLAN.md`):** from the VAD end, or from the true end of speech (VAD end + minimum silence)? Claude proposed the true end in C1; Aren did not select it.
- **Not selected in C1:** a sim test with both sources at the same time (C4), a warm-up run at startup.
- **R5:** C1 found test ideas (Armenian normalization rules for WER, a resample test, call-path clips). They are in `PLAN.md` §5.2 C3/C4. They go into `TESTS.md` when C2/C3 design the tests.
- **Known limits so far** (`PLAN.md` C8): Eastern Armenian only; MT for each segment alone («նա» = he or she); overlapping remote speakers get one label.

## Read list for the next chat

1. `docs/handovers/01-research.md` (this file)
2. `RULES.md`
3. `PLAN.md`: §1, §4, §5.2 (C2), §9
4. `ARCHITECTURE.md`
5. `TESTS.md`

`DECISIONS.md` D-013 to D-020 and `RESEARCH.md` §0: only if this handover does not give a detail (ask Aren, R4).

## First task in the next chat

1. Ask for access to `/home/aren/dev/armenian-asr`.
2. Do the chat start checklist (`RULES.md` §5.1).
3. Read `test-results/c1-downloads.txt` (ask Aren, R4).
4. Propose the install check commands (uv add for torch, NeMo `[asr]`, ctranslate2, the CUDA 12 cuBLAS, silero-vad, soundcard) and one model test for each model.

## Do not

- **Remote writes:** do not reuse a staged path. In C1, a second write from the same staged path kept the old content with no error (new time stamp, old size). A write from a new staged path worked. After each write, check the size with the folder list and compare the checksums.
- Do not try to write into `.github/workflows/`.
- **uv in the workspace:** `pip install uv==0.12.21` puts uv in `/root/.local/bin`, but `uv` on the PATH stayed 0.11.32. Use `python3 -m uv`.
- **Web access in the workspace:** `huggingface.co` is blocked for curl. WebFetch opens only URLs that appear in a search result or in a fetched page. GitHub raw files work with curl. `gh api` is blocked for repositories that are not attached.
- Do not use the CTranslate2 compute type `auto` on this GPU.
- Do not start sub-agents (R15). Do not make decisions without the R7 steps.
