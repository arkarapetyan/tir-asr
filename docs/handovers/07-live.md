# Handover 07 → 08 (C7 live test and P4 fixes → C8 delivery)

**Date:** 2026-10-28

## Goal of the next chat

C8 (`PLAN.md` §5.2 C8): the full README from `DECISIONS.md`, `ARCHITECTURE.md`, and the measured numbers; the known limits; a check of each item of `PLAN.md` §1; Aren's rehearsal of the interview start; then the final chat export (D-011, D-012), after the last message of C8.

## Current state

- **`main`:** `c7-p4` and `c7-notext` are merged (fast-forward). `c7-notext` (D-031): no block for an empty text; the shutdown line still counts it (unit 263, T-E2E-01 to T-E2E-03 pass).
- **P4 fixes (D-066, D-067):**
  - The core module `text/clean.py`; `TextStep.process` applies its rules for P1 and P4. Rule 1 removes the hesitation marks of P4 (`#err` in HY, the `#` of `#Hmm` in EN). Rule 2 shows only Armenian text in the HY line and only English text in the EN line; a run of words in another script becomes one `[?]`.
  - `GIL_SWITCH_S` = 1 ms while `run()` runs (`pipeline.py`); `run()` sets the old value back. T-SIM-03 passes (largest gap 61.0 ms; limit 64 ms).
- **Tests (Aren's laptop, 2026-10-28; `TESTS.md` §2.9):**
  - Unit: 263 passed (on `c7-p4`, with the T-NORM-08 fix).
  - Model: T-PERF-P4-01 (WER 7.1 %, chrF 59.0, line mean 0.330 s), T-MODEL-P4-01/02, T-E2E-01 to T-E2E-03 pass.
  - Sim: T-SIM-01, T-SIM-02 (gaps at most 47.0 ms), and T-SIM-03 pass.
  - Live: L-04 passes; L-07 recorded with script S5 (two calls).
- **Live numbers (script S5, `docs/eval/results.md`, "Live calls (C7)"):**

  | Call | Side | WER | CER | chrF | Totals |
  |---|---|---|---|---|---|
  | P1 | Me / call | 7.1 % / 12.7 % | 2.1 % / 2.8 % | 56.0 / 59.6 | 0.57–0.67 s |
  | P4 | Me / call | 8.3 % / 18.1 % | 1.8 % / 7.9 % | 64.2 / 65.5 | 0.70–0.94 s |

  P4 gives the better English, but it changes casual spoken Armenian to standard Armenian (the call-side WER). No growth of the totals; GPU at most 24.2 W and 50 °C.
- **Documents:** `ARCHITECTURE.md` v0.35, `PLAN.md` v0.19, `DECISIONS.md` to D-067, `TESTS.md` §2.9, `docs/eval/results.md` ("Live calls (C7)"), `docs/eval/scripts.md` (Script 5), `README.md` (the P4 limits and the output rules).

## Decisions made in C7

| ID | Subject | Summary |
|---|---|---|
| D-065 | C7 plan | Scope A; no separate red run; Part A (A1, A2); live test B3 with the new script S5 (P1 call, then P4 call, outputs and audio saved); fix P4. |
| D-066 | P4 fixes | `#err` is the hesitation mark of the model (not «՞»); the output rules of `text/clean.py` (marks; only one script on each line, `[?]`); the GC is not the cause of the gap; P4 and casual Armenian is a model limit; P1 stays the default. |
| D-067 | GIL switch interval | `GIL_SWITCH_S` = 1 ms during `run()`; T-SIM-03 passes; the mechanism is [UNVERIFIED], and the margin is small (61.0 ms against 64 ms). |

## Open questions

1. R16: C0 to C7 took about 22.4 h (C7 1.62 h, inside its time box). With C8 (1 h), about 23.4 h. C8 has a time box of 1 h.
2. M4: the C7 live test had one person on the call side (the goal says two or more). **Aren (2026-10-28):** a final live test with two speakers on the call side comes in C8 (L-06 again, the output in a file, `scripts/score_live.py` if the people read a script).
3. Not done in C7 (D-065, scope A): the speaker diagnostic line, the D-060 VAD measurements (interruptions, noises, short texts), L-06 again. The README states the limits.
4. The NeMo load lines at the startup (about 185 lines, D-043 point 3). **Aren (2026-10-28):** silence them in C8. C8 proposes the method with the R7 steps (for example the NeMo log level during the load); errors must stay visible (R10).
5. P1 or P4 as the default: P4 gives the better English, P1 the better Armenian text on casual call speech. A change needs a new decision (D-056).
6. `data/c7/p1.*.wav` are about 22 min long, because the P1 recorders ran after the P1 call. No test uses `data/c7/`.

## Read list for the next chat

1. `docs/handovers/07-live.md` (this file)
2. `README.md`
3. `PLAN.md`: §1, §2, §5.2 C8, §11
4. `docs/eval/results.md`
5. `ARCHITECTURE.md`: §1 and §2.7

`RULES.md` and `DECISIONS.md` (D-065 to D-067) are Project documents. Read them with the Projects tool.

## First task in the next chat

1. Ask for the access to `/home/aren/dev/armenian-asr`.
2. Do the chat start checklist (`RULES.md` §5.1).
3. Ask Aren: the state of CI on `main`; the C8 scope inside the 1 h time box (the README, the startup lines, the final live test, the rehearsal, the export).
4. Propose the README structure (PLAN §5.2 C8, step 1) with the R7 steps.

## Do not

- **Remote writes:** prepare the files in a scratch copy; write them only after Aren is on the branch of that change. Use a new output path for each write. After each write, stage the files back and compare the checksums. **After a `git checkout` or a merge, stage the files again before a write**, because git changes their mtimes (the mtime guard of the write).
- **A commit that changes a file that tests read** (for example `docs/eval/scripts.md`) gets a unit test run first. C7: S5 broke T-NORM-08 in CI (fixed: the test reads only S1 to S4).
- **`ruff` in the workspace:** only `ruff check --no-cache` and `ruff format --no-cache --check`, with `--config pyproject.toml`, on a scratch copy with the full `src/tir_asr` tree. The workspace has ruff 0.16.9 (the project needs 0.17.2 or newer), so Aren's run is the official check.
- **The workspace** cannot reach Hugging Face or the PyTorch package index; a model check runs on Aren's laptop.
- **Test commands:** sim and model runs with `env -u LD_LIBRARY_PATH HF_HUB_OFFLINE=1`; the sim tests with `-m "sim and model"`; `tee -i`. Do not run a sim test during a call.
- **Live tests:** always with the output in a file in `test-results/`. Stop the recorders (`parecord`, `nvidia-smi`) after each call.
- **Keep:** the output rules in the template (D-066); `GIL_SWITCH_S` in `run()` (D-067); the Template Method text step (D-062); P1 as the default (D-056); the speaker step as its own component; the clean stop (D-061); the load order (D-062 part 5).
- **Commits:** the full `git add`, `git commit -m`, and `git push` commands; one logical change in each commit; no co-author line (D-039). Do not start sub-agents (R15).
