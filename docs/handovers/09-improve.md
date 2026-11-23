# Handover 08 → 09 (delivery → improvement of the program)

**Date:** 2026-11-23

## Goal of the next chat

C9: improve the delivered program. The chat start chooses the scope from the open items below, with the R7 steps, and adds a C9 entry with a time box to `PLAN.md` before any code (R1, R16). Measure first, then change (R6).

## Current state

- **`main`:** `e18c53d` ("test(scripts): record T-EXPORT-11 run 2 and close Q-02"). C8 is merged (fast-forward). The chats C0 to C8 are in `chats/` (deliverable D3).
- **Note:** the C8 chat continued after the export (this handover). The new messages are not in `chats/08-delivery.md`. C9 decides if the chats after the delivery go into `chats/` as new files (for example `09-improve.md`).
- **Program:** P1 (NeMo RNNT + NLLB on CTranslate2) is the default; P4 (Seamless end to end) is behind `--seamless`, experimental. Speaker labels: TitaNet-large with online centroids (`spk_threshold` 0.50, `spk_min_new_s` 1.0 s). VAD: Silero, `vad_min_silence_ms` 500 ms, `vad_max_speech_s` 15 s (D-069). NeMo shows only its errors (D-068). `GIL_SWITCH_S` = 0.5 ms (D-070).
- **Tests (Aren's laptop, 2026-10-28):** unit 263 passed; model T-E2E-01 to T-E2E-03 passed; sim T-SIM-01, T-SIM-02, T-SIM-03 passed. CI green on `main`.
- **Documents:** `README.md` (complete; §7 limits, §8 improvements), `ARCHITECTURE.md` v0.38, `PLAN.md` v0.20, `DECISIONS.md` to D-070, `TESTS.md` §2.9.

## Open items (candidates for the C9 scope)

Facts first, then the source. All numbers are [RUN] on Aren's laptop.

1. **Two voices in one line (interruptions, fast turns).** The VAD cuts only after 500 ms of silence (D-060 part 3, Q-04). C8 live test: turns of two people in one line (for example 06:20 in `test-results/c8-live.txt`). D-069: 300 ms split a normal sentence of T-E2E-01, so 300 ms was not kept. Options from D-060: a measured value from 250 to 500 ms on S1–S3 (WER, chrF, segment count, speaker accuracy); a separate value for the `System` side; a speaker-change split inside a segment (embeddings on short windows).
2. **Extra speaker labels from noise.** C8 live test (2 people on the call side, bad connection): 7 labels; Speakers 3–7 have 1–2 short fragments each («Օի։», «Խ։», «Հովհ.»). L-06 (C5): 3 of 9 `System` lines were noises. Options from D-060 part 4: `vad_threshold`, `vad_min_speech_ms`, a rule for texts with one or two letters, `spk_min_new_s`. They need a new recording of coughs, laughs, and short words («Այո», «Հա», «Լավ»). The speaker diagnostic line (D-060 part 6, not done) gives the data for `spk_min_new_s`.
3. **Long speech.** C8 live test: 4 hard cuts at 10 s. Now 15 s (D-069), with no live data yet.
4. **P4 capture gap.** T-SIM-03 passed with 0.5 ms (D-070), after 70.4 ms with 1 ms. One run only; the mechanism is [UNVERIFIED].
5. **Translation context (P1).** Each segment is translated alone; NLLB leaves out the second sentence of some segments (Q-13); «նա» is "he" or "she".
6. **P1 or P4 as the default.** P4 gives the better English, P1 the better Armenian on casual speech (C7, S5 calls). A change needs a new decision (D-056, D-066).
7. **Other README §8 items:** a CPU mode (D-063 probe numbers), models with a commercial licence, a larger eval set.

## Data that exists

- Eval set S1–S3 with labels (`data/eval/raw/`, local only); the speaker streams (`tir_asr.eval`, `scripts/spk_bakeoff.py`); the bake-off runner (`scripts/bakeoff.py`).
- The S5 calls (C7): output files and the audio of both sides in `data/c7/` (the P1 files are about 22 min, because the recorders ran after the call); `scripts/score_live.py`.
- The C8 live test: output only (`test-results/c8-live.txt`), **no audio**. It cannot be replayed.

## Decisions to read

D-060 (L-06, the open VAD and speaker items), D-066 (output rules), D-067 and D-070 (GIL), D-068 (NeMo lines), D-069 (segment values). Read them with the Projects tool (`claude/DECISIONS.md`).

## Read list for the next chat

1. `docs/handovers/09-improve.md` (this file)
2. `README.md`: §5, §7, §8
3. `PLAN.md`: §1, §5.2 C8 (the result), §11
4. `ARCHITECTURE.md`: §2.2 (segment), §2.8 (speakers), §6 (parameters)
5. `docs/eval/results.md`

`RULES.md` and `DECISIONS.md` are Project documents. Read them with the Projects tool.

## First task in the next chat

1. Ask for the access to `/home/aren/dev/armenian-asr`.
2. Do the chat start checklist (`RULES.md` §5.1).
3. Ask Aren: the state of CI on `main`; the goal of C9 (which open items); the time box; whether Aren can make new recordings (noises, fast turns, 2 or more people on the call side).
4. Propose the C9 scope and the order (measure first) with the R7 steps. Add the C9 entry to `PLAN.md`.
5. Make a branch for each component (R3), for example `c9-<item>`.

## Do not

- **Parameters:** do not change a parameter without a measurement and Aren's approval (R6, R10). D-069 showed that a value from one live test can break a sentence.
- **Keep:** P1 as the default (D-056); the Template Method text step (D-062); the output rules in the template (D-066); `GIL_SWITCH_S` in `run()` (D-067, D-070); the speaker step as its own component (D-056); the clean stop (D-061); the load order (D-062 part 5); the NeMo log level (D-068).
- **Tests:** Claude does not run tests in the workspace (D-038). Aren runs them; the results go into `test-results/`. Model and sim runs: `env -u LD_LIBRARY_PATH HF_HUB_OFFLINE=1`; sim tests with `-m "sim and model"`; `tee -i`. Do not run a sim test during a call. A change to a file that tests read (for example `docs/eval/scripts.md`) needs a unit test run first.
- **Unit tests that use `Params()`:** `test_pipeline.py` expects the latency text of 500 ms (`vad 0.51s`). A change of `vad_min_silence_ms` must pin these tests to their own `Params` (as `RULE_PARAMS` in `test_segment_endpoint.py`), because they check the rules, not the program values.
- **Remote writes:** prepare the files in a scratch copy, then write them. Use a new output path for each write. After each write, stage the files again and compare them. If a staged copy still shows the old content, write again (C8: one write gave the old content). After a `git checkout` or a merge, stage the files again before a write (the mtime guard).
- **`ruff` in the workspace:** only `--no-cache`, with `--config pyproject.toml`; the workspace ruff is older than the project ruff, so Aren's run is the official check.
- **The workspace** cannot reach Hugging Face or the PyTorch package index. Model checks run on Aren's laptop.
- **Live tests:** always with the output in a file in `test-results/`, and with the audio of both sides saved (`parecord`), so that the test can be replayed. Stop the recorders after each call.
- **Commits:** the full `git add`, `git commit -m`, and `git push` commands; one logical change in each commit; no co-author line (D-039). Do not start sub-agents (R15).
