# C3 step

- Chat ID: `b2e5c77f-9f06-416a-9f06-f54b066ec181`
- Created: 2026-10-26T11:14:28.204470Z
- Updated: 2026-10-26T13:45:39.778941Z
- Messages in this file: 46

> **Note:** This file has only the text blocks of the main branch of the chat.
> The text is not changed. Human text is in code fences.
> Not in this file: 8 messages in side branches.
> Blocks of other types in the main branch: document 1, injected_prompt_block 5, thinking 136, tool_result 294, tool_use 294.
> The original chat in the Claude app has all blocks.

## 1. human · 2026-10-26T11:14:28.377271Z

```text
Let's begin C3 the last commit hash is 
[1ef128a](https://github.com/arkarapetyan/tir-asr/commit/1ef128a8389c498411fae0205b88c52105de3f00).
I have also recorded Scripts S1-S3. It is now saved in separate mic and call files for the whole dialogue. Do you need them mixed in a single file or in other format tell me?
```

## 2. assistant · 2026-10-26T11:14:54.646446Z

I will read the Project rules and the plan first. Then I will ask for the access to the project folder.

I can read the project folder. I read the handover, the files on its Read list, and RULES and DECISIONS in the Project.

## 1. Goal of C3 (please confirm)

First, C3 makes the eval tools, with the tests first. The tools are the Armenian text normalization, WER/CER, chrF, latency, RTF, VRAM, and the 48 → 16 kHz resample step. Then you run the bake-off of the ASR shortlist (D-014) and the MT shortlist (D-015) on S1–S3, and I make the results table. Last, we decide the ASR model and the MT model.

**Time (R16):** the time box is 2.5 h. The expected total is already 23.9 h. The full shortlists (5 ASR variants and 3 MT models) possibly do not fit in 2.5 h. After the metric code, I will propose the order of the candidates, with a time box.

## 2. Your question: one mixed file, or a different format?

You do not need to mix or convert them. Keep the files as they are (48 kHz, float32). The reasons:

- **Same as the program:** the program has two sources, the microphone ("Me") and the call side (F1, C4). Your two files are the same two sources. The program never gets a mix.
- **We know the side of each word:** each file holds one side. Thus each file has a known list of script lines. A mix loses this.
- **Later chats need the separate files:** C4 sim tests can play each file into its own null sink (D-020). C5 needs the call file only, because the speaker labels are for the call side only.
- **The resample has a test:** the eval code resamples to 16 kHz mono, and a test checks this step (PLAN C3). If you convert by hand, no test checks that step.

## 3. Open questions

- **Q-a.** Is `1ef128a` the merge of `c2d-cli` into `main`? Is CI green?
- **Q-b.** There is also a file `data/eval/raw/s1.wav`. It is 36 bytes smaller than `s1.mic.wav`, and you saved it about 14 h later. What is it? If it is a mix, we do not use it.
- **Q-c.** Who spoke on each side? I expect you on the microphone, and Speaker 1 and Speaker 2 on the call. Which devices and which call application did they use?
- **Q-d.** Is each side only in its own file? A loudspeaker can put the call side into the microphone file. Some call apps can also send your own voice back into the call file.
- **Q-e.** Did a speaker say words that are not in the script? Then please correct the Armenian text in `scripts.md`, so that it shows the words in the audio.
- **Q-f.** Will you also record S4? S1–S3 give 34 lines, 397 Armenian words, and 6 files [RUN, count of `scripts.md`]. D-019 says "at least 20 recordings". I count each line as one recording, which gives 34. Do you agree with this count?
- **Q-g.** Can I copy the 6 files here and read them? I do not change them. I will check:
  - the WAV header and the length,
  - the samples at full scale (Q-11),
  - the silences between the turns (D-046 needs them).

## 4. D-046 (proposal): match each audio file to its reference text

**Context:** to calculate WER, we need the ASR text and the reference text of the same audio. Each file holds one side of the full dialogue. `scripts.md` asked for label files, but the folder has none.

**Facts** [RUN, from `scripts.md`]:

- On each side, the lines come in runs. A run is one or more lines of the same side, between two lines of the other side.
- S1–S3 have 30 runs, 5 for each file.
- Only the S1 call side has runs with two lines: 02+03, 05+06, 10+11, and 13+14.
- Between two runs, a side is silent for a full turn of the other side.

**Options:**

- **A. Text of the full side, no labels.**
  - How: the program's VAD (`Params()`) cuts the full file into segments. ASR and MT run on each segment. The eval joins all the texts of the file and compares them with the joined reference lines of that side.
  - Weak point: we get only one number for each file. It is hard to find which line has an error.
- **B. You make labels** (an Audacity label track).
  - Weak points: about 20–30 min of your time [UNVERIFIED estimate]; the times can have errors from the manual work.
- **C. Automatic split into runs.**
  - How: a silence of 1.5 s or more splits each file into runs. The eval checks the number of runs against the script. If the numbers are not equal, the eval stops with an error (R10). Then each run goes through the program's segmentation, ASR, and MT. We get numbers for each run and for the full set.
  - Weak points:
    - 1.5 s is a new eval constant (not a program parameter), and you must approve it.
    - On the S1 call side, one number covers two speakers.
    - A long pause inside a run, or a short turn of the other side, gives a wrong count. That file then needs labels (B).

**My preference: C.** It needs no work by you, it gives a number for each run, and a wrong split stops the eval with an error.
- **Fact that can show C is wrong:** the run count fails on 2 or more of the 6 files.

With A and C, each model gets the same VAD segments as in the live program. Thus the numbers include the segment errors (the cut words of Q15, the missing sentences of Q-13). This is the quality that the user sees.

## 5. Components and branches (R3)

| # | Branch | Component | Test level |
|---|---|---|---|
| 1 | `c3-normalize` | `eval/normalize.py`: Armenian normalization (D-047) | unit |
| 2 | `c3-metrics` | `eval/metrics.py`: WER, CER, chrF, totals, latency and RTF statistics | unit |
| 3 | `c3-audio` | `eval/wav.py`: read a 48 kHz float32 WAV, resample to 16 kHz mono | unit |
| 4 | `c3-runs` | `eval/runs.py`: split into runs, with the count check (D-046 C) | unit (fake VAD) |
| 5 | `c3-bakeoff` | `scripts/bakeoff.py`: runs one candidate on all files, writes the results to `test-results/` | model |
| 6+ | one branch for each new candidate adapter | after we agree the order and the time box | model |

- **Place of the code:** `src/tir_asr/eval/`. The unit tests can then import the functions, and CI runs them. The program (`cli`, `app`, `pipeline`) does not import `eval`.
  - Weak point: the installed package then contains eval code that the program does not use.
- **Libraries:** we choose the library for each metric (our own code, or `jiwer` and `sacrebleu`) and for the resample in branches 2 and 3. I will research them first (R8).

## 6. D-047 (proposal): Armenian normalization for WER and CER

**Facts** [RUN, Python `unicodedata`, Unicode 15.1, all 44 lines of `scripts.md`]:

- **Marks in the references:**
  - «։» U+0589 (102 times)
  - «,» (62)
  - «՞» U+055E (17)
  - «՝» U+055D (4)
  - «» (1 pair)
  - «՜» U+055C (1)
  - No digits.
- **Marks inside a word:** «՞» and «՜» are inside the word, on the stressed vowel, for example «Լսո՞ւմ», «ներառվա՞ծ», «Վա՜յ». If we put a space in place of these marks, one word becomes two words.
- **The letter «և» U+0587** occurs 15 times. It is one character.
  - NFKC changes it to «եւ» (U+0565 U+0582).
  - It has no capital form. At the start of a sentence, the reference writes «Եվ», and `"Եվ".lower()` gives «եվ».
  - Thus one word can have three spellings: «և», «եւ», and «եվ».

**Rules, in this sequence:**

1. Apply Unicode NFKC. This also changes the ligatures U+FB13–U+FB17 into two letters.
2. Make all letters lowercase.
3. Delete the marks that go inside a word, with no space: «՞» U+055E, «՜» U+055C, «՛» U+055B, «՟» U+055F, «՚» U+055A.
4. Change «եւ» to «եվ». After rule 1, this also covers «և».
   - Assumption: modern Armenian spelling uses «ւ» only in «ու». Thus «ե» followed by «ւ» is always this word [UNVERIFIED].
5. Put one space in place of each other punctuation mark or symbol (Unicode categories P and S). Examples: «։ , ՝ « » . : ; ? ! - ֊ — …».
6. Change each group of spaces to one space. Remove the spaces at the start and at the end.

**Numbers (an open part):**

- **N1.** No rule for numbers. The eval shows how many words with digits each model writes.
  - Weak point: if a model writes "8-ին" for «ութին», the word counts as an error, but the recognition was correct.
- **N2.** A converter that changes digits to Armenian words, with the case endings.
  - Weak points: more code and more tests. The rules for the words and the endings need a source. Some number words are compound words, for example «տասնհինգ».
- **N3.** You write a second reference with digits.
  - Weak point: WER with two references is more complex.

**My preference: N1.** We measure first (R6).
- **Fact that can show N1 is wrong:** a candidate writes 3 or more words with digits on S1–S3. Then we decide N2 with that data.

When you approve D-047, I will write the T-NORM tests in TESTS.md for your approval (R5).

You can answer in your usual short form, for example "Q-a …, D-046 C, D-047 N1".

## 3. human · 2026-10-26T11:32:03.556147Z

```text
Q-a. no that hash corresponds me commiting the md file changes after the merging, a mistake on my part
Q-b. yes s1.wav is amix
Q-c. mic is my whole part (including silences during their parts), call is Speaker1 and Speaker2. We used google meet for S1 and telegram for S2 and S3
Q-d. yes 
Q-e. no we were faithful to the script
Q-f. I agree with the count I'll perhaps add the S4 at a later time
Q-g. Yes you may
Please note that in S1 there are parts with interruptions that I have put on purpose from my side, the audio can be edited if we dont want interruptions
Let me do the labelling in audacity no problem just tell me how

6. I agree, but, U+055E is important as it shows that the sentence is a question so we must not get rid of it

Yes no rule for numbers
```

## 4. assistant · 2026-10-26T11:38:23.601276Z

Below are my notes on your answers, then three points for you to decide, the Audacity steps, and the draft T-NORM tests.

## 1. Notes on your answers

- **Q-a:** I still need two facts for the handover and PLAN:
  - the merge hash of `c2d-cli`. This command shows it: `git log --oneline --merges -1`.
  - the CI result for `1ef128a`.
- **Q-b:** the eval does not use `s1.wav`. It reads only the `.mic.wav` and `.call.wav` files.
- **Q-g, file check** [RUN, read only, the 6 files]:
  - **Format:** all 6 files are 48 kHz, mono, float32. Each mic file has the same length as its call file: S1 70.66 s, S2 62.81 s, S3 59.05 s.
  - **Clipping:** `s1.mic.wav` clips. It has 500 samples at full scale (|x| ≥ 0.999). The other 5 files do not clip (peak 0.62–0.99). This is data for Q-11.
  - **Echo:** I found none. In the 5 places that I checked, the call file had only noise during your turns, not your voice. This agrees with your answer to Q-d.
  - **S1 interruptions** [RUN, simple level check, not the VAD]: the two sides speak at the same time three times, for 0.35–1.1 s each time.
  - **S1 call side:** the pause between Speaker 1 and Speaker 2 is 0.38–0.99 s. The pause from s1-13 to s1-14 is 0.38 s, which is shorter than `vad_min_silence_ms` (500 ms). Thus the program will probably make one segment with two speakers there [inference]. This is data for Q-04 in C5.

## 2. D-047: the question mark «՞»

Your point is correct. «՞» is the Armenian question mark, and it is the only mark that shows a question in the text. For example, s3-08 ends with «։». Only the «՞» in «փոխե՞նք» shows that it is a question. In S1–S3, 12 of the 34 lines have one «՞» each [RUN].

**Note:** the normalization changes only the two texts that WER and CER compare. The program output and the MT input keep «՞».

**Options:**

- **P1. Keep «՞» in the word** (your proposal). Then «լսո՞ւմ» and «լսում» are different words.
  - A correct word with no «՞» counts as one full word error. WER then measures two things together: the words and the questions.
  - If the ASR puts «՞» on a different word, WER counts two errors.
- **P2. Delete «՞» for WER and CER, and measure the questions in a different number.**
  - For each line, the eval checks whether the reference has «՞» and whether the ASR text has «՞». It also checks «?» in the English reference and in the MT output.
  - The table shows these counts for ASR and for MT: questions found, questions missed, and false questions.
  - Weak point: the ASR decision has two numbers in place of one.
- **P3. Move «՞» to a word of its own.** For example, «լսո՞ւմ» becomes «լսում ՞».
  - A missed «՞» then gives one error, and the word stays correct.
  - Weak points: WER counts a mark as a word. A «՞» on a different word still gives two errors.

**My preference: P2.** WER then measures only the words. The question count measures your point directly, also after MT.
- **Fact that can show P2 is wrong:** we cannot decide D-ASR from WER and the question count together.

## 3. D-046: labels by you (option B)

I accept B. The main risk (R14, one time): the work takes about 20–30 min [UNVERIFIED estimate] of the 20 h budget, which is already over.

**How the eval uses the labels (my proposal):**

1. **Main numbers:**
   - The program's VAD (`Params()`) cuts each full file into segments, the same as in the live program.
   - The eval joins all the texts of a file in time order. It compares them with all the reference lines of that side, in script order.
   - This gives WER, CER, and chrF for each file, for each side, and for the full set. An error in a label does not change these numbers.
2. **Line view:**
   - Each segment goes to the line label that has the largest time overlap with it.
   - This gives the numbers for each line, the question check (P2), and the number of segments in each line (cut words, Q15).
   - Why the main numbers do not use the line view: one segment can hold two lines (s1-13 + s1-14). The line view then counts errors that are not real, but the joined text does not.
3. **Interruptions:**
   - Do not edit S1. Each side is in its own file, so an interruption does not put two voices into one ASR input.
   - Interruptions occur in real calls, so we keep them. The table shows S1 separately.

**Fact that can show point 1 is wrong:** in the joined text, WER matches words of one line with words of a different line, so the result is lower than the true error.

## 4. How to make the labels in Audacity

Make one label file for each script. One file holds the labels of both sides.

**CAUTION:**
- Do not export audio, and do not save over the WAV files.
- Keep the label style at its default (no frequency lines). If the file has frequency lines, the eval stops with an error.

**Steps:**

1. Start Audacity. Select File > Import > Audio.
2. Select `s1.mic.wav` and `s1.call.wav` together. Audacity shows them as two tracks.
3. Find the start and the end of a line. Push Space to play.
4. On the waveform, drag from just before the first word to just after the last word of the line.
5. Push Ctrl+B. Type the line ID, for example `s1-01`. Push Enter.
6. Do steps 3 to 5 for each line of the script. The sequence of the lines is not important.
7. Select File > Export Other > Export Labels. In versions before 3.4, the menu is File > Export > Export Labels [UNVERIFIED].
8. Save the file as `data/eval/raw/s1.labels.txt`.
9. Do steps 1 to 8 for S2 and S3.

**Rules for the labels:**

- Write each ID with no "†", for example `s3-04`, not `s3-04 †`.
- Make one label for each line: 14 for S1, 10 for S2, and 10 for S3.
- Put the pauses inside a line into its label.
- At an interruption, two labels can overlap in time. This is correct.
- Do not make labels for short noises, breaths, or clicks.
- An error of about 0.1 s at a label edge is acceptable.
- If you want to change the labels later, save the Audacity project in `data/eval/raw/`. Git ignores `data/`, but it does not ignore project files that you save in a different folder.

Each line in the exported file has the start time (s), a tab, the end time (s), a tab, and the ID. The eval stops with an error if an ID is unknown or missing, or if two labels have the same ID.

## 5. T-NORM tests (draft for your approval, R5)

- **Function:** `normalize_hy(text) -> str` in `src/tir_asr/eval/normalize.py`.
- **Imports:** the standard library only.
- **Level:** unit (CI runs them). T-IMPORT-01 adds `tir_asr.eval.normalize` to `REQUIRED`.

| ID | Rule | Input | Expected result |
|---|---|---|---|
| T-NORM-01 | NFKC | «ﬓա» (U+FB13 + «ա») | «մնա» |
| T-NORM-02 | lowercase | «Բարև ԵՐԵՎԱՆ OK» | «բարեվ երեվան ok» |
| T-NORM-03 | «և» | «և», «եւ», «Եվ», «ԵՒ»; «Երևան», «Երեւան», «Երեվան»; «ուր» | «եվ» four times; «երեվան» three times; «ուր» (no change to «ու») |
| T-NORM-04 | marks inside a word | «Լսո՞ւմ», «Վա՜յ», «ե՛ս», and one test word each with U+055F and U+055A | «լսում», «վայ», «ես»; the mark goes, with no space |
| T-NORM-05 | punctuation → space | «Բարև, տղերք։ Լսո՞ւմ եք ինձ։»; «այսօր՝ մինչև»; «երկու-մեկ», «երկու֊մեկ»; ««Նռնենի»»; the ASCII marks `. : ; ? ! "` and «… —» | «բարեվ տղերք լսում եք ինձ»; «այսօր մինչեվ»; «երկու մեկ» two times; «նռնենի»; one space for each mark |
| T-NORM-06 | spaces | tabs, new lines, several spaces, spaces at the ends; only «։ ,»; an empty text | one space between words; empty; empty |
| T-NORM-07 | digits (N1) | «ժամը 8-ին» | «ժամը 8 ին» (digits do not change) |
| T-NORM-08 | a word stays one word | each Armenian line of S1–S4 in `docs/eval/scripts.md` | The output has the same number of words as the words with a letter in the input. Only lowercase Armenian letters and single spaces remain. |
| T-NORM-09 | stable result | each line of T-NORM-08 | `normalize_hy(normalize_hy(x)) == normalize_hy(x)` |

If you select P1 or P3, T-NORM-04, T-NORM-05, and T-NORM-08 change.

After your answer, I will write the tests into TESTS.md and into the test file. Then I will give you the command for the red run. Please make the branch now, before I write: `git switch main && git pull && git switch -c c3-normalize`.

You can answer in the short form, for example: "Q-a <hash>, CI green; D-047 P2; D-046 1–3 agree; T-NORM approved."

**Sources:**
- [Audacity manual: Importing and Exporting Labels](https://Manual.Audacityteam.org/man/importing_and_exporting_labels.html)
- [Audacity manual: File Menu: Export Other](https://manual.audacityteam.org/man/file_menu_export_other.html)
- [Audacity manual: Creating and Selecting Labels](https://manual.audacityteam.org/man/creating_and_selecting_labels.html)

## 5. human · 2026-10-26T11:46:19.639309Z

```text
Q-a. ci is green. merge hash is [b38cc6b](https://github.com/arkarapetyan/tir-asr/commit/b38cc6b6dbc4484ea9ea3e74f224f9956c3b45ae)
I am for option P1, let's keep the question mark, but we can get rid of the other symbols
Ok I agree on D46. We are now on the new branch and I begin the labelling
```

## 6. assistant · 2026-10-26T11:48:23.980291Z

I added D-046 to `DECISIONS.md` in the project folder. I read the file back, and its checksum is the same as my copy.

## 1. Commit D-046 now

You can run this between two label files:

```bash
git add DECISIONS.md
git commit -m "docs(decisions): add D-046 eval labels and their use"
git push -u origin c3-normalize
```

I will write D-047 after this commit, so that each decision has its own commit (D-039).

## 2. D-047 with P1: the changed rules and tests

I accept P1. The main risk was in the options, so I do not repeat it.

**Rule changes for P1:**

- **Rule 3:** delete «՜» U+055C, «՛» U+055B, «՟» U+055F, and «՚» U+055A, with no space. Keep «՞» U+055E.
- **Rule 5:** «՞» is not in the set of marks that become a space.
- **Known limit:** if an ASR model writes the ASCII «?» in place of «՞», the «?» becomes a space. «լսում» then does not match «լսո՞ւմ», and WER counts an error. The ASR outputs will show if this occurs.

**Changed tests** (T-NORM-01, -02, -03, -06, -07, and -09 do not change):

| ID | Input | Expected result |
|---|---|---|
| T-NORM-04 | «Լսո՞ւմ»; «Վա՜յ»; «ե՛ս»; one test word each with U+055F and U+055A; «լսում ՞» | «լսո՞ւմ» («՞» stays); «վայ»; «ես»; the mark goes, with no space; «լսում ՞» («՞» alone stays as its own word) |
| T-NORM-05 | «Բարև, տղերք։ Լսո՞ւմ եք ինձ։»; the other inputs as before, with the ASCII «?» | «բարեվ տղերք լսո՞ւմ եք ինձ»; one space for each mark, also for «?» |
| T-NORM-08 | each Armenian line of S1–S4 | The output has the same number of words as the words with a letter in the input. Only lowercase Armenian letters, «՞», and single spaces remain. |

Numbers: no rule (N1).

## 3. Two requests

1. **Approve the tests:** please approve T-NORM-01 to T-NORM-09 with these changes. Then I write them into TESTS.md and into the test file.
2. **Permission to read three files (R4):** I need them to write the tests and the code in the project style.
   - `pyproject.toml`, for the ruff settings.
   - `tests/unit/test_imports.py`, because T-IMPORT-01 needs the new module `tir_asr.eval.normalize`.
   - `tests/unit/test_config.py`, as an example of a short unit test.

I wait for your answer and the D-046 commit. Meanwhile, you can continue with the labels.

## 7. human · 2026-10-26T11:53:41.764721Z

```text
tests approved. you may read those files.
```

## 8. assistant · 2026-10-26T11:58:07.963885Z

I wrote the red state of `c3-normalize` into the project folder. I read the 5 files back, and the checksums are the same as my copies. ruff passes on the changed files (format and check, scratch copy, `--no-cache`).

**Files:**

- `tests/unit/test_normalize.py`: T-NORM-01 to T-NORM-09, 47 test cases in total. Marks that are hard to see are escapes (for example `"\u055e"`).
- `src/tir_asr/eval/__init__.py` and `src/tir_asr/eval/normalize.py`. `normalize.py` is a stub: `normalize_hy` raises `NotImplementedError`. Thus each test runs and fails alone, and ruff finds no import error.
- `tests/unit/test_imports.py`: `REQUIRED` now has `tir_asr.eval` and `tir_asr.eval.normalize`.
- `TESTS.md`: the new §2.5 "Eval tools (C3)" with the 9 tests, status APPROVED.

**Red run** (pytest only). Run it on the branch `c3-normalize`:

```bash
{ uv run pytest tests/unit/test_normalize.py tests/unit/test_imports.py --tb=line -q; git ls-files docs/eval/scripts.md; git status --short --branch; } > test-results/c3-norm-red.txt 2>&1
```

**Expected result:**

- In `test_normalize.py`: 47 failed, each with `NotImplementedError`.
- In `test_imports.py`: all pass.
- `git ls-files` shows `docs/eval/scripts.md`. T-NORM-08 reads this file, so it must be in git for CI.

**D-046 commit:** if you did not commit D-046 yet, please do it before the next step (the command is in my last message). I will write D-047 into `DECISIONS.md` after that commit, so that each decision stays in its own commit. The `git status` line in the result file will show me.

I have the code for the green state ready in my workspace. I will write it after I read your red result. Do not commit anything from this branch yet: the tests are red.

## 9. human · 2026-10-26T12:01:57.442747Z

```text
D46 was committed. I ran the tests but please make sure that the result is printed on the commandline as well.
```

## 10. assistant · 2026-10-26T12:04:10.666036Z

The tests are red as expected. I wrote the D-047 entry and the code for the green state. From now on, each command writes its output to the terminal and to the result file (`tee`).

**Red result** (`c3-norm-red.txt`): 47 failed, all with `NotImplementedError`; 15 passed (T-IMPORT-01). `docs/eval/scripts.md` is in git.

**A finding in your `git status`:** `docs/eval/scripts.md` has changes that are not committed (` M`). I did not change this file. Its time shows a change today at about 14:15, between the S2 and the S3 recordings.
- This file holds the references for the eval, and T-NORM-08 reads it. CI uses the committed version.
- Thus I must know what changed. If the change is correct, it needs its own commit.
- Command 3 below shows the change.

**Files that I wrote** (I read each one back, and the checksums are the same as my copies):
- `DECISIONS.md`: D-047.
- `src/tir_asr/eval/normalize.py`: the code for rules 1 to 6. ruff passes on it.
- `ARCHITECTURE.md` v0.13: a new §8.2 for the eval tools and `normalize_hy`. R13 puts this change in the same commit as the code.

**1. Commit D-047** (only `DECISIONS.md`):

```bash
git add DECISIONS.md
git commit -m "docs(decisions): add D-047 Armenian normalization for WER and CER"
git push
```

**2. Green run** (ruff and all unit tests):

```bash
{ uv run ruff check --no-cache . && uv run ruff format --check --no-cache .; uv run pytest -q --tb=short; } 2>&1 | tee test-results/c3-norm-green.txt
```

Expected result: ruff passes, and 118 unit tests pass (69 before, 47 T-NORM, and 2 new T-IMPORT-01 cases).

**3. The change in `scripts.md`:**

```bash
git diff docs/eval/scripts.md 2>&1 | tee test-results/c3-scripts-diff.txt
```

Do not commit the code yet. I will read the two result files and then give you the commit command for the component.

## 11. human · 2026-10-26T12:09:27.516354Z

```text
change in the scripts has been made by me to that they are true to the recordings. I finished the labelling. I have to point out however that s2 and s3 are cut short in the end, s2 ends with "շնորհակալ" and s3 ends with "քե" instead of "քեզ".
green run passed/
```

## 12. assistant · 2026-10-26T12:12:30.356358Z

The green run passed: ruff passes, and 118 unit tests pass. I set the T-NORM statuses in TESTS.md to PASSES and checked the file after the write.

## 1. Commit and merge `c3-normalize`

```bash
git add src/tir_asr/eval/__init__.py src/tir_asr/eval/normalize.py tests/unit/test_normalize.py tests/unit/test_imports.py ARCHITECTURE.md
git commit -m "feat(eval): add Armenian text normalization for WER and CER"
git add TESTS.md
git commit -m "docs(tests): add T-NORM tests and their results"
git push
```

**CAUTION:** do not add `docs/eval/scripts.md` to these commits. Point 4 below tells why.

When CI is green, merge `c3-normalize` into `main` as before. Then please tell me the merge hash.

## 2. The label files

All 34 labels are there, and the format is correct. In S1, s1-08 and s1-09 overlap for 0.27 s (your interruption). This is correct.

Two findings:

- **The names of the S2 and S3 files changed:** the sizes and the times of the S2 files and the S3 files changed places after my check. Your labels agree with the new names: the call labels of S2 are on the speech in the file that has the name `s2.call.wav` now. Thus I think that you changed the names, because the old names were wrong. Please confirm.
  - If this is correct, the lengths in D-046 are wrong. The correct lengths are S2 59.05 s and S3 62.81 s. I will correct them in the next decision commit.
- **Three files end during speech:** the last label ends at the end of the file (s1-14, s2-10, s3-10).
  - The VAD closes a segment only after 500 ms of silence (D-027). Thus the last segment of these sides does not close, and the eval loses these lines.
  - The eval audio step needs a rule for this, for example 1.0 s of zeros after the end of each file. This was option A of D-032; C2d did not select it, because the test clips had enough silence. I will propose the rule with the eval audio component.

## 3. D-048 (proposal): the cut ends of S2 and S3

**Context:**
- s2-10 ("Me") stops after «Շնորհակալ». «եմ, ցտեսություն» is not in the audio.
- s3-10 (Speaker 1) stops in the last word: the audio has «քե», not «քեզ».

**Options:**

- **A. Make the references the same as the audio** (the rule in `scripts.md`, "Changes").
  - s2-10: Armenian «Անպայման։ Շնորհակալ», English "Definitely. Thank you".
  - s3-10: Armenian «… Վաղն առավոտյան կզանգեմ քե». The English does not change, because a translation of a part of a word has no correct form.
  - A note under each table tells where the recording stops.
  - Weak points: the table no longer shows the full text that a speaker reads in a new recording. A reference with a part of a word is unusual: a model that writes «քեզ» gets one error.
- **B. Remove s2-10 and s3-10 from all numbers.**
  - Weak points: the main numbers then depend on the labels, which goes against D-046 point 2. We also lose 2 lines.
- **C. Record the two ends again.**
  - Weak points: time, the other speaker, and new labels.

**My preference: A.** All models get the same audio, so the effect on the comparison is equal: about 3 of 397 words. Fact that can show A is wrong: a new recording of S2 or S3 (for example in C5) needs the full text.

## 4. `scripts.md`

Your changes are not committed yet. With A, I add the two cut ends to `scripts.md`. Then one commit holds all the changes that make the references agree with the recordings. That is one logical change. With B or C, you commit your changes alone.

## 5. Time (R16)

C3 used about 1.0 h of its 2.5 h. The normalization is done. These parts are not done yet:
- the metrics,
- the eval audio step (resample and the end rule),
- the labels and the references,
- the bake-off runner,
- the candidates.

The full shortlist does not fit in the time box. After the merge, I will propose the order of the candidates with a time box, as I said at the start.

Please answer: the file names (point 2), and A, B, or C for D-048.

## 13. human · 2026-10-26T12:16:39.544779Z

```text
1. yes the wrong names were wrong
2. Agree on A for the cut ends

Let's make sure that we stay under the time box for C3.
```

## 14. assistant · 2026-10-26T12:19:04.856998Z

D-048 is in place. I read both files back, and the checksums are correct.

**Changes on disk:**
- `DECISIONS.md`: D-048, and a correction line in D-046 (the S2 and S3 file names and lengths).
- `docs/eval/scripts.md`: s2-10 and s3-10 now agree with the audio. A note under each row gives the original script text. Your earlier changes in the same file are still there.

## 1. Commits (after the merge of `c3-normalize`)

These commits go on the next branch:

```bash
git switch main && git pull
git switch -c c3-metrics
git add DECISIONS.md
git commit -m "docs(decisions): add D-048 cut ends and correct the D-046 file lengths"
git add docs/eval/scripts.md
git commit -m "docs(eval): match the S1-S3 references to the recordings"
git push -u origin c3-metrics
```

## 2. D-049 (proposal): C3 scope in the time box

**Context:** the C3 time box ends at about 17:45. About 80 min remain. The full shortlists need 3 more eval components and 5 more candidates, with installs, downloads, and adapters.

**Plan for option A** (each time is an estimate [UNVERIFIED]):

1. **`c3-metrics`** (about 20 min): `eval/metrics.py`.
   - WER and CER: our own edit distance, on the normalized text, for the full set (total edits ÷ total reference words).
   - chrF: `sacrebleu` with its default values (character order 6, word order 0, beta 2) [SOURCE: sacrebleu 2.6.0, `metrics/chrf.py`]. The English text gets no normalization.
2. **`c3-data`** (about 20 min): `eval/data.py`.
   - Read a 48 kHz float32 WAV file. Resample it to 16 kHz with `scipy.signal.resample_poly(x, 1, 3)`.
   - Add 1.0 s of zeros at the end of each file (the end rule of D-048).
   - Read the references of each side from `scripts.md`.
3. **`c3-bakeoff`** (about 25 min, with your run): `scripts/bakeoff.py`, model level.
   - For each side file: the program's VAD and `Params()` make the segments. Then ASR, MT, the joined text, and the metrics.
   - It also measures the time of each call, the RTF, and the VRAM.
4. **Candidates:**
   - ASR-1 with RNNT (the current decoder) and ASR-1 with CTC. The model and the weights are the same; only the decoder changes, so nothing new to install.
   - MT: NLLB-600M only. OPUS-MT comes only if time remains, because it needs a download, a conversion, and an adapter.
5. **Not in C3:**
   - **Candidates moved to C6:** ONNX-CTC, BuzzASR (ASR-5), Seamless (ASR-2 and MT-5), and OPUS-MT if there is no time. C6 measures them only if the C3 numbers show that ASR or MT is the weakest link.
   - **Line view (D-046 point 3):** also moved to C6, because the main numbers do not need it. Your labels stay for the line view.
6. **New dev dependencies (D-028):**
   - `sacrebleu`: Apache-2.0. It also installs `portalocker`, `regex`, `tabulate`, `colorama`, and `lxml` [SOURCE: wheel METADATA].
   - `scipy`: BSD.
   - Command: `uv add --dev sacrebleu scipy`. This changes `pyproject.toml` and `uv.lock`, and CI then installs both.

**Options:**
- **A.** The plan above.
- **B.** The full shortlists. This takes about 1.5–2 h more [UNVERIFIED estimate], which is over the time box and the budget (R16).
- **C.** Numbers for the current models only. Weak point: there is no comparison, so D-ASR and D-MT only confirm the skeleton.

**My preference: A.**
- Weak points:
  - We measure no end-to-end model and no different ASR weights. The D-014 and D-015 shortlists stay partly open.
  - D-ASR then chooses between two decoders of one model.
- Fact that can show A is wrong: on our data, the WER of ASR-1 is much higher than its published WER (Common Voice 17.0: 9.90 %, D-014). Then a candidate that we moved can win, and C6 must measure it first.

Please answer A, B, or C. You can also change a part, for example "A without the CTC decoder".

## 15. human · 2026-10-26T12:23:16.674973Z

```text
No let's not cut on research. Will make cuts later.
```

## 16. assistant · 2026-10-26T12:24:05.578756Z

I accept B: we measure the full shortlists in C3. You said earlier to stay under the time box. B does not fit in it. Main risk, one time (R14): C3 will go over its time box by about 1.5–2 h [UNVERIFIED estimate], and the total budget is already over. The cuts later must cover this time. C6 is the first item to cut. If you do not agree, tell me now.

From the D-049 plan, I keep these points: the eval components (`c3-metrics`, `c3-data`, `c3-bakeoff`), `sacrebleu` and `scipy` as dev dependencies, and the end rule of 1.0 s of zeros. With B, the line view (D-046 point 3) also stays in C3. I will log D-049 after you commit D-048.

## 1. Permission to read `docs/research/RESEARCH.md` §1 and §2 (R4)

The adapters for the candidates need the facts from C1: the model names, the runtimes, the install notes, and what BuzzASR (ASR-5) is. These facts are in RESEARCH.md, which is not in the Read list.

## 2. `c3-metrics`: contract and tests (for your approval)

**Module:** `src/tir_asr/eval/metrics.py`.

**Functions:**
- `edit_distance(ref, hyp) -> int`: the minimum number of substitutions, deletions, and insertions. Each one costs 1.
- `wer(refs, hyps) -> float`: normalizes each text with `normalize_hy` (D-047) and splits it into words. The result is the total edits ÷ the total reference words, for the full list. It is not a mean of the rates of the lines.
- `cer(refs, hyps) -> float`: the same calculation on the characters of the normalized text, with the spaces.
- `chrf(refs, hyps) -> float`: `sacrebleu` chrF with its default values, for the full list, on 0–100. The English text gets no normalization.
- `digit_words(texts) -> int`: the number of normalized words that contain a digit (D-047 N1).

**Errors:** `MetricError(TirError)` with the text `metrics: <cause>`. It occurs when the two lists have different lengths, or when the references have no words.

| ID | Requirement | Input | Expected result |
|---|---|---|---|
| T-MET-01 | edit distance | words: `a b c`/`a b c`; `a b c`/`a x c`; `a b c`/`a c`; `a b`/`a b c`; empty/`a b`; `a b`/empty; empty/empty. Characters: `kitten`/`sitting` | 0; 1; 1; 1; 2; 2; 0; 3 |
| T-MET-02 | WER uses D-047 | ref «Բարև, տղերք։», hyp «բարև տղերք» | 0.0 |
| T-MET-03 | WER for the full list | refs «ա բ», «գ դ ե զ»; hyps «ա», «գ դ ե զ» | 1/6 (not 0.25, the mean of the lines) |
| T-MET-04 | WER keeps «՞» (P1) | ref «Լսո՞ւմ եք», hyp «լսում եք» | 0.5 |
| T-MET-05 | CER with the spaces | ref «աբ գդ», hyp «աբ գե» | 1/5 |
| T-MET-06 | chrF | the same English text; texts with no common character; «Hello there» vs «hello there» | 100.0; 0.0; less than 100 (no lowercase) |
| T-MET-07 | digit words | «ժամը 8-ին», «15 000 դրամ» | 3 |
| T-MET-08 | errors (R10) | 2 refs and 1 hyp; refs with only punctuation | `MetricError`: `metrics: 2 references and 1 hypotheses`; `metrics: the references have no words` |

T-IMPORT-01 gets `tir_asr.eval.metrics` in `REQUIRED`.

## 3. Next steps

When you approve the tests:

1. Commit D-048 and `scripts.md` on `c3-metrics` (the commands in my last message).
2. Add `sacrebleu` with its own commit:
   ```bash
   uv add --dev sacrebleu 2>&1 | tee test-results/c3-add-sacrebleu.txt
   git add pyproject.toml uv.lock
   git commit -m "build(deps): add sacrebleu to the dev group for chrF"
   ```
3. I write the D-049 entry, the T-MET tests, and the stub. Then you do the red run.

Please answer: RESEARCH.md (yes or no), and the T-MET tests (approve or change).

## 17. human · 2026-10-26T12:25:05.525458Z

```text
yes and approve
```

## 18. assistant · 2026-10-26T12:26:58.265434Z

The red state of `c3-metrics` is in the project folder. I read the 4 files back, and the checksums are correct. ruff passes on them.

**Files:**
- `tests/unit/test_metrics.py`: T-MET-01 to T-MET-08, 21 test cases.
- `src/tir_asr/eval/metrics.py`: a stub. `MetricError` exists, and each function raises `NotImplementedError`.
- `tests/unit/test_imports.py`: `tir_asr.eval.metrics` is now in `REQUIRED`.
- `TESTS.md` §2.5: the T-MET table.

The green code is ready in my workspace. I read RESEARCH.md §1 and §2 for the candidate adapters.

**Run these in this sequence, on `c3-metrics`:**

1. If you did not commit D-048 and `scripts.md` yet, do it first. The commands are in my message before last.
2. Add `sacrebleu` in its own commit:
   ```bash
   uv add --dev sacrebleu 2>&1 | tee test-results/c3-add-sacrebleu.txt
   git add pyproject.toml uv.lock
   git commit -m "build(deps): add sacrebleu to the dev group for chrF"
   ```
3. Do the red run:
   ```bash
   { uv run pytest tests/unit/test_metrics.py tests/unit/test_imports.py --tb=line -q; git log --oneline -6; git status --short --branch; } 2>&1 | tee test-results/c3-met-red.txt
   ```

**Expected result:**
- In `test_metrics.py`: 21 failed, each with `NotImplementedError`.
- In `test_imports.py`: 16 passed.
- The git lines show me the D-048 commits. After them, I write the D-049 entry.

Do not commit the files of this branch yet: the tests are red.

## 19. human · 2026-10-26T12:28:14.166857Z

```text
proceed
```

## 20. assistant · 2026-10-26T12:29:41.017762Z

The red run is correct: 21 failed, each with `NotImplementedError`, and 16 passed. I wrote the green code (`metrics.py`) and its contract (`ARCHITECTURE.md` v0.14, §8.2), and I checked both files after the write.

## A branch problem

Your `git status` shows that you are still on `c3-normalize`.
- The `sacrebleu` commit (`b75693e`) is on `c3-normalize`, one commit before `origin`.
- D-048 and `scripts.md` are not committed yet.

The fix: make `c3-metrics` from the current commit, then set `c3-normalize` back to its pushed state. Your uncommitted changes stay in the folder.

```bash
git switch -c c3-metrics
git branch -f c3-normalize origin/c3-normalize
git add DECISIONS.md
git commit -m "docs(decisions): add D-048 cut ends and correct the D-046 file lengths"
git add docs/eval/scripts.md
git commit -m "docs(eval): match the S1-S3 references to the recordings"
```

- `c3-metrics` then holds the `c3-normalize` commits, the `sacrebleu` commit, and the two D-048 commits.
- Merge `c3-normalize` into `main` later, at a point with no uncommitted changes, and then `c3-metrics`. Please check that CI is green for `c3-normalize`.

## Note on `sacrebleu`

`uv add` resolved 177 packages, the same number as before. Thus `sacrebleu` was already in the lock, probably as a dependency of a `laptop` package [inference]. It is now also in the dev group, so CI installs it too.

## Green run

```bash
{ uv run ruff check --no-cache . && uv run ruff format --check --no-cache .; uv run pytest -q --tb=short; uv run python -c "import sacrebleu; print('sacrebleu', sacrebleu.__version__)"; git log --oneline -4; } 2>&1 | tee test-results/c3-met-green.txt
```

Expected result: ruff passes, and 140 unit tests pass (118 before, 21 T-MET, 1 new T-IMPORT-01 case).

After the green result, I write D-049. Then I give you three commits: D-049, the component, and the T-MET results.

## 21. human · 2026-10-26T12:31:18.643448Z

```text
proceed
```

## 22. assistant · 2026-10-26T12:33:03.610440Z

The green run passed: ruff passes, 140 unit tests pass, and `sacrebleu` is 2.6.0. I wrote D-049 into `DECISIONS.md` and set the T-MET statuses in `TESTS.md` to PASSES. I checked both files after the write.

## 1. Commits on `c3-metrics`

```bash
git add DECISIONS.md
git commit -m "docs(decisions): add D-049 C3 scope with the full shortlists"
git add src/tir_asr/eval/metrics.py tests/unit/test_metrics.py tests/unit/test_imports.py ARCHITECTURE.md
git commit -m "feat(eval): add WER, CER, and chrF metrics"
git add TESTS.md
git commit -m "docs(tests): add T-MET tests and their results"
git push -u origin c3-metrics
```

## 2. Merge, then start the next branch

Wait until CI is green on `c3-normalize` and on `c3-metrics`. Then:

```bash
git switch main && git pull
git merge --no-ff c3-normalize -m "Merge branch 'c3-normalize'"
git merge --no-ff c3-metrics -m "Merge branch 'c3-metrics'"
git push
git switch -c c3-data
uv add --dev scipy 2>&1 | tee test-results/c3-add-scipy.txt
git add pyproject.toml uv.lock
git commit -m "build(deps): add scipy to the dev group for the resample"
```

## 3. `c3-data`: contract and tests (for your approval)

**Module:** `src/tir_asr/eval/data.py`. Errors use `DataError(TirError)`, with messages that start `data: `.

**Functions:**
- `load_wav_16k(path)`: reads a mono float32 WAV file. At 48 kHz, it resamples with `resample_poly(x, 1, 3)`. At 16 kHz, it changes nothing. Any other file gives an error, with no conversion (R10).
- `with_end_silence(audio)`: adds 1.0 s of zeros at the end (`END_SILENCE_S`, the D-048 end rule).
- `read_references(scripts_md, script)`: reads the lines of one script in order. Each line gives the ID (with no "†"), the speaker, the side ("mic" for "Me", "call" for the other speakers), the Armenian text, and the English text.
- `read_labels(path, lines)`: reads an Audacity label file and checks it against the lines of the script.
- `assign_segments(segments, labels)`: gives each segment the label with the largest time overlap. If two overlaps are equal, it gives the label that starts first. A segment with no overlap gets no label. This is the line view of D-046.

**Facts for the limits** [RUN, scipy 1.18.1 in the workspace, `resample_poly(x, 1, 3)`]:
- A 440 Hz tone keeps its level (0.0 dB) and its frequency.
- A 7 kHz tone loses 0.3 dB.
- An 11 kHz tone loses 67.6 dB. This is correct, because 16 kHz audio cannot hold frequencies above 8 kHz.

| ID | Requirement | Input (each test makes its own file in `tmp_path`) | Expected result |
|---|---|---|---|
| T-DATA-01 | resample 48 → 16 kHz | 1.0 s, 440 Hz, amplitude 0.5, float32, 48 kHz | 16000 samples, float32; spectrum peak at 440 ± 1 Hz; RMS 0.3536 ± 2 % |
| T-DATA-02 | no aliasing | 1.0 s, 11 kHz tone, 48 kHz | output RMS at least 40 dB below the input RMS |
| T-DATA-03 | 16 kHz is not changed | float32, 16 kHz | the same samples |
| T-DATA-04 | errors (R10) | stereo; 44100 Hz; int16 | `data: <file>: 2 channels, expected 1`; `data: <file>: sample rate 44100 Hz, expected 48000 or 16000`; `data: <file>: sample format int16, expected float32` |
| T-DATA-05 | end rule | 100 samples | 16100 samples; the first 100 do not change; the last 16000 are 0.0 |
| T-DATA-06 | references | a small table with 2 scripts, one "†" ID, "Me" and "Speaker 1" | only the lines of the selected script, in order; ID with no "†"; correct side, Armenian text, and English text |
| T-DATA-07 | references in the real file | `docs/eval/scripts.md`, s1, s2, s3 | 14, 10, 10 lines; 5 "mic" lines in each |
| T-DATA-08 | references error | script `s9` | `data: no lines for s9 in <file>` |
| T-DATA-09 | labels | 3 Audacity lines | 3 labels with the start, the end, and the ID |
| T-DATA-10 | label errors | 2 fields on a line; a time that is not a number; end before start; an unknown ID; a missing ID; a repeated ID | one `DataError` for each, with the line number or the ID |
| T-DATA-11 | line view | labels a 0–5 s, b 6–10 s; segments 0.2–4.8, 4.9–6.5, 11–12; a segment with equal overlaps | a; b (0.5 s overlap against 0.1 s); none; the label that starts first |

T-IMPORT-01 gets `tir_asr.eval.data` in `REQUIRED`. `scipy` is not on the `FORBIDDEN` list, and CI installs it with the dev group.

Please answer: approve or change the T-DATA tests.

## 23. human · 2026-10-26T12:37:33.216312Z

```text
approve. in order to save time, you'll write the tests and then immediately implement the files so I only run the green run
```

## 24. assistant · 2026-10-26T12:41:30.145216Z

I wrote `c3-data` with its tests and code in one step, as you asked. I checked all 6 files after the write, and ruff passes on them.

**About D-050:** your request conflicts with R5, step 3: the tests must fail first. I name the risk one time: a test that cannot fail stays hidden. An example is a wrong expected value that the code also has. My mitigation: the tests come from the approved table, not from the code. D-050 records this, for C3 only.

**Files:**
- `src/tir_asr/eval/data.py` and `tests/unit/test_data.py`: T-DATA-01 to T-DATA-11, 20 test cases.
- `tests/unit/test_imports.py`: `tir_asr.eval.data` is now in `REQUIRED`.
- `TESTS.md`: the T-DATA table.
- `ARCHITECTURE.md` v0.15: the `data.py` contract in §8.2.
- `DECISIONS.md`: D-050.

## 1. Green run (on `c3-data`)

```bash
{ uv run ruff check --no-cache . && uv run ruff format --check --no-cache .; uv run pytest -q --tb=short; git log --oneline -3; git status --short --branch; } 2>&1 | tee test-results/c3-data-green.txt
```

Expected result: ruff passes, and 161 unit tests pass (140 before, 20 T-DATA, 1 new T-IMPORT-01 case).

If the run passes, make these two commits:

```bash
git add DECISIONS.md
git commit -m "docs(decisions): add D-050 no red run for the rest of the C3 eval code"
git add src/tir_asr/eval/data.py tests/unit/test_data.py tests/unit/test_imports.py ARCHITECTURE.md
git commit -m "feat(eval): add eval audio, references, labels, and the line view"
```

I will then set the T-DATA statuses and give you the `TESTS.md` commit.

## 2. Now, at the same time: the files of the candidate models

The downloads for the shortlist take time, so we can start them early. First, this command lists the files and sizes of the 4 new model repositories, with no download. It also shows the free disk space.

```bash
uv run python - <<'EOF' 2>&1 | tee test-results/c3-repo-files.txt
from huggingface_hub import HfApi
api = HfApi()
for repo in ["Helsinki-NLP/opus-mt-hy-en", "BuzzASR/armenian",
             "facebook/seamless-m4t-v2-large", "OpenVoiceOS/stt_hy_fastconformer_hybrid_large_pc_onnx"]:
    print("==", repo, flush=True)
    for f in api.list_repo_tree(repo, recursive=True, expand=True):
        print(f"  {f.path}\t{getattr(f, 'size', '-')}", flush=True)
EOF
df -h ~/.cache/huggingface | tee -a test-results/c3-repo-files.txt
```

With the list, I give you `hf download` commands that get only the files that each runtime needs. `hf` is the command of `huggingface-hub` 2.3.0 [SOURCE: wheel `entry_points.txt`]. The list is necessary because some repositories hold the same weights in several formats.

## 3. Permission to read the program files (R4)

`c3-bakeoff` must use the same VAD, segments, and adapters as the program. Then the eval numbers show the program as it is. For this, I need to read:

- `src/tir_asr/types.py`, `config.py`, and `errors.py`
- `src/tir_asr/segment/endpoint.py` and `segment/silero.py`
- `src/tir_asr/asr/nemo_rnnt.py` and `mt/ct2_nllb.py`
- `src/tir_asr/app.py` (`load_models`) and `tests/support/wav_source.py`

Please answer: yes or no for point 3.

## 25. human · 2026-10-26T12:42:59.548409Z

```text
you may read the files
```

## 26. assistant · 2026-10-26T12:45:23.140093Z

The `c3-data` green run passed: 161 unit tests pass, and ruff passes. I set the T-DATA statuses in `TESTS.md` to PASSES. I read the program files.

## 1. Commits and merge for `c3-data`

```bash
git add DECISIONS.md
git commit -m "docs(decisions): add D-050 no red run for the rest of the C3 eval code"
git add src/tir_asr/eval/data.py tests/unit/test_data.py tests/unit/test_imports.py ARCHITECTURE.md
git commit -m "feat(eval): add eval audio, references, labels, and the line view"
git add TESTS.md
git commit -m "docs(tests): add T-DATA tests and their results"
git push -u origin c3-data
```

When CI is green: merge `c3-data` into `main`, then `git switch -c c3-run`.

## 2. Downloads: start them now, in a second terminal

The file lists come from your `c3-repo-files.txt`. The commands get only the files that the Transformers, CTranslate2, or ONNX runtime needs, about 13 GB in total. They leave out the duplicate formats: `tf_model.h5` and the two fairseq2 `.pt` files of Seamless, which are 20 GB together. You have 197 GB free.

```bash
{ uv run hf download Helsinki-NLP/opus-mt-hy-en README.md config.json generation_config.json pytorch_model.bin source.spm target.spm tokenizer_config.json vocab.json
  uv run hf download OpenVoiceOS/stt_hy_fastconformer_hybrid_large_pc_onnx README.md config.json model.onnx vocab.txt
  uv run hf download BuzzASR/armenian README.md added_tokens.json config.json generation_config.json merges.txt model.safetensors normalizer.json preprocessor_config.json special_tokens_map.json tokenizer_config.json vocab.json
  uv run hf download facebook/seamless-m4t-v2-large README.md added_tokens.json config.json generation_config.json model-00001-of-00002.safetensors model-00002-of-00002.safetensors model.safetensors.index.json preprocessor_config.json sentencepiece.bpe.model special_tokens_map.json tokenizer.model tokenizer_config.json
} 2>&1 | tee test-results/c3-downloads.txt
```

Then copy the model cards and the ONNX `config.json` into the project folder. I can read only that folder, and the adapters need the usage notes from the cards (R9).

```bash
mkdir -p test-results/cards
uv run python - <<'EOF' 2>&1 | tee -a test-results/c3-downloads.txt
import shutil
from huggingface_hub import hf_hub_download
for repo, name in [("Helsinki-NLP/opus-mt-hy-en", "README.md"), ("BuzzASR/armenian", "README.md"),
                   ("facebook/seamless-m4t-v2-large", "README.md"),
                   ("OpenVoiceOS/stt_hy_fastconformer_hybrid_large_pc_onnx", "README.md"),
                   ("OpenVoiceOS/stt_hy_fastconformer_hybrid_large_pc_onnx", "config.json")]:
    path = hf_hub_download(repo, name, local_files_only=True)
    shutil.copy(path, f"test-results/cards/{repo.replace('/', '__')}__{name}")
    print("copied", repo, name, flush=True)
EOF
```

## 3. D-051 (proposal): the structure of the bake-off

**Places of the code:**
- **`src/tir_asr/eval/run.py`** (core, no `laptop` import, unit tests with fakes):
  - `segment_file(audio, vad, params)`: adds the 1.0 s end rule, then sends the 512-sample frames into the program's `Endpointer`. Frame k has the arrival time (k + 1) × 0.032 s, so all times are audio times.
  - `transcribe_all` and `translate_all`: one call for each segment, with the time of each call. An empty ASR text gets no MT call, the same as in the program (D-031).
  - `score_side`: the main numbers (WER, CER, chrF on the joined texts, D-046 point 2), the line view (D-046 point 3), and the time numbers: the RTF and the mean and maximum time of each step.
- **`scripts/bakeoff.py`** (model level): `--asr <name> --mt <name> [--mt-input asr|reference]`.
  - It runs S1–S3, both sides, and writes `test-results/bakeoff/<asr>+<mt>.json`. It also prints a short summary.
  - `--mt-input reference` translates the reference Armenian lines. This shows the MT quality with no ASR errors.
  - The VRAM comes from `torch.cuda.mem_get_info()`, before and after the load, as in `app.py`.
- **Candidate adapters:** one module and one branch for each, in `src/tir_asr/eval/`, in `ADAPTERS` of T-IMPORT-01.
  - Branch `c3-run` holds the first candidates: `nemo-rnnt` and `nllb-ct2`. They use the program adapters with no change, which gives the baseline.
  - Next branches: `nemo-ctc` (an eval class that loads the same `.nemo` file and selects the CTC decoder), `opus-ct2`, `buzz-whisper`, `seamless` (ASR, T2TT, and end-to-end S2TT), and `onnx-ctc`. The ONNX candidate needs `onnxruntime-gpu`, a new `laptop` package, so it gets its own decision.
- **Model tests:** I propose no separate model test for each eval candidate. The bake-off run is their model-level check, and it stops loudly at an error (R10).
  - Weak point: an adapter problem shows only in the bake-off run.

**My preference:** the structure above. The other option is a single script with no core module and no unit tests. That is faster, but it goes against R5 and gives no test for the joined-text rule.

## 4. T-RUN tests (unit, with fakes; for your approval)

| ID | Requirement | Input | Expected result |
|---|---|---|---|
| T-RUN-01 | Segments in audio time, with the end rule | 3.0 s of audio. A fake VAD gives 1.0 for a frame with a peak over 0.1, else 0.0. Loud frames 10–39, and loud frames from 80 to the last frame. | 2 segments; the first has start 0.320 s and speech end 1.280 s; the second closes, because of the 1.0 s of zeros |
| T-RUN-02 | ASR and MT calls | 3 fake segments; the ASR gives «ա», «» (empty), «բ»; the MT gives "A"; a fake clock adds 0.1 s for each call | ASR texts in order; English "A", "", "A"; 2 MT calls only; each time 0.1 s |
| T-RUN-03 | Main numbers on the joined text (D-046 point 2) | refs «ա բ» (0–2 s) and «գ դ» (3–5 s); segment texts «ա բ գ» (0–3.5 s) and «դ» (4–5 s) | WER 0.0 on the joined text; the line view gives line 1 WER 0.5 and line 2 WER 0.5 |
| T-RUN-04 | Segment outside each label | one segment with no label overlap and the text «ե» | line view: 1 segment outside the labels; the main WER counts «ե» as an insertion |
| T-RUN-05 | Time numbers | segment audio 2.0 s and 3.0 s; ASR times 0.1 s and 0.3 s; MT times 0.2 s and 0.4 s | ASR RTF 0.08; ASR mean 0.2 s, maximum 0.3 s; MT mean 0.3 s, maximum 0.4 s |

Please answer: approve or change D-051 and the T-RUN tests. Then I write `c3-run` in one step (D-050).

## 27. human · 2026-10-26T12:48:36.062429Z

```text
agree D51 and tests,downloads are undergoing
```

## 28. assistant · 2026-10-26T12:51:50.385441Z

I wrote the 3 new files of `c3-run`, tests and code in one step (D-050). I checked them after the write, and ruff passes on them.

**New files:**
- `src/tir_asr/eval/run.py`: the bake-off core.
- `tests/unit/test_run.py`: T-RUN-01 to T-RUN-05.
- `scripts/bakeoff.py`: the runner. It knows `nemo-rnnt` and `nllb-ct2` now. The VAD loads after the models, as in the program (D-043).

**Changes that I hold back:** D-051 (`DECISIONS.md`), §8.2 (`ARCHITECTURE.md`), the T-RUN table (`TESTS.md`), and `test_imports.py`.
- The file times show that the `c3-data` commits did not happen yet.
- If I write these 4 files now, your `git add` commands for `c3-data` would take my `c3-run` changes too.

## 1. First: finish `c3-data`

Run the commits of my last message. When CI is green, merge `c3-data` into `main`, then:

```bash
git switch -c c3-run
```

Then tell me, and I write the 4 documents.

## 2. Now, at the same time: the green run and the baseline

These runs do not depend on the branch, because the new files are not in git yet. The downloads in the other terminal can continue.

```bash
{ uv run ruff check --no-cache . && uv run ruff format --check --no-cache .; uv run pytest -q --tb=short; } 2>&1 | tee test-results/c3-run-green.txt
env -u LD_LIBRARY_PATH HF_HUB_OFFLINE=1 uv run python scripts/bakeoff.py --asr nemo-rnnt --mt nllb-ct2 2>&1 | tee test-results/c3-bake-rnnt-nllb.txt
env -u LD_LIBRARY_PATH HF_HUB_OFFLINE=1 uv run python scripts/bakeoff.py --asr none --mt nllb-ct2 --mt-input reference 2>&1 | tee test-results/c3-bake-ref-nllb.txt
```

**Expected results:**
- **Unit tests:** 167 pass (161 before, 5 T-RUN, and 1 T-IMPORT-01 case for `tir_asr.eval.run`).
- **Run 2:** one line for each file (WER, CER, chrF, segments, outside, digit words, ASR RTF), the totals, and `test-results/bakeoff/nemo-rnnt+nllb-ct2.json`.
- **Run 3:** the chrF of NLLB on the reference Armenian text, with no ASR errors.

These two runs give the baseline: the current program on S1–S3.

## 29. human · 2026-10-26T12:55:05.635617Z

```text
done
```

## 30. assistant · 2026-10-26T12:56:58.597600Z

The green run passed (167 unit tests), and the baseline ran. Below are the numbers, then two questions.

## 1. Baseline: the current program on S1–S3 [RUN]

**Conditions:**
- Hardware and versions: RTX 5070 Laptop, torch 2.14.1, NeMo 3.0.0, CTranslate2 4.8.3.
- Settings: `Params()` (the program values), with the segments from the program's VAD.
- Data: S1–S3, 6 files. WER and CER use the D-047 normalization (P1). chrF uses the joined texts (D-046).

| Side | WER | CER | chrF, ASR → MT | chrF, reference → MT |
|---|---|---|---|---|
| mic (you) | 6.6 % | 1.3 % | 52.4 | 56.5 |
| call (Speaker 1 and 2) | 13.5 % | 4.8 % | 51.3 | 56.1 |
| all | **10.6 %** | **3.3 %** | **51.7** | **56.3** |

**Time and memory:**

| Item | Value |
|---|---|
| ASR RTF | 0.004 |
| ASR, slowest segment | 0.026 s |
| MT, slowest segment | 0.112 s |
| ASR load | 3.99 s, 952 MiB VRAM |
| MT load | 1.16 s, 1664 MiB VRAM |

## 2. What the numbers show

- **ASR:** WER 10.6 % is near the published value of the model (Common Voice: 9.90 %). Thus the "fact that can show A is wrong" in D-049 did not occur.
  - The S1 call side (Google Meet) has WER 21.4 %. The S2 and S3 call sides (Telegram) have 2.0 % and 9.0 %.
- **Q-13 is confirmed. NLLB leaves out sentences** when one segment has two or more:
  - "But the trunk is small" (s1-05) and "I will call Armen myself" (s3-07) are missing.
  - With the clean reference input, three more lines lose a sentence (s2-06, s2-07, s3-04).
  - Even with perfect Armenian, the chrF is only 56.3. Thus MT is probably the weakest link.
- **«՞» (P1):** the references have 12 words with «՞». The ASR wrote «՞» on 6 of these words, so the 6 misses add about 1.5 % to the WER.
- **Digits (N1):** the ASR wrote 0 words with digits. NLLB writes digits in English ("8:00"). It also changed «տասնհինգ հազար դրամ» to "$15,000", which is the wrong currency.

## 3. Two questions

**a. The branch state.** The file times show that `c3-data` is not merged yet. While `c3-data` is not committed, I do not write `DECISIONS.md`, `ARCHITECTURE.md`, `TESTS.md`, or `test_imports.py`. Please tell me the state, or run:

```bash
{ git status --short --branch; git log --oneline -5; } 2>&1 | tee test-results/c3-git-state.txt
```

**b. One branch for all candidates.** D-051 says one branch for each candidate, but each branch costs a CI run and a merge. I propose one branch `c3-candidates`, with one commit for each candidate. Each commit holds the adapter, its runner line, and its §8.2 line. Do you agree?

## 4. Now, at the same time: convert OPUS-MT to CTranslate2

The download of OPUS-MT is complete. The command has the same form as the NLLB conversion of C2:

```bash
HF_HUB_OFFLINE=1 uv run --no-sync ct2-transformers-converter --model Helsinki-NLP/opus-mt-hy-en --output_dir models/opus-mt-hy-en-ct2-float16 --quantization float16 2>&1 | tee test-results/c3-opus-convert.txt
```

**Next:** after your answers, I write the `nemo-ctc` and `opus-ct2` adapters. BuzzASR, Seamless, and ONNX follow after the model cards are in `test-results/cards/`.

## 31. human · 2026-10-26T13:00:07.172876Z

````text
3. agree for one branch for all candidates and the results of the git state ```## c3-run
?? scripts/bakeoff.py
?? src/tir_asr/eval/run.py
?? tests/unit/test_run.py
9a8a9b7 docs(tests): add T-DATA tests and their results
40c1b00 feat(eval): add eval audio, references, labels, and the line view
40b6651 docs(decisions): add D-050 no red run for the rest of the C3 eval code
cee6a9c build(deps): add scipy to the dev group for the resample
0c48517 Merge branch 'c3-metrics'

write the adapters
````

## 32. assistant · 2026-10-26T13:03:04.446312Z

I wrote the `c3-run` documents and the first two candidate adapters. I checked all files after the write.

**`c3-run` documents:**
- `DECISIONS.md`: D-051, with your change to point 4 (one branch for all candidates).
- `ARCHITECTURE.md` v0.16: the contracts of `run.py` and `scripts/bakeoff.py` in §8.2.
- `TESTS.md`: the T-RUN table with PASSES (167 unit tests), and a note on the two baseline runs.
- `tests/unit/test_imports.py`: `tir_asr.eval.run` in `REQUIRED`.

**First candidate adapters** (new files for `c3-candidates`):
- `src/tir_asr/eval/nemo_ctc.py`: the same `.nemo` file as the program, with `change_decoding_strategy(decoder_type="ctc")`.
- `src/tir_asr/eval/opus_ct2.py`: OPUS-MT on CTranslate2, with the same `compute_type` and `beam_size` as NLLB. Its CTranslate2 import comes after the cuBLAS preload (D-030).
- Your conversion log shows only a warning about `sacremoses`. That package is only a recommendation of the Marian tokenizer, so the conversion is complete.

## 1. Commits on `c3-run`, then the new branch

**CAUTION:** do not add `nemo_ctc.py` or `opus_ct2.py` to these commits, because they belong to `c3-candidates`. Also, do not run the unit tests until I put these two modules in `ADAPTERS`. Until then, T-IMPORT-01 fails, because they import NeMo and CTranslate2.

```bash
git add DECISIONS.md
git commit -m "docs(decisions): add D-051 structure of the bake-off"
git add src/tir_asr/eval/run.py scripts/bakeoff.py tests/unit/test_run.py tests/unit/test_imports.py ARCHITECTURE.md
git commit -m "feat(eval): add the bake-off core and runner"
git add TESTS.md
git commit -m "docs(tests): add T-RUN tests and their results"
git push -u origin c3-run
git switch -c c3-candidates
```

When CI is green, you can merge `c3-data` and `c3-run` into `main` at any time.

## 2. After the switch

Tell me when you are on `c3-candidates`. Then I add the two candidates to the runner, `ADAPTERS`, and §8.2, and I give you the bake-off commands.

## 3. Model cards

The Seamless download is still in progress. When it is complete, please run the card block from my earlier message (`mkdir -p test-results/cards` …). The BuzzASR, Seamless, and ONNX adapters need the usage notes from those cards.

## 33. human · 2026-10-26T13:06:50.060056Z

```text
all CI-s green provide the merge commands, and I am now on the new branch
```

## 34. assistant · 2026-10-26T13:07:43.106589Z

All CI runs are green. These are the merge commands. Your untracked candidate files (`nemo_ctc.py`, `opus_ct2.py`) do not stop the branch changes.

```bash
git switch main && git pull
git merge --no-ff c3-data -m "Merge branch 'c3-data'"
git merge --no-ff c3-run -m "Merge branch 'c3-run'"
git push
git switch c3-candidates
```

**Why I wait:** the branch changes rewrite `DECISIONS.md`, `ARCHITECTURE.md`, `TESTS.md`, and `test_imports.py`. If I write these files before you switch, `git switch main` stops with "local changes would be overwritten". Tell me when you are back on `c3-candidates`.

**Ready in my workspace for `c3-candidates`:**
- `scripts/bakeoff.py` knows `nemo-ctc` and `opus-ct2`. ruff passes.
- `ADAPTERS` of T-IMPORT-01 gets `tir_asr.eval.nemo_ctc` and `tir_asr.eval.opus_ct2`.
- §8.2 of `ARCHITECTURE.md` gets one line for each candidate.

**One question about the commits:** the two candidates share three files (`bakeoff.py`, `test_imports.py`, `ARCHITECTURE.md`). For one commit for each candidate (D-051 point 4), I must write them one after the other, with a commit between them. That costs one more round trip. My proposal: one commit for these two candidates. BuzzASR, Seamless, and ONNX each get their own commit later, because their model cards arrive later anyway. Do you agree?

**Model cards:** `test-results/cards/` does not exist yet. Please run the card block when the Seamless download is complete.

## 35. human · 2026-10-26T13:10:12.650966Z

```text
agree. merges complete. cards are there now. proceed
```

## 36. assistant · 2026-10-26T13:13:12.906542Z

I did not write three of the files that are on your disk now. Please check this before the next commit.

## 1. A finding: three files changed, but not by me

When I staged the files after your merges, `scripts/bakeoff.py`, `tests/unit/test_imports.py`, and `ARCHITECTURE.md` (v0.17) already had the `nemo-ctc` and `opus-ct2` changes. Their file times are 17:09:48–49.
- I did not write these files in this chat. I had the same changes only in my workspace.
- The content is the same as my plan. The `bakeoff.py` change is the same as my workspace version, line for line.

**Question:** did you, or a different Claude session, write to the project folder? R15 requires that each step is visible in a chat. Also, if two sessions write to one folder, they can overwrite each other's changes. Please read `git diff` of these three files before the commit (R12).

## 2. Runs for `nemo-ctc` and `opus-ct2`

```bash
{ uv run ruff check --no-cache . && uv run ruff format --check --no-cache .; uv run pytest -q --tb=short; } 2>&1 | tee test-results/c3-cand1-green.txt
env -u LD_LIBRARY_PATH HF_HUB_OFFLINE=1 uv run python scripts/bakeoff.py --asr nemo-ctc --mt nllb-ct2 2>&1 | tee test-results/c3-bake-ctc-nllb.txt
env -u LD_LIBRARY_PATH HF_HUB_OFFLINE=1 uv run python scripts/bakeoff.py --asr nemo-rnnt --mt opus-ct2 2>&1 | tee test-results/c3-bake-rnnt-opus.txt
env -u LD_LIBRARY_PATH HF_HUB_OFFLINE=1 uv run python scripts/bakeoff.py --asr none --mt opus-ct2 --mt-input reference 2>&1 | tee test-results/c3-bake-ref-opus.txt
```

Expected result: 167 unit tests pass. The two adapters are in `ADAPTERS`, so T-IMPORT-01 does not test them as core modules. The three runs each write one JSON file.

If the runs pass, commit:

```bash
git add src/tir_asr/eval/nemo_ctc.py src/tir_asr/eval/opus_ct2.py scripts/bakeoff.py tests/unit/test_imports.py ARCHITECTURE.md
git commit -m "feat(eval): add the nemo-ctc and opus-ct2 candidates"
git push -u origin c3-candidates
```

## 3. Next: BuzzASR and Seamless

The two adapters are ready in my workspace, and ruff passes. I made them from the model cards and from the transformers 5.20.2 source [SOURCE: the wheel].
- **BuzzASR:** `WhisperForConditionalGeneration` in float16. The `generate` values come from the card (`num_beams=1`, `no_repeat_ngram_size=3`, `repetition_penalty=1.2`).
- **Seamless:** `SeamlessM4Tv2ForSpeechToText` for ASR (`tgt_lang="hye"`) and for the end-to-end mode (`"eng"`), and `SeamlessM4Tv2ForTextToText` for MT.

I write them after your commit. While they are on the disk but not in `ADAPTERS`, T-IMPORT-01 fails.

## 4. D-052 (proposal): ONNX-CTC after the `nemo-ctc` result

**Facts:**
- The card says that `model.onnx` holds only the CTC head of the same model, and that it gave "identical transcriptions" to the NeMo checkpoint [SOURCE: card]. Thus the `nemo-ctc` run also measures the quality of ONNX-CTC.
- ONNX-CTC needs two new `laptop` packages: `onnx-asr` 0.12.0 (MIT) and `onnxruntime-gpu` [SOURCE: wheel METADATA].

**Options:**
- **A.** Install the two packages and run ONNX-CTC now.
- **B.** Decide after the `nemo-ctc` result.
  - If the CTC WER is clearly higher than the RNNT WER, ONNX-CTC cannot win on quality. Its only gain is speed, and the slowest ASR call is already 0.026 s.
  - If the CTC WER is equal or lower, we install the packages and measure the speed.

**My preference: B.** This is not a cut of the research: the `nemo-ctc` run gives the ONNX quality without a new install.
- Fact that can show B is wrong: we must remove NeMo from the laptop install (K4). Then ONNX matters for the install, not for the quality.

Please answer: the source of the three files (point 1), and A or B for D-052.

## 37. human · 2026-10-26T13:16:33.075303Z

```text
1. wow, nobody made any changes to any files
2. agree on option B

tests done and committed
```

## 38. assistant · 2026-10-26T13:19:29.678110Z

The candidate results so far are below. First, a correction.

## 1. Correction: I wrote the three files

My statement in the last message was wrong. My workspace has an output folder `c3-w16` from 17:09:46 with the same three files, and the write to your disk came from there at 17:09:48. Thus this session wrote the files, not you and not a different session. That step is not in the part of this chat that I can see, so I did not know about it.

For R15, this means the chat export will probably not show this one step. I will put a note in the handover. I am sorry for the false alarm.

## 2. Results so far [RUN, S1–S3, same conditions as the baseline]

| Run | WER | CER | chrF, ASR → MT | chrF, reference → MT | Slowest MT call |
|---|---|---|---|---|---|
| `nemo-rnnt` + `nllb-ct2` (baseline) | **10.6 %** | **3.3 %** | 51.7 | **56.3** | 0.112 s |
| `nemo-ctc` + `nllb-ct2` | 12.7 % | 3.6 % | 53.6 | — | 0.109 s |
| `nemo-rnnt` + `opus-ct2` | 10.6 % | 3.3 % | 42.7 | 43.6 | 0.027 s |

- **CTC:** its WER is 2.1 points higher than RNNT. Its chrF is higher only because of the punctuation. Where RNNT writes «։» between two sentences, NLLB leaves out the second sentence (Q-13). CTC wrote a comma in two of these places (s1-05, s3-07). Thus the chrF gain comes from the MT fault, not from better ASR.
- **D-052 result:** the CTC WER is clearly higher, so we do not install ONNX and we do not run it. D-052 records this.
- **OPUS-MT:** chrF 9–13 points lower than NLLB. It is 4 times faster, but the MT speed is not a problem.

## 3. Written: BuzzASR and Seamless

I checked all files after the write, and ruff passes on them.
- `buzz_whisper.py` and `seamless.py`.
- `bakeoff.py` knows the new names:
  - `buzz-whisper` and `seamless` (ASR).
  - `seamless` (MT).
  - `seamless-s2tt` (end to end). It uses the same model as `--asr seamless`, with no second load.
- The two adapters are in `ADAPTERS`. `ARCHITECTURE.md` v0.18 has their §8.2 lines. `DECISIONS.md` has D-052.
- **One commit for the two candidates:** they share the same three files again, so I propose one commit, for the same reason as before.

## 4. Runs

```bash
{ uv run ruff check --no-cache . && uv run ruff format --check --no-cache .; uv run pytest -q --tb=short; } 2>&1 | tee test-results/c3-cand2-green.txt
B="env -u LD_LIBRARY_PATH HF_HUB_OFFLINE=1 uv run python scripts/bakeoff.py"
$B --asr buzz-whisper --mt nllb-ct2 2>&1 | tee test-results/c3-bake-buzz-nllb.txt
$B --asr seamless --mt nllb-ct2 2>&1 | tee test-results/c3-bake-seam-nllb.txt
$B --asr seamless --mt seamless-s2tt 2>&1 | tee test-results/c3-bake-seam-e2e.txt
$B --asr nemo-rnnt --mt seamless 2>&1 | tee test-results/c3-bake-rnnt-seam.txt
$B --asr none --mt seamless --mt-input reference 2>&1 | tee test-results/c3-bake-ref-seam.txt
```

**Expected result:** 167 unit tests pass, and each run writes its JSON file. These adapters ran for the first time in this command. If one run stops with an error, send me the file, and I correct the adapter.

**Commits** (only if all runs pass):

```bash
git add DECISIONS.md
git commit -m "docs(decisions): add D-052 ONNX-CTC after the nemo-ctc result"
git add src/tir_asr/eval/buzz_whisper.py src/tir_asr/eval/seamless.py scripts/bakeoff.py tests/unit/test_imports.py ARCHITECTURE.md
git commit -m "feat(eval): add the buzz-whisper and seamless candidates"
git push
```

**Time (R16):** the C3 time box ends at about 17:45. After these runs, the work that remains is the results table, D-ASR, D-MT, the handover, and the documents. I expect to finish about 15–20 min after the time box [UNVERIFIED estimate].

## 39. human · 2026-10-26T13:23:17.233004Z

```text
done, check the results and proceed immedieately, by the way saw how my laptop stressed during seamless run. It might show bettter result but we have to compare performance-wise
```

## 40. assistant · 2026-10-26T13:25:17.484052Z

All five runs passed. Seamless gives the best quality, but it costs more GPU time. Below are the numbers, then one short measurement for your "laptop stress" point.

## 1. Results [RUN, Aren's laptop, S1–S3, the same segments for all runs]

**ASR candidates** (MT = NLLB):

| ASR | WER | CER | ASR time per segment, mean / max | VRAM |
|---|---|---|---|---|
| `nemo-rnnt` (now) | 10.6 % | 3.3 % | 0.021 / 0.026 s | 952 MiB |
| `nemo-ctc` | 12.7 % | 3.6 % | 0.017 / 0.022 s | 952 MiB |
| `buzz-whisper` | 19.0 % | 7.5 % | 0.256 / 0.352 s | 3190 MiB |
| `seamless` | **6.8 %** | **2.3 %** | 0.321 / 0.417 s | 2884 MiB |

- BuzzASR is the worst, and it is the only ASR that writes digits (9 words).

**MT candidates** (chrF: higher is better):

| MT | chrF, RNNT text in | chrF, reference text in | MT time per segment, mean / max | VRAM |
|---|---|---|---|---|
| `nllb-ct2` (now) | 51.7 | 56.3 | 0.074 / 0.112 s | 1664 MiB |
| `opus-ct2` | 42.7 | 43.6 | 0.016 / 0.027 s | 192 MiB |
| `seamless` (text to text) | 55.5 | **61.1** | 0.245 / 0.324 s | 2632 MiB |

**Full pipelines** (the time is ASR + MT for each line; the VAD wait of about 0.5 s comes on top):

| Pipeline | WER | chrF | Line time, mean / max | GPU s per audio s | VRAM |
|---|---|---|---|---|---|
| P1: RNNT + NLLB (now) | 10.6 % | 51.7 | 0.10 / 0.14 s | 0.020 | 2.6 GB |
| P2: RNNT + Seamless text MT | 10.6 % | 55.5 | 0.27 / 0.35 s | 0.056 | 3.6 GB |
| P4: Seamless end to end (HY and EN from the audio, one model) | **6.8 %** | **59.0** | 0.63 / 0.83 s | **0.133** | 2.9 GB |
| P5: RNNT for HY + Seamless audio → EN | 10.6 % | 59.0 | 0.33 / 0.44 s | 0.069 | 3.8 GB |

- P5 is composed from two runs [calc]. The segments of the two runs are identical, which I checked.
- **Seamless does not leave out sentences.** It translated all four lines where NLLB lost a sentence (Q-13).
- **All pipelines meet K1 (5 s):** the slowest line, with the VAD wait, is about 1.3 s (P4).
- **Your point about performance is correct:** P4 uses the GPU about 6.6 times as long as P1 for the same audio. The bake-off runs the segments one after the other with no pause, so the GPU works all the time. That is the stress you saw. In live use, P4 keeps the GPU busy for about 13 % of the time [calc]. But we did not measure the power or the temperature.

## 2. Next step: measure the power (R6)

This command runs P1, P2, and P4 again, with a 30 s pause before each for the GPU to cool. `nvidia-smi` logs the power, the temperature, the GPU load, and the clock every 200 ms. It takes about 3 min. The runs write the same JSON files again.

```bash
B="env -u LD_LIBRARY_PATH HF_HUB_OFFLINE=1 uv run python scripts/bakeoff.py"
for P in "p1 --asr nemo-rnnt --mt nllb-ct2" "p2 --asr nemo-rnnt --mt seamless" "p4 --asr seamless --mt seamless-s2tt"; do
  set -- $P; name=$1; shift
  sleep 30
  nvidia-smi --query-gpu=timestamp,power.draw,temperature.gpu,utilization.gpu,clocks.sm --format=csv,noheader,nounits -lms 200 > test-results/c3-power-$name.csv &
  SMI=$!
  $B "$@" > test-results/c3-power-$name.txt 2>&1
  kill $SMI
  echo "== $name"; tail -4 test-results/c3-power-$name.txt
done
```

From the logs, I calculate the energy for each audio second, the peak power, and the peak temperature.

## 3. D-053 (proposal, the decision comes after the power numbers): ASR and MT

| Option | Quality | Cost |
|---|---|---|
| **P1** (keep) | lowest chrF; sentences missing (Q-13; C6 must fix it) | no code change |
| **P2** | chrF +3.8 | only a new MT adapter (the same `Translator` contract) |
| **P4** | best WER and best chrF | a new adapter, and the MT step takes the audio, not the text (a change to the pipeline and to the contracts, about one code chat); the HY line and the EN line are two separate outputs, so they can differ |
| **P5** | the chrF of P4 | the WER of P1; the same pipeline change as P4 |

**My preference: P4,** if the power numbers are acceptable. If they are not, P2.
- Weak points of P4: the most GPU work, a change to the architecture after M1, and one more chat of work against a budget that is already over.
- Fact that can show P4 is wrong: at live speed, the GPU reaches its power or temperature limit, or the line time grows after a few minutes (a live check in C7).
- Licence: Seamless is CC-BY-NC 4.0, the same as NLLB, so this does not change.

Please run the power command. Then we decide D-053.

## 41. human · 2026-10-26T13:30:57.836949Z

```text
ok. the results are there. I really want P4 but we have to also know that it will run <5s with CPU. will that be possible? if so, then it is definitely P4
```

## 42. assistant · 2026-10-26T13:32:48.490923Z

The power numbers are in. Whether P4 meets 5 s on the CPU: I do not know, so I wrote a probe to measure it.

## 1. Power [RUN, `nvidia-smi` every 200 ms]

Each run processes the same 161 s of segment audio. The numbers include the model loads. The start temperature was 41–42 °C, and the idle power about 12 W.

| Run | Energy | Mean power | Peak power | Peak temperature | Time at GPU load ≥ 50 % |
|---|---|---|---|---|---|
| P1: RNNT + NLLB | 356 J | 30.5 W | 65.7 W | 54 °C | 2.2 s |
| P2: RNNT + Seamless text MT | 591 J | 31.7 W | 53.3 W | 53 °C | 2.0 s |
| P4: Seamless end to end | 1183 J | 41.0 W | 56.5 W | 59 °C | 11.2 s |

- P4 uses 3.3 times the energy of P1, because the GPU works longer.
- The peak power and the peak temperature stay low: the highest values were 66 W (P1) and 59 °C (P4).
- Thus the GPU did not come near a limit in these runs [inference: I did not measure the limits of this GPU].

## 2. P4 on the CPU: we must measure it

**I do not know if P4 is under 5 s on the CPU.**
- Seamless is a 2.3B model, and P4 makes two calls for each line (ASR and S2TT).
- On the CPU, each call can take several seconds [UNVERIFIED].

**The probe:** `scripts/probe_cpu.py` (new; ruff passes; I checked it after the write).
- It loads all models on the CPU and times 3 real segments of S3 (about 5.4 s, 7.8 s, and 5.4 s of speech).
- It runs P4 (Seamless, float32) and also P1 (NeMo RNNT, and NLLB in CTranslate2 int8) for comparison.
- It does not import Silero, because Silero sets torch to 1 CPU thread.

```bash
env -u LD_LIBRARY_PATH HF_HUB_OFFLINE=1 uv run python scripts/probe_cpu.py all 2>&1 | tee test-results/c3-probe-cpu.txt
```

The time of a line is the VAD wait (about 0.5 s) plus the ASR call plus the MT call. A segment can be up to 10 s long (`vad_max_speech_s`), so the 7.8 s segment is the most important result.

## 3. Before the decision (R14)

The CPU requirement is not decided yet.
- K4 says that the program runs on this laptop, with its GPU, at the interview.
- Q16 (a CPU mode) is still open.

If P4 is too slow on the CPU, these are the options:
- **a.** P4 on the GPU, and P1 as a CPU mode. This must be a flag, not a fallback (R10), and it needs a Q16 decision. Two pipelines also mean more code and more tests.
- **b.** P1 for all hardware.
- **c.** P4 with no CPU mode.

**Time (R16):** the C3 time box ends at about 17:45. With this probe, the decision, the results table, and the handover, I expect C3 to end about 20–30 min later [UNVERIFIED estimate].

## 43. human · 2026-10-26T13:36:52.107437Z

```text
It's fine this will do the most of the improvement stage, let's continue. The results are there.
What I read is that no CPU is not a option for P4, so here's what we are gonna do. Let's implement P4 as well, and I'll contact them regarding the laptop capabilities part.
```

## 44. assistant · 2026-10-26T13:40:28.552418Z

C3 is closed: D-053 records P4 (Seamless end to end on the GPU) as the decision for ASR and MT. The results table is in `docs/eval/results.md`, and I wrote the handover for the next chat.

## The CPU probe [RUN, 24 threads, 3 segments of 5.4–7.8 s]

| Segment | P4 on the CPU | P1 on the CPU |
|---|---|---|
| s3-01 (5.4 s) | 9.9 s | 0.38 s |
| s3-05 (7.8 s) | 36.4 s | 0.43 s |
| s3-07 (5.4 s) | 14.1 s | 0.40 s |

Thus P4 does not meet K1 (5 s) on the CPU. P1 meets it easily, also on the CPU.

## D-053 as I wrote it

- **Decision:** P4 runs on the GPU. One Seamless model gives the HY line and the EN line from the audio of each segment.
- **My reading of "implement P4 as well":** the P1 code stays in the repository, and a CPU mode (Q16) waits for the answer of the Mathrix team. If you meant to remove P1, tell me, and I change D-053.
- **Main risk (R14, one time):** if the Mathrix team requires a CPU-only run, the program needs P1 as a CPU mode. That is a flag (R10), so we would keep two pipelines.
- **The P4 work** goes into C6, as you said ("the improvement stage"). `PLAN.md` v0.13 has this. The order is open: P4 before C4, or after M3. In the handover, I note that P4 first prevents a second change of the worker.

## Documents

I checked each file after the write.

| File | Change |
|---|---|
| `DECISIONS.md` | D-053 |
| `docs/eval/results.md` | the results table, with the conditions, the power, the CPU probe, and the findings |
| `TESTS.md` | the bake-off runs; answers for Q-06, Q-11, and Q-13 |
| `PLAN.md` v0.13 | C3 result; C6 is now the P4 implementation; data for Q15 and Q16 |
| `docs/handovers/03-eval.md` | the handover, with the traceability note about the 17:09 write |

I also put the current `DECISIONS.md`, `ARCHITECTURE.md`, and `PLAN.md` into the Project.

## Commits on `c3-candidates`, then the merge

```bash
git add scripts/probe_cpu.py
git commit -m "test(eval): add the CPU probe for P1 and P4"
git add DECISIONS.md
git commit -m "docs(decisions): add D-053 Seamless end to end (P4)"
git add docs/eval/results.md
git commit -m "docs(eval): add the C3 bake-off results"
git add TESTS.md
git commit -m "docs(tests): add the bake-off runs and the C3 QA answers"
git add PLAN.md
git commit -m "docs(plan): close C3 and give C6 the P4 implementation"
git add docs/handovers/03-eval.md
git commit -m "docs(handover): add the C3 handover"
git push
```

When CI is green:

```bash
git switch main && git pull
git merge --no-ff c3-candidates -m "Merge branch 'c3-candidates'"
git push
```

## What remains for you

1. **Time log (R16):** write the C3 time in `PLAN.md` §11, or give it to me. C3 started at 15:14 and went over its 2.5 h time box.
2. **Next chat:** give the handover `docs/handovers/03-eval.md` as the first message, and tell me the order (P4 or C4) and the answer of the Mathrix team.

## 45. human · 2026-10-26T13:44:18.252611Z

```text
ok, let's leave P4 for now. It will go on the improvement stage. let's end C3 and I'll contact them. Write the time in the Plan. 
When we get back to P4 we want a pipeline that is suitable for both P1 and P4. You shall OOP and abstraction technqiues and Template pattern to achieve this invariance. 
C3 is ended
```

## 46. assistant · 2026-10-26T13:45:39.858887Z

C3 is closed. The time is in the plan, and the documents now say that P4 waits for C6 (after M3) and that C4 comes next.

**What changed** (I checked each file after the write):
- **`PLAN.md`:**
  - C3 took 2.5 h (15:14–17:44, from the chat times), the same as its time box. The total is now 13.92 h.
  - C6: P4 comes after M3. Your design rule is in it: one pipeline for both P1 and P4, with OOP abstraction and the Template Method pattern.
- **`DECISIONS.md`:** D-053 has an addition with your words. C6 will propose the design with the R7 steps.
- **`docs/handovers/03-eval.md`:** the next chat is now C4 (two audio sources), with a new Read list and the C3 facts that C4 needs. The P4 facts stay in it, for C6.
- **Project documents:** I put the new `DECISIONS.md` and `PLAN.md` into the Project.

**One note for C6 (R14):** the adapters already use Protocols (`Transcriber`, `Translator`). A Template Method base class for the segment step fits on top of them:
- P1: transcribe, then translate the text.
- P4: two calls on the speech.

The alternative is composition (Strategy). Inheritance ties the steps of the template together more than composition does. The handover notes this for the C6 discussion.

**Commits:**
- If you did not run the commits from my last message yet, those commands include these changes.
- If you ran them already, run these:

```bash
git add PLAN.md
git commit -m "docs(plan): log the C3 time and the C6 design note"
git add DECISIONS.md
git commit -m "docs(decisions): add the C6 note to D-053"
git add docs/handovers/03-eval.md
git commit -m "docs(handover): set C4 as the next chat"
git push
```

When CI is green, merge `c3-candidates` into `main` (the merge commands are in my last message).

To start C4, give `docs/handovers/03-eval.md` as the first message of the new chat.
