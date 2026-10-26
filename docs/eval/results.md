# C3 bake-off results

**Date:** 2026-10-26 · **Decision:** D-053 (P4: Seamless end to end) · **Rules:** R6 (measure, do not guess)

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
