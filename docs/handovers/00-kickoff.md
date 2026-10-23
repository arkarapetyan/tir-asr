# Handover 00 → 01 (C0 Kickoff → C1 Research)

**Date:** 2026-10-23

## Goal of the next chat

Do chat C1, Research (`PLAN.md` §5.2 C1 and §6).

1. Collect facts about the candidate models, libraries, and data. Make no decisions during the research (R8).
2. Write `docs/research/RESEARCH.md`, with one table for each component and a source for each fact.
3. Discuss the facts with Aren.
4. Decide the first candidate for the skeleton (C2) and the shortlists for the bake-off (C3).

## Current state

- The repository `tir-asr` is set up. It uses uv 0.12.21 (pinned, D-009), Python 3.12, ruff, pytest with `model` and `sim` markers, and GitHub Actions CI.
- **Tests:** T-SETUP-01 passes (unit). There are no model or sim tests yet.
- **CI:** Aren reported that CI passes after the D-010 fix.
- **Last commit:** "build: pin uv 0.12.21 (D-009)". Aren gives the hash at the start of C1.
- **Decisions:** D-001 to D-010 are ACCEPTED.

## Facts that C1 needs

- **Laptop** (`PLAN.md` §1.6): RTX 5070 Laptop GPU (Blackwell) with 8 GB VRAM, 32 GB RAM, Ubuntu 26.04.1 LTS, PulseAudio on PipeWire 1.6.2, NVIDIA driver 595.99.02 (supports CUDA up to 13.2).
- **Aren's candidates:**
  - `nvidia/stt_hy_fastconformer_hybrid_large_pc` (ASR),
  - `Helsinki-NLP/opus-mt-hy-en` (MT),
  - the ArmBench-ASR leaderboard (`Metric-AI/ArmBench-ASR`).
- **Hypothesis H-S1** (speaker models and Armenian): research only. No fine-tuning before the C5 measurements (D-003).
- The Claude workspace cannot download models (the proxy blocks huggingface.co). Models run only on Aren's laptop.

## Open questions

None from C0. The research questions are in `PLAN.md` §6.1–§6.8.

## Read list for the next chat

1. `docs/handovers/00-kickoff.md` (this file)
2. `RULES.md`
3. `PLAN.md`: §1, §5.2 (C1), §6
4. `DECISIONS.md`

## First task in the next chat

1. Ask for access to `/home/aren/dev/armenian-asr`.
2. Do the chat start checklist (`RULES.md` §5.1).
3. Propose the research order and the table format of `RESEARCH.md`. Aren confirms.
4. Start with §6.1 (ASR).

## Do not

- Do not make decisions during research. Mark each fact [SOURCE], [RUN], or [UNVERIFIED] (R8).
- Do not start sub-agents. Do the research in the chat itself (R15).
- Do not trust a remote file write. After each write, copy the file back and compare checksums. In C0, one write kept the old text without an error.
- Do not try to write into `.github/workflows/`. The remote tools refuse it. Aren edits the CI files himself.
- For a GitHub Action, check that the exact tag exists with `git ls-remote --tags`, not only the release (D-010).
- In the workspace, install uv 0.12.21 first (`pip install uv==0.12.21`). A different uv version stops with an error (D-009).
- Do not read files outside the Read list without asking Aren (R4).
