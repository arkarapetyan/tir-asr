# Bake-off results (C3, C5, C6, C7, C9)

**Date:** 2026-10-26 (C3), 2026-10-27 (C5, C6) · **Decisions:** D-053 (P4: Seamless end to end), D-058 (speaker model), D-063 (P4 variant) · **Rules:** R6 (measure, do not guess)

The sections up to "Not measured" are the C3 bake-off. The section "Speaker labels (C5)" is the C5 sweep. The section "P4 variants (C6)" is the C6 probe. The section "C9: OhanASR-v0.1" is the C9 eval (D-072).

## Conditions

- **Laptop (Aren):** NVIDIA GeForce RTX 5070 Laptop GPU (8 GB), 24 CPU threads. torch 2.14.1, NeMo 3.0.0, CTranslate2 4.8.3, transformers 5.20.2, silero-vad 6.2.3.
- **Data:** S1–S3 (D-019, D-046, D-048), one file for each side: "mic" (Aren) and "call" (Speaker 1 and Speaker 2; Google Meet for S1, Telegram for S2 and S3). 6 files, 34 lines.
- **Segments:** the program's VAD and `Endpointer` with `Params()` (D-051), with 1.0 s of zeros after each file (D-048). All runs have the same 34 segments, 161.0 s of segment audio. No segment had a hard cut at 10 s.
- **WER and CER:** D-047 normalization (P1: «՞» stays; N1: no number rule), on the joined text of each file (D-046 point 2).
- **chrF:** `sacrebleu` 2.6.0 default values, on the joined English text, no normalization.
- **Times:** each model call after one warm-up call. **VRAM:** `torch.cuda.mem_get_info()` before and after the load.
- **Files:** `test-results/bakeoff/*.json`, `test-results/c3-bake-*.txt`, `test-results/c3-power-*.csv`, `test-results/c3-probe-cpu.txt`.

## ASR candidates (MT = NLLB)

| ASR | WER | CER | ASR time per segment, mean / max | VRAM | Words with digits |
|---|---|---|---|---|---|
| `nemo-rnnt` (ASR-1, RNNT; the program until D-053) | 10.6 % | 3.3 % | 0.021 / 0.026 s | 952 MiB | 0 |
| `nemo-ctc` (ASR-1, CTC) | 12.7 % | 3.6 % | 0.017 / 0.022 s | 952 MiB | 0 |
| `buzz-whisper` (ASR-5) | 19.0 % | 7.5 % | 0.256 / 0.352 s | 3190 MiB | 9 |
| `seamless` (ASR-2) | **6.8 %** | **2.3 %** | 0.321 / 0.417 s | 2884 MiB | 0 |

- ONNX-CTC: not run (D-052). It has the CTC transcriptions of `nemo-ctc`.
- By side, `nemo-rnnt`: mic 6.6 %, call 13.5 %. The S1 call side (Google Meet) has 21.4 %; the S2 and S3 call sides (Telegram) have 2.0 % and 9.0 %.

## MT candidates

| MT | chrF, RNNT text in | chrF, reference text in | MT time per segment, mean / max | VRAM |
|---|---|---|---|---|
| `nllb-ct2` (MT-2; the program until D-053) | 51.7 | 56.3 | 0.074 / 0.112 s | 1664 MiB |
| `opus-ct2` (MT-1) | 42.7 | 43.6 | 0.016 / 0.027 s | 192 MiB |
| `seamless` text to text (MT-5) | 55.5 | **61.1** | 0.245 / 0.324 s | 2632 MiB |

## Pipelines (GPU)

The line time is the ASR time plus the MT time of one segment. The VAD wait (about 0.5 s, D-023) comes on top.

| Pipeline | WER | chrF | Line time, mean / max | GPU s per audio s | VRAM | Energy (run with load) |
|---|---|---|---|---|---|---|
| P1: `nemo-rnnt` + `nllb-ct2` | 10.6 % | 51.7 | 0.10 / 0.14 s | 0.020 | 2.6 GB | 356 J |
| P2: `nemo-rnnt` + Seamless text to text | 10.6 % | 55.5 | 0.27 / 0.35 s | 0.056 | 3.6 GB | 591 J |
| P3: `seamless` ASR + `nllb-ct2` | 6.8 % | 52.7 | 0.39 / 0.51 s | 0.083 | 4.5 GB | — |
| **P4: Seamless end to end** (HY: `tgt_lang="hye"`, EN: `"eng"`, one model) | **6.8 %** | **59.0** | 0.63 / 0.83 s | 0.133 | 2.9 GB | 1183 J |
| P5: `nemo-rnnt` HY + Seamless audio → EN [calc, from two runs] | 10.6 % | 59.0 | 0.33 / 0.44 s | 0.069 | 3.8 GB | — |

- **Power and temperature** (`nvidia-smi` every 200 ms, 30 s pause before each run; start 41–42 °C; idle about 12 W):
  - P1: mean 30.5 W, peak 65.7 W, peak 54 °C.
  - P2: mean 31.7 W, peak 53.3 W, peak 53 °C.
  - P4: mean 41.0 W, peak 56.5 W, peak 59 °C, 11.2 s at GPU load ≥ 50 %.
- With the VAD wait, the slowest P4 line is about 1.3 s. K1 (5 s) is met on the GPU.

## CPU probe (Q16)

`scripts/probe_cpu.py`: 3 segments of the S3 mic file, all models on the CPU (24 threads), Seamless in float32, CTranslate2 in int8.

| Segment | Audio | P4 on the CPU: ASR + S2TT | P1 on the CPU: ASR + MT |
|---|---|---|---|
| s3-01 | 5.4 s | 7.76 + 2.10 = 9.86 s | 0.09 + 0.28 = 0.38 s |
| s3-05 | 7.8 s | 3.91 + 32.52 = 36.43 s | 0.13 + 0.31 = 0.43 s |
| s3-07 | 5.4 s | 4.04 + 10.09 = 14.13 s | 0.10 + 0.30 = 0.40 s |

- P4 does not meet K1 on the CPU. P1 meets it on the CPU.
- The P4 times vary much: the English output of s3-05 has a normal length (110 characters), but S2TT took 32.5 s. The cause is not known.

## Findings

1. **Q-13, confirmed for NLLB:** NLLB leaves out a sentence when a segment has two or more sentences. With the RNNT text: s1-05 ("But the trunk is small") and s3-07 ("I will call Armen myself"). With the reference text: also s2-06, s2-07, s3-04. Seamless (text to text and end to end) translated all these sentences.
2. **CTC chrF:** `nemo-ctc` + NLLB has a higher chrF (53.6) than `nemo-rnnt` + NLLB (51.7), but a higher WER. The cause is the punctuation: CTC wrote a comma where RNNT wrote «։», so NLLB did not leave out the second sentence (D-052).
3. **«՞» (D-047 P1):** the references have 12 words with «՞». `nemo-rnnt` wrote «՞» on 6 of them (about 1.5 % of the WER).
4. **Digits (D-047 N1):** only BuzzASR writes digits. NLLB writes digits in English ("8:00") and changed «տասնհինգ հազար դրամ» to "$15,000".
5. **Q-11:** `s1.mic.wav` has 500 samples at full scale. Its WER with `nemo-rnnt` is 6.8 %, close to the other mic files.

## Not measured

- Power and temperature at live speed (the bake-off runs the segments with no pause).
- Other voices and devices than the S1–S3 speakers; S4.
- Seamless with `SeamlessM4Tv2Model` (one load for speech and text input).

## Speaker labels (C5)

### Conditions

- **Laptop (Aren), 2026-10-27:** RTX 5070 Laptop GPU. torch 2.14.1, torchaudio 2.11.0, NeMo 3.0.0, speechbrain 1.1.2, pyannote.audio 4.0.7, silero-vad 6.2.3.
- **Data (D-057 part 1):** the call sides of S1 (Google Meet; Speaker 1 and Speaker 2), S2 and S3 (Telegram; one speaker each). The four speakers are different people. Four streams, each a new session: S1, S2, S3, and stream D (S1 0–34.0 s, S2, S1 34.0 s to the end, S3; 192.5 s).
- **Segments:** the program's VAD and `Endpointer` with `Params()`. S1: 9, S2: 5, S3: 5, D: 19 segments, 2.40–8.19 s of speech. Each segment overlaps a labelled line (0 outside).
- **Method:** one embedding for each segment; the segments go into the clusterer in time order; `min_new_s` = 1.0 s (no segment was shorter, so this rule did not act); 15 thresholds from 0.20 to 0.90.
- **Metric (D-057 part 2):** label accuracy after the best one-to-one mapping of the labels to the true speakers; an extra label counts as an error. "Wrong" counts the segments.
- **Pass rule (D-057 part 3):** at one threshold, at most 1 wrong segment on each stream; the passing thresholds cover 0.10 or more.
- **Files (local):** `test-results/bakeoff/spk-*.json`, `test-results/c5-spk-*.txt`.

### Results

| | TitaNet-large (SPK-3) | ECAPA, SpeechBrain (SPK-2) | WeSpeaker ResNet34-LM, pyannote (SPK-1) |
|---|---|---|---|
| Passing range, rule A (centroid) | 0.40–0.65 (0.25) | 0.35–0.55 (0.20) | 0.50–0.65 (0.15) |
| Passing range, rule B-max (nearest) | 0.40–0.65 (0.25) | 0.35–0.60 (0.25) | 0.50–0.65 (0.15) |
| Zero errors on all four streams (both rules) | 0.40–0.60 | 0.35–0.45 | 0.50–0.60 |
| Stream D: lowest same-speaker cosine | 0.542 | 0.396 | 0.620 |
| Stream D: highest different-speaker cosine | 0.372 | 0.413 | 0.496 |
| Stream D: margin (lowest same − highest different) [calc] | +0.170 | −0.017 | +0.124 |
| Embedding time per segment, mean / max | 6.0–9.8 / 28.3 ms | 5.5–6.5 / 7.7 ms | 11.7–13.8 / 19.2 ms |
| Load time; VRAM | 3.34 s; 200 MiB | 0.32 s; 104 MiB | 2.19 s; 30 MiB |
| New packages | 0 (NeMo) | 5 | 27 |

TitaNet with rule A, accuracy by count on stream D: 52.6 % (0.20–0.25), 78.9 % (0.30–0.35), 100 % (0.40–0.60), 94.7 % (0.65), 84.2 % (0.70), 63.2 % (0.80), 26.3 % (0.90). At 0.50: 100 % on all four streams, by count and by speech time (9/9, 5/5, 5/5, 19/19).

### Decision and limits

- **D-058:** TitaNet-large with rule A (centroid). The widest range (0.25) is shared by TitaNet with rule A and ECAPA with rule B-max; the tie-break (fewer new packages) selects TitaNet. For TitaNet, B-max is not wider than A, so A stays. Start values: `spk_threshold` = 0.50 (the middle of the zero-error range), `spk_min_new_s` = 1.0 s. L-06 tests both.
- **Removed after the sweep (D-058):** the ECAPA and WeSpeaker adapters and the dependency group `spk-eval` (`speechbrain`, `pyannote.audio`). The `c5-embed` commits in git keep them.
- **Limits:** 4 voices and 19 segments. 0 errors in 19 segments gives an approximate 95 % upper limit of about 15 % for the error rate [calc]. No segment under 2.40 s and no noise, so `spk_min_new_s` and Q-14 are not tested. The live check is L-06.
- **H-S1 (D-003):** three models trained on English voices separate the four Armenian voices with no error over a range of thresholds. No fine-tuning is necessary on this data.

## P4 variants (C6)

### Conditions

- **Laptop (Aren), 2026-10-27:** RTX 5070 Laptop GPU; CPU with 24 cores: 8 fast cores (2 at 5.4 GHz, 6 at 5.3 GHz) and 16 slow cores (4.7 GHz). torch 2.14.1, transformers 5.20.2, attention `sdpa`.
- **Script:** `scripts/probe_p4.py` (D-062 part 1). `facebook/seamless-m4t-v2-large`, `SeamlessM4Tv2ForSpeechToText`, the generate values of the model: greedy (no `num_beams` in the model files), `max_new_tokens` 256.
- **GPU data:** float16; the 34 segments of S1–S3 (the program's VAD, `Params()`, as in C3). For each segment, the variants run one after the other. The VAD loads after the model, so torch has 1 CPU thread, as in the program.
- **CPU data:** float32 (and INT8); the 3 segments of the C3 CPU probe (s3-01, s3-05, s3-07, mic side, cut with the labels); no Silero import.
- **Variants:** V0, two full `generate` calls (the HY line, then the EN line), as in C3; V1, one encoder pass and two decodes that get the encoder output; V2, one encoder pass and one decode of a batch of two rows (the `hye` code and the `eng` code).
- **Files (local):** `test-results/c6-probe-gpu.txt`, `test-results/c6-probe-cpu.txt`, `test-results/bakeoff/p4-probe-{gpu,cpu}.json`.

### Results on the GPU

| Variant | WER | CER | chrF | Line mean / max | Texts as V0 | Decode steps (mean) | One decode step |
|---|---|---|---|---|---|---|---|
| V0 | 6.8 % | 2.3 % | 59.0 | 0.661 / 0.829 s | 34 of 34 | 45.9 | — |
| V1 | 6.8 % | 2.3 % | 59.0 | 0.586 / 0.744 s | 34 of 34 | 45.9 | 12.1 ms (batch of one) |
| **V2** | 7.1 % | 2.3 % | 59.0 | **0.337 / 0.443 s** | 32 of 34 | 24.8 | 12.3 ms (batch of two) |

- V0 gives the C3 numbers again.
- V2 gives the same English text as V0 on all 34 segments. Two Armenian texts differ by one character: «:» → «։» (no WER change after the normalization) and «պատշգամբում» → «պատճգամբում» (1 word of 397).
- A step with a batch of two takes 1.02 times a step with a batch of one, so the decode waits for the CPU, not for the GPU work. Thus INT8 on the GPU is not measured (D-062 part 8).
- VRAM 2884 MiB after the load; peak torch memory 2955 MiB for each variant.
- With the VAD wait (about 0.5 s), the slowest V2 line is about 0.95 s [calc].

### Results on the CPU (3 segments)

| Setting | V0 | V1 | V2 |
|---|---|---|---|
| float32, 24 threads | 5.2–50.5 s | 15.0–30.7 s | 15.3–29.5 s |
| float32, 8 threads | 4.1–6.1 s | 3.4–4.7 s | 2.7–3.9 s |
| INT8 (`quantize_dynamic`, `nn.Linear`), 8 threads | — | — | 1.18–1.76 s |

- The slow C3 CPU lines (up to 36.4 s) come from the thread count: 24 threads on 8 fast and 16 slow cores. The decode steps do not explain the times (s3-01: 45 steps, 50.5 s with 24 threads, 4.1 s with 8 threads).
- INT8: the Armenian texts are the same as float32, except one first letter that is not a capital; the English texts differ in some words (chrF 61.5 against 59.7 on 3 segments, not a quality result). torch 2.14.1 writes that `torch.ao.quantization` "is deprecated and will be removed in 2.10".
- With INT8 and 8 threads, the longest line plus the VAD wait is about 2.3 s, under K1 [calc, 3 segments]. The program has no CPU mode (D-063 part 4); this is a limit in the README and a possible next step.

### Decision

- **D-063:** V2 on the GPU, float16. The latency line of P4 has one step, `s2t` (part 2). No INT8 on the GPU; no CPU mode. T-PERF-P4-01 checks V2 in the program adapter: WER ≤ 7.6 %, chrF ≥ 58.5, line mean ≤ 0.40 s, maximum ≤ 0.55 s.

## Live calls (C7)

### Conditions

- Aren's laptop, RTX 5070 Laptop GPU, 2026-10-28. Me: the laptop microphone. System: the monitor of Redmi Buds 3 Lite.
- Script S5 (`docs/eval/scripts.md`): casual Eastern Armenian, 49 lines (Me 24, Speaker 1 25), 499 words. Two people read it in two calls: first P1 (`./run.sh`), then P4 (`./run.sh --seamless`) (D-065). The readers did not write down changed words; Aren: "close to the text by 99%". Thus all differences count as errors of the program.
- Program: `main` at `0eb4b54`, before the C7 fixes (D-066, D-067).
- Scores: `scripts/score_live.py` on `test-results/c7-live-p1.txt` and `c7-live-p4.txt`. The texts of each side, joined in the order of the output, against the S5 lines of that side (as the C3 main numbers, D-046 point 2). WER and CER after `normalize_hy` (D-047); chrF on the English text.

### Results

| Call | Side | WER | CER | chrF | `#` marks | HY lines with Latin letters | Blocks / lines | Totals |
|---|---|---|---|---|---|---|---|---|
| P1 | Me | 7.1 % | 2.1 % | 56.0 | 0 | 0 | 24 / 24 | 0.57–0.67 s |
| P1 | call | 12.7 % | 2.8 % | 59.6 | 0 | 0 | 26 / 25 | (both sides) |
| P4 | Me | 8.3 % | 1.8 % | 64.2 | 0 | 0 | 24 / 24 | 0.70–0.94 s |
| P4 | call | 18.1 % | 7.9 % | 65.5 | 1 | 1 | 28 / 25 | (both sides) |

- The totals do not grow (mean of the first third against the last third: P1 0.62 / 0.61 s, P4 0.85 / 0.83 s).
- GPU (`nvidia-smi`, 1 s): P1 mean 13.4 W, max 20.6 W, max 47 °C; P4 mean 14.1 W, max 24.2 W, max 50 °C.
- Question marks «՞» in the HY lines: P1 8 + 5, P4 6 + 5 (the reference has 18 + 19).

### Findings

1. **`#err`** is the mark of the model for a hesitation sound: it came one time, at s5-43, for the interjection «Հը», and the EN line had `#Hmm`. «՞» is in the vocabulary and is not the cause (D-066). The output rules of D-066 remove the mark.
2. **English text in the HY line** did not come in a call with a read script.
3. **P4 changes casual Armenian to standard Armenian**, mostly on the call side: «էս շաբաթ-կիրակի» → «այս շաբաթվա կիրակի», «էնտեղ» → «այնտեղ», «իր ամուսինը ու» → «նրա ամուսինը եւ», «հետ կգանք» → «կվերադառնանք». The meaning stays, but WER and CER count each change. P1 makes sound errors instead: «լճի» → «հրեշի», «վարձել» → «բարձել», «կքնեն» → «կքննեն».
4. **P4 gives the better English** on both sides (chrF +8.2 for Me, +5.9 for the call side).
5. Two readings of the script, not one audio file, so the comparison has the noise of the reading.

### Decision

- **D-066:** fix P4 with the output rules (hesitation marks; only Armenian text in the HY line and only English text in the EN line). **D-067:** a shorter GIL switch interval during `run()`; T-SIM-03 passes. P1 stays the default (D-056).

## C9: OhanASR-v0.1 (D-072, D-073)

### Conditions

- **Laptop (Aren), 2026-11-23:** NVIDIA GeForce RTX 5070 Laptop GPU. Main environment: torch 2.14.1, NeMo 3.0.0, CTranslate2 4.8.3, transformers 5.20.2, silero-vad 6.2.3. OhanASR environment (D-073): Python 3.11, torch 2.8.0, fairseq2 0.5.2, omnilingual-asr 0.2.0.
- **Models:** `Metric-AI/OhanASR-v0.1` (omniASR_LLM_1B_v2, 2,279,634,560 parameters, bfloat16 on CUDA, the model's own `ohanasr.py`); `nemo-rnnt` (P1); P4 (the program adapter, variant V2). **Ayb-0.5-4B was not measured:** Hugging Face answered "Access denied. Model 'Metric-AI/Ayb-0.5-4B' requires approval" (`test-results/c9-dl-ayb.txt`). Ayb was measured later: see "Ayb-0.5-4B" below.
- **Data:** one segment dump for all models (`scripts/c9_run.py dump`, `Params()`): S1–S3, 34 segments, 161.0 s; S5, both calls and both sides, 102 segments, 356.2 s. The P1 recordings are cut at 234 s (Aren); the last P1 segments (s5-48, s5-49) end at 229.6 s and 231.9 s. No hard cut.
- **Scores:** the joined text of each side of each call against the reference lines of that side (D-046 point 2); the output rules of `text/clean.py` on all texts (D-066); WER and CER with `normalize_hy` (D-047, N1: no number rule); chrF with `sacrebleu` 2.6.0.
- **Times:** each call after one warm-up call; "model s per audio s" is the sum of the call times divided by the segment audio. **VRAM:** the peak used memory minus the used memory before the load (148 MiB in each run).
- **Files (local):** `data/c9/segments.{npz,json}`, `test-results/c9/*.json`, `test-results/c9/report.txt`, `test-results/c9-*.txt`.

### ASR

| ASR | S1–S3 WER | S1–S3 CER | S5 WER | S5 CER | Digit words (S1–S3) | Time per segment, mean / max | Model s per audio s (S5) | VRAM |
|---|---|---|---|---|---|---|---|---|
| `nemo-rnnt` (P1) | 10.6 % | 3.3 % | 10.0 % | 2.5 % | 0 | 0.028 / 0.033 s | 0.007 | 952 MiB |
| P4 (Seamless, V2, Armenian line) | 7.1 % | 2.3 % | 13.0 % | 9.0 % | 0 | 0.338 / 0.456 s (S1–S3) | 0.092 | 3082 MiB |
| **OhanASR-v0.1** | 9.1 % | 4.6 % | **6.3 %** | **2.3 %** | 10 | 0.724 / 1.276 s (S1–S3); 0.572 / 0.829 s (S5) | 0.164 | 4646 MiB |
| OhanASR, digits as the reference words [calc] | **5.3 %** | **1.7 %** | 6.3 % | 2.3 % | 0 | — | — | — |

- **Digits (D-047 N1, revisit condition met):** OhanASR wrote 10 words with digits on S1–S3, for example «15 հազար դրամ», «ժամը 7-ին», «099-11, 22-33». Each number is the correct number of the reference. N1 counts each one as an error. The [calc] row puts the reference words in place of the 6 digit groups (`15`, `7-ի`, `7-ին` two times, `099-11, 22-33`, `7-ին 6`, `11-ին`) and changes nothing else.
- **S5 (casual speech):** OhanASR keeps the casual forms; P4 changes them to standard Armenian (C7, D-066), so P4 has the highest WER on S5.
- By side (WER, N1): OhanASR S1–S3 mic 3.4 / 22.2 / 4.8 %, call 8.9 / 8.0 / 10.4 % (S2 mic: the phone number and the times); S5 mic 5.0 / 2.9 %, call 7.7 / 9.3 % (P1 / P4 call).
- No empty text from OhanASR or P4.

### MT (chrF, S1–S3 / S5)

| MT input | NLLB (CTranslate2) | Seamless text to text | P4 end to end (audio to English) |
|---|---|---|---|
| Reference Armenian text | 56.3 / 59.2 | 61.1 / 65.3 | — |
| `nemo-rnnt` text (P1) | 51.7 / 57.8 | — | — |
| OhanASR text | 52.3 / 58.7 | 56.0 / 62.9 | — |
| Audio | — | — | **59.0 / 65.3** |

- Model s per audio s on S5 (ASR + MT): P1 0.026; OhanASR + NLLB 0.183; OhanASR + Seamless text to text 0.233; P4 0.092. All are under the limit of 0.5 (K1, D-071).
- VRAM of the MT models: NLLB 1932 MiB; Seamless text to text 2724–2726 MiB.
- Flag rule (D-072 part 3, condition 4): 0 marked lines in each run, also for the P4 English lines.

### Findings

1. **ASR:** OhanASR gives the best Armenian text on casual speech (S5: 6.3 % against 10.0 % and 13.0 %). On S1–S3, its digits count as errors under N1 (9.1 %); with the digits as words, it is also the best (5.3 % [calc]).
2. **MT:** with the OhanASR text, no available text translator reaches the English of P4: Seamless text to text is 3.0 / 2.4 points lower, NLLB 6.7 / 6.6 points lower. Seamless text to text on the reference text is the same as P4 on S5 (65.3), so the end-to-end English of P4 is near the best that a text translator gives with perfect Armenian text.
3. **Decision rule (D-072 part 3) with no Ayb:** no cascade with OhanASR passes condition 2. A combination of the OhanASR Armenian line and the P4 English line (audio to English) passes condition 2 (equal chrF), and condition 1 on S5; on S1–S3 it passes only with the digits as words. Its VRAM is 4646 + 3082 + 148 + 200 (TitaNet) = 8076 MiB [calc], 75 MiB under 8151 MiB, with a second CUDA context not counted; only a run with both models loaded can show it.

### Ayb-0.5-4B (D-076, D-077, D-078)

- **Conditions:** the laptop and the dump as above. `Metric-AI/Ayb-0.5-4B`, the text model (`Qwen3_5ForCausalLM`, 4,211,977,216 parameters [RUN: checkpoint header]); transformers 5.20.2, accelerate 1.16.0, bitsandbytes 0.50.2; the linear attention with the torch code of transformers (no `fla`, no `causal_conv1d`). Greedy, thinking off, at most 256 new tokens.
- **Forms (D-076):** `nf4` (4-bit NF4, double quantization, compute bfloat16; weights 2,928 MiB); `bf16-cpu` (bfloat16, layers 26–31 and the final norm in CPU memory; weights 8,033 MiB).
- **Prompt:** the system prompt of D-072 part 2. "Prompt 1": with no context, the user message is only the Armenian text. "Prompt 2" (D-077): "Translate only this text:" before the text in each user message. Context 3: the last 3 lines of the call, Armenian and English, before that.
- **Problem lines:** "Armenian" = the English output has an Armenian letter (a copy of the text, a corrected text, or an answer in Armenian). "Added" = the output has text that is not the translation (the earlier lines again, a note, or an answer).

| Run | Prompt | Lines | Armenian | Added | chrF S1–S3 / S5 | Time per line, mean / max | VRAM peak |
|---|---|---|---|---|---|---|---|
| `nf4`, context 0, reference | 1 | 83 | 25 | 2 | 56.2 / 44.2 | 0.570 / 1.248 s | +3,248 MiB |
| `nf4`, context 3, reference | 1 | 83 | 1 | 1 | **73.1 / 71.9** | 0.589 / 2.237 s | +3,294 MiB |
| `nf4`, context 0, reference | 2 | 83 | 6 | 1 | 69.1 / 66.9 | 0.539 / 0.985 s | +3,248 MiB |
| `nf4`, context 3, reference | 2 | 83 | 1 | 1 | 72.8 / 71.9 | 0.596 / 2.330 s | +3,294 MiB |
| `nf4`, context 0, OhanASR | 2 | 136 | 21 | 0 | 56.3 / 57.2 | 0.522 / 0.911 s | +3,248 MiB |
| `nf4`, context 3, OhanASR (rule candidate) | 2 | 136 | 5 | 7 | 63.4 / 63.6 | 0.634 / 4.070 s | +3,298 MiB |
| `bf16-cpu`, context 0, reference | 2 | 83 | 8 | 0 | 66.5 / 68.2 | 2.694 / 4.476 s | +6,936 MiB |
| `bf16-cpu`, context 3, reference | 2 | 83 | 3 | 1 | 72.8 / 69.1 | 2.903 / 11.542 s | +6,984 MiB |

- **Rule (D-072 part 3) for the candidate:** condition 3 fails: VRAM 4,646 + 3,298 + 148 + 200 = 8,292 MiB [calc], more than 8,151 MiB; the speed passes (0.282 / 0.348 model s per audio s). Condition 4 fails: 7 lines with added text. Condition 2 also fails on S5: 63.6 against 65.3 (the chrF of prompt 2 came with the report of D-080).
- **Findings:** with context 3, Ayb gave the best English on the reference text of all MT models (prompt 1: 73.1 / 71.9 against 61.1 / 65.3 for Seamless text to text). With no context, Ayb often corrects or copies the Armenian text in place of a translation. With context 3, it sometimes writes the earlier lines again. The `bf16-cpu` form has the same problems, so the 4-bit form is not their cause.

### Google Translate through `googletrans` (D-079, D-080)

- **Conditions:** `googletrans` 4.0.2 and httpx 0.28.1, over the network from the laptop (2026-11-23). Source `hy`, target `en`; `raise_exception=True`; timeout 5 s; the service URL `translate.googleapis.com`. The MT input: the reference text and the OhanASR text (output rules applied, D-066). VRAM: +0 MiB.

| MT input | Lines | chrF S1–S3 / S5 | Problem lines | Time per line, mean / max | Model s per audio s (OhanASR + Google), S1–S3 / S5 |
|---|---|---|---|---|---|
| Reference text | 83 | **76.2 / 75.0** | 0 | 1.085 / 2.360 s | — |
| OhanASR text | 136 | **67.5 / 69.3** | 0 | 0.989 / 3.023 s | 0.401 / 0.429 |

- **Rule (D-072 part 3) for OhanASR + Google:**
  1. WER: passes with D-075 (5.3 % [calc] / 6.3 %, against the lower values of P1 and P4, 7.1 % / 10.0 %). The report uses N1 and gives False (9.1 % on S1–S3).
  2. chrF: passes (67.5 / 69.3 against P4 59.0 / 65.3).
  3. VRAM and speed: passes (4,994 MiB [calc]; 0.429 against 0.5).
  4. Added text: passes (0 lines; Aren's count).
- **Result (D-080):** OhanASR + Google replaces P1 and P4. C10 makes it the program default.
- **Findings:** Google gives the best English of all MT candidates, on the reference text and on the OhanASR text. Its time is network time: the speed margin is 0.07 under the limit.
