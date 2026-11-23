# Handover 09 → 09b (C9 continued: the Ayb eval)

**Date:** 2026-11-23

## Goal of the next chat

C9 continues when Hugging Face grants the access to `Metric-AI/Ayb-0.5-4B` (D-074). The chat does the Ayb install check and the Ayb eval. Then it applies the decision rule of D-072 part 3 and records the result (D-076). If the access does not come and Aren wants to use the time, the chat can first do the test changes for tuning (D-072 part 5) on their own branch.

## Current state

- **Branches:** `c9-d071` is merged into `main` (D-071: rules after the challenge; `chats/` and the chat export converter removed). `c9-eval` has three commits: the eval tools (D-072, D-073), the results with D-074 and D-075, and the C8 handover. Aren pushes it and merges it when CI is green. Claude does not know the commit hashes.
- **Program:** no change in C9. P1 is the default; P4 is behind `--seamless`.
- **C9 results** (`docs/eval/results.md`, "C9: OhanASR-v0.1"), all [RUN] on Aren's laptop:
  - Armenian WER, S1–S3 / S5: `nemo-rnnt` (P1) 10.6 / 10.0 %; P4 7.1 / 13.0 %; OhanASR 9.1 / 6.3 %. OhanASR wrote 10 digit words on S1–S3, each the correct number; with them as words: 5.3 % [calc] (D-075).
  - English chrF, S1–S3 / S5: P4 (audio to English) 59.0 / 65.3; Seamless text to text on the OhanASR text 56.0 / 62.9; NLLB on the OhanASR text 52.3 / 58.7.
  - VRAM over the 148 MiB base: OhanASR 4646 MiB, P4 3082 MiB. Model s per audio s on S5: OhanASR 0.164, P4 0.092.
  - D-074 option B ("P6": the OhanASR Armenian line + the Seamless English line) stays a candidate: VRAM 8076 of 8151 MiB [calc].
- **Tests:** unit 284 passed before the merge of `c9-d071` (`test-results/c9-unit-2.txt`, with the 25 old converter tests). The run on `c9-eval` is `test-results/c9-unit-3.txt` (expected: 259 passed).
- **Documents:** `RULES.md` v0.6, `PLAN.md` v0.24, `DECISIONS.md` to D-075, `ARCHITECTURE.md` v0.40, `TESTS.md` §2.10.
- **Models (`models/`, not in git):** `ohanasr-v0.1` (complete); `ayb-0.5-4b` (only `README.md` and `LICENSE`).
- **Data:** `data/c9/segments.{npz,json}` (136 segments: S1–S3 34, S5 102; P1 cut at 234 s). All runs use this dump.

## Ayb: facts for the install check (research in C9, no run)

- **Access:** "Access denied. Model 'Metric-AI/Ayb-0.5-4B' requires approval" (`test-results/c9-dl-ayb.txt`). vLLM does not avoid the gate (D-074).
- **Size [calc]:** from the Qwen3.5-4B-Base config [SOURCE: `huggingface.co/Qwen/Qwen3.5-4B-Base`, `config.json`: hidden 2560, intermediate 9216, 32 layers (24 linear attention, 8 full attention), tied embeddings] and the Ayb vocabulary of 250,635 (model card). The text model has about 4.21B parameters: embedding 0.64B, MLP 2.27B, full attention 0.29B, linear attention 1.01B. With the vision encoder (about 0.30B), the calc gives 9.03 GB in BF16; the card gives about 9.3 GB. Thus the calc is about 3 % low.
- **Forms [calc, text model only]:** BF16 about 8,030 MiB (it does not fit in 8151 MiB, also alone); 8-bit (bitsandbytes LLM.int8, embeddings in BF16) about 4,630 MiB; 4-bit NF4 about 2,980 MiB.
- **Space next to OhanASR and TitaNet:** 8151 − 148 − 4646 − 200 = 3,157 MiB [calc] for Ayb with its CUDA context, cache, and activations. Only NF4 can come close, with a small margin.
- **bitsandbytes 0.50.2** (PyPI; `torch>=2.4,<3`) has `libbitsandbytes_cuda130.so` with `sm_120` code [RUN: `strings` on the wheel library in the workspace]. A run on the RTX 5070: [UNVERIFIED].
- **Linear attention:** transformers 5.20.2 loads the Qwen3.5 kernels from the Hub with a torch fallback (`use_kernel_func_from_hub_with_fallback`). With `HF_HUB_OFFLINE=1`, the fallback runs [UNVERIFIED speed].
- **CPU:** the laptop has 32 GB of RAM, so BF16 or float32 fits. A memory-bound estimate gives a few tokens per second [UNVERIFIED]. Thus a CPU form can fail the speed limit of 0.5 in the program; for the eval only, a CPU run is possible.
- **`ayb.py` now** has only the form "bf16" (`AutoModelForCausalLM`, the text model only).

## Open questions for the next chat

1. **New dependency (R11, D-028):** `bitsandbytes>=0.50.2` in a new dependency group `c9-eval` that is not in `default-groups` (as `spk-eval`, D-057). It leaves the project if Ayb loses. Aren decides.
2. **Ayb forms to measure.** Claude's proposal: NF4 on the GPU (the program form) for the rule; BF16 with some layers on the CPU as an upper bound, on the reference text only (it needs `accelerate`; whether it is installed: [UNVERIFIED]). Aren decides.
3. **If Ayb fails the rule or does not fit:** D-074 option B (P6), or no change.
4. **The test changes for tuning (D-072 part 5):** before C10, or in C10 as planned?

## Read list for the next chat

1. `docs/handovers/09b-ayb.md` (this file)
2. `DECISIONS.md`: D-071 to D-075 (in the project folder, the end of the file)
3. `docs/eval/results.md`: "C9: OhanASR-v0.1"
4. `ARCHITECTURE.md` §8.2: `c9.py`, `ayb.py`, `scripts/c9_run.py`, `scripts/ohanasr_transcribe.py`
5. `src/tir_asr/eval/ayb.py`

Read `RULES.md` with the Projects tool (`claude/RULES.md`, v0.6). The Project copies of `DECISIONS.md` and `ARCHITECTURE.md` can be older than git (C9 could not copy them: the files are too large for the copy tool). Read these two files in the project folder, or ask Aren to upload them into the Project.

## First task in the next chat

1. Ask for the access to `/home/aren/dev/armenian-asr`. Do the chat start checklist (`RULES.md` §5.1).
2. Ask Aren: the CI state on `main`; the Ayb access; the open questions 1, 2, and 4.
3. Aren downloads Ayb: `uv run hf download Metric-AI/Ayb-0.5-4B --local-dir models/ayb-0.5-4b`. Claude reads `config.json`, `generation_config.json`, the chat template (it must accept `enable_thinking`), and `README.md`, and checks the size calc above.
4. Add the approved forms to `ayb.py`. Then the install check: load, VRAM, and 3 lines (`--limit 3`). Then the runs:
   - `scripts/c9_run.py mt --model ayb --form <form> --input reference [--context 3]`
   - `scripts/c9_run.py mt --model ayb --form <form> --input asr-ohanasr [--context 3]`
   - `scripts/c9_run.py report --candidate ayb-<form>-ctx3+asr-ohanasr --added-text <n>`. Aren reads the marked lines first, and n is his count.
5. Apply the rule of D-072 part 3 and record D-076.

## Do not

- **The Ayb prompt:** do not change `SYSTEM_PROMPT` in `tir_asr/eval/c9.py`. T-C9-03 checks it word for word, and a change needs a record (D-072 part 2).
- **OhanASR** runs only in its own environment (D-073): `env -u LD_LIBRARY_PATH HF_HUB_OFFLINE=1 uv run --python 3.11 --script scripts/ohanasr_transcribe.py`. Do not make the segment dump again unless `Params` changes: all model results use the same 136 segments.
- **Report names:** an Ayb run writes `test-results/c9/mt-ayb-<form>-ctx<k>+<input>.json`. The default candidate of `report` is `ayb-bf16-ctx3+asr-ohanasr`; give `--candidate` for another form.
- **VRAM (condition 3):** the report adds the two processes and TitaNet [calc]. Only a run with both models loaded is a measurement (C10).
- **Digits:** D-075. For a comparison between models, use the substitution of the checked groups [calc]; for tuning one model, N1.
- **Remote writes:** write each output file one time into a new folder, write it to the laptop, then stage it again and compare. In C9, a file that Claude changed after its first save in the outputs folder reached the laptop in its old form (two times). After a `git switch` or a merge, stage the files again before a write (the mtime guard).
- **`ruff` in the workspace:** only `--no-cache`, with `--config pyproject.toml`, in a scratch tree that has an empty file for each module of `tir_asr`. Without the full module list, the import sort is wrong.
- **From the earlier handovers:** measure before a change (R6); no parameter without Aren's approval (R10); Claude does not run tests in the workspace (D-038); the full `git add`, `git commit -m`, and `git push` commands, with no co-author line (D-039); no sub-agents (R15).
