# Armenian ASR research C1

- Chat ID: `3470b934-f0fe-4fc7-a982-7bf58e4e13e0`
- Created: 2026-10-24T07:43:36.009821Z
- Updated: 2026-10-24T09:31:00.504876Z
- Messages in this file: 12

> **Note:** This file has only the text blocks of the main branch of the chat.
> The text is not changed. Human text is in code fences.
> Not in this file: 4 messages in side branches.
> Blocks of other types in the main branch: injected_prompt_block 5, thinking 91, tool_result 214, tool_use 214.
> The original chat in the Claude app has all blocks.

## 1. human · 2026-10-24T07:43:36.109866Z

````text
```markdown
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
- **Last commit:** Aren gives the hash of the last commit on `main` at the start of C1.
- **Decisions:** D-001 to D-011 are ACCEPTED.

## Facts that C1 needs

- **Laptop** (`PLAN.md` §1.6): RTX 5070 Laptop GPU (Blackwell) with 8 GB VRAM, 32 GB RAM, Ubuntu 26.04.1 LTS, PulseAudio on PipeWire 1.6.2, NVIDIA driver 595.99.02 (supports CUDA up to 13.2).
- **Aren's candidates:**
  - `nvidia/stt_hy_fastconformer_hybrid_large_pc` (ASR),
  - `Helsinki-NLP/opus-mt-hy-en` (MT),
  - the ArmBench-ASR leaderboard (`Metric-AI/ArmBench-ASR`).
- **Hypothesis H-S1** (speaker models and Armenian): research only. No fine-tuning before the C5 measurements (D-003).
- The Claude workspace cannot download models (the proxy blocks huggingface.co). Models run only on Aren's laptop.

## Open questions

- **Chat export (D-011):** not a C1 task. The side chat S1 handles the export format. C1 does not wait for it.
- The research questions are in `PLAN.md` §6.1–§6.8.

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

```

Let's begin C1.
````

## 2. assistant · 2026-10-24T07:44:19.291281Z

I am starting C1. First, I ask for access to the project folder.

Access is granted. Now I do the chat start checklist. First, I look at the folder and the memory notes for this project.

Now I copy the Read-list files from your folder into my workspace.

I have access to the project folder. I read the handover and the files in its Read list: `RULES.md`, `PLAN.md` §1, §5.2 (C1) and §6, and `DECISIONS.md`.

## 1. Goal of C1 (please confirm)

C1 collects facts for the research questions in `PLAN.md` §6.1–§6.8, with a tag and a source for each fact. I write the facts into `docs/research/RESEARCH.md`, with one table for each component. Then we discuss the facts, and you decide the first C2 candidate, the C3 shortlists and the other C1 items in `DECISIONS.md`.

## 2. Notes from the Read list

- The handover lists D-001 to D-011. `DECISIONS.md` also has D-012 (the chat converter, from S1, ACCEPTED). D-012 does not change C1.
- D-007 tells C1 to check that each candidate library supports Python 3.12. The tables have a column for this.

## 3. Proposed research order

The handover says "Start with §6.1". I propose one short step before it.

| Step | Section | Reason for the position |
|---|---|---|
| 0 | §6.8 Q1–Q2: the PyTorch and CUDA versions for Blackwell; support in NeMo, CTranslate2, ONNX Runtime and pyannote | Each table has a "Blackwell" column, and all of these columns need this fact. |
| 1 | §6.1 ASR (automatic speech recognition), with the test-set facts from §6.7 that the WER values need | The brief names the model choice as the main risk for Armenian (D-002). |
| 2 | §6.2 MT (machine translation) | — |
| 3 | §6.3 Cascade or end-to-end | It uses the facts from steps 1 and 2. |
| 4 | §6.4 Speaker labels and H-S1 | — |
| 5 | §6.5 VAD (voice activity detection) | — |
| 6 | §6.6 Audio capture and virtual devices | — |
| 7 | §6.7 Eval data: licence, size, access | — |
| 8 | §6.8 Q3: total VRAM | It adds up the values from the other tables. |

**Weak point of step 0:** ASR starts a little later. If you prefer, I start with §6.1 and fill in the Blackwell column after it.

## 4. Proposed format of `RESEARCH.md`

Each component gets one section with four parts:

1. **Quality table.** The columns are different for each component. ASR uses WER/CER, MT uses chrF/BLEU, and speaker models use EER (equal error rate).
2. **Practical table.** The columns are the same for all components: runtime and version, Python 3.12, Blackwell, VRAM, speed, licence, and gated (a token or accepted terms). For §6.8 Q3, I add up these tables.
3. **Other facts.** Facts that do not fit in a table, one fact on each line, with a tag.
4. **Sources.** A numbered list with the title, the URL, the date I read it, and the model revision if the page gives one.

The file has no recommendations (R8). Its last section is "Questions for the discussion".

**Tags in the cells:**
- `[S3]` means [SOURCE], source S3 in the list of the same section.
- `[RUN: <file>]` means a measured value. The result file is in `test-results/`.
- `[UNVERIFIED]` means there is no source. We do not use it as a reason for a decision.
- `—` means I found no value.

**Proposed addition:** a "Dialect" column. Armenian has two standard forms, Eastern and Western. A model or a test set can cover only one of them. §6 does not ask about this.

Example (ASR, structure only, no real values):

```markdown
## 1. ASR

### 1.1 Quality
| ID | Model (exact name) | Size | Armenian WER / CER (test set) | Test sets seen in training | Dialect | Punctuation | Streaming |
|---|---|---|---|---|---|---|---|
| ASR-1 | nvidia/stt_hy_fastconformer_hybrid_large_pc | … [S1] | … (FLEURS hy_am) [S2] | … [S1] | … | … [S1] | … |

### 1.2 Practical
| ID | Runtime (version) | Python 3.12 | Blackwell | VRAM | Speed (RTF) | Licence | Gated |
|---|---|---|---|---|---|---|---|
| ASR-1 | NeMo … [S3] | … | [UNVERIFIED] | — | — | … [S1] | … |

### 1.3 Other facts
- ASR-1: … [S1]

### 1.4 Sources
- S1. Model card, nvidia/stt_hy_fastconformer_hybrid_large_pc, <URL>, read 2026-10-24.
```

## 5. Open questions

1. What is the hash of the last commit on `main`?
2. The C1 time box is in `PLAN.md` §5.1, which is not in the Read list. May I read §5.1? R16 needs the time box.
3. Do you want small [RUN] checks on your laptop during C1?
   - For example, one command could check PyTorch on the RTX 5070 in a temporary environment. It does not change `pyproject.toml` or `uv.lock`. It downloads a large PyTorch package (several GB [UNVERIFIED]).
   - The other option is that all runs wait for the install check in C2 (D-002). Then the Blackwell and VRAM columns stay [SOURCE] or [UNVERIFIED] in C1.
4. Do you confirm the research order (§3) and the format (§4) with the Dialect column?

When you confirm, I start with step 0.

## 3. human · 2026-10-24T07:52:41.917637Z

```text
1. [3bf69fd](https://github.com/arkarapetyan/tir-asr/commit/3bf69fdc2f32fb0be294f9fdbf18a991bd9eb1c0)
2. you may read all of the PLAN.md
3. All runs wait for the install check. I dont want to download anything twice
4. I confirm the research order. There is no need for the dialect variations, only Eastern Armenian will be sufficient. I have questions regarding CTransalte and pyannote since I dont have experience with this frameworks. How much of performance do they give and do we need them in addition to ONNX?
```

## 4. assistant · 2026-10-24T08:09:24.436202Z

I will read the rest of `PLAN.md` first. Then I start step 0. Your questions about CTranslate2 and pyannote are part of step 0 (§6.8 Q2), so I will answer them with sources.

C1 has a time box of 2.5 h. It started at 11:43, so it ends at about 14:13, and no buffer is left. I will keep the research short.

Now the original Hugging Face blog post has a URL in a fetched result, so I can read it.

Step 1 (ASR) has its main facts. I write sections 0 and 1 of the draft now, while the details are fresh.

I have enough facts for the other sections. I now write sections 2 to 8 and the discussion questions.

The run shows a real conflict: `diart` 0.9.2 cannot install with `pyannote.audio` 4.0.7. I correct three places in the draft.

All source references resolve. Now I write the file into your project folder.

The handover says not to trust a remote write. I copy the file back and compare checksums.

The file in your folder matches my copy byte for byte (SHA-256 `e0ddca05…dd507`).

The research draft is done. It is in your project folder at `docs/research/RESEARCH.md`, and I checked the write with a checksum. Every fact has a tag and a source, and the file makes no decisions (R8). C1 has used about 30 minutes of its 2.5-hour time box.

## Main facts

- **ASR:**
  - On ArmBench-ASR, the best open model is your candidate `nvidia/stt_hy_fastconformer_hybrid_large_pc`, with a combined WER of 19.86. Next are SeamlessM4T v2 with 28.94 and the Whisper fine-tunes with about 33. Plain Whisper-large-v3 has 65.12.
  - The FastConformer model is small (115M) and has the CC-BY-4.0 licence. It gives punctuation and capital letters.
  - It does not stream, and it saw Common Voice 17.0 and FLEURS in training.
  - A community ONNX export of its CTC head exists, so ONNX Runtime can run it without NeMo.
  - ArmBench gives no data on which models saw its test sets in training, and 3 of its 5 test sets are private.
- **MT:**
  - I found no Armenian → English score on one common test set for the MT candidates.
  - 91 % of the OPUS-MT `hy-en` training pairs come from JW300 and the Bible. Only 0.7 % comes from subtitles.
  - NLLB has the CC-BY-NC licence, and its model card says it is "not released for production deployment".
  - FLEURS `hy_am` links each clip to its English sentence, so one clip gives the audio, the Armenian text, and the English text.
- **Speaker labels (H-S1):**
  - Three sources show that language has an effect on speaker scores. I found no results for Armenian.
  - Sortformer allows a maximum of 4 speakers and is trained "primarily in English".
  - **My workspace check:** `diart` 0.9.2 cannot install together with `pyannote.audio` 4.0.7, because the two need different numpy versions.
- **Audio capture:** I found no source that says how either library reads two devices with one clock. C4 must test this.
- **Licences:** SeamlessM4T v2, NLLB, and MMS have the CC-BY-NC licence (non-commercial).

## Discussion (step 3)

Section 9 of the file has 8 open points. Two of them are your choice, and I need your answer before I propose the decisions:

1. **Licence:** does a non-commercial licence matter for this project (RK12)? Your answer can remove SeamlessM4T v2, NLLB, and MMS from the lists.
2. **pyannote:** are these three things acceptable for the interview laptop?
   - telemetry that is on by default,
   - gated models that need a Hugging Face token,
   - `lightning` fixed at exactly 2.4.0 next to NeMo.

After your answers, I propose the decisions one at a time, as R7 requires. Each proposal has two or more options, the weak points of my preference, and a test that can show my preference is wrong. The order is:

1. ASR (first candidate and shortlist)
2. MT
3. Speaker models
4. VAD
5. Eval data
6. Capture library and virtual-device method
7. "Eastern Armenian only" as a scope entry

**Commit now (optional):** this step is complete, so you can commit it after you read the diff:

```
docs(research): add C1 research facts (RESEARCH.md)
```

## 5. human · 2026-10-24T08:16:28.463841Z

```text
My questions 

1. stt model does not stream, but can we make sure that it will work under 5s latency?
2. Will ONNX Runtime run the stt model faster than its original nemo framework?
3. What about whisper turbo? it seems that it does stream but it is a heavier model
Answering to your points
1. I guess that NC license is fine in this case
2. The three points mentioned for pyannote are fine.
Please propose the decisions  in a bulk and I'll use checkbox to select each of them.
I won't be commiting the changes to the RESEARCH file
```

## 6. assistant · 2026-10-24T08:48:36.087502Z

I will answer your three questions with sources first. Then I propose all decisions together.

The follow-up facts are now section 10 of `RESEARCH.md`, and I verified the write with a checksum.

Neither file changed. I now write the accepted decisions into `DECISIONS.md` and make the matching changes to `PLAN.md`.

I wrote the decisions into your folder and checked both files with checksums:

- **`DECISIONS.md`:**
  - D-013, D-014, D-016, D-017, D-018, D-019, and D-020 are ACCEPTED (2026-10-24). Each entry has your words as the reason. Where you only ticked a box, the entry says that you gave no reason of your own.
  - D-007 has a short C1 note: Python 3.12 stays.
- **`PLAN.md` v0.6:**
  - **C2 install check:** it now names the two ASR paths (NeMo first, ONNX-CTC second) and CTranslate2 with the CUDA 12 libraries.
  - **C3:** it now uses your 20 recordings and the new shortlists.

**D-015 is still PROPOSED and needs your confirmation.** In round 1 you agreed, but in round 2 you did not tick it. D-016 B changed its runtime. The new text is:

- **First candidate for C2:** NLLB-200-distilled-600M on **CTranslate2**. The first version said Transformers.
- **C3 shortlist:**
  - OPUS-MT on CTranslate2,
  - NLLB-600M on CTranslate2,
  - Seamless text-to-text on PyTorch. I do not know if CTranslate2 supports Seamless.

Do you accept D-015 as changed? If yes, please give a short reason in your own words (R7).

Then I finish C1:

1. I write the handover `docs/handovers/01-research.md`.
2. I copy `DECISIONS.md` and `PLAN.md` into the Project documents.
3. I give you one commit message for `DECISIONS.md`, `PLAN.md`, and the handover. `RESEARCH.md` stays out of the commit, as you decided.

C1 has used about 1 hour of its 2.5 hours.

## 7. human · 2026-10-24T08:52:57.118196Z

```text
Regarding 20 recordings. I'll actually try to include more recordings that will include voices of multiple people and recordings done on different devices.
Regarding D15. I see that CTranslate 2 will theoretically provide good amount of performance boost. But since it doesnt support INT8 on Blackwell and I have noticed people reporting errors when trying to use it, my question is that will it actually be slower on Blackwell since it will use FP16 or FP32? Is there still a point in using it as opposed to ONNX runtime?
And since we have still got time, let's discuss a  bit (not too much) things that we might have missed or didnt dive deep into. You read all of the discussion for today in this chat and find blindspots or other new ideas to discuss.
```

## 8. assistant · 2026-10-24T09:19:09.586260Z

I will check the facts about CTranslate2 on Blackwell first. Then I review the chat for blind spots.

I will check two facts before I write the download commands: the name of the Hugging Face download command, and the file list of the NLLB model.

The staged sizes are the same as the old versions. That can be the problem from C0, where a write kept the old text. I compare the checksums.

The read-back still shows the old text. The stage tool says a re-staged file can show old content for a short time, so I wait and read it once more.

The sizes are now correct. I confirm with checksums.

I wrote your answers into the files on your laptop. The first write failed without an error, the same way as in C0: the files got a new time stamp but kept the old text. I wrote them again from a new staged path, and now the checksums match. The handover will say to use a new staged path for every write.

**What changed in the files:**
- **D-015 is ACCEPTED.** It now has the parameter `mt_compute_type = float16`. The C2 install check also times NLLB on PyTorch.
- **D-019 has your amendment:** at least 20 recordings, several voices and devices, the 4 scripts below, and some clips that go through a real call.
- **`PLAN.md`:**
  - C3 writes the Armenian WER normalization rules and their tests first.
  - The C4 setup guide says "use wired headphones".
  - C8 has a list of the known limits found so far: Eastern Armenian only, "նա" in MT, and overlapping speakers.
- **Offline start (item 5):** dropped, as you decided. I did not mean an offline-only app. The idea was a check that the start does not need the network.
- **Items 8–10:** you did not tick them, so I did not add them. The latency definition (item 9) is a C2 decision in the plan anyway.

## Scripts for the eval recordings

**How to record:**
- Each person reads only their own lines.
- If someone changes a word, change the Armenian reference to what is in the audio.
- Numbers are written as words, as people say them.
- † marks a line with «նա». Where the text does not show the gender, the English says "he/she".
- Read text sounds less natural than free talk. If you have time, also record 2–3 minutes of free talk and write its reference after.

### Script 1: trip planning (3 people)

| # | Speaker | Armenian | English |
|---|---|---|---|
| 1 | Anna | Բարև, տղերք։ Լսո՞ւմ եք ինձ։ Ուզում էի խոսել շաբաթ օրվա ճամփորդության մասին։ | Hi, guys. Can you hear me? I wanted to talk about Saturday's trip. |
| 2 | Davit | Բարև, Աննա։ Այո, լավ եմ լսում։ Ես արդեն մտածել եմ, որ կարող ենք առավոտյան ժամը ութին դուրս գալ Երևանից։ | Hi, Anna. Yes, I can hear you well. I have already thought that we could leave Yerevan at eight in the morning. |
| 3 | Narek | Ութը շատ վաղ է, Դավիթ։ Գուցե ժամը իննի՞ն։ Ես ուրբաթ երեկոյան մինչև ուշ աշխատում եմ։ | Eight is very early, Davit. Maybe at nine? I work until late on Friday evening. |
| 4 | Anna | Լավ, թող լինի ժամը ինը։ Ո՞վ է մեքենա վարելու։ | Okay, let it be nine o'clock. Who is going to drive? |
| 5 | Davit | Ես կարող եմ վարել։ Իմ մեքենայում չորս տեղ կա, բայց բեռնախցիկը փոքր է։ | I can drive. There are four seats in my car, but the trunk is small. |
| 6 | Narek | Ուրեմն շատ իրեր չվերցնենք։ Իսկ որտե՞ղ ենք գիշերելու։ | Then let's not take many things. And where are we going to stay overnight? |
| 7 | Anna | Ես երեկ զանգեցի մի հյուրատան։ Նրանք ասացին, որ երկու սենյակ ազատ ունեն, մեկ գիշերը տասնհինգ հազար դրամ։ | Yesterday I called a guesthouse. They said that they have two free rooms, fifteen thousand drams per night. |
| 8 | Davit | Դա նորմալ գին է։ Նախաճաշը ներառվա՞ծ է։ | That is a normal price. Is breakfast included? |
| 9 | Anna | Այո, նախաճաշը ներառված է։ Բայց պետք է մինչև վաղը պատասխանեմ նրանց։ | Yes, breakfast is included. But I have to give them an answer by tomorrow. |
| 10 | Narek | Ես համաձայն եմ։ Միայն թե ուզում եմ կիրակի օրը վաղ վերադառնալ, որովհետև երկուշաբթի հանդիպում ունեմ։ | I agree. I only want to come back early on Sunday, because I have a meeting on Monday. |
| 11 | Davit | Խնդիր չկա։ Կիրակի ճաշից հետո կճանապարհվենք։ Ճանապարհին կարող ենք կանգնել Սևանի մոտ։ | No problem. We will leave on Sunday after lunch. On the way we can stop near Sevan. |
| 12 | Anna | Հիանալի է։ Ուրեմն ես հիմա կգրեմ հյուրատանը և կամրագրեմ սենյակները։ | Great. Then I will write to the guesthouse now and book the rooms. |
| 13 | Narek | Շնորհակալ եմ, Աննա։ Ես էլ կվերցնեմ մրգեր և ջուր ճանապարհի համար։ | Thank you, Anna. I will also take fruit and water for the road. |
| 14 | Davit | Լավ, ուրեմն շաբաթ առավոտյան ժամը ինը ես ձեզ կվերցնեմ տնից։ Մինչ այդ։ | Okay, then I will pick you up from home on Saturday at nine in the morning. See you then. |

### Script 2: table booking (2 people)

| # | Speaker | Armenian | English |
|---|---|---|---|
| 1 | Aram | Բարև ձեզ, «Նռնենի» ռեստորանն է, լսում եմ ձեզ։ | Hello, this is the Nrneni restaurant, I am listening. |
| 2 | Lilit | Բարև ձեզ։ Ուզում եմ սեղան ամրագրել վաղվա երեկոյի համար, վեց հոգու համար։ | Hello. I want to book a table for tomorrow evening, for six people. |
| 3 | Aram | Իհարկե։ Ո՞ր ժամին եք ցանկանում գալ։ | Of course. At what time do you want to come? |
| 4 | Lilit | Ժամը յոթի կողմերը։ Հնարավո՞ր է, որ սեղանը պատշգամբում լինի։ | Around seven o'clock. Is it possible for the table to be on the terrace? |
| 5 | Aram | Պատշգամբում ազատ տեղ կա միայն ժամը ութից։ Ներսում կարող եմ սեղան տալ ժամը յոթին։ | On the terrace there is a free place only from eight o'clock. Inside I can give you a table at seven o'clock. |
| 6 | Lilit | Լավ, ուրեմն ներսում, ժամը յոթին։ Մեզ հետ փոքր երեխա էլ կլինի։ Մանկական աթոռ ունե՞ք։ | Okay, then inside, at seven o'clock. A small child will also be with us. Do you have a child's chair? |
| 7 | Aram | Այո, ունենք, կնշեմ ամրագրման մեջ։ Ի՞նչ անունով գրեմ։ | Yes, we have one; I will note it in the booking. Under what name should I write it? |
| 8 | Lilit | Լիլիթ Հովհաննիսյան։ Հեռախոսահամարս՝ զրո իննսունինը, տասնմեկ, քսաներկու, երեսուներեք։ | Lilit Hovhannisyan. My phone number is zero ninety-nine, eleven, twenty-two, thirty-three. |
| 9 | Aram | Շնորհակալություն, տիկին Հովհաննիսյան։ Ամրագրեցի՝ վաղը, ժամը յոթին, վեց հոգի։ Եթե ուշանաք, խնդրում եմ, զանգահարեք։ | Thank you, Mrs. Hovhannisyan. I have booked it: tomorrow, at seven o'clock, six people. If you are late, please call. |
| 10 | Lilit | Անպայման։ Շնորհակալ եմ, ցտեսություն։ | Definitely. Thank you, goodbye. |

### Script 3: work deadline (2 people)

| # | Speaker | Armenian | English |
|---|---|---|---|
| 1 | Mariam | Գոռ, բարև։ Ներողություն, մի քիչ ուշացա։ Կարո՞ղ ենք արագ քննարկել ներկայացումը։ | Gor, hi. Sorry, I am a little late. Can we quickly discuss the presentation? |
| 2 | Gor | Բարև, Մարիամ։ Իհարկե։ Ես պատրաստել եմ առաջին տասը սլայդը, մնացածը դեռ պետք է անել։ | Hi, Mariam. Of course. I have prepared the first ten slides; the rest still has to be done. |
| 3 | Mariam | Լավ է։ Իսկ Արմենն ուղարկե՞լ է վերջին թվերը։ Առանց դրանց չենք կարող ավարտել։ | Good. And has Armen sent the latest numbers? We cannot finish without them. |
| 4 † | Gor | Ոչ, նա ասաց, որ կուղարկի այսօր՝ մինչև ժամը վեցը։ Հիմա նա ուրիշ նախագծով է զբաղված։ | No, he said that he will send them today, by six o'clock. He is busy with another project now. |
| 5 | Mariam | Հասկանալի է։ Հաճախորդի հետ հանդիպումը հինգշաբթի է՝ ժամը տասնմեկին։ Ուզում եմ, որ չորեքշաբթի երեկոյան ամեն ինչ պատրաստ լինի։ | Understood. The meeting with the client is on Thursday, at eleven o'clock. I want everything to be ready on Wednesday evening. |
| 6 | Gor | Կփորձեմ։ Բայց եթե թվերն ուշանան, գուցե մի օր ավել պետք լինի։ | I will try. But if the numbers are late, maybe we will need one more day. |
| 7 | Mariam | Հինգշաբթին տեղափոխել չենք կարող, հաճախորդն արդեն հաստատել է։ Ես ինքս կզանգեմ Արմենին։ | We cannot move Thursday; the client has already confirmed. I will call Armen myself. |
| 8 | Gor | Լավ միտք է։ Եվ մի բան էլ։ Դիզայնը փոխե՞նք, թե նույնը թողնենք։ | Good idea. And one more thing. Should we change the design, or keep it the same? |
| 9 † | Mariam | Թողնենք նույնը։ Նա արդեն հավանել է այս տարբերակը։ | Let's keep it the same. He/she has already approved this version. |
| 10 | Gor | Համաձայն եմ։ Ուրեմն ես շարունակում եմ սլայդները, իսկ դու խոսիր Արմենի հետ։ Վաղն առավոտյան կզանգեմ քեզ։ | I agree. Then I continue with the slides, and you talk to Armen. I will call you tomorrow morning. |

### Script 4: two friends (2 people)

| # | Speaker | Armenian | English |
|---|---|---|---|
| 1 | Tigran | Ալո, Սոնա, լսո՞ւմ ես։ Կապը վատ է։ | Hello, Sona, can you hear me? The connection is bad. |
| 2 | Sona | Հա, Տիգրան, հիմա լավ է լսվում։ Ո՞նց ես։ Վաղուց չէինք խոսել։ | Yes, Tigran, now I can hear you well. How are you? We have not talked for a long time. |
| 3 | Tigran | Լավ եմ, շնորհակալ եմ։ Երեկ ֆուտբոլի էի գնացել, մերոնք երկու մեկ հաղթեցին։ | I am fine, thank you. Yesterday I went to the football match; our team won two to one. |
| 4 | Sona | Վա՜յ, ապրեն։ Ես չկարողացա նայել, ամբողջ օրը աշխատանքի էի։ Ո՞վ խփեց գոլերը։ | Wow, well done to them. I could not watch; I was at work all day. Who scored the goals? |
| 5 † | Tigran | Երկուսն էլ նոր հարձակվողը խփեց։ Նա ընդամենը տասնինը տարեկան է։ | The new forward scored both. He is only nineteen years old. |
| 6 | Sona | Լավ է։ Իսկ քույրդ ինչպե՞ս է։ Լսեցի, որ նոր բնակարան են գնել։ | Good. And how is your sister? I heard that they bought a new apartment. |
| 7 | Tigran | Այո, Կոմիտասի պողոտայում։ Երեք սենյականոց է, բայց վերանորոգում է պետք։ | Yes, on Komitas Avenue. It has three rooms, but it needs renovation. |
| 8 | Sona | Ոչինչ, կանեն։ Ի դեպ, եղանակը տեսե՞լ ես, վաղը ձյուն է սպասվում։ | That is okay, they will do it. By the way, have you seen the weather? Snow is expected tomorrow. |
| 9 | Tigran | Հա, լսել եմ։ Դե, ուրեմն տանը կմնամ։ Լավ, Սոնա, հետո կզանգեմ, հիմա պիտի գնամ։ | Yes, I have heard. Well, then I will stay at home. Okay, Sona, I will call later; now I have to go. |
| 10 | Sona | Լավ, հաջող, բարևներ տնեցիներին։ | Okay, bye, say hello to your family. |

The scripts also test things that the C3 normalization rules must handle:
- the marks ՞ and ՜ inside a word,
- «և» inside a sentence and «Եվ» at the start of a sentence,
- numbers and a phone number,
- loanwords such as «սլայդ», «դիզայն», and «ֆուտբոլ».

## Download commands (models only)

These commands put the weights into the normal Hugging Face cache (`~/.cache/huggingface/hub`), not into the project folder (R11). The Python packages download one time in C2 with `uv add`. Run the commands from your home folder:

```bash
cd ~
LOG=/home/aren/dev/armenian-asr/test-results/c1-downloads.txt
date 2>&1 | tee "$LOG"
uvx --from huggingface_hub==2.3.0 hf download nvidia/stt_hy_fastconformer_hybrid_large_pc 2>&1 | tee -a "$LOG"
uvx --from huggingface_hub==2.3.0 hf download OpenVoiceOS/stt_hy_fastconformer_hybrid_large_pc_onnx 2>&1 | tee -a "$LOG"
uvx --from huggingface_hub==2.3.0 hf download facebook/nllb-200-distilled-600M 2>&1 | tee -a "$LOG"
du -sh ~/.cache/huggingface/hub/models--* 2>&1 | tee -a "$LOG"
```

- **Download size:** about 3 GB or more:
  - the ASR model, about 459 MB,
  - the ONNX export (size not known),
  - NLLB, 2.48 GB as one `pytorch_model.bin` file.
- **If NeMo uses a different cache in C2 [UNVERIFIED]:** we load the `.nemo` file by its path. Nothing downloads again.
- **C3 models:** I can give the commands for Seamless, BuzzASR, and OPUS-MT now too, if you want them.

C1 has used about 1 h 35 min of its 2.5 hours. The last step is the chat close: the handover, the Project documents, and one commit message for `DECISIONS.md`, `PLAN.md`, and the handover. Do you want me to close C1 now?

## 9. human · 2026-10-24T09:22:48.057100Z

```text
Ok. let's close it, if any problem appears during the downloading , it will be discussed in C2. before closing however, one question, how should I save these recordings. What will be the best format? Should I separate each speaker's line or record one full audiofile with the dialogues? Must I save it in wav or can I use other format? Is it ok if we dont specify these names anymore and use just Speaker1 and Speaker 2 and Me for the first speaker
```

## 10. assistant · 2026-10-24T09:25:46.172761Z

Below I answer your recording questions. Then I close C1: I save the scripts with the new speaker labels, write the handover, and update the Project documents.

Now the handover for C2.

C1 is closed. The scripts, the handover, and the Project documents are saved, and I checked every write with a checksum.

## Your recording questions

- **Format:** WAV (16-bit PCM) or FLAC. Both are lossless. If a phone app saves only M4A, keep the original file and do not convert it. The program converts it one time.
- **Sample rate:** use the default of the device (44.1 or 48 kHz), in mono if the device allows it. The minimum is 16 kHz. The program resamples to 16 kHz mono.
- **One file or one file per line:** record **one continuous file for each take of a script**, with all the speakers.
  - Leave about 1 s between turns, and do not speak at the same time.
  - Make a label file with the start, the end, and the line ID of each turn. An Audacity label track is easy.
  - Reason: the sim tests and C5 need continuous dialogue. A script can cut single lines from a full file, but single files cannot become a natural dialogue.
- **Names:** yes. The scripts now use "Me", "Speaker 1", and "Speaker 2". "Me" is the person on the microphone side in the call tests. The names inside the sentences stay, because they are words in the audio.
- **Where to save:** `data/eval/`, for example `s1_phone_take1.wav` with `s1_phone_take1.txt` for the labels. `data/` is in `.gitignore`. `*.m4a` is not in its patterns, so keep all audio inside `data/`.

All of this is in `docs/eval/scripts.md`, together with the 4 scripts.

## Files written in C1

- `DECISIONS.md`: D-013 to D-020 are ACCEPTED, and D-007 has a C1 note.
- `PLAN.md` v0.6.
- `docs/eval/scripts.md`: new.
- `docs/handovers/01-research.md`: the handover for C2. Its "Do not" list has the write failure and the fix that worked.
- `docs/research/RESEARCH.md`: on your laptop only.
- The Project copies of `DECISIONS.md` and `PLAN.md` are updated.

## Your steps to close the chat

1. Run the unit check. No code changed, but the end-of-chat checklist needs the result file:
   ```bash
   cd /home/aren/dev/armenian-asr
   { uv run ruff check . && uv run ruff format --check . && uv run pytest; } > test-results/c1-unit.txt 2>&1; echo "exit=$?" >> test-results/c1-unit.txt
   ```
2. Read the diff, then commit and push. `RESEARCH.md` stays out of the commit:
   ```bash
   git add DECISIONS.md PLAN.md docs/handovers/01-research.md docs/eval/scripts.md
   git diff --cached
   git commit -m "docs(c1): log decisions D-013 to D-020, PLAN v0.6, eval scripts, handover 01"
   git push
   ```
3. Run the download commands from my last message. If they fail, we fix it in C2.
4. Write the C1 time in the `PLAN.md` time log (§11). C1 started at 11:43 and has taken about 1 h 50 min. That is within the 2.5-hour time box.

For C2, start a new chat in this Project and paste the handover as the first message. Give the hash of this commit there.

## 11. human · 2026-10-24T09:29:39.583253Z

```text
Everything is done update C1 time in PLAN.md and add the time saved to the buffer
```

## 12. assistant · 2026-10-24T09:31:00.580853Z

Your `PLAN.md` is the same as my last version. I add the C1 time and move the saved time to the buffer.

I added the C1 time to `PLAN.md` (now v0.7) on your laptop and checked the write with a checksum. The Project copy is updated too.

| Row | Time box | Actual | Note |
|---|---|---|---|
| C1 | 2.5 h | 1.8 h | 11:43–13:29 (1 h 46 min), 0.7 h under the time box |
| Buffer | 1 h + 0.7 h from C1 | 1.0 h | C0 used 1.0 h, so 0.7 h is left |
| Total | 20.5 h | 4.3 h | C0 + C1; the total time box does not change |

The total time box stays the same because the saving only moves 0.7 h from C1 to the buffer. I also added a v0.7 line to the change log.

Please commit and push this change:

```bash
cd /home/aren/dev/armenian-asr
git add PLAN.md
git diff --cached
git commit -m "docs(plan): log C1 time (1.8 h), move 0.7 h to the buffer"
git push
```

When you start C2, give the hash of this commit, because it is the newest commit on `main`.
