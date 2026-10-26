# Handover 02d → 03 (C2d `audio` + `output` + `pipeline` + `cli` → C3 evaluation set and bake-off)

**Date:** 2026-10-26

## Goal of the next chat

Do chat C3 (`PLAN.md` §5.2 C3): the eval scripts and the metrics, with tests first (R5), and then the bake-off of the ASR and MT shortlists on Aren's laptop (D-014, D-015). The first step is the Armenian text normalization rules for WER/CER and their tests (PLAN C3, step 1).

## Current state

- **M1 reached (2026-10-26).** `./run.sh` starts the program: microphone → VAD → ASR → MT → terminal, label "Me", latency on each line. T-E2E-01: each total about 0.6 s (K1: 5 s).
- **Code on `main`:** `types`, `config` (`Params`, `parameter_lines`), `errors` (`TirError`), `segment`, `asr`, `mt`, `audio` (`SoundcardMicrophone`), `output`, `pipeline` (`warm_up`, `run`), `app`, `cli`, and `run.sh`. Merges: `ab0820f` (c2d-output), `b363fed` (c2d-audio), `2bfd7b3` (c2d-pipeline), c2d-cli (Aren gives the hash).
- **Tests:** unit 69 pass; sim T-AUDIO-01 to T-AUDIO-03 pass; model T-MODEL-*, T-E2E-01, T-E2E-02 pass; live L-01 to L-03 pass (`TESTS.md` §2.4, §4, "C2d results"). CI: Aren reports.
- **Documents:** `ARCHITECTURE.md` v0.12, `PLAN.md` v0.12, `RULES.md` v0.5, `DECISIONS.md` to D-045, `TESTS.md` with the C2d results.
- **Eval recordings (Aren, C2d):** in `data/eval/raw/`, two files for each recording: `<name>.mic.wav` (the laptop microphone, `alsa_input…analog-stereo`) and `<name>.call.wav` (the monitor of the Bluetooth sink `bluez_output.E0:08:71:6B:2A:A2`). 48 kHz, mono, float32 WAV, from `parecord`. The two files start a few milliseconds apart [UNVERIFIED size]. Claude does not know the number of recordings.

## Decisions made in C2d

| ID | Subject | Summary |
|---|---|---|
| D-040 | `output` interface | `format_block(line, session_start)`, `write_block(line, session_start, stream)`: one write and one flush; a blank line after each block; the seconds are cut. |
| D-041 | Audio adapter and T-AUDIO-01 | Sim test with a null sink (Aren); exact device id (soundcard matches a part of the name); limits from probe B; samples can be a little outside [−1, 1] (no clip); the stream opens in `blocks()`. |
| D-042 | Pipeline, startup, stop | `app.py` loads the adapters; `run()` owns the exit codes; `TirError` base class; `warm_up()` separate; the session start before the capture; segments in the queue are lost at Ctrl+C (risk accepted). |
| D-043 | CLI and startup log | `cli.py` is `argparse` only; `startup: ` lines; load order ASR → MT → VAD (2a); NeMo lines not hidden until C7; T-E2E-01 with the WAV source. |
| D-044 | Ctrl+C | The main thread waits with `STOP_POLL_S = 0.5` s in a loop. With no time limit, Ctrl+C did nothing (75–79 native threads; probe C). T-E2E-02 checks it. |
| D-045 | Launcher | `run.sh`: `cd` to the project folder, `HF_HUB_OFFLINE=1`, `exec .venv/bin/tir-asr "$@"`. |

## Facts that C3 needs

- **Latency steps [RUN]:** `vad` 0.50–0.52 s (the silence wait, D-027), `asr` 0.03–0.05 s, `mt` 0.06–0.10 s, `out` 0.00 s. The warm-up is enough (D-022).
- **Startup [RUN]:** ASR 1.5 s (1100 MiB), MT 1.1 s (+1664 MiB), VAD 0.02 s; 2764 MiB of 8151 MiB used.
- **Live data (Script 4, `TESTS.md`, "C2d results"):** ASR errors («Ալոս Սորա» for «Ալո, Սոնա», «երեք» for «Երեկ»); MT errors ("Tiger", "truck", "attacker"); a 10 s hard cut split a word (Q15); MT left out a sentence (Q-13); the microphone clips (Q-11).
- **Audio [RUN]:** the arrival gaps alternate 21/43 ms (PipeWire cycle, size [UNVERIFIED]); the hidden capture delay is 21–44 ms (a README limit); a monitor gives zero blocks during a silence.
- **The test WAV source** (`tests/support/wav_source.py`) reads only 16 kHz, mono, 16-bit files. The eval recordings are 48 kHz float32, so C3 needs the resample step with its test (D-019).
- `docs/eval/scripts.md` has the 4 conversation scripts with the Armenian and English references.

## Open questions

- **Aren (`PLAN.md` §10.2):** Q15 (a longer `vad_max_speech_s`; now with live data), Q16 (CPU-only and limited-resource modes).
- **QA (`TESTS.md` §3):** Q-06, Q-07, Q-10, Q-11, Q-12, Q-13.
- **C7:** the NeMo load lines (D-043 point 3); the removal of the `(no text)` block (D-031).
- **After M3:** the start/pause keys (D-034).
- **Time (R16):** C2d took 2.92 h (1.42 h over). Total 11.42 h; expected about 23.9 h. C6 is the first item to cut (Aren decides).

## Read list for the next chat

1. `docs/handovers/02d-cli.md` (this file)
2. `PLAN.md`: §5.2 C3, §10.2
3. `docs/eval/scripts.md`
4. `TESTS.md`: §2.3, §3
5. `ARCHITECTURE.md`: §2.3, §2.4, §6

`RULES.md` and `DECISIONS.md` (D-014, D-015, D-019, D-038, D-039) are Project documents. Read them with the Projects tool.

## First task in the next chat

1. Ask for the access to `/home/aren/dev/armenian-asr`.
2. Do the chat start checklist (`RULES.md` §5.1).
3. Ask Aren for the merge hash of `c2d-cli`, the state of CI, and the names of the recordings in `data/eval/raw/` (names only).
4. Propose the C3 components, their branches (R3), and the normalization rules, with the R7 steps.

## Do not

- **Remote writes:** use a new output path for each write. Before a new stage, delete the old staged copy (the copies are read-only). After each write, stage the file back and compare the checksums.
- **File times after git:** a branch change or a merge rewrites the file times. Stage the file again before a write with `expectedMtimeMs`.
- **`.venv` files:** do not stage them; `uv` hard-links them, and the bridge refuses. Download the same wheel from PyPI and compare its hash with `uv.lock`.
- **ruff:** use `--no-cache`. Check with a scratch copy of the project layout (`pyproject.toml` and `src/tir_asr/`), not in an empty folder: with no `src/tir_asr`, ruff passes where the laptop gives I001. In the red state, a test that imports a new module gives I001; the red run is pytest only.
- **Pipes:** a probe or a test that prints into a pipe must flush each line (the probe C error in C2d).
- **Ctrl+C:** do not remove `STOP_POLL_S`, and do not change the main-thread wait to a wait with no time limit (D-044).
- **Load order:** ASR first, then MT, then VAD (D-043 2a).
- **Launcher:** do not use `uv run` in `run.sh` (D-045). After a change to `pyproject.toml`: `uv lock --check && uv sync`. The bridge cannot set the executable mode; Aren runs `chmod +x`.
- **Call audio:** the call side plays on the Bluetooth sink, not on the analog output; use its monitor. `soundcard.get_microphone` matches a part of a name; always use exact ids (D-041).
- **MT model tests:** always run them with `env -u LD_LIBRARY_PATH` (D-030), and with `HF_HUB_OFFLINE=1`.
- **Model test files:** import the `laptop` packages inside the test functions, because CI collects the file.
- **D-038:** no unit-test runs in the workspace; Claude runs `ruff` only. A dry run of probe or test logic with fakes is acceptable, when Claude tells Aren.
- `import soundcard` fails with no PulseAudio server and with `python -c`. Use a script file.
- Do not use a private attribute of an adapter in a test (Aren). Do not commit red tests. Do not write into `.github/workflows/`. Do not put two components on one branch. Do not start sub-agents (R15). Do not make decisions without the R7 steps.
