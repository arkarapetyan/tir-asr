# tir-asr

Live Armenian speech transcription and English translation in the terminal, with speaker labels.
All models run locally.

**Status:** C0, project setup. The program does not work yet. See `PLAN.md` for the phases.

The name comes from Tir. In Armenian mythology, Tir is the god of written language and wisdom, the scribe of the chief god Aramazd, and an interpreter of dreams ([source](https://en.wikipedia.org/wiki/Tir_(god))).

---

## Contents (complete at milestone M5)

1. Setup and run, with the audio device setup.
2. Chosen models, the alternatives, and the reasons.
3. Architecture.
4. Known limits and possible improvements.

## Project documents

| File | Contents |
|---|---|
| `RULES.md` | How we work: the rules of engagement. |
| `PLAN.md` | Phases, chats, milestones, risks, time log. |
| `DECISIONS.md` | Each decision, with its options and reasons. |
| `ARCHITECTURE.md` | Modules, contracts, data flow, parameters. |
| `TESTS.md` | Each test, with the requirement that it checks. |

## Development

Requirements: [uv](https://docs.astral.sh/uv/). uv installs Python 3.12 if necessary.

```bash
uv sync --locked              # install the environment from uv.lock
uv run ruff check .           # lint
uv run ruff format --check .  # format check
uv run pytest                 # unit tests only
uv run pytest -m model        # model tests (laptop with GPU)
uv run pytest -m sim          # sim tests (laptop with virtual audio devices)
```
