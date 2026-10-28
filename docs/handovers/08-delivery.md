# Handover 08 (C8 delivery): end of the project

**Date:** 2026-10-28

## Goal of the next step

No next chat. Aren does the last step of C8 (`PLAN.md` §5.2 C8, step 5): the full chat export, the converter (`scripts/export_chats.py`, D-012), one `.md` file for each chat in `chats/`, the commit, and the merge. Then Aren sends the repository link.

## Current state

- **Branch `c8-delivery`:** README, D-068 (NeMo log level ERROR), D-069 (`vad_max_speech_s` = 15 s), D-070 (`GIL_SWITCH_S` = 0.5 ms).
- **Tests (Aren's laptop, 2026-10-28):** unit 263 passed; model T-E2E-01 to T-E2E-03 passed; sim T-SIM-01, T-SIM-02, T-SIM-03 passed. Final live test: `test-results/c8-live.txt` (P1, 2 people on the call side, about 6.5 min, totals 0.17–0.69 s).
- **Documents:** `README.md` (complete), `ARCHITECTURE.md` v0.38, `PLAN.md` v0.20, `DECISIONS.md` to D-070.

## Decisions made in C8

| ID | Subject | Summary |
|---|---|---|
| D-068 | NeMo log lines | NeMo logger level ERROR from the model load; 0 NeMo lines live. |
| D-069 | Segment values | `vad_max_speech_s` 15 s; `vad_min_silence_ms` stays 500 ms (300 ms split a sentence in T-E2E-01). |
| D-070 | GIL switch interval | 0.5 ms, after a P4 gap of 70.4 ms; T-SIM-03 passes. |

## Open questions

1. The C8 time in `PLAN.md` §11 is an estimate. Aren corrects it.
2. P1 or P4 as the default: P1 stays (D-056, D-066).
3. Possible improvements: README §8.

## Do not

- Do not edit the exported chats (D-011, D-012).
- Do not commit `data/`, `models/`, `test-results/`, or audio files (`.gitignore`).
