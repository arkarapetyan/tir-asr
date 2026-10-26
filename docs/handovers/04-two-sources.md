# Handover 04 → 05 (C4 two audio sources → C5 speaker labels, or C6 P4)

**Date:** 2026-10-26

## Goal of the next chat

The plan says C5 (`PLAN.md` §5.2 C5): label different people on the system side as "Speaker 1", "Speaker 2", and so on (F4). C5 gives M3, the MVP. After C4, Aren said: "Overall P1 isnt bad, but it fails frequently, especially on translation. would like to see P4 in action". Thus Aren decides first: C5 first (the plan) or C6 (P4) first. See open question 1.

## Current state

- **M2 reached.** The program captures the microphone (`Me`) and the system audio (`System`) at the same time, with one capture thread for each source, one queue, and one worker (D-054).
- **Device selection (F1):** `./run.sh --list-devices`; `./run.sh --mic <id> --system <id>`. With no flag: the default microphone and the monitor of the default output. The ids must be exact (D-041). Setup guide: `docs/setup-audio.md`.
- **Branches:** `c4-audio` and `c4-pipeline` are merged into `main`. `c4-cli`: Aren merges it at the end of C4 (merge hash: Aren gives it).
- **Tests (Aren's laptop):** unit 177 passed; model T-E2E-01, T-E2E-02 passed; sim T-AUDIO-01 to T-AUDIO-04 and T-SIM-01 passed; live L-05 passed; L-04 not run. Details: `TESTS.md` §2.6.
- **Documents:** `ARCHITECTURE.md` v0.21, `PLAN.md` v0.14, `DECISIONS.md` to D-055, `TESTS.md` §2.6, §3 (new Q-14), §4 (L-04, L-05).

## Decisions made in C4

| ID | Subject | Summary |
|---|---|---|
| D-054 | Two sources and device selection | Flags with exact ids and defaults (A); source label `System` until C5; new class `SoundcardSource(label, device)`; `run()` with one `(source, vad)` pair for each source; the sources are checked before the model load; one VAD for each source. |
| D-055 | Process | No separate red run in C4 (as D-050 in C3). |

## Facts from C4 [RUN]

- T-SIM-01 (S1 into two null sinks, 72.7 s): labels correct (WER `Me` 0.085 on the mic side, `System` 0.205 on the call side); totals ≤ 0.66 s; arrival gaps ≤ 47.8 ms (Q-10); no drift between the two sources (span ÷ real time 1.0000).
- L-05 (a video call, about 6 min): 84 blocks (38 `Me`, 46 `System`); totals 0.11–0.68 s, no growth; 2 hard cuts at 10 s (Q15); about 11 blocks from noises with one letter and an invented English sentence (Q-14). The `System` source was the monitor of Bluetooth buds.
- The rule `<output id>.monitor` is true for the laptop output (T-AUDIO-04) and for a Bluetooth output (L-05).
- With two sources and P1, VRAM is 2764 MiB after the model load (two Silero instances on the CPU).

## Open questions

1. **Order of C5 and C6 (Aren decides).** Claude's view (R14):
   - For C5 first: R2 says MVP first, and M3 needs F4. C6 is an improvement after the MVP.
   - For C6 first: Aren's live result (P1 translation fails often) and the C3 numbers (D-053: WER 10.6 → 6.8 %, chrF 51.7 → 59.0).
   - C5 and C6 both change the worker step: C5 adds a speaker step on the system side; C6 adds the Template Method design for P1 and P4. The chat that comes second must fit into the design of the first one.
2. **Q16:** the answer of the Mathrix team on the laptop and a CPU mode.
3. **Q-14** (noise blocks) and **Q15** (10 s limit): data only; C7 decides with numbers (R6).
4. **L-04:** run `./run.sh --list-devices` one time.

## Read list for the next chat

If C5 comes first:

1. `docs/handovers/04-two-sources.md` (this file)
2. `PLAN.md`: §5.2 C5, §6.4
3. `ARCHITECTURE.md`: §2.1, §2.6, §3, §4
4. `TESTS.md`: §2.6, §3
5. `docs/research/RESEARCH.md`: §4

If C6 comes first:

1. `docs/handovers/04-two-sources.md` (this file)
2. `PLAN.md`: §5.2 C6
3. `ARCHITECTURE.md`: §2.3, §2.4, §2.6, §2.7, §8.2
4. `src/tir_asr/eval/seamless.py`
5. `TESTS.md`: §2.6, §3

`RULES.md` and `DECISIONS.md` (D-017, D-053, D-054) are Project documents. Read them with the Projects tool.

## First task in the next chat

1. Ask for the access to `/home/aren/dev/armenian-asr`.
2. Do the chat start checklist (`RULES.md` §5.1).
3. Ask Aren: the merge hash of `c4-cli` and the state of CI; the order of C5 and C6 (open question 1); the Mathrix answer (Q16).
4. Propose the components, their branches (R3), and the tests, with the R7 steps.

## Do not

- **Remote writes:** prepare the files in a scratch copy of the project layout; write them only after Aren is on the new branch. Use a new output path for each write. Before a new stage, delete the old staged copy. After each write, stage the files back and compare the checksums.
- **Git state:** do not write a tracked file before Aren is on the branch of that change.
- **`ruff` in the workspace:** only `ruff check --no-cache` and `ruff format --no-cache --check` on the scratch copy (D-038). The scratch copy needs each imported `tir_asr` module as a file (an empty file is enough), or the import sort can differ.
- **Sim and model runs:** `env -u LD_LIBRARY_PATH HF_HUB_OFFLINE=1` (D-030). T-SIM-01 loads the models and needs `data/eval/raw/s1.*.wav` (local only).
- **Two sources:** each source needs its own VAD instance, because the Silero model keeps its state. `SoundcardSource` needs an exact id; `app.select_sources` finds the defaults.
- **R5:** D-055 was for C4 only. C5 has red runs again, unless Aren decides otherwise.
- **Commits:** the full `git add`, `git commit -m`, and `git push` commands; one logical change in each commit; no co-author line (D-039).
- Do not remove `STOP_POLL_S` (D-044). Load order: sources, ASR, MT, VAD (D-043, D-054). Do not use `uv run` in `run.sh` (D-045). Do not start sub-agents (R15).
