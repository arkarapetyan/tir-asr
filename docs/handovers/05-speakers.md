# Handover 05 → 06 (C5 speaker labels → C6 P4)

**Date:** 2026-10-27

## Goal of the next chat

C6 (`PLAN.md` §5.2 C6, D-053, D-056): put P4 (Seamless end to end, `SeamlessM4Tv2ForSpeechToText`) in the program behind a flag. P1 stays the default. Optimize P4 for the GPU and the CPU, for example one encoder pass for the HY line and the EN line, and INT8 if the quality drop is acceptable (measured, R6). Make a separate P4 performance test and a P4 live test. No custom ONNX. Aren gives the C6 time box first (D-056, question 5).

## Current state

- **M3 (MVP) reached** (D-060 part 7). The program captures `Me` (the microphone) and the system audio. System lines get `Speaker 1`, `Speaker 2`, …, and a short first segment gets `Unidentified`. The latency line has the step `spk`.
- **Speaker step** (D-058, D-059): TitaNet-large (`speakers/titanet.py`, about 200 MiB VRAM) and the online centroid rule (`speakers/cluster.py`, `CentroidClusterer`). `SpeakerLabeler.label(segment)` runs in the worker after MT, only for `System` and only for a text that is not empty. `spk_threshold` = 0.50, `spk_min_new_s` = 1.0 s.
- **Clean stop** (D-061): `run()` waits for all threads (`STOP_JOIN_S` = 2.0 s) before it returns. The capture threads close their audio streams. A thread that does not stop gives `tir-asr: stop: thread <name> did not stop in <s> s`.
- **Branches:** `c5-d056`, `c5-cluster`, `c5-embed`, `c5-pipeline`, and `c5-stop`, one after the other. Aren merges `c5-stop` into `main` at the end of C5 (merge hash: Aren gives it).
- **Tests (Aren's laptop):** see `TESTS.md` §2.7 for each branch.
  - Unit: 229 passed.
  - Model: T-MODEL-SPK-01, T-MODEL-SPK-02, T-E2E-01, and T-E2E-02 passed (no abort line).
  - Sim: T-SIM-01 and T-SIM-02 passed. T-SIM-02: 19 of 19 labels correct, `spk` 0.01–0.02 s.
  - Live: L-06 fails on one point (fixed by D-060). The exit check passes after D-061.
- **Documents:** `ARCHITECTURE.md` v0.27, `PLAN.md` v0.16, `DECISIONS.md` to D-061, `TESTS.md` §2.7, §3 (Q-04 answered, Q-14 data), §4 (L-02, L-06). `README.md` has "Known limits (M3)".

## Decisions made in C5

| ID | Subject | Summary |
|---|---|---|
| D-056 | Target hardware, C6 scope, order | No question to Mathrix (Q16 closed); P4 in C6 behind a flag, P1 the default; optimizations; P4 tests; no custom ONNX; C5 before C6. |
| D-057 | Speaker design and process | Eval streams S1, S2, S3, and D; label accuracy after the best mapping; three candidates; rules A and B-max measured; `spk_min_new_s`; the speaker step after MT; no red run. |
| D-058 | Speaker model and start values | TitaNet with rule A; 0.50 and 1.0 s; ECAPA, WeSpeaker, and the `spk-eval` group removed. |
| D-059 | Interface of the speaker step | `SpeakerEmbedder`, `Labeler`, `SpeakerLabeler`; `Line.spk_end`; load and warm-up; the `spk` step. |
| D-060 | L-06 result and the next steps | `Unidentified` for a short first segment; two voices in one segment recorded as a limit; the VAD measurements and the diagnostic line go to C7; the parameters stay. |
| D-061 | The clean stop | `run()` waits for its threads; the error line for a thread that does not stop. |

## Facts for C6 [RUN]

- From C3 (`docs/eval/results.md`): P4 on the GPU: WER 6.8 %, chrF 59.0, a line takes 0.63 s on average (at most 0.83 s), 2.9 GB VRAM. P4 on the CPU: 9.9–36.4 s per line. The 36.4 s line (s3-05) has an English output of normal length, so the cause of the long time is not known (D-058 correction of D-056 question 4).
- After the P1 load with TitaNet, the GPU memory used is 2508 MiB. The startup line shows `-256 MiB` at the speaker load; the cause is [UNVERIFIED].
- The clean stop waits at most 2.0 s for the worker. A P4 call on the GPU (at most 0.83 s) fits; a P4 call on the CPU (up to 36.4 s) does not, and then the stop gives the error line. C6 must check `STOP_JOIN_S` against the P4 times.
- The speaker step uses `segment.audio`, not the text. Thus P4 can change the text step and keep the speaker step as it is (D-056 rule). The worker calls the labeler only when the HY text is not empty.

## Open questions

1. D-056 questions for C6: a CPU mode of P1; INT8 on the GPU; the reuse of the encoder output; the 36.4 s line of the CPU probe; the C6 time box.
2. R16: C5 took about 4.4 h (1.4 h over its time box). The expected total is about 23.9 h. C6 is the first item to cut. Aren decides.
3. L-04 (`./run.sh --list-devices`) is still not run.
4. For C7 (D-060): the diagnostic line, the VAD measurements for fast changes and noises, and L-06 again.

## Read list for the next chat

1. `docs/handovers/05-speakers.md` (this file)
2. `PLAN.md`: §5.2 C6
3. `ARCHITECTURE.md`: §2.3, §2.4, §2.6 (with the clean stop), §2.8, §8.2
4. `src/tir_asr/eval/seamless.py`
5. `docs/eval/results.md`

`RULES.md` and `DECISIONS.md` (D-053, D-056, D-059, D-061) are Project documents. Read them with the Projects tool.

## First task in the next chat

1. Ask for the access to `/home/aren/dev/armenian-asr`.
2. Do the chat start checklist (`RULES.md` §5.1).
3. Ask Aren: the merge hash of `c5-stop` and the state of CI; the C6 time box; red runs in C6 or not (D-057 part 8 was for C5 only).
4. Propose the design of the text step for P1 and P4 (Template Method, D-053), the flag, the branches (R3), and the tests, with the R7 steps.

## Do not

- **Remote writes:** prepare the files in a scratch copy; write them only after Aren is on the branch of that change. Use a new output path for each write. After each write, stage the files back and compare the checksums.
- **An interrupted reply** can leave files that are already written on the laptop. Before new writes, compare the laptop files with the last outputs.
- **`ruff` in the workspace:** only `ruff check --no-cache` and `ruff format --no-cache --check`, with `--config pyproject.toml`, on a scratch copy that has the full `src/tir_asr` tree; else the import sort is wrong (D-038).
- **The device bridge** cannot stage files that are deeper than about 7 folder levels (for example, in `.venv`). Read a package from its wheel on PyPI.
- **Test commands:** sim and model runs with `env -u LD_LIBRARY_PATH HF_HUB_OFFLINE=1` (D-030). Use `tee -i` for a run that Aren can stop with Ctrl+C, so that the file keeps the summary.
- **Keep:** the clean stop and `STOP_JOIN_S` (D-061); `STOP_POLL_S` (D-044); the speaker step as its own component (D-056 rule); the load order: sources, ASR, MT, VAD, speaker model (D-057 part 6).
- **Commits:** the full `git add`, `git commit -m`, and `git push` commands; one logical change in each commit; no co-author line (D-039). Do not use `uv run` in `run.sh` (D-045). Do not start sub-agents (R15).
