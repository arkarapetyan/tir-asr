# RESEARCH.md: Research for C1

**Project:** tir-asr (Live Armenian Transcription to English Translation)
**Chat:** C1 Research · **Date:** 2026-10-24 · **Status:** DRAFT (facts only, no decisions, RULES.md R8)
**Questions:** `PLAN.md` §6.1–§6.8. **Target language:** Eastern Armenian only (Aren, 2026-10-24).

## How to read this file

- Each component has: a quality table, a practical table, other facts, and a source list.
- Tags (R8):
  - `[S3]` = [SOURCE]: source S3 in the source list of the same section.
  - `[RUN: <what>]` = measured with code. In C1, the only runs are dependency resolutions in Claude's workspace. They download package metadata, not packages or models.
  - `[UNVERIFIED]` = no source. We do not use it as a reason in a decision.
  - `(calc)` = arithmetic from a value with a source, for example weight size = parameters × 2 bytes for float16.
  - `—` = Claude found no value.
- Aren decided that all model runs wait for the C2 install check (2026-10-24). Thus VRAM and speed on the RTX 5070 are not measured in C1.
- Western Armenian: when a source says that a model or a test set is Western Armenian or mixed, "Other facts" tells it. A WER on such data does not show the WER on Eastern speech.

---

## 0. Platform baseline (§6.8 Q1–Q2)

### 0.1 Runtimes

| Runtime | Newest version (PyPI, date) | Python 3.12 | CUDA of the PyPI wheel | Blackwell (sm_120) | Notes |
|---|---|---|---|---|---|
| PyTorch | 2.14.1 (2026-09-30) [S6] | yes, cp312 wheel [S6] | 13.0 [S6] | yes in the CUDA 13.0 and 13.2 builds; **no** in the CUDA 12.6 build [S1] | Driver 595.99.02 supports CUDA up to 13.2 (`PLAN.md` §1.6). |
| ONNX Runtime GPU | 1.31.0 (2026-10-09) [S6] | yes [S6] | 13.0 since v1.27; separate CUDA 12.8 packages exist [S2] | built with CUDA 13.0 [S2]; native sm_120 kernels not stated [UNVERIFIED] | "Compatible with PyTorch for CUDA 13.x" [S2]. Requires Python >= 3.11 [S6]. |
| CTranslate2 | 4.8.3 (2026-10-13) [S6] | yes [S6] | 12.8 [S3] | INT8 is disabled on sm120 since v4.6.2 [S4]; float16 on sm120 [UNVERIFIED] | No CUDA 13 build in the changelog [S4]. Needs the CUDA 12 cuBLAS [S7]; cuDNN is optional since v4.6.3 [S4]. |
| NeMo toolkit | 3.0.0 (2026-08-07) [S6] | `requires_python >=3.10` [S6]; classifiers list only 3.10 [S6] | uses PyTorch (`torch>=2.6.0`) [S6] | depends on the PyTorch build [UNVERIFIED] | `[asr]` extra pins `lightning>2.2.1,<=2.4.0` [S6]. |
| pyannote.audio | 4.0.7 (2026-06-30) [S6] | `requires_python >=3.10` [S6] | uses PyTorch (`torch>=2.8.0`) [S6] | depends on the PyTorch build [UNVERIFIED] | Needs `torchaudio>=2.8.0`, `torchcodec>=0.7.0`, `lightning>=2.4`, and `ffmpeg` [S6][S8]. |
| torchaudio | 2.11.0 (2026-03-23) [S6] | — | — | — | "Maintenance phase" since 2.9 [S10]. No pin to a torch version in the metadata [S6]. |
| omnilingual-asr / fairseq2 | 0.2.0 (2025-12-15) / fairseq2 0.8.1 [S6] | omnilingual-asr: `>=3.10,<=3.12` [S6] | omnilingual-asr pins `fairseq2<=0.6.0`; `fairseq2n` 0.6 pins `torch==2.8.0` (CUDA 12.8 wheel) [S6] | PyTorch 2.8 CUDA 12.8 build [UNVERIFIED for sm_120 in 2.8] | Native code is tied to one torch version [S11]. |

### 0.2 Other facts

- **pyannote telemetry:** on by default (`metrics_enabled: true`). It sends usage metrics (file duration, number of speakers) to `otel.pyannote.ai` [S9][S8]. `PYANNOTE_METRICS_ENABLED=0` stops it [S8].
- **pyannote models** are gated: accept the user conditions and use a Hugging Face token [S8].
- **CTranslate2 speed** [S5]: OPUS-MT model, NVIDIA A10G, CUDA 11, batch translation of newstest2014:
  - Transformers 4.26.1 (PyTorch 1.13.1): 1022.9 tokens/s, 4097 MB GPU memory, BLEU 27.90.
  - CTranslate2 3.6.0 float16: 9296.7 tokens/s, 909 MB GPU memory, BLEU 27.90.
  - The benchmark measures throughput, not the latency of one short segment. Versions are from 2023.
- **faster-whisper** (CTranslate2): "up to 4 times faster than openai/whisper for the same accuracy while using less memory" [S7].
- `faster-whisper` 1.2.1 depends on `onnxruntime` (CPU) for its Silero VAD [S6][S7].

### 0.3 Dependency resolution [RUN]

- **What:** `uv pip compile` with uv 0.12.21, Python 3.12, platform `x86_64-manylinux_2_28`, in Claude's workspace, 2026-10-24.
- **Input:** `nemo-toolkit[asr]==3.0.0`, `pyannote.audio==4.0.7`, `ctranslate2==4.8.3`, `onnxruntime-gpu==1.31.0`, `torch==2.14.1`.
- **Result:** the set resolves (192 packages).
  - `lightning==2.4.0`: the only version that fits NeMo (`<=2.4.0`) and pyannote (`>=2.4`).
  - `torchaudio==2.11.0` with `torch==2.14.1`. Claude found no source that says that these versions work together [UNVERIFIED].
  - CUDA packages: `cuda-toolkit==13.0.3.0`, `nvidia-cudnn-cu13`. There is no CUDA 12 cuBLAS. CTranslate2 on the GPU needs extra CUDA 12 packages and `LD_LIBRARY_PATH` [S7].
- **Limit:** a resolution does not show that the packages run. The C2 install check shows that.

### 0.4 Sources

- S1. PyTorch `RELEASE.md`, release compatibility matrix and CUDA architectures for 2.14. https://github.com/pytorch/pytorch/blob/main/RELEASE.md (read 2026-10-24)
- S2. ONNX Runtime docs, CUDA Execution Provider, requirements (doc source). https://github.com/microsoft/onnxruntime/blob/gh-pages/docs/execution-providers/CUDA-ExecutionProvider.md (read 2026-10-24)
- S3. CTranslate2 Linux wheel build script (installs CUDA 12.8). https://github.com/OpenNMT/CTranslate2/blob/master/python/tools/prepare_build_environment_linux.sh (read 2026-10-24)
- S4. CTranslate2 CHANGELOG (v4.6.2 "Disable INT8 for sm120 - Blackwell GPUs"; v4.6.3 "Support for CUDA 12.8"). https://github.com/OpenNMT/CTranslate2/blob/master/CHANGELOG.md (read 2026-10-24)
- S5. CTranslate2 README, Benchmarks. https://github.com/OpenNMT/CTranslate2/blob/master/README.md (read 2026-10-24)
- S6. PyPI JSON metadata (`https://pypi.org/pypi/<name>/json`) for torch, onnxruntime-gpu, ctranslate2, nemo-toolkit, pyannote.audio, torchaudio, faster-whisper, omnilingual-asr, fairseq2, fairseq2n 0.6 (read 2026-10-24)
- S7. faster-whisper README. https://github.com/SYSTRAN/faster-whisper/blob/master/README.md (read 2026-10-24)
- S8. pyannote.audio README. https://github.com/pyannote/pyannote-audio/blob/main/README.md (read 2026-10-24)
- S9. pyannote telemetry `config.yaml`. https://github.com/pyannote/pyannote-audio/blob/main/src/pyannote/audio/telemetry/config.yaml (read 2026-10-24)
- S10. torchaudio 2.11 documentation. https://docs.pytorch.org/audio/2.11.0/torchaudio.html (read 2026-10-24)
- S11. fairseq2 README, "Variants". https://github.com/facebookresearch/fairseq2/blob/main/README.md (read 2026-10-24)

---

## 1. ASR: speech → Armenian text (§6.1)

### 1.1 ArmBench-ASR v1.0, open models (WER %, lower is better) [S1]

| Rank | Model | Combined | Common Voice 26 | FLEURS | Poems | Movies | News |
|---|---|---|---|---|---|---|---|
| 11 | nvidia/stt_hy_fastconformer_hybrid_large_pc | 19.86 | 7.70 | 15.00 | 31.28 | 60.78 | 23.55 |
| 19 | facebook/seamless-m4t-v2-large | 28.94 | 15.15 | 14.44 | 43.93 | 80.16 | 37.43 |
| 20 | chillarmo/whisper-large-v3-turbo-armenian | 33.00 | 12.94 | 24.69 | 55.09 | 82.01 | 48.80 |
| 21 | arampacha/whisper-large-hy-2 | 33.17 | 23.16 | 17.37 | 44.48 | 77.82 | 39.48 |
| 23 | facebook/omniASR-LLM-3B | 37.76 | 27.45 | 26.68 | 49.84 | 87.43 | 35.18 |
| 24 | facebook/omniASR-LLM-1B | 38.10 | 28.09 | 27.18 | 49.06 | 87.64 | 35.78 |
| 25 | facebook/omniASR-CTC-3B | 39.85 | 30.55 | 28.75 | 51.76 | 86.64 | 36.14 |
| 26 | facebook/omniASR-CTC-1B | 40.50 | 33.78 | 31.01 | 47.05 | 79.37 | 38.35 |
| 27 | facebook/omniASR-LLM-300M | 41.10 | 30.75 | 29.40 | 53.61 | 91.83 | 38.06 |
| 28 | cast/whisper-large-v3-mwa-hy | 41.41 | 29.59 | 30.69 | 52.89 | 75.04 | 55.75 |
| 29 | facebook/mms-1b-all | 47.50 | 43.09 | 34.52 | 53.04 | 83.38 | 44.79 |
| 30 | facebook/omniASR-CTC-300M | 50.61 | 44.92 | 40.25 | 57.79 | 86.53 | 47.25 |
| 31 | google/gemma-4-e4b-it | 50.65 | 48.48 | 37.11 | 57.62 | 79.72 | 44.14 |
| 32 | google/gemma-4-e2b-it | 53.46 | 50.44 | 42.76 | 59.88 | 80.19 | 48.92 |
| 34 | openai/whisper-large-v3 | 65.12 | 61.67 | 51.84 | 71.10 | 106.17 | 55.25 |

- Ranks 1–10 are closed systems (cloud APIs). The best one is `google/gemini-2.5-pro`, combined 13.80 [S1]. The brief does not allow cloud APIs (K2).
- **Facts about the benchmark:**
  - 5 datasets, 10,113 clips, about 20.7 h; "primarily focused on Eastern Armenian"; 3 datasets are private [S2]. The Common Voice 26 and FLEURS sets are public test sets [S1].
  - The leaderboard page does not give the normalization or the formula of "Combined" [S1].
  - A summary of the blog post gives a "combined strict WER" of 14.31 % for Gemini 2.5 Pro [S2]. The leaderboard shows 13.80 [S1]. Claude does not know the reason for the difference.
  - The leaderboard page does not tell which models saw the test sets in training [S1].
  - Claude could not read the original blog post (`huggingface.co/blog/Metric-AI/armbench-asr`): the fetch tool does not allow this URL. The facts about the blog come from secondary summaries [S2][S3].

### 1.2 Candidates: quality

| ID | Model | Size | Published WER outside ArmBench | Test sets seen in training | Punctuation and case | Streaming |
|---|---|---|---|---|---|---|
| ASR-1 | nvidia/stt_hy_fastconformer_hybrid_large_pc | 115M [S4] | MCV 17.0 test: RNNT 9.90, CTC 11.19; FLEURS test: RNNT 12.32, CTC 13.23 (greedy, no LM) [S4] | Trained on Common Voice 17.0 (48 h) and FLEURS (12 h); splits not given [S4] | yes: "all Armenian punctuation and capitalization" [S4] | no: "non-streaming" [S4] |
| ASR-2 | facebook/seamless-m4t-v2-large | 2.3B [S7] | — | — | [UNVERIFIED] | no (SeamlessStreaming is a separate model) [S7] |
| ASR-3 | Chillarmo/whisper-large-v3-turbo-armenian | 0.8B [S10] | — | Trained on `Chillarmo/common_voice_20_armenian` [S9] | [UNVERIFIED] | no [UNVERIFIED] |
| ASR-4 | arampacha/whisper-large-hy-2 | — | — | — | [UNVERIFIED] | no [UNVERIFIED] |
| ASR-5 | BuzzASR/armenian (Whisper-large-v3, full fine-tune) | 2B listed [S11] | FLEURS: WER 11.89, CER 3.72; Common Voice 25: WER 2.41, CER 0.65 (normalized) [S11] | Trained on FLEURS and Common Voice 25.0 [S11] | — | no [UNVERIFIED] |
| ASR-6 | facebook/omniASR (CTC and LLM, 300M–7B) | CTC-1B 975M; LLM-1B 2.28B [S5] | LLM-7B, Armenian (`hye_Armn`): CER 1.9, with 294.2 training hours [S6] | — | — | no; input must be shorter than 40 s (CTC and LLM) [S5] |
| ASR-7 | facebook/mms-1b-all | 1B [UNVERIFIED] | — | — | — | no [UNVERIFIED] |
| ASR-8 | openai/whisper-large-v3 (no fine-tune) | — | — | — | — | no [UNVERIFIED] |

### 1.3 Candidates: practical

| ID | Runtime | Python 3.12 | Blackwell | VRAM | Speed (RTF) | Licence | Gated |
|---|---|---|---|---|---|---|---|
| ASR-1 | NeMo (card: NeMo 2.0.0) [S4]; or ONNX Runtime with the community CTC export [S8] | see §0.1 | see §0.1 (PyTorch or ONNX Runtime) | — (`.nemo` file 459 MB [S12]) | — | CC-BY-4.0, "commercial and non-commercial use" [S4] | no [UNVERIFIED] |
| ASR-2 | Transformers (dedicated speech-to-text model) or `seamless_communication` [S7] | see §0.1 | PyTorch | ~4.6 GB weights in float16 (calc from 2.3B) | — | **CC-BY-NC 4.0** (non-commercial) [S7] | no [UNVERIFIED] |
| ASR-3 | Transformers; faster-whisper after conversion [UNVERIFIED] | see §0.1 | PyTorch or CTranslate2 | ~1.6 GB weights in float16 (calc from 0.8B) | — | Apache-2.0 [S9] | no [UNVERIFIED] |
| ASR-4 | Transformers [UNVERIFIED] | — | PyTorch | — | — | — | — |
| ASR-5 | Transformers, float16 on CUDA (card example) [S11] | — | PyTorch | ~4 GB weights in float16 (calc from 2B) | — | MIT [S11] | no [UNVERIFIED] |
| ASR-6 | `omnilingual-asr` on fairseq2; pins `torch==2.8.0` (see §0.1) [S13] | yes, max. 3.12 [S13] | PyTorch 2.8, CUDA 12.8 [UNVERIFIED for sm_120] | CTC-1B ~3 GiB; LLM-1B ~6 GiB (A100, BF16, batch 1, 30 s) [S5] | CTC-1B RTF 0.002; LLM-1B RTF 0.091 (A100) [S5] | Apache-2.0 [S5] | no [UNVERIFIED] |
| ASR-7 | Transformers [UNVERIFIED] | — | PyTorch | — | — | **CC-BY-NC 4.0** [S14] | — |
| ASR-8 | Transformers, faster-whisper | — | PyTorch or CTranslate2 | — | — | [UNVERIFIED] | no [UNVERIFIED] |

### 1.4 Other facts

- ASR-1: training data, total 296.19 h: Common Voice 17.0 (48 h), FLEURS (12 h), ArmenianGrqaserAudioBooks (21.96 h), two proprietary corpora (69.23 h and 145 h) [S4].
- ASR-1: tokenizer SentencePiece, vocabulary 1024; input 16 kHz mono [S4].
- ASR-1: limits in the card: "noise-sensitive"; output "may need inverse text normalization" [S4].
- ASR-1: the community ONNX export uses only the CTC head, in fp32. ONNX Runtime and the NeMo checkpoint gave "identical transcriptions on a reference clip". It runs "offline with ONNX Runtime; PyTorch and NeMo are not required." No int8 version [S8].
- ASR-1: on ArmBench it has the best open WER on Common Voice 26 (7.70) and on News (23.55) [S1]. It saw Common Voice 17.0 in training [S4]. Claude does not know if the Common Voice 26 test set overlaps with the Common Voice 17.0 training set [UNVERIFIED].
- ASR-2: Armenian (`hye`) is supported for speech input and text input; output is text only [S7]. ASR is "equivalent to S2TT with tgt_lang = src_lang" [S7]. Thus one model can give the Armenian text and the English text (§6.3).
- ASR-2: it has the best open WER on ArmBench FLEURS (14.44) [S1].
- ASR-5: not on ArmBench [S1]. The card says: "Evaluated only on FLEURS and Common Voice test splits, so other domains or dialects may perform differently" [S11].
- ASR-6: the own results file gives CER 1.9 for Armenian (LLM-7B) [S6]. On ArmBench, the LLM-3B has combined WER 37.76 [S1]. The two numbers use different metrics and test data.
- On ArmBench, the "Movies" set (film dialogue) has the highest WER for all open models: 60.78 to 106.17 [S1].
- Other Armenian models found, not on ArmBench and not examined: `Chillarmo/checkpoint_9971` (morpheme-aware Whisper) and the "Armenian ASR" hackathon project (no model card) [S15].

### 1.5 Sources

- S1. ArmBench-ASR leaderboard v1.0. https://metric-ai-armbench-asr.static.hf.space/index.html (read 2026-10-24)
- S2. Plushcap summary of the Hugging Face blog "ArmBench-ASR: A Benchmark for Armenian ASR" (2026-08-20). https://www.plushcap.com/content/huggingface/blog/huggingface-armbench-asr-a-benchmark-for-armenian-asr (read 2026-10-24)
- S3. RuntimeWire, "Metric releases Armenian speech benchmark" (2026-08-20). https://runtimewire.com/article/metric-armbench-asr-armenian-speech-benchmark (read 2026-10-24)
- S4. Model card, nvidia/stt_hy_fastconformer_hybrid_large_pc. https://huggingface.co/nvidia/stt_hy_fastconformer_hybrid_large_pc (read 2026-10-24)
- S5. omnilingual-asr README (model table, licence, 40 s limit). https://github.com/facebookresearch/omnilingual-asr/blob/main/README.md (read 2026-10-24)
- S6. omnilingual-asr per-language results, 7B LLM-ASR. https://github.com/facebookresearch/omnilingual-asr/blob/main/per_language_results_table_7B_llm_asr.csv (read 2026-10-24)
- S7. seamless_communication README (licences, model sizes) and `docs/m4t/README.md` (languages, tasks). https://github.com/facebookresearch/seamless_communication (read 2026-10-24)
- S8. Model card, OpenVoiceOS/stt_hy_fastconformer_hybrid_large_pc_onnx. https://huggingface.co/OpenVoiceOS/stt_hy_fastconformer_hybrid_large_pc_onnx (read 2026-10-24)
- S9. Mixpeek page for Chillarmo/whisper-large-v3-turbo-armenian (tags, dataset, licence). https://mixpeek.com/model/Chillarmo/whisper-large-v3-turbo-armenian (read 2026-10-24)
- S10. Hugging Face listing of the Chillarmo models ("0.8B"), seen in a search result. https://huggingface.co/Chillarmo (2026-10-24)
- S11. Model card, BuzzASR/armenian. https://huggingface.co/BuzzASR/armenian (read 2026-10-24)
- S12. File list, nvidia/stt_hy_fastconformer_hybrid_large_pc (refs/pr/3). https://huggingface.co/nvidia/stt_hy_fastconformer_hybrid_large_pc/tree/refs%2Fpr%2F3 (read 2026-10-24)
- S13. PyPI metadata, omnilingual-asr 0.2.0 and fairseq2n 0.6 (see §0.4 S6).
- S14. MMS README, licence. https://github.com/facebookresearch/fairseq/blob/main/examples/mms/README.md (read 2026-10-24)
- S15. Search results, 2026-10-24: https://huggingface.co/Chillarmo/checkpoint_9971, https://lablab.ai/submissions/rpt6nfeu15u2dp0sp0ggqbke

---

## 2. MT: Armenian text → English text (§6.2)

### 2.1 Candidates: quality

| ID | Model | Size | Published Armenian → English score | Training data | Domain note |
|---|---|---|---|---|---|
| MT-1 | Helsinki-NLP/opus-mt-hy-en (Marian, transformer-align) | — | Tatoeba: BLEU 29.5, chrF 0.466 (version opus-2019-12-18); BLEU 36.8, chrF 0.524 (version opus+bt-2020-05-23) [S1] | 442,131 sentence pairs: JW300 388,439; QED 36,597; bible-uedin 12,963; OpenSubtitles 3,204; others < 600 [S1] | JW300 + bible-uedin = 91 % of the pairs (calc from [S1]). Domain of JW300: religious text [UNVERIFIED]. Conversation text (OpenSubtitles): 0.7 % (calc) |
| MT-2 | facebook/nllb-200-distilled-600M (also 1.3B, 3.3B) | 600M (name) | FLORES per-direction scores are behind a link that Claude could not open [S2] | — | "general-domain text"; "not intended to be used with domain specific texts" [S2] |
| MT-3 | MADLAD-400 MT models | 3B, 7.2B, 10.7B [S3] | — | — | — |
| MT-4 | M2M-100 | 418M, 1.2B, 12B [S4] | — | — | — |
| MT-5 | SeamlessM4T v2 large, text-to-text (T2TT) | 2.3B (see §1) | Armenian text is supported as input [§1 S7]. Only an X→English average is given: chrF 59.2 (95 languages); NLLB-3.3B: 60.6 [S5] | — | — |
| MT-6 | Small LLMs: TranslateGemma (4B, 12B, 27B) | 4B–27B [S6] | — | TranslateGemma: Armenian only as English → Armenian in the training list [S6] | — |
| MT-7 | Small LLMs: arm-gemma-e4b (Gemma-4-E4B, continued pretraining on Armenian) | "E4B" [S7] | No translation scores [S7] | 10B-token mixture [S7] | — |

- **Fact:** C1 found no Armenian → English score on one common test set for MT-1 to MT-7. The Tatoeba scores of MT-1 do not compare with FLORES scores.

### 2.2 Candidates: practical

| ID | Runtime | Python 3.12 | Blackwell | VRAM | Speed | Licence | Gated |
|---|---|---|---|---|---|---|---|
| MT-1 | Transformers (MarianMT) [UNVERIFIED]; CTranslate2 supports OPUS-MT models [§0 S5] | see §0.1 | see §0.1 | — | — | [UNVERIFIED] | no [UNVERIFIED] |
| MT-2 | Transformers; CTranslate2 conversions exist [S8] | see §0.1 | see §0.1 | ~1.2 GB weights in float16 (calc from 600M) | — | **CC-BY-NC 4.0**; "not released for production deployment" [S2] | no [UNVERIFIED] |
| MT-3 | T5X checkpoints on Google Cloud Storage [S3]; Transformers conversions [UNVERIFIED] | — | — | ~6 GB weights in float16 for 3B (calc) | — | [UNVERIFIED] | — |
| MT-4 | fairseq [S4]; Transformers [UNVERIFIED] | — | — | ~0.8 GB weights in float16 for 418M (calc) | — | fairseq code: MIT [S9]; weights [UNVERIFIED] | — |
| MT-5 | Transformers or `seamless_communication` [§1 S7] | see §0.1 | PyTorch | ~4.6 GB (calc), shared with ASR-2 if both tasks use one model | — | **CC-BY-NC 4.0** [§1 S7] | no [UNVERIFIED] |
| MT-6 | Transformers [UNVERIFIED] | — | — | ~8 GB weights in bfloat16 for 4B (calc) | — | not stated in the report [S6] | — |
| MT-7 | Transformers [UNVERIFIED] | — | — | — | — | not stated [S7] | — |

### 2.3 Other facts

- MT-2: "The model was trained with input lengths not exceeding 512 tokens" [S2].
- §6.2 Q3 (ASR errors and missing punctuation): Claude found no source for any candidate. ASR-1 gives punctuation and case [§1 S4], so missing punctuation applies only to an ASR without punctuation.
- FLEURS sentences come from FLORES. Each sentence has an index that links it to the same sentence in English [§7 S1]. Thus FLEURS `hy_am` gives Armenian audio, Armenian text, and English text for one clip.

### 2.4 Sources

- S1. OPUS-MT-train, `models/hy-en/README.md`. https://github.com/Helsinki-NLP/OPUS-MT-train/blob/master/models/hy-en/README.md (read 2026-10-24)
- S2. Model card, facebook/nllb-200-distilled-600M. https://huggingface.co/facebook/nllb-200-distilled-600M/blob/main/README.md (read 2026-10-24)
- S3. MADLAD-400 README (checkpoints). https://github.com/google-research/google-research/blob/master/madlad_400/README.md (read 2026-10-24)
- S4. fairseq M2M-100 README. https://github.com/facebookresearch/fairseq/blob/main/examples/m2m_100/README.md (read 2026-10-24)
- S5. Seamless paper, arXiv 2312.05187, Table 7 (averages). https://arxiv.org/pdf/2312.05187 (read 2026-10-24)
- S6. TranslateGemma Technical Report, arXiv 2601.09012 (Table 6, Appendix B). https://arxiv.org/pdf/2601.09012 (read 2026-10-24)
- S7. "From Zero to Hero: An Open LLM Ecosystem for Armenian", arXiv 2609.03350. https://arxiv.org/html/2609.03350 (read 2026-10-24)
- S8. Search result: https://huggingface.co/entai2965/nllb-200-3.3B-ctranslate2 (2026-10-24)
- S9. fairseq LICENSE (MIT). https://github.com/facebookresearch/fairseq/blob/main/LICENSE (read 2026-10-24)

---

## 3. Cascade or end-to-end (§6.3)

| Item | Cascade (ASR → MT) | End-to-end (SeamlessM4T v2) |
|---|---|---|
| Models | Two, for example ASR-1 (115M) + an MT model [§1 S4] | One model, 2.3B [§1 S7] |
| Armenian text (required by the brief) | ASR output | ASR task: "equivalent to S2TT with tgt_lang = src_lang" [§1 S7]. Thus a second decoder pass for the English text [UNVERIFIED that the encoder output can be shared]. |
| Armenian WER on ArmBench | ASR-1: combined 19.86 [§1 S1] | combined 28.94 [§1 S1] |
| English quality | depends on the MT model; no common score (§2) | X→English T2TT average chrF 59.2 [§2 S5]; no Armenian speech → English score found |
| Weights in VRAM | ASR-1 `.nemo` file 459 MB [§1 S12] + MT model | ~4.6 GB in float16 (calc) |
| Latency | not measured | not measured |
| Licence | depends on the models | **CC-BY-NC 4.0** [§1 S7] |

---

## 4. Speaker labels and H-S1 (§6.4)

### 4.1 Candidates

| ID | Model | Type | Size | Training data | Published result | Licence | Gated |
|---|---|---|---|---|---|---|---|
| SPK-1 | pyannote/wespeaker-voxceleb-resnet34-LM | embedding (WeSpeaker wrapper) | — | VoxCeleb (name and licence note) [S1] | — | CC-BY-4.0 [S1] | not stated on the card [S1] |
| SPK-2 | speechbrain/spkrec-ecapa-voxceleb (ECAPA-TDNN) | embedding | — | VoxCeleb1 + VoxCeleb2 [S2] | EER 0.69 % on VoxCeleb1 test [S2] | Apache-2.0 [S2] | no [UNVERIFIED] |
| SPK-3 | nvidia/speakerverification_en_titanet_large | embedding | ~23M [S3] | "several thousand hours of English speech": VoxCeleb-1/2, Fisher, Switchboard, LibriSpeech, SRE 2004–2010 [S3] | EER 0.66 % on VoxCeleb1 (cleaned) [S3] | CC-BY-4.0 [S3] | no [UNVERIFIED] |
| SPK-4 | nvidia/diar_streaming_sortformer_4spk-v2.1 | streaming end-to-end diarization | 117M [S4] | "primarily in English" [S4] | DER at 1.04 s latency: CALLHOME-part2 11.19, AMI IHM 16.67 [S4] | NVIDIA Open Model License [S4] | — |
| SPK-5 | diart (online diarization pipeline) | pipeline on pyannote models | — | default: `pyannote/segmentation` + `pyannote/embedding` [S5] | VoxConverse, CPU: DER 44.86 %, mean latency 0.057 s (best combination in [S6]) | MIT [S5][S7] | the pyannote models are gated [§0 S8] |

### 4.2 Practical facts

- SPK-1: needs `pyannote.audio` 3.1 or higher [S1]. See §0 for the pyannote dependencies and telemetry.
- SPK-2: `speechbrain` 1.1.2 (2026-10-14) needs `torch>=2.7.1` and `torchaudio>=2.7.1` [S7].
- SPK-3 and SPK-4: NeMo [S3][S4]. SPK-4: "install NeMo from the main branch" [S4].
- SPK-4: "maximum of 4 speakers; performance degrades on recordings with 5 and more speakers" [S4]. "Performance may degrade on non-English speech" [S4].
- SPK-4: latency = chunk size + right context: 1.04 s (RTF 0.093) or 30.4 s (RTF 0.002), RTX 6000 Ada, batch 1 [S4].
- SPK-5: `diart` 0.9.2 (2025-02-12) needs `numpy<2.0.0` [S7].
- SPK-5 [RUN: `uv pip compile`, uv 0.12.21, Python 3.12, 2026-10-24]: `diart==0.9.2` with `pyannote.audio==4.0.7` has **no solution**. Cause: pyannote.audio 4.0.7 → `pyannote-core>=6.0.1` → `numpy>=2.0`; diart needs `numpy<2.0.0`. Thus diart 0.9.2 needs an older pyannote.audio (3.x) [UNVERIFIED which 3.x version works].
- In [S6], the embedding model causes most of the latency difference: pyannote/embedding 0.057 s, WeSpeaker ResNet34-LM 0.218 s, SpeechBrain ECAPA 0.461 s (CPU) [S6].

### 4.3 Evidence for H-S1 (cross-lingual loss)

- **For a language effect:**
  - "Performance degradation caused by language mismatch is a common problem" (abstract, no baseline numbers) [S8].
  - Non-target trials in the same language give higher similarity scores than trials across languages. "Speaker similarity scores correlate with language similarity." The effect is stronger for a system trained on several languages [S9].
  - TidyVoice 2026 (cross-lingual speaker verification, derived from Common Voice): baseline EER from 0.88 % to 5.19 % across four trial subsets. The highest EER: target trials across languages with non-target trials in the same language [S10].
  - SPK-4 card: "Performance may degrade on non-English speech" [S4].
- **Armenian results:** Claude found none. TidyVoice does not say if Armenian is in its 40 + 38 languages [S10].
- **Against a large effect:** Claude found no source that measures the loss for an untrained language as small. Claude's earlier view (`PLAN.md` §6.4) stays [UNVERIFIED].

### 4.4 Minimum segment length (§6.4 Q3)

- "Speaker verification systems experience significant performance degradation when tasked with short-duration trial recordings" [S11].
- ERes2NetV2 on VoxCeleb1-O: EER 0.61 % (full), 0.98 % (3 s), 1.48 % (2 s) [S11].
- No source gives a minimum length for online clustering. C5 measures it (RK5).

### 4.5 Armenian speech data with speaker IDs (§6.4 Q2)

- Common Voice has Armenian sets: "Common Voice Scripted Speech 23.0 - Armenian (Armenia)" and "25.0 - Armenian" on the Mozilla Data Collective [S12]. The speaker ID field (`client_id`) [UNVERIFIED in C1].
- FLEURS: three recordings by three different native speakers for each sentence; train and test speakers are disjoint [§7 S1]. Speaker IDs are not stated [§7 S1].

### 4.6 Sources

- S1. Model card, pyannote/wespeaker-voxceleb-resnet34-LM. https://huggingface.co/pyannote/wespeaker-voxceleb-resnet34-LM (read 2026-10-24)
- S2. Model card, speechbrain/spkrec-ecapa-voxceleb (revision 5a40f2c). https://huggingface.co/speechbrain/spkrec-ecapa-voxceleb/blob/5a40f2c96080d36cc8d73d0560ec5eabf96d6209/README.md (read 2026-10-24)
- S3. Model card, nvidia/speakerverification_en_titanet_large. https://huggingface.co/nvidia/speakerverification_en_titanet_large (read 2026-10-24)
- S4. Model card, nvidia/diar_streaming_sortformer_4spk-v2.1. https://huggingface.co/nvidia/diar_streaming_sortformer_4spk-v2.1 (read 2026-10-24)
- S5. diart README. https://github.com/hbredin/diart (read 2026-10-24)
- S6. Aperdannier et al., "Systematic Evaluation of Online Speaker Diarization Systems Regarding their Latency", arXiv 2407.04293. https://arxiv.org/pdf/2407.04293 (read 2026-10-24)
- S7. PyPI JSON metadata: diart, speechbrain (read 2026-10-24)
- S8. Li, Liu, Lee, "EDITnet", Interspeech 2022. https://www.isca-archive.org/interspeech_2022/li22m_interspeech.html (read 2026-10-24)
- S9. Reuter, Jessen, "On the influence of language similarity in non-target speaker verification trials", arXiv 2506.02777 (Interspeech 2025). https://arxiv.org/html/2506.02777v1 (read 2026-10-24)
- S10. Summary of the TidyVoice 2026 Challenge evaluation plan. https://www.themoonlight.io/review/tidyvoice-2026-challenge-evaluation-plan (read 2026-10-24)
- S11. ERes2NetV2, arXiv 2406.02167. https://huggingface.co/papers/2406.02167 (read 2026-10-24)
- S12. Search results (dataset titles), Mozilla Data Collective, 2026-10-24: https://datacollective.mozillafoundation.org/datasets/cmflnuzw5rrgpaoglo803u6h5, https://datacollective.mozillafoundation.org/datasets/cmn2e8k9z01kymm07yqqy4bk1

---

## 5. VAD and segmentation (§6.5)

| ID | Option | Version (date) | Facts | Licence |
|---|---|---|---|---|
| VAD-1 | Silero VAD | `silero-vad` 6.2.3 (2026-09-23) [S2] | One chunk (30+ ms) takes "less than 1ms" on one CPU thread; model about 2 MB; 8000 Hz and 16000 Hz; trained on "over 6000 languages"; runs on PyTorch or ONNX Runtime (`[onnx-cpu]`, `[onnx-gpu]` extras) [S1] | MIT; "no telemetry, no keys, no registration" [S1] |
| VAD-2 | WebRTC VAD | `webrtcvad` 2.0.10 (2017-01-07); `webrtcvad-wheels` 2.0.14.post1 (2026-10-02), Python >= 3.10 [S2] | Frame sizes [UNVERIFIED in C1] | MIT [S2] |
| VAD-3 | pyannote segmentation | part of pyannote.audio [§0 S8] | gated model; see §0 for dependencies and telemetry | see §4 |

- **Settings (minimum silence, maximum segment length):** Claude found no source with values for our latency target (K1). One data point: the `faster-whisper` VAD filter is "conservative and only removes silence longer than 2 seconds" by default [§0 S7]. Aren approves the final values (R10). C2 and C3 measure them.

### 5.1 Sources

- S1. Silero VAD README. https://github.com/snakers4/silero-vad/blob/master/README.md (read 2026-10-24)
- S2. PyPI JSON metadata: silero-vad, webrtcvad, webrtcvad-wheels (read 2026-10-24)

---

## 6. Audio capture on Ubuntu (§6.6)

| ID | Library | Version (date) | Backend on Linux | System audio | Licence |
|---|---|---|---|---|---|
| CAP-1 | `sounddevice` | 0.5.6 (2026-08-17) [S1] | PortAudio; on Linux, install PortAudio with the package manager (`libportaudio2`) [S2] | through a device that PortAudio shows [UNVERIFIED] | MIT [S1] |
| CAP-2 | `soundcard` | 0.4.6 (2026-04-12) [S1] | "Linux/pulseaudio" [S3]; its README example shows "Driver: PipeWire" [S3] | `include_loopback=True` allows "recording of speaker outputs" [S4] | BSD 3-clause [S1] |

- **Monitor source:** Ubuntu documents system sound capture with the "Monitor of <sound card>" source, selected in `pavucontrol` [S5]. The page does not say directly that the user still hears the audio [S5].
- **Virtual devices for sim tests:** `pipewire-pulse` has the built-in module `module-null-sink`. "The built-in modules can be loaded using Pulseaudio client programs, for example pactl load-module <module-name>" [S6]. The name of the monitor source of a null sink [UNVERIFIED in C1].
- **Two devices with one clock (§6.6 Q1):** Claude found no source for either library. `soundcard`: "Multiple calls to record() record immediately and concurrently" (this is for one microphone object) [S4]. C4 must check two devices.
- **Do virtual devices behave like real devices (§6.6 Q3):** no source found.

### 6.1 Sources

- S1. PyPI JSON metadata: sounddevice, soundcard (read 2026-10-24)
- S2. python-sounddevice, `doc/installation.rst`. https://github.com/spatialaudio/python-sounddevice/blob/master/doc/installation.rst (read 2026-10-24)
- S3. SoundCard README. https://github.com/bastibe/SoundCard/blob/master/README.rst (read 2026-10-24)
- S4. SoundCard documentation. https://soundcard.readthedocs.io/en/stable/ (read 2026-10-24)
- S5. Ubuntu Wiki, "record_system_sound". https://wiki.ubuntu.com/record_system_sound (read 2026-10-24)
- S6. `pipewire-pulse-modules(7)`. https://man.archlinux.org/man/pipewire-pulse-modules.7.en (read 2026-10-24)

---

## 7. Eval data (§6.7)

| ID | Data | Size | English reference | Speaker IDs | Licence | Access |
|---|---|---|---|---|---|---|
| DATA-1 | FLEURS `hy_am` | ~12 h per language; split 1509 / 150 / 350 sentences (train / dev / test); 3 recordings per sentence by 3 native speakers [S1] | yes: each sentence links to FLORES, which includes English [S1] | not stated [S1] | [UNVERIFIED in C1] | Hugging Face `google/fleurs`, config `hy_am` [S2] |
| DATA-2 | Common Voice Armenian (Armenia) | — | no [UNVERIFIED] | `client_id` [UNVERIFIED] | [UNVERIFIED in C1] | Mozilla Data Collective, versions 23.0 and 25.0 listed [§4 S12] |
| DATA-3 | ArmBench-ASR test sets | 10,113 clips, ~20.7 h in total; 3 of 5 sets are private [§1 S2] | no [UNVERIFIED] | — | — | the 2 public sets are Common Voice 26 and FLEURS [§1 S1] |

- ASR-1 and ASR-5 saw FLEURS and Common Voice in training [§1 S4][§1 S11]. FLEURS test speakers are disjoint from train speakers [S1].

### 7.1 Sources

- S1. FLEURS paper, arXiv 2205.12446 (HTML). https://ar5iv.arxiv.org/html/2205.12446 (read 2026-10-24)
- S2. NVIDIA NeMo Curator docs, "Load FLEURS Dataset" (`lang="hy_am"`). https://docs.nvidia.com/nemo/curator/curate-audio/load-data/fleurs-dataset.md (read 2026-10-24)

---

## 8. GPU and memory budget (§6.8 Q3)

- No VRAM value is measured on the RTX 5070 (all runs wait for C2).
- Weights only, float16 (calc). Activations, the CUDA context, and the runtime memory are not included [UNVERIFIED]:

| Combination | Weights (calc) |
|---|---|
| ASR-1 (115M) + MT-2 (600M) + SPK-3 (23M) + VAD-1 (~2 MB) | ~1.5 GB |
| ASR-2 / MT-5 SeamlessM4T v2 (2.3B) + SPK-3 + VAD-1 | ~4.7 GB |
| ASR-6 omniASR-LLM-1B (source: ~6 GiB inference VRAM on an A100 [§1 S5]) + MT + speaker model | > 6 GiB |

- The GPU has 8151 MiB VRAM (`PLAN.md` §1.6).

---

## 9. Questions for the discussion

These are open points from the facts. They are not decisions (R8).

1. **ASR licence:** ASR-2 (SeamlessM4T v2), MT-2 (NLLB), MT-5, and ASR-7 (MMS) are non-commercial (CC-BY-NC 4.0). Does a non-commercial licence matter for this project (RK12)?
2. **ASR quality data:** ArmBench has no contamination data, and 3 of its 5 sets are private. ASR-1 saw Common Voice 17.0 and FLEURS. Which test set do we trust for the C3 bake-off: FLEURS test, our own recordings, or both?
3. **MT quality data:** C1 found no common Armenian → English score for the MT candidates. FLEURS `hy_am` gives the English text for each clip (DATA-1). Is FLEURS test the MT eval set for C3?
4. **Runtimes:** PyTorch with CUDA 13 is the common base. CTranslate2 needs CUDA 12 libraries and has no INT8 on Blackwell (§0). Do we add CTranslate2 only if a C2/C3 measurement shows that MT is too slow?
5. **pyannote:** telemetry is on by default, the models are gated, and `lightning` must be exactly 2.4.0 with NeMo (§0). Are these acceptable, or do they count against SPK-1 and SPK-5?
6. **H-S1:** the sources show a language effect on scores. Claude's reading [not a fact]: all speakers on the call speak Armenian, so all non-target pairs are in one language, and the clustering threshold must come from Armenian data. C5 already plans this (D-003).
7. **Sortformer (SPK-4):** it is streaming and needs no clustering code. But it has a maximum of 4 speakers, it is trained "primarily in English", and it uses the NVIDIA Open Model License (Claude did not read the terms). The interview has "two or more people on the call side" (`PLAN.md` §1.5). Is a limit of 4 speakers acceptable?
8. **diart (SPK-5):** version 0.9.2 does not install with pyannote.audio 4.0.7 [RUN]. Do we keep it on the list with an older pyannote.audio, or remove it?

---

## 10. Follow-up questions from Aren (2026-10-24)

### 10.1 Can a non-streaming ASR give a line in less than 5 s (K1)?

- K1 counts from "the end of a spoken phrase" (`PLAN.md` §1.2). A segment pipeline does this work after the end of the phrase:
  1. VAD waits for the minimum silence (a parameter, R10).
  2. ASR on the full segment.
  3. MT on the text.
  4. Speaker embedding (system side only).
- No step is measured on the RTX 5070 (Aren: runs wait for C2).
- Speed facts from other hardware (throughput, not one-segment latency):
  - Open ASR Leaderboard, A100, batch up to 64, English models: FastConformer CTC Large RTFx 6399.25; Parakeet TDT 0.6B v2 RTFx 3386.02; Whisper Large v3 RTFx 145.51 [S1].
  - "CTC and TDT decoders deliver much better RTFx" [S1].
  - Fast Conformer is "2.8× faster than an equivalent Conformer during inference" [S2].
- Limit: these numbers use large batches on an A100. The latency of one 2–10 s segment on the RTX 5070 [UNVERIFIED]. The C2 test that measures the latency of each line answers this.

### 10.2 Is ONNX Runtime faster than NeMo for ASR-1?

- Claude found no source that compares ONNX Runtime with NeMo for this model or for a FastConformer model.
- `onnx-asr` benchmark (ONNX only, no NeMo row): NeMo Parakeet v2/v3 (FastConformer) RTFx 57 on a T4 with CUDA; RTFx 320 on an **RTX 5070 Ti with TensorRT** [S3]. Thus ONNX Runtime with TensorRT runs on a Blackwell GPU [S3].
- `onnx-asr` supports NeMo FastConformer models "with CTC, RNN-T, TDT, and Transformer decoders" [S3].
- The existing ASR-1 export uses the CTC head only [§1 S8]. The CTC head has a higher WER than the RNNT head: MCV 17.0 11.19 vs 9.90; FLEURS 13.23 vs 12.32 [§1 S4].

### 10.3 Whisper turbo

- Whisper is not a streaming model. `transcribe()` "processes the audio with a sliding 30-second window" [S4]. Whisper "is not designed for real-time transcription" [S5].
- Streaming wrappers exist: Whisper-Streaming ("local agreement policy", "3.3 seconds latency" on an English long-form test set) [S5]. The authors say that it is "becoming outdated, replaced by SimulStreaming" [S5].
- `turbo`: 809M parameters, ~6 GB VRAM, ~8x relative speed to `large` (A100, English) [S4]. "The `turbo` model is not trained for translation tasks" [S4].
- ASR-3 (Armenian fine-tune of large-v3-turbo) has a higher WER than ASR-1 on all 5 ArmBench sets [§1 S1].

### 10.4 Sources

- S1. Open ASR Leaderboard paper, arXiv 2510.06961v3, Table 3 and Section 3 (A100-SXM4-80GB, CUDA 12.6). https://arxiv.org/html/2510.06961v3 (read 2026-10-24)
- S2. Fast Conformer paper, arXiv 2305.05084v6. https://arxiv.org/html/2305.05084v6 (read 2026-10-24)
- S3. onnx-asr README, "Benchmarks" and supported models. https://github.com/istupakov/onnx-asr/blob/main/README.md (read 2026-10-24)
- S4. openai/whisper README (model table, turbo notes). https://github.com/openai/whisper/blob/main/README.md (read 2026-10-24)
- S5. ufal/whisper_streaming README. https://github.com/ufal/whisper_streaming/blob/main/README.md (read 2026-10-24)
