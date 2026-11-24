# Handover 10 → 11 (C11: speaker labels and the segment split)

**Date:** 2026-11-24

## Goal of the next chat

Aren did a live test after C10 (2026-11-24, no output file): "STT works excellent, but diarization creates too many speakers for a single person". Aren uses the program in meetings with few people. His two improvements for C11:

1. **Fewer speakers for one person:** "let's penalize new cluster creations in diarization". A new speaker must cost more than now.
2. **The split:** "let's improve the split part so that speech of same people does not go into the same box". Claude reads this as: the speech of two **different** people must not go into one block (D-060 part 3, Q-04). Confirm this reading with Aren first.

Before a value changes, do the test changes for tuning (D-072 part 5). Without them, a new value breaks the tests that check rules, as in D-069. End C11 with a live test that saves the audio of both sides (D-072 part 6).

## Current state

- **Branch:** `c10-ohanasr`, 7 commits, pushed; CI is green (Aren, 2026-11-24). Aren merges it into `main`. Claude does not know the commit hashes.
- **Program (D-080, D-081, D-082):**
  - The text step is OhanASR (in the program process), then Google Translate through `googletrans`.
  - One environment: Python 3.11, torch 2.8.0, numpy 1.26.4, fairseq2 0.5.2, omnilingual-asr 0.2.0, NeMo 3.0.0 (TitaNet only), `silero-vad` 6.2.3.
  - The Google timeout is 10 s, and `STOP_JOIN_S` is 5.0 s.
- **Speaker step (no change since C8):**
  - TitaNet-large and `CentroidClusterer` (D-058).
  - `spk_threshold` = 0.50: a segment joins the most similar speaker when the cosine to its centroid is 0.50 or more; else it starts a new speaker.
  - `spk_min_new_s` = 1.0 s: a shorter segment never starts a new speaker; it gets the nearest label, or `Unidentified` when no speaker exists yet (D-057 part 5, D-060 part 2).
- **Tests:** ruff passes; unit 253 passed; model 14 passed; T-E2E-01, T-E2E-02, T-SIM-02, and T-MODEL-ASR-02 pass (`TESTS.md` §2.11). Each program test runs in its own pytest process (D-082).
- **Documents:** `RULES.md` v0.6, `PLAN.md` v0.27, `DECISIONS.md` to D-082, `ARCHITECTURE.md` v0.44, `TESTS.md` §2.11.
- **Project documents:** the Project copies of `PLAN.md`, `DECISIONS.md`, and `ARCHITECTURE.md` are from C8. Only `RULES.md` is current. Read these three files from the project folder on the laptop; git is the source of truth (`PLAN.md` §7.3).

## Facts for the C11 design (no decision yet)

- **Speaker counts in the live tests [RUN, counted from the output files]:**
  - C7, the two S5 calls (`test-results/c7-live-p1.txt`, `c7-live-p4.txt`): one person on the call side gave one label (26 and 28 lines). No extra speaker.
  - C8 (`test-results/c8-live.txt`, two people on the call side, D-069): 7 labels. Speaker 1 (20 lines) and Speaker 2 (27 lines) were the two people. Speakers 3–7 had 1–2 short fragments each, from noise and a bad connection.
  - Thus the extra speakers probably come from short, noisy segments, not from the main voice [inference]. The C11 live test with saved audio checks this.
- **Threshold sweep (D-058) [RUN]:** TitaNet with `CentroidClusterer` had 0 errors on all four eval streams from 0.40 to 0.60. At 0.35, two S1 voices got one label. Stream D margin: +0.170. Thus a lower `spk_threshold` (fewer new speakers) has a measured limit near 0.40 on our eval.
- **Possible forms of "a cost for a new speaker" (each new value needs Aren's approval, R10, and a measurement, R6):**
  - a lower `spk_threshold`;
  - a higher `spk_min_new_s`, so that more short segments cannot start a speaker;
  - a separate, lower threshold for a new speaker (a margin), or a margin that grows with the number of speakers;
  - a new speaker only after two or more segments agree (a pending speaker), which keeps one-off fragments out;
  - a maximum number of speakers.
  - F4: the labels of past lines must not change, so a later merge of two speakers cannot change printed lines.
- **The split (D-060 part 3):**
  - The VAD cuts only after `vad_min_silence_ms` (500 ms) of silence. A fast change of speaker stays in one segment, and the segment gets the label of the voice with more speech.
  - Option B, a shorter silence: [RUN, D-069] 300 ms split a sentence of clip 1 into two lines (T-E2E-01 failed). A separate value for the `System` side was proposed in D-060.
  - Option C, a speaker change inside a segment: TitaNet embeddings on short windows, then a cut before the ASR. Not measured.
  - S1 call side: the pauses between Speaker 1 and Speaker 2 are 0.38–0.99 s; s1-13 → s1-14 is 0.38 s, under 500 ms (D-046).
- **Eval data on disk:**
  - `data/c7/p1.{mic,system}.wav` and `data/c7/p4.{mic,system}.wav`: the audio of both sides of the two S5 calls (one person on the call side).
  - The S1–S3 recordings and labels (`data/eval/raw/`), and stream D (made by `tir_asr.eval.streams`).
  - No eval file has the problem of Aren's live test (one person with many labels). Thus the C11 live test must save the audio of both sides (as C7, with `parecord`).
- **Tools:** `scripts/spk_bakeoff.py --model titanet` sweeps `spk_threshold` on the four streams (D-057 part 7). `scripts/c9_run.py` uses `Params()` for `dump`.

## Open questions for C11

1. Merge state of `c10-ohanasr` into `main`.
2. Aren's live test: how many people, and how many labels for each person? Was the audio saved?
3. Confirm the reading of the split request (point 2 of the goal).
4. The time box of C11.
5. Do you delete the models that are not in use (`models/ayb-0.5-4b`, `models/nllb-200-distilled-600M-ct2-float16`, and the Hugging Face cache entries of NeMo RNNT, NLLB, and Seamless)?

## Read list for the next chat

1. `docs/handovers/11-tuning.md` (this file)
2. `DECISIONS.md`: D-057, D-058, D-060, D-069, D-072 (parts 5 and 6), D-081, D-082 (from the project folder on the laptop)
3. `ARCHITECTURE.md` §2.2, §2.8, and §6
4. `TESTS.md` §2.7 (the speaker tests) and §2.11
5. `src/tir_asr/speakers/cluster.py`

Read `RULES.md` with the Projects tool (`claude/RULES.md`, v0.6).

## First task in the next chat

1. Ask for the access to `/home/aren/dev/armenian-asr`. Do the chat start checklist (`RULES.md` §5.1).
2. Ask the open questions.
3. Propose the design for goal 1 and goal 2 (options, weak points, R7), with a measurement plan (R6). Then write the tests in `TESTS.md` (R5), together with the test changes of D-072 part 5.

## Do not

- Do not change a value by preference. Each new value needs a measurement (R6) and Aren's approval (R10).
- Do not change the labels of printed lines (F4).
- Do not run two program loads in one pytest process (D-082). Run T-E2E-01, T-E2E-02, T-SIM-01, and T-SIM-02 each in their own process.
- Do not stop a sim test early. It prints nothing while the program runs. T-SIM-02 takes about 3.5 min.
- Do not change the OhanASR pins (Python 3.11, torch 2.8.0, numpy 1.26.4). fairseq2 0.5.2 needs them (D-081).
- Do not set `raise_exception=False`, and do not add retries or a fallback to another translator (R10, D-079).
- **Commands:** the model and sim tests run with `HF_HUB_OFFLINE=1`. `LD_LIBRARY_PATH` is empty on the laptop, so no `env -u` is necessary.
- **Remote writes:** write each output file one time into a new folder, write it to the laptop with the mtime guard, then stage it again and compare. After a `git switch` or a merge, stage the files again before a write.
- **`ruff` in the workspace:** only `--no-cache`, with `--config pyproject.toml`, in a scratch tree that has each module of `tir_asr`. In a red run, a missing module gives I001.
- **From the earlier handovers:** Claude does not run tests in the workspace (D-038); the full `git add`, `git commit -m`, and `git push` commands, with no co-author line (D-039); no sub-agents (R15).
