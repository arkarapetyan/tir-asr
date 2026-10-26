# Handover 03 → next (C3 evaluation set and bake-off → C6 P4 implementation, or C4)

**Date:** 2026-10-26

## Goal of the next chat

Aren decides the order (`PLAN.md` §5.2 C6, "Open"):

- **Option 1:** C6 now: put P4 (D-053, Seamless end to end on the GPU) into the program, with the tests first (R5; D-050 was for C3 only).
- **Option 2:** C4 (two audio sources) first, as in the plan; P4 after M3.

Claude's note: P4 changes the worker (two calls on one model for each segment; the second step takes the audio, not the text) and the contracts of `ARCHITECTURE.md` §2.3, §2.4, and §2.6. C4 and C5 also change the worker and its load. P4 first prevents a second change of these parts [inference].

## Current state

- **Branches:** `c3-normalize`, `c3-metrics`, `c3-data`, and `c3-run` are merged into `main` (merge hashes: Aren gives them). `c3-candidates` holds the candidate commits and the C3 documents; Aren merges it at the end of C3.
- **Code:** `tir_asr.eval` core modules `normalize`, `metrics`, `data`, `run`; candidate adapters `nemo_ctc`, `opus_ct2`, `buzz_whisper`, `seamless`; `scripts/bakeoff.py`; `scripts/probe_cpu.py`. The program still runs P1 (NeMo RNNT + NLLB).
- **Tests:** 167 unit tests pass (`test-results/c3-cand2-green.txt`). All bake-off runs passed.
- **Documents:** `ARCHITECTURE.md` v0.18, `PLAN.md` v0.13, `DECISIONS.md` to D-053, `TESTS.md` (§2.5 and §3), `docs/eval/results.md`.
- **Eval data:** `data/eval/raw/s{1,2,3}.{mic,call}.wav` (48 kHz, float32) and `s{1,2,3}.labels.txt` (Aren). `s1.wav` is a mix; the eval does not use it.
- **New in the Hugging Face cache:** `Helsinki-NLP/opus-mt-hy-en`, `BuzzASR/armenian`, `facebook/seamless-m4t-v2-large` (only the Transformers files), the ONNX repository. New folder `models/opus-mt-hy-en-ct2-float16`.

## Decisions made in C3

| ID | Subject | Summary |
|---|---|---|
| D-046 | Eval data | Labels by Aren; main numbers on the joined text of each file; line view by the largest overlap; S1 interruptions not edited. |
| D-047 | Normalization | NFKC, lowercase, in-word marks deleted except «՞» (P1), «եւ» → «եվ», other marks → space; no number rule (N1). |
| D-048 | Cut ends | s2-10 and s3-10 references = the audio; 1.0 s of zeros after each file (end rule). |
| D-049 | C3 scope | Full shortlists (option B); `sacrebleu` and `scipy` in the dev group. |
| D-050 | Process | No red run for the rest of the C3 eval code (C3 only). |
| D-051 | Bake-off structure | Core `run.py`, runner `scripts/bakeoff.py`, eval adapters; one branch for all candidates. |
| D-052 | ONNX-CTC | Decided after `nemo-ctc`: CTC WER 12.7 % > RNNT 10.6 %, so no ONNX run. |
| D-053 | ASR and MT | **P4: Seamless end to end on the GPU.** P1 code stays. CPU mode (Q16) waits for the Mathrix team. |

## Facts for P4

- **Numbers [RUN]:** WER 6.8 %, chrF 59.0 (P1: 10.6 %, 51.7). ASR call mean 0.32 s, max 0.42 s; S2TT call mean 0.31 s, max 0.41 s; load 3.9 s; warm-up 0.66 s; VRAM 2884 MiB. Energy 3.3 times P1. Peak temperature 59 °C.
- **API that works [RUN]** (`src/tir_asr/eval/seamless.py`): `AutoProcessor(audio=…, sampling_rate=16000, return_tensors="pt")` (the card says `audios=`, transformers 5.20.2 uses `audio=`); `SeamlessM4Tv2ForSpeechToText.from_pretrained(…, dtype=torch.float16)`; `generate(**inputs, tgt_lang=…)`; `processor.decode(tokens[0].tolist(), skip_special_tokens=True)`.
- **Rules that need a new form:** D-031 (empty HY text: P4 gives the EN text from the audio, also when the HY text is empty); D-022 (warm-up: two calls on one model); the startup log and the load order (D-043).
- **Known effects:** the HY line and the EN line are two separate outputs and can differ. Seamless did not leave out sentences on S1–S3 (Q-13). Licence CC-BY-NC 4.0 (the same as NLLB).
- **CPU:** P4 does not meet K1 on the CPU (9.9–36.4 s for each line); P1 does (0.38–0.43 s).

## Open questions

- **Aren:** the order (P4 or C4); the answer of the Mathrix team on the laptop and a CPU mode (Q16); the C3 time for the time log.
- **Plan:** Q15 (no hard cut in S1–S3); the line view numbers are in the JSON files, not in the results table.
- **QA (`TESTS.md` §3):** Q-04, Q-05, Q-07, Q-10, Q-12 are still open.

## Traceability note (R15)

At 17:09:48, a write of `scripts/bakeoff.py`, `tests/unit/test_imports.py`, and `ARCHITECTURE.md` (the `nemo-ctc` and `opus-ct2` changes) came from Claude's workspace folder `c3-w16`. This step is not in the visible text of the C3 chat. Claude first reported it as an unknown write, then found its own folder. Aren read the change and committed it.

## Read list for the next chat

1. `docs/handovers/03-eval.md` (this file)
2. `PLAN.md`: §5.2 C6 (and C4 if C4 is next), §10.2
3. `ARCHITECTURE.md`: §2.3, §2.4, §2.6, §4, §6, §8.2
4. `docs/eval/results.md`
5. `src/tir_asr/eval/seamless.py`

`RULES.md` and `DECISIONS.md` (D-022, D-031, D-043, D-053) are Project documents. Read them with the Projects tool.

## First task in the next chat

1. Ask for the access to `/home/aren/dev/armenian-asr`.
2. Do the chat start checklist (`RULES.md` §5.1).
3. Ask Aren for the order, the Mathrix answer (Q16), the merge hash of `c3-candidates`, and the state of CI.
4. For P4: propose the contract changes (§2.3, §2.4, §2.6, §7) with the R7 steps, then the tests.

## Do not

- **Remote writes:** use a new output path for each write. Before a new stage, delete the old staged copy. After each write, stage the file back and compare the checksums.
- **Git state first:** do not write a tracked file while Aren has uncommitted work of a different branch or before a branch change; ask for `git status` first (C3).
- **Escapes:** `\uXXXX` in a tool input becomes the character itself. To write an escape into a file, use a placeholder and replace it in a script (C3).
- **Commands:** each command prints to the terminal and writes its result file (`tee`) (Aren, C3).
- **MT and Seamless runs:** `env -u LD_LIBRARY_PATH HF_HUB_OFFLINE=1` (D-030).
- **Transformers 5.20.2:** `dtype=`, not `torch_dtype=`; the Seamless processor takes `audio=`.
- **Unit tests in the workspace:** none (D-038); ruff only, with `--no-cache`, on a scratch copy of the project layout.
- **T-IMPORT-01:** a new adapter module on the disk must be in `ADAPTERS` before the next unit-test run, or T-IMPORT-01 fails.
- Do not remove `STOP_POLL_S` (D-044). Load order ASR, MT, VAD (D-043). Do not use `uv run` in `run.sh` (D-045). Do not start sub-agents (R15).
