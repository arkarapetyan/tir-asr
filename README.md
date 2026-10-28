# tir-asr

Live Armenian speech transcription and English translation in the terminal, with speaker labels.
All models run locally.

**Status:** M3 (MVP, C5), with an experimental P4 behind a flag (C6). The program captures your microphone (`Me`) and the other side of a call (`Speaker 1`, `Speaker 2`, …), and prints the Armenian text and the English translation of each speech segment, with its latency. See `PLAN.md` for the phases.

The name comes from Tir. In Armenian mythology, Tir is the god of written language and wisdom, the scribe of the chief god Aramazd, and an interpreter of dreams ([source](https://en.wikipedia.org/wiki/Tir_(god))).

---

## Contents (complete at milestone M5)

1. Setup and run, with the audio device setup.
2. Chosen models, the alternatives, and the reasons.
3. Architecture.
4. Known limits and possible improvements.

## Run (MVP)

The full setup guide comes at milestone M5. The audio setup is in `docs/setup-audio.md`.

```bash
uv sync --locked          # one time: install the environment
./run.sh --list-devices   # show the sources and their exact ids
./run.sh                  # start: the default microphone and the monitor of the default output
./run.sh --seamless       # experimental P4: one Seamless model gives the Armenian and the English text
```

Push Ctrl+C one time to stop. The models must be in the local Hugging Face cache (`run.sh` sets `HF_HUB_OFFLINE=1`, so nothing downloads).

## Known limits (M3)

- **Interruptions:** the program cuts the speech only after 0.5 s of silence. When a person starts to speak less than 0.5 s after another person, or interrupts, both voices are in one line. That line gets the label of the person who spoke more (D-060, Q-04).
- **Noises:** a cough or another short sound can pass as speech. Then the line has one letter or a fragment, and the translation can be an invented sentence (Q-14). A short sound before the first speaker gets the label `Unidentified` (D-060).
- **Translation:** the default pipeline (P1: NeMo ASR, then NLLB) sometimes leaves out a sentence or gives a wrong translation (`docs/eval/results.md`).
- **P4 (`--seamless`) is experimental:** on the recorded eval set, P4 has fewer word errors and better translations than the default P1 (WER 7.1 % against 10.6 %, chrF 59.0 against 51.7; `docs/eval/results.md`). But in live tests (L-07), P4 often failed on normal and clear speech, some lines had `#err` symbols, and some Armenian lines had English text; P1 was much better. The cause is not measured yet (D-064). With P4, a line takes about 0.85 s in all (P1: about 0.63 s), and the capture can wait up to 145 ms (T-SIM-03). Thus P1 is the default.
- **Hardware:** the program needs an NVIDIA GPU with CUDA. It has no CPU mode. A probe of P4 on the CPU of the laptop gave 1.2–1.8 s for each line with INT8 and 8 threads on the 8 fast cores, but 5–50 s with float32 and 24 threads (3 segments; `docs/eval/results.md`, "P4 variants (C6)", D-063).

C7 measures the possible improvements (D-060) and makes the final decision on P4 (D-064).

## Project documents

| File | Contents |
|---|---|
| `RULES.md` | How we work: the rules of engagement. |
| `PLAN.md` | Phases, chats, milestones, risks, time log. |
| `DECISIONS.md` | Each decision, with its options and reasons. |
| `ARCHITECTURE.md` | Modules, contracts, data flow, parameters. |
| `TESTS.md` | Each test, with the requirement that it checks. |

## Development

Requirements: [uv](https://docs.astral.sh/uv/) version 0.12.21 (pinned in `pyproject.toml`, D-009). uv installs Python 3.12 if necessary.

```bash
uv sync --locked              # install the environment from uv.lock
uv run ruff check .           # lint
uv run ruff format --check .  # format check
uv run pytest                 # unit tests only
uv run pytest -m model        # model tests (laptop with GPU)
uv run pytest -m sim          # sim tests (laptop with virtual audio devices)
```
