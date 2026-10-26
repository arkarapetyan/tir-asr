# DECISIONS.md: Decision Log

**Project:** Live Armenian Transcription to English Translation
**Rules:** RULES.md R7 (both of us question each decision) and R8 (research first).

Status values: **PROPOSED** (open), **ACCEPTED** (final), **REPLACED BY D-xxx** (a new entry replaced it).
We do not delete entries. A new fact opens a decision again with a new entry.
Quotes from Aren come from the chat. Claude corrected only the spelling.

---

## Template

```markdown
## D-NNN. <Title>
- Status: PROPOSED | ACCEPTED (date) | REPLACED BY D-xxx
- Context: why we must decide.
- Options: A, B, C, each with its weak points.
- Claude's preference: option, weak point, and a test or fact that can show it is wrong.
- Decision:
- Reason (Aren's words):
- Questions raised: who asked what, and the answer.
- Revisit when: the fact or result that opens this decision again.
```

---

## D-001. Working method

- **Status:** ACCEPTED (2026-10-23)
- **Context:** The brief evaluates the working method and the use of AI tools. Aren asked for written rules and a plan before any work.
- **Decision:** We work by `RULES.md` and `PLAN.md`. The rules come from the Mathrix tips (T1–T10), Aren's rules (A1–A10), and Claude's rules R14–R16.
- **Reason (Aren's words):** "Yes, I approve the addition of those rules."
- **Questions raised:**
  - Claude: Research is not the first step, because rule A1 puts plan approval first. Aren: "Yes, Research comes after C0 that is approving the plan."
  - Claude: TDD cannot test audio devices or large models in CI. Aren: "simulate live model tests whenever possible and automate the model tests on my laptop." Result: the sim test level (R5) and D-006.
  - Claude: The rule against timeouts needs a line for segment parameters. Aren: parameters are "allowed only as named but not added by you". Result: R10.
- **Revisit when:** A rule blocks the work. Then we change `RULES.md` and log the change here.

## D-002. Phase order: skeleton first (option B)

- **Status:** ACCEPTED (2026-10-23)
- **Context:** Tip T2 says to build a walking skeleton first. Tip T5 says to build an eval set early. One of them must come first.
- **Options:**
  - **A.** Eval set and bake-off first, then the skeleton. Weak point: M1 comes about 2.5 h later.
  - **B.** Skeleton first with the best research candidate, then the eval set and the bake-off. Weak point: if the first candidate does not install or is too slow, we lose skeleton time.
- **Claude's preference:** A, because the brief names the model choice as the main risk for Armenian.
- **Decision:** B.
- **Reason (Aren's words):** "it follows tip T2 more closely".
- **Questions raised:** Claude named the weak point of B. Mitigation: the first step of C2 is an install check of the first candidates on Aren's laptop.
- **Revisit when:** The install check in C2 fails for the first candidate and for the second candidate of the same component.

## D-003. Speaker model fine-tuning only after measurement

- **Status:** ACCEPTED (2026-10-23)
- **Context:** Aren noted that speaker models can need fine-tuning for a low-resource language (hypothesis H-S1, `PLAN.md` §6.4). Fine-tuning needs labelled Armenian speaker data and much of the 20-hour budget.
- **Decision:** No fine-tuning before we measure. C1 researches H-S1. C5 measures the label accuracy on Armenian multi-speaker eval streams. We fine-tune only if the numbers fail and time allows.
- **Reason (Aren's words):** "fine-tuning is a hypothetical scenario and meanwhile we'll do it according to your proposal".
- **Questions raised:** Claude: the harder problem is stable labels during a live session (online clustering), not the language.
- **Revisit when:** The C5 numbers show that the labels fail on Armenian speech.

## D-004. Aren owns the repository

- **Status:** ACCEPTED (2026-10-23)
- **Context:** Somebody must do the git operations and own the GitHub repository.
- **Decision:** Aren owns the repository and does all git operations. Claude tells Aren when to commit and when to push, and gives the commit message. Claude never pushes.
- **Reason (Aren's words):** "I suggest running the repo on my own and you are to only instruct me when to do commits and push them".
- **Questions raised:** Claude: this adds manual steps for each change. It also makes Aren read each change before the commit (tip T8). The transfer method is open (D-005).
- **Revisit when:** The manual steps take too much of the time budget.

## D-005. How Claude gives each change to Aren

- **Status:** ACCEPTED (2026-10-23), see "Status update"
- **Context:** Claude writes code in the cloud workspace (D-004). The workspace cannot write to Aren's laptop (`PLAN.md` §3). Claude must also get the latest code at the start of each chat.
- **Options:**
  - **A. Patch file.** At the start of a chat, Claude clones the repository read-only at Aren's latest commit. Claude makes the change and runs `ruff` and the unit tests. Claude sends one `.patch` file and the commit message. Aren runs `git apply --check`, then `git apply`, reads `git diff`, runs the tests, commits, and pushes.
    - Weak points: more steps for Aren. Claude needs read access (a public repository, or GitHub access for a private one). If Aren's files differ from Claude's copy, `git apply` fails. This failure is loud, which is correct (R10).
  - **B. Separate files.** Claude sends each changed file. Aren copies the files into the repository.
    - Weak points: Aren can put a file in the wrong place. Deleted files are easy to miss. There is no single unit to review.
  - **C. Device bridge.** Aren connects the repository folder to the chat through the Claude desktop app. Claude writes the files directly into it. Aren reads `git diff`, commits, and pushes.
    - Weak points: **[RUN]** this session shows no tool that writes to the laptop. We do not know that it works. Claude writes directly to Aren's disk, so Aren has less control before the review.
- **Claude's preference:** A. Test that can show it is wrong: if a patch fails to apply two times in one chat because of a copy mismatch, we change to C or B.
- **Status update:** ACCEPTED (2026-10-23), option C with a limit.
- **Decision:** Claude reads and writes **only** in the project folder `/home/aren/dev/armenian-asr` on Aren's laptop. Claude does not use the GitHub repository. Aren does all git operations.
- **Reason (Aren's words):** "I have provided a folder for the project (home/aren/dev/armenian-asr). You are free to read and write to that folder ONLY and you dont need to see the github repo that I will run."
- **Questions raised:** Claude named the weak point of C: Claude writes directly to Aren's disk. Mitigation: Aren reads `git diff` before each commit (R12). A folder grant is for one chat only, so each new chat asks for access again.
- **Revisit when:** the folder tools do not work in a chat.

## D-006. How the tests run on Aren's laptop

- **Status:** ACCEPTED (2026-10-23), see "Status update"
- **Context:** Aren asked to simulate live tests when possible and to automate the model tests on the laptop (D-001). CI cannot run them, because it has no GPU, no models, and no audio devices.
- **Options:**
  - **A. One command.** One command runs all model and sim tests and prints a short summary, for example `uv run pytest -m "model or sim"`. Aren runs it before each push that changes `src/`. Aren pastes the summary into the chat.
    - Weak point: Aren must remember to run it.
  - **B. Pre-push hook.** A git hook runs the same command before each push. The push stops if a test fails.
    - Weak points: each push waits for model loads and for real-time audio playback, probably minutes **[UNVERIFIED]**. `git push --no-verify` can skip the hook. The sim tests change the audio devices during the push.
  - **C. Self-hosted GitHub Actions runner** on the laptop. Each push runs the model and sim tests and shows the result on GitHub.
    - Weak points: setup time. **[UNVERIFIED]** GitHub advises self-hosted runners only for private repositories, for security. The laptop must be on. **[UNVERIFIED]** A runner that is a system service possibly cannot use the audio session of the user.
- **Claude's preference:** A for the MVP. Test that can show it is wrong: if a broken model or sim test reaches `main` one time, we change to B.
- **Status update:** ACCEPTED (2026-10-23), option A with a change.
- **Decision:**
  1. When a test run is necessary, Claude tells Aren and gives the exact commands. Then Claude waits.
  2. Aren runs the commands on the laptop.
  3. The commands write the result into a file in `test-results/` in the project folder. This folder is in `.gitignore`.
  4. Claude reads the file.
- **Reason (Aren's words):** "I agree on running the sim tests by myself and sharing the results with you. Each result of tests and simulation tests can be dumped to a file in the project folder that you can read."
- **Detail (Q13), ACCEPTED (2026-10-23):** Claude also runs `ruff` and the unit tests on a copy in the workspace before Claude asks Aren. Aren's run stays the official result. Aren's words: "Yes, you may run tests and checks on your own".
- **Revisit when:** a broken model or sim test reaches `main`.

## D-007. Tool baseline

- **Status:** ACCEPTED (2026-10-23), see "Status update"
- **Context:** Rule R11 requires industry-grade tools. The setup files in C0 need concrete values.
- **Proposal:**
  - Python **3.12**, provisional. C1 checks the Python versions that each candidate library supports.
  - uv project with the `src/` layout. Package name: `hy2en` (proposal; Aren can choose a different name).
  - Dependency group `dev`: `ruff`, `pytest`. We add each model library later, with its own decision.
  - ruff: line length 100; rule sets `E`, `F`, `W`, `I`, `B`, `UP`; `ruff format` for format.
  - pytest markers: `model` and `sim`. A plain `uv run pytest` runs the unit tests only.
  - CI: GitHub Actions on `ubuntu-latest`, with `astral-sh/setup-uv`. Steps: `uv sync --locked`, `ruff check`, `ruff format --check`, `pytest` (unit tests only).
  - `.gitignore`: Python files, `.venv/`, `data/`, `models/`, audio files (`*.wav`, `*.flac`, `*.mp3`, `*.ogg`), weight files (`*.nemo`, `*.pt`, `*.pth`, `*.bin`, `*.safetensors`, `*.onnx`), `.env`.
- **Options not in the proposal:**
  - Python 3.11: wider support in older libraries. Weak point: older.
  - Type check (mypy or pyright): not now, because tip T8 says to keep it simple. We can add it later with a decision.
  - pre-commit hooks: not now, for the same reason. CI does the same checks.
- **Claude's preference:** the proposal above. Weak point: Python 3.12 can be too new for one candidate library **[UNVERIFIED]**. Test that can show it is wrong: the C1 research finds a shortlisted library that does not support 3.12.
- **Status update:** ACCEPTED (2026-10-23). The Python version and the package name are provisional. The package name comes from D-008.
- **Decision:** the proposal above.
- **Reason (Aren's words):** "agree on the tools proposed and yes some of the suggestions are provisional."
- **Revisit when:** C1 finds a shortlisted library that does not support Python 3.12.
- **C1 result (2026-10-24):** the revisit condition did not occur. All libraries on the C1 shortlists accept Python 3.12 in their PyPI metadata. Small risk: `nemo-toolkit` 3.0.0 lists only Python 3.10 in its classifiers (`RESEARCH.md` §0).

## D-008. Name of the application, the package, and the repository

- **Status:** ACCEPTED (2026-10-23): `tir-asr`
- **Context:** Aren asked for a name before he makes the repository. The repository and the distribution use the name. The Python import name is the same name with an underscore (`tir_asr`), because an import name cannot have a hyphen.
- **Options:** 5 names, on the historical side. **[RUN]** None of them is in use on PyPI (checked on 2026-10-23). The history notes come from Claude's knowledge. **[UNVERIFIED]**
  1. **`dragoman`**: the old word for an interpreter at courts and embassies. It comes from the same old root as the Armenian "targmanich" (translator). Many Armenians worked as dragomans. Weak points: it does not look Armenian; English readers can think of "dragon".
  2. **`koryun`**: Koryun, one of the 5th-century "Holy Translators" and a student of Mesrop Mashtots. Weak point: few people outside Armenia know the name.
  3. **`mesrop`**: Mesrop Mashtots made the Armenian alphabet. The program changes Armenian speech into Armenian letters. Weak points: many Armenian projects and organisations use this name; it is a very serious name for a demo.
  4. **`tirgir`**: Tir is the god of writing and wisdom in old Armenian myth, and "gir" means "letter" or "script". Weak point: it is a new word that needs an explanation. Note: `tir` alone is in use on PyPI.
  5. **`sayatnova`**: Sayat-Nova, the 18th-century poet and singer who sang in several languages. Weak point: the link is to songs, not to translation.
- **Names that Claude did not include:** `babelfish` (from Douglas Adams' fiction, and an earlier translation product used the name); `grogh` (a figure from Armenian folk belief who writes down deeds, but the word is also part of a common Armenian curse).
- **Claude's preference:** `dragoman`. It tells an English reader what the program does, and it has an Armenian link. Fact that can show it is wrong: if the interviewers must ask what the name means, `koryun` gives the same effort for a stronger Armenian link.
- **Decision:** `tir-asr` (Aren's own proposal). Import name: `tir_asr`.
- **Reason (Aren's words):** "I suggest tir-asr as a name, I believe that one isnt used by other packages?"
- **Facts:**
  - **[RUN]** `tir-asr`, `tir_asr`, and `tirasr` are not in use on PyPI (checked on 2026-10-23).
  - **[SOURCE]** In Armenian mythology, Tir is the god of written language and wisdom, the scribe of the chief god Aramazd, and an interpreter of dreams ([Wikipedia: Tir (god)](https://en.wikipedia.org/wiki/Tir_(god))).
- **Questions raised:** Claude: "asr" names only one of the three functions (speech recognition, translation, speaker labels). Also, "TIR" is a known term in ML compilers (TensorIR in Apache TVM) **[UNVERIFIED]**. Both are small risks.
- **Revisit when:** Aren wants a different name before the first push. After the first push, a change costs more.

## D-009. Pin one uv version

- **Status:** ACCEPTED (2026-10-23), see "Status update"
- **Context:** Three different uv versions are in use now:
  - **[RUN]** Aren's laptop: uv 0.12.21 (`test-results/c0-setup.txt`).
  - **[RUN]** Claude's workspace: uv 0.11.32.
  - **[RUN]** The newest uv on PyPI is 0.13.5 (checked on 2026-10-23). **[SOURCE]** CI uses the newest uv when the project does not give a `required-version` ([setup-uv README](https://github.com/astral-sh/setup-uv)).
  - **[RUN]** On Aren's laptop, `uv sync` printed a warning: `uv_build>=0.11.32,<0.12.0` does not contain uv 0.12.21. The run did not fail.
- **Options:**
  - **A. Pin Aren's uv 0.12.21.** Add `[tool.uv] required-version = "==0.12.21"` and change the build backend range to `uv_build>=0.12.21,<0.13`. Claude updates the workspace uv to 0.12.21. CI reads `required-version` from `pyproject.toml`, so `ci.yml` does not change. If a different uv runs the project, uv stops with an error (fails loudly, R10).
    - Weak point: we do not use the newest uv.
  - **B. Pin the newest uv 0.13.5.** Same changes with 0.13.5. Aren updates the uv on the laptop.
    - Weak points: one more step on the interview laptop; a very new version has less use.
  - **C. No pin.** Change only the build backend range.
    - Weak point: three places run three different uv versions. The results can differ, and the warning comes back when uv changes.
- **Claude's preference:** A. The laptop is the interview machine (K4), so we do not change its tools without a reason. Fact that can show it is wrong: we need a uv feature or fix that exists only in 0.13 or later.
- **Status update:** ACCEPTED (2026-10-23), option A.
- **Decision:** `[tool.uv] required-version = "==0.12.21"` and `uv_build>=0.12.21,<0.13` in `pyproject.toml`.
- **Reason (Aren's words):** "ok lets pin my uv"
- **Checks [RUN] in the workspace:** with uv 0.12.21, `uv lock`, `uv sync --locked`, `ruff`, and `pytest` pass, and the build warning is gone. `uv.lock` did not change. With uv 0.11.32, `uv sync` stops with an error: "Required uv version `==0.12.21` does not match the running version `0.11.32`" (fails loudly, R10).
- **Revisit when:** we need a uv feature or fix from 0.13 or later.

## D-010. Pin the CI actions to commit SHAs

- **Status:** ACCEPTED (2026-10-23), see "Status update"
- **Context:** The first CI run failed: `Unable to resolve action astral-sh/setup-uv@v10, unable to find version v10`.
  - **Cause (Claude's error):** Claude checked that the v10 releases exist, but did not check that a `v10` tag exists (R9).
  - **[RUN]** `git ls-remote --tags` shows that setup-uv publishes only full version tags (for example `v10.3.2`), not a `v10` tag. `actions/checkout` has a `v7` tag, which points to `v7.0.1`.
  - **[SOURCE]** The setup-uv README pins the action to a full commit SHA with a version comment ([setup-uv README](https://github.com/astral-sh/setup-uv)).
- **Options:**
  - **A. Commit SHA with a version comment**, for both actions:
    - `actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1`
    - `astral-sh/setup-uv@07a047e608db84b3d8c06cd9a7c7dcc9c355c18e # v10.3.2`
    - A SHA cannot move, so the CI always runs the same code. Weak point: updates are manual.
  - **B. Full version tag:** `actions/checkout@v7.0.1`, `astral-sh/setup-uv@v10.3.2`. Simpler to read. Weak point: a tag can move to different code.
- **Claude's preference:** A. Fact that can show it is wrong: if the manual updates take time more than once in this project, B is enough for a 20-hour project.
- **Status update:** ACCEPTED (2026-10-23), option A.
- **Decision:** both actions use a commit SHA with a version comment.
- **Reason (Aren's words):** "Option A done". Aren reported the next CI run: "CI done".
- **Lesson for later chats:** for each GitHub Action, check that the exact tag exists (`git ls-remote --tags`), not only the release.
- **Revisit when:** an action needs an update.

## D-011. When we learn the chat export format

- **Status:** ACCEPTED (2026-10-23), option A
- **Context:** Deliverable D3 needs each chat as its own `.md` file in `chats/`, complete and unedited. **[SOURCE]** The support article describes only a full data export (Settings > Privacy > Export data, a download link by email that expires after 24 hours). It does not give the file format ([Export your Claude data](https://support.claude.com/en/articles/9450526-export-your-claude-data)).
- **Fact found during the discussion:** the final export must come after the last message of the last chat (C8). If the format needs a conversion, the converter must exist before that. Thus a conversion always needs one earlier export to learn the format.
- **Options:**
  - **A.** Request one full export now, to learn the format. Do the final export after C8. Weak point: two export requests and a few minutes now.
  - **B.** Only one export, after C8. Weak point: if the format needs a conversion, B also needs two exports, and the converter comes late with no buffer.
  - **Not exporting:** rejected. It breaks deliverable D3, and the interview uses the original chats and the exported copies.
- **Claude's preference:** A.
- **Decision:** A. Aren requests the full export now. Aren shows the format (file names and the keys of one conversation, not the content) in a separate side chat, S1. The final export comes after the last message of C8.
- **Reason (Aren's words):** "ok I see your point, I will request the format now and will present the result in a separate chat once we get it."
- **Questions raised:** Aren first chose B, "so I only request chat exports once". Claude then showed that B gives one export only if no conversion is necessary. Aren changed to A.
- **Revisit when:** S1 shows that the export already has one Markdown file for each chat. Then no converter is necessary.
- **S1 result (2026-10-23):** **[RUN]** The export is one JSON file with a list of chats. It is not one Markdown file for each chat. The "Revisit when" condition did not occur. A converter is necessary (D-012).

## D-012. Chat export converter: text only (option B)

- **Status:** ACCEPTED (2026-10-23), option B
- **Context:** Deliverable D3 needs one `.md` file for each chat. S1 measured the format **[RUN]** on Aren's export of C0 (a file `conversations.json`, upload of 2026-10-23 12:49 UTC). A script printed only keys, types, and counts.
  - The export is one JSON file with a list of chats. Thus D3 needs a converter (D-011).
  - Chat keys: `uuid`, `name`, `summary`, `created_at`, `updated_at`, `account`, `chat_messages`. No key gives the project.
  - Message keys: `uuid`, `parent_message_uuid`, `sender`, `created_at`, `updated_at`, `text`, `content`, `attachments`, `files`.
  - The messages are a tree, not a list. C0 has 3 branches, because Aren edited 2 messages. No key marks the branch that the app shows.
  - `message.text` is not complete. It puts the text "This block is not supported on your current device yet." in place of the tool calls. The `content` list has the blocks.
  - Block types in C0: `text` 27, `tool_use` 149, `tool_result` 149, `thinking` 74, `injected_prompt_block` 10, `document` 4.
  - The `thinking` text is empty in all 74 thinking blocks. 63 of them have short summaries.
  - `files` and `document` blocks give only a name and an ID, not the file content.
  - Size of C0: about 310,000 characters. Most of it is tool inputs (155,000) and tool results (75,000).
- **Options:**
  - **A. Full converter.** All blocks and all branches. Tool calls, tool results, thinking summaries, and injected prompts in closed sections. The converter stops on an unknown block type or key.
    - Weak points: the final export after C8 can have new block types. Then the converter stops after C8, and we must fix it. The files are long (C0: about 0.3 MB).
  - **A2.** The same as A, but the converter writes an unknown block type as raw JSON and does not stop.
    - Weak points: more code than B. The files are long.
  - **B. Text only.** Only the `text` blocks of the main branch.
    - Weak points: the file does not have the tool calls, the tool results, the thinking summaries, or the side branches. Thus it is not "complete" in the sense of D-011. The work steps are visible only in the original chats (R15).
  - **C. Split only.** One JSON file for each chat, and a short `.md` file with a link.
    - Weak point: D3 asks for `.md` files. JSON is hard to read in the interview.
- **Claude's preference:** A. After Aren did not accept the main risk of A, Claude proposed A2. Fact that can show the preference is wrong: the interviewers use only the original chats to see the work steps.
- **Decision:** B. Details:
  - Each file starts with a note. The note tells what is not in the file, with counts, and that the original chat has all blocks.
  - Human text goes into a code fence. Assistant text stays Markdown. The text does not change.
  - **Main branch:** the path from the root to the newest leaf message. Aren confirmed that the app shows this branch for C0.
  - **Chat selection:** by the chat title, in a manifest `chats/manifest.toml`. The converter stops when a title matches no chat or two or more chats. Aren selected the title, not the chat ID. He does not want to check the chat addresses: "idk and wont check".
  - **C0 now, S1 at the end:** Aren runs the converter on the C0 export of 2026-10-23 as the real-data check. The final run after C8 replaces the C0 file and adds S1 and the other chats. D-011 does not change.
  - **Time:** the time for this converter is not part of the 20-hour budget. Aren's words: "The time that takes you to build it is not counted under the whole project time".
  - The contract is in `ARCHITECTURE.md` §8.1. The tests are in `TESTS.md` §2.2.
- **Reason (Aren's words):** "let's not spend too much on this since it is not a project-related thing."
- **Questions raised:**
  - Claude named the main risk of A one time (R14). Aren did not accept the risk and selected B.
  - Claude (R14): B conflicts with "complete and unedited" in D-011. Claude proposed A2, which removes the risk of A. Aren selected B again.
- **Revisit when:** the brief or the interviewers need the tool calls in the `.md` files, or a title in the final export matches no chat or two or more chats.

## D-013. Target language: Eastern Armenian only

- **Status:** ACCEPTED (2026-10-24)
- **Context:** Armenian has two standard forms, Eastern and Western. A model or a test set can cover only one of them. C1 needed the scope before the research tables.
- **Options:**
  - **A.** Eastern Armenian only.
  - **B.** Eastern and Western Armenian.
- **Claude's preference:** A. Weak point: we do not measure Western speech.
- **Decision:** A. Research and evaluation use Eastern Armenian. The README lists Western Armenian as a known limit.
- **Reason (Aren's words):** "There is no need for the dialect variations, only Eastern Armenian will be sufficient." Later: "Eastern Only that one I agree".
- **Questions raised:** Claude (R14): a WER on a Western or mixed test set does not show the WER on Eastern speech. `RESEARCH.md` notes such sets.
- **Revisit when:** the brief or the interviewers need Western Armenian.

## D-014. ASR: first candidate and C3 shortlist

- **Status:** ACCEPTED (2026-10-24)
- **Context:** C1 research, `docs/research/RESEARCH.md` §1 and §10.
- **Options for the first candidate:**
  - **A.** ASR-1 `nvidia/stt_hy_fastconformer_hybrid_large_pc` on NeMo, RNNT decoder. Weak points: NeMo is the heaviest install (`lightning` exactly 2.4.0, torchaudio in maintenance); no streaming; "noise-sensitive"; it saw Common Voice 17.0 and FLEURS in training.
  - **B.** ASR-1 on ONNX Runtime with the community CTC export. Weak point: the CTC head has a higher WER (MCV 17.0: 11.19 vs 9.90; FLEURS: 13.23 vs 12.32).
  - **C.** ASR-3 `Chillarmo/whisper-large-v3-turbo-armenian`. Weak points: higher WER than ASR-1 on all 5 ArmBench sets; about 6 GB VRAM for `turbo`; no streaming.
- **Claude's preference:** A. First shortlist proposal: ASR-1, ASR-2, ASR-3. After Aren's question, Claude removed ASR-3 and proposed ASR-5 (`BuzzASR/armenian`) for the third place. Test that can show the preference is wrong: the C2 install check fails two times, or C3 shows a different model with a lower WER on Aren's recordings within K1.
- **Decision:**
  - **First candidate (C2):** ASR-1 on NeMo, RNNT decoder.
  - **Planned second path:** if NeMo does not install in C2, ASR-1 runs on ONNX Runtime with the CTC head (`OpenVoiceOS/stt_hy_fastconformer_hybrid_large_pc_onnx`). This is a decided plan, not a silent fallback (R10).
  - **C3 shortlist:**
    - ASR-1 in three runtime variants: NeMo-RNNT, NeMo-CTC, ONNX-CTC,
    - ASR-2 `facebook/seamless-m4t-v2-large` (the only end-to-end option; the same weights give MT-5),
    - ASR-5 `BuzzASR/armenian`. ASR-5 leaves the list if its WER on Aren's recordings is not lower than the WER of ASR-1.
- **Reason (Aren's words):**
  - On Whisper turbo: "Since it shows worse results than the fastconformer on the benchmark, what is the point of even bothering with heavier and worse model."
  - On the weak points of A: "as the design document suggests we are fine with noise and I guess heavy installation is a problem that can be solved, especially if we resort to using ONNX".
  - Third place: Aren selected "BuzzASR third (Recommended)" in the checkbox, with no own words.
- **Questions raised:**
  - Aren: can a non-streaming model meet K1? Claude: not known before the C2 measurement. K1 counts from the end of a phrase, so streaming gives no direct gain except for long phrases. A maximum segment length (a parameter, R10) limits that case.
  - Aren: is ONNX Runtime faster than NeMo? Claude: "I do not know". No source compares them for a FastConformer model.
  - Aren: why keep Whisper turbo? Claude: removed. ASR-1 also has the lowest open WER on the three private ArmBench sets. ASR-2 stays only as the end-to-end option and for MT-5.
- **Revisit when:** both ASR-1 paths fail the C2 install check (D-002); the ASR time makes the C2 latency of a line more than 5 s; or C3 shows a lower WER for a different model within K1.

## D-015. MT: first candidate and C3 shortlist

- **Status:** ACCEPTED (2026-10-24), changed after D-016
- **Context:** C1 research, `RESEARCH.md` §2. C1 found no Armenian → English score on one common test set for the candidates.
- **Options for the first candidate:**
  - **A.** MT-2 `facebook/nllb-200-distilled-600M`. Weak points: no Armenian score found in C1; "not released for production deployment"; CC-BY-NC 4.0.
  - **B.** MT-1 `Helsinki-NLP/opus-mt-hy-en`. Weak point: 91 % of its training pairs come from JW300 and the Bible; 0.7 % from subtitles (calc).
  - **C.** MT-5 SeamlessM4T v2, text-to-text. Weak point: 2.3B parameters (~4.6 GB in float16, calc).
- **Claude's preference:** A. Test that can show it is wrong: in C3, MT-1 or MT-5 has a higher chrF on Aren's recordings within K1.
- **Decision (changed for D-016):**
  - **First candidate (C2):** MT-2 NLLB-200-distilled-600M on **CTranslate2** (first proposal: on Transformers).
  - **New parameter `mt_compute_type = float16`** (approved 2026-10-24, R10). Reason: the CTranslate2 value `auto` selects `int8_float16`, which fails on RTX 50-series GPUs with `CUBLAS_STATUS_NOT_SUPPORTED`; a fixed value also prevents a silent choice. In the CTranslate2 GPU benchmark, float16 was the fastest mode (9297 tokens/s vs 7522 for int8, A10G).
  - The C2 install check also times the same sentences on PyTorch (data for the D-016 revisit condition).
  - **C3 shortlist:** MT-1 OPUS-MT (CTranslate2), MT-2 NLLB-600M (CTranslate2), MT-5 Seamless text-to-text (PyTorch; CTranslate2 support for Seamless [UNVERIFIED]).
- **Reason (Aren's words):** "D15. Full agree" (before the change for D-016). On CTranslate2: "I see that CTranslate 2 will theoretically provide good amount of performance boost." Aren then selected "Accept D-015 as changed" in the checkbox.
- **Questions raised:** Aren: is CTranslate2 slower on Blackwell without INT8, and is there a point in it as opposed to ONNX Runtime? Claude: in the published benchmark, float16 was faster than int8; the reported RTX 50-series errors come from the default `int8_float16`; no source compares CTranslate2 with ONNX Runtime for MT ("I do not know").
- **Revisit when:** C3 shows a higher chrF for a different model within K1.

## D-016. Runtime base: PyTorch and CTranslate2 (option B)

- **Status:** ACCEPTED (2026-10-24), option B
- **Context:** C1 research, `RESEARCH.md` §0. The RTX 5070 needs PyTorch CUDA 13 builds. ONNX Runtime GPU uses CUDA 13. CTranslate2 wheels use CUDA 12.8 and disable INT8 on sm120.
- **Options:**
  - **A.** PyTorch (CUDA 13) only. Add CTranslate2 or ONNX Runtime only after a measurement shows that a model is too slow. Weak point: if NeMo fails, the second path for ASR-1 comes late.
  - **B.** PyTorch and CTranslate2 from the start (CTranslate2 for MT). Weak points: CUDA 12 libraries next to CUDA 13 in one environment, with `LD_LIBRARY_PATH`; no INT8 on Blackwell; the published speed gain is batch throughput with 2023 versions, not the latency of one segment.
  - **C.** ONNX Runtime for all models. Weak points: no source shows a speed gain for our models; ASR-1 has a CTC-only export unless our own RNNT export works [UNVERIFIED]; an export step for each model before the MVP (R2).
  - **E.** C2 on PyTorch/NeMo; C3 measures each model on each runtime with a working conversion; change to the faster runtime at equal quality. Weak point: more runs in C3.
- **Claude's preference:** A, then E after Aren's objection. Test that can show it is wrong: the C2 latency is more than 5 s and MT is a large part of it (for A); C3 shows ONNX faster for all models (for E).
- **Decision:** B. CTranslate2 runs the MT model from C2. PyTorch (CUDA 13 build) runs the models without a CTranslate2 path. The C2 install check includes CTranslate2 on the GPU, with the CUDA 12 libraries.
- **Reason (Aren's words):** "if we know a faster framework we should utilize it from the beginning, since we have no issues with keeping two packages".
- **Questions raised:**
  - Aren: why is C not a good option? Claude gave the four weak points above.
  - Claude (R14): "faster" is not yet a fact for one short segment on this GPU (R6).
- **Revisit when:** CTranslate2 does not run on the GPU in the C2 install check, or C3 shows no latency gain over PyTorch for MT.

## D-017. Speaker models: C5 shortlist

- **Status:** ACCEPTED (2026-10-24)
- **Context:** C1 research, `RESEARCH.md` §4. Hypothesis H-S1 (D-003).
- **Options:**
  - **A.** An embedding for each segment and our own online clustering, with the shortlist below.
  - **B.** NVIDIA Streaming Sortformer (end-to-end streaming diarization). Weak points: maximum 4 speakers; trained "primarily in English"; "may degrade on non-English speech"; NVIDIA Open Model License (terms not read).
  - **C.** diart. Weak point: `diart` 0.9.2 does not install with `pyannote.audio` 4.0.7 (numpy conflict) [RUN].
- **Claude's preference:** A. Weak point: all three models were trained on English or VoxCeleb data, and C1 found no Armenian results. Test that can show it is wrong: all three fail the C5 label-accuracy test.
- **Decision:** A. C5 shortlist:
  - `pyannote/wespeaker-voxceleb-resnet34-LM`,
  - `speechbrain/spkrec-ecapa-voxceleb`,
  - `nvidia/speakerverification_en_titanet_large`.
- **Reason (Aren's words):** "Agree with D17 with reservation. Will they work with Armenian?" On pyannote (telemetry on by default, gated models, `lightning` 2.4.0): "The three points mentioned for pyannote are fine."
- **Questions raised:** Aren: will they work with Armenian? Claude: "I do not know". Three sources show that language changes the scores: pairs of different speakers in the same language get higher similarity. Only the C5 measurement with several Armenian speakers answers it (D-019).
- **Revisit when:** all three fail the C5 label-accuracy test. Then D-003 (fine-tuning) or option B opens again.

## D-018. VAD

- **Status:** ACCEPTED (2026-10-24)
- **Context:** C1 research, `RESEARCH.md` §5.
- **Options:** A. Silero VAD; B. WebRTC VAD (`webrtcvad-wheels`); C. pyannote segmentation.
- **Claude's preference:** A. Facts: MIT licence, no telemetry, less than 1 ms for each 30+ ms chunk on one CPU thread, model about 2 MB. Weak point: no source gives settings for K1. Test that can show it is wrong: in C2 or C3, segments cut phrases or add latency, and WebRTC VAD does better.
- **Decision:** Silero VAD on the CPU is the first candidate. WebRTC VAD is the second. Claude proposes the settings (minimum silence, maximum segment length) in C2 with numbers. Aren approves them (R10).
- **Reason (Aren's words):** "Agree".
- **Revisit when:** the C2 or C3 numbers show cut phrases or a latency problem from the VAD.

## D-019. Eval data

- **Status:** ACCEPTED (2026-10-24)
- **Context:** C1 research, `RESEARCH.md` §7. `PLAN.md` §5.2 C3 had a proposal: about 30 public clips, about 10 own recordings, and 1–2 multi-speaker streams.
- **Options:**
  - **A.** FLEURS `hy_am` test (about 30 clips), about 10 recordings by Aren, Common Voice streams for C5.
  - **A2.** 20 recordings by Aren for ASR and MT; Common Voice clips of different speakers for the C5 streams only.
  - **A3.** 20 recordings by Aren only; C5 data decided in C5.
  - **A4.** 20 recordings by Aren; recordings that Aren makes with other people for C5.
- **Claude's preference:** A, then A2 after Aren's proposal. Weak point of A2: Common Voice needs a registration, and the `client_id` field is [UNVERIFIED].
- **Decision:** A4.
  - ASR and MT eval: 20 recordings by Aren. Aren writes the Armenian and the English reference text.
  - C5 speaker eval: recordings that Aren makes with other people.
  - No public eval set.
- **Reason (Aren's words):** "I propose 20 recordings only by me since FLEURS and Common Voice are Train data". For C5, Aren selected "20 own + you record others" in the checkbox, with no own words.
- **Questions raised:**
  - Claude (correction): Common Voice and FLEURS are training data for the ASR candidates (ASR-1, ASR-5). The model cards do not give the splits. They are not training data for the speaker models (VoxCeleb or English corpora).
  - Claude (R14): 20 recordings with one voice, one microphone, and one room do not show the WER for other voices or for call audio.
- **Amendment (2026-10-24, Aren):** "I'll actually try to include more recordings that will include voices of multiple people and recordings done on different devices." Thus:
  - at least 20 recordings, with several voices and several devices;
  - conversation text, not read sentences: 4 short scripts from Claude (one with 3 people, three with 2 people), with Armenian and English references;
  - some recordings go through a real call and come from the monitor source (call-path audio);
  - the 3-person script also serves the C5 speaker eval.
- **Revisit when:** the C7 live test shows much more errors than the eval recordings.

## D-020. Capture library and virtual devices

- **Status:** ACCEPTED (2026-10-24)
- **Context:** C1 research, `RESEARCH.md` §6.
- **Options:** A. `soundcard` first, `sounddevice` second; B. `sounddevice` first, `soundcard` second.
- **Claude's preference:** A. `soundcard` uses the PulseAudio API (its README shows "Driver: PipeWire") and has a documented `include_loopback` option. Weak points: no source shows two devices with one clock for either library; the monitor source name of a null sink is [UNVERIFIED]. Test that can show it is wrong: the C4 two-device test shows drift or lost audio.
- **Decision:** A. Sim tests use `pactl load-module module-null-sink` (built into pipewire-pulse). A script plays audio into the sink, and the program captures from its monitor source.
- **Reason (Aren's words):** "Agree".
- **Revisit when:** the C4 two-device test fails with `soundcard`.

## D-021. Packages for the GPU and the audio server: the dependency group `laptop`

- **Status:** ACCEPTED (2026-10-25)
- **Context:** CI runs `uv sync --locked`, which installs all default dependency groups. The C2 packages add 167 packages and 4.04 GB of wheels on the laptop platform (Linux x86-64, Python 3.12) [RUN]. `setup-uv` v10.3.2 has the cache on by default on GitHub runners, with no pruning [SOURCE: setup-uv `action.yml`, `docs/caching.md`]. The cache key changes when `uv.lock` or `pyproject.toml` changes [SOURCE]. The GitHub cache gives 10 GB for each repository and removes an entry after 7 days with no use [SOURCE: GitHub changelog 2025-11-20]. `import soundcard` fails with an `AssertionError` when no PulseAudio server runs [RUN].
- **Options:**
  - **1.** A dependency group in `default-groups`. CI runs `uv sync --locked --no-group <group>`. Weak points: unit tests must not import the group packages; groups are local only, so `pip install .` gives a program with no models [SOURCE: uv docs]; CI does not check that the group installs.
  - **2.** Main dependencies, with the cache as it is now. Weak points: 4 GB from PyPI after each change of `uv.lock` or `pyproject.toml`; some GB from the cache on each other push; two cache keys use most of the 10 GB.
  - **3.** An extra (`[project.optional-dependencies]`). Weak point: uv does not sync extras by default [SOURCE: uv docs], so each `uv sync` on the laptop and at the interview needs `--extra`.
- **Claude's preference:** 1. [RUN] A CI-style sync with no group installs 7 packages (32 MB cache). Test that can show it is wrong: a C2 unit test that cannot run without a group package.
- **Decision:** 1.
  - The group name is `laptop`, because the group also has `soundcard`, which is not a model. `default-groups = ["dev", "laptop"]`, so a plain `uv sync` on the laptop installs all packages.
  - CI runs `uv sync --locked --no-group laptop`. Each later CI step runs `uv run --no-sync`, because a plain `uv run` installs the default groups again [RUN].
  - Only the adapter modules import the `laptop` packages. Unit tests use fakes that follow the module contracts. A unit test checks that the core modules do not import the `laptop` packages.
- **Reason (Aren's words):** "I see that option 1 is the most appropriate".
- **Questions raised:**
  - Aren: does each push need downloads, or can they happen only at the first push? Claude: with option 2, yes. The cache only makes the PyPI download less frequent: a new key after each change of `uv.lock` or `pyproject.toml`, a removal after 7 days with no use, and a download of the cache itself on each push.
  - Aren: "can we have normal tests without importing the model dependencies?" Claude: yes. The core logic (segments, latency arithmetic, line format, pipeline order) has no model import. Unit tests give it fakes in place of the models and the audio device. Model tests and sim tests on the laptop use the real packages.
- **Revisit when:** a unit test needs a `laptop` package, or CI must check the model install.

## D-022. Warm-up run at startup

- **Status:** ACCEPTED (2026-10-25), option A
- **Context:** The first call of a GPU model can take longer than the next calls. A slow first line can break K1.
- **Facts (T-INSTALL-02, T-INSTALL-03, Aren's laptop, 2026-10-25) [RUN]:**
  - ASR (NeMo, GPU): call 1 0.458 s; the next calls 0.027–0.036 s, also for new lengths (2.78–12.17 s of audio).
  - MT (CTranslate2, float16, GPU): call 1 5.104 s; the next calls 0.066–0.132 s, also for new lengths (25–52 tokens).
  - With no warm-up, the first line needs about 0.5 + 0.46 + 5.1 = 6.1 s (calc), which is more than the 5 s of K1.
- **Options:**
  - **A.** A warm-up run of each model at startup, with a synthetic input (no audio file in git, R11).
  - **B.** No warm-up run.
- **Claude's preference:** A, with one warm-up call for each GPU model. Weak points: the start takes about 6 s longer; the install check used a real clip and a real text as call 1, but the program must use a synthetic warm-up input (no audio file in git, R11), which is not tested yet. Test that can show it is wrong: in the end-to-end model test, the first line after the warm-up is slower than the next lines.
- **Decision:** A. One warm-up call for each GPU model at startup: ASR with 2 s of zeros, MT with a fixed Armenian sentence (`ARCHITECTURE.md` §5).
- **Reason (Aren's words):** "the longer start is fine, but we need to be careful with the other lengths part. Let's test it first to see if we need it or not". After the numbers: "Accept option A".
- **Revisit when:** the end-to-end model test shows a slow first line after the warm-up.

## D-023. Latency definition (K1)

- **Status:** ACCEPTED (2026-10-25)
- **Context:** K1: maximum 5 s from the end of a spoken phrase to its English line. The program needs one measured definition (PLAN C2).
- **Options:**
  - **A.** From the true end of speech: the start of the first silent VAD frame after the speech.
  - **B.** From the VAD end event, which comes after the minimum silence.
- **Claude's preference:** A (C1). Weak points: the minimum silence counts against the 5 s; the VAD frame gives a resolution of 32 ms; the true end is the VAD estimate, not an end that a person marks by hand. Test that can show it is wrong: on some C3 recordings, the VAD end and a hand-marked end differ by more than one frame.
- **Decision:** A. The latency of a line is the print time minus the start of the first silent VAD frame after the speech.
- **Reason (Aren's words):** "We agreed on the true end of the speech". After the D-027 answer: "Ok let's agree on 500ms on minimum silence initially" (Claude read this answer as the confirmation of D-023 too).
- **Questions raised:** Aren: the minimum silence can give a longer perceived latency (D-027). Claude: definition A does not add a delay. It shows the silence wait in the number; definition B hides it.
- **Revisit when:** D-027 changes the end rule.

## D-024. Line format with the latency of each step

- **Status:** ACCEPTED (2026-10-25), option B
- **Context:** F5 (time, speaker, Armenian text, English text) and PLAN C2: how the program shows the measured latency of each line.
- **Options:**
  - **A.** Aren's format: the format of the brief, with one more line for the latency of each step and the total.
  - **B.** Format A with three changes from Claude: a defined time, a simpler latency line, and two decimals.
- **Claude's preference:** B. The steps add up to the total and include the queue waits: `vad` (true end to segment closed), `asr`, `mt`, `out`; `spk` comes in C5 on the system side only. Weak point: long lines on the screen at the interview. Test that can show it is wrong: in the C2 live run, Aren cannot read the lines at the speed of speech.
- **Decision:** B. Each segment gives one block, printed with one call, so that the lines of two sources do not mix:

  ```
  [00:01:12] Me
   HY: Լավ եմ, շնորհակալություն։
   EN: I'm fine, thank you.
   [Latency: vad 0.53s, asr 0.41s, mt 0.18s, out 0.00s | Total 1.12s]
  ```

  - The time is the start of the segment, as time since the program start (`hh:mm:ss`).
  - The steps add up to the total and include the queue waits. Two decimals.
  - `spk` comes in C5, for the system side only.
- **Reason (Aren's words):** "Each line must show the latency for each step (VAD, stt, mt, diarization...)". "Agree on option B for D-024". On the format: "follows the one provided in the original document with my addition of the latency output".
- **Revisit when:** the C7 live test.

## D-025. WAV file source only for tests and eval

- **Status:** ACCEPTED (2026-10-25)
- **Context:** PLAN C2: model tests and the end-to-end test feed a WAV file through the pipeline at real-time speed. Tip T8 warns about extra features.
- **Decision:** The WAV file source exists only for tests and eval. The command-line program has no flag for it. The tests make the pipeline with the WAV source in code.
- **Reason (Aren's words):** "Yes, WAV files are only for test purposes. Production only needs live input".
- **Revisit when:** never for the MVP.

## D-026. VAD parameters (all except the minimum silence)

- **Status:** ACCEPTED (2026-10-25)
- **Context:** D-018. Facts from the Silero VAD 6.2.3 source [SOURCE: `utils_vad.py`, `model.py`]:
  - The model accepts only frames of 512 samples (32 ms) at 16 kHz.
  - `VADIterator` defaults: threshold 0.5, minimum silence 100 ms, pad 30 ms. The end threshold is the threshold minus 0.15, fixed in the code.
  - `VADIterator` has no minimum and no maximum segment length. Only the offline function `get_speech_timestamps` has them (defaults 250 ms and no limit).
  - `silero_vad` calls `torch.set_num_threads(1)` at import, for the full process.
- **Decision (parameters, R10, approved 2026-10-25):**

  | Name | Value | Reason |
  |---|---|---|
  | `vad_threshold` | 0.5 | Silero: "'lazy' 0.5 is pretty good for most datasets". C3 tunes it. |
  | `vad_end_threshold` | 0.35 | The Silero rule (threshold − 0.15): a short drop below 0.5 does not end the speech. |
  | `vad_speech_pad_ms` | 30 | Silero default. The pad is shorter than the minimum silence, so it adds no latency. |
  | `vad_min_speech_ms` | 250 | Silero default. It removes clicks and coughs before ASR. |
  | `vad_max_speech_s` | 10 | With no limit, a long speech with no pause gives no line until its end. Hard cut at 10 s. |

- **Claude's weak points (given before the approval):** 250 ms can remove a short "ոչ" or "հա"; 10 s has no source (6 s and 15 s were the alternatives); the hard cut can split a word.
- **Reason (Aren's words):** "As for the other parameters for the vad, I agree".
- **Revisit when:** C3 numbers show removed short words or split words.

## D-027. End-of-segment rule (minimum silence)

- **Status:** ACCEPTED (2026-10-25), option A
- **Context:** The VAD must decide that a phrase ended. Silence is the only signal that a VAD has. Aren: a long minimum silence can give a longer perceived latency and worse speaker labels; a short one can lose short responses.
- **Facts:**
  - Pauses under 200 ms are "brief". In read speech of 5 languages, the "medium" pauses (200–1000 ms) have a peak at 500–600 ms. Long pauses (> 1 s) occur only in spontaneous speech [SOURCE: Campione & Véronis 2002].
  - In 10 languages, the mean gap between turns of each language is within 250 ms of the cross-language mean [SOURCE: Stivers et al. 2009].
  - Kaldi online endpoint defaults: 0.5 s of silence only when the decoder is in a final state with a good score; 1.0 s and 2.0 s for weaker cases; 20 s maximum length [SOURCE: `online-endpoint.h`].
  - sherpa-onnx endpoint defaults: 1.2 s of silence after some decoded text; 2.4 s with no text; 20 s maximum length [SOURCE: `endpoint.h`].
  - The minimum silence does not remove segments; `vad_min_speech_ms` does. But a shorter silence splits more, and a short word at the start of a phrase can become a segment under 250 ms (Aren's point).
- **Options:**
  - **A.** One fixed minimum silence.
  - **B.** Two values by segment length: a short segment needs a longer silence; a long segment ends at a shorter silence.
  - **C.** ASR-informed end: at a short silence, ASR reads the open segment; a sentence-end mark ends it, or else the program waits for a longer silence (similar to Kaldi rule 2).
  - **D.** A speaker-change split inside a segment (C5).
  - **E.** One fixed short value (250–300 ms).
- **Claude's preference:** A in C2, with the value from the T-INSTALL-04 pause numbers (500 ms if they show nothing different). The end rule is in our own code with unit tests, so a change to B, C, or D is small. C3 measures A and B; C5 measures the speaker purity of the segments. Weak point: C3 can change the C2 value.
- **Decision:** A. New parameter `vad_min_silence_ms = 500` (approved 2026-10-25, R10). It is a start value. T-INSTALL-04, C3, and C5 can change it, or change the rule to B, C, or D.
- **Reason (Aren's words):** "Ok let's agree on 500ms on minimum silence initially but it will be open for further testing and enhancement".
- **Revisit when:** T-INSTALL-04, C3, and C5 numbers.

## D-028. Declare each package that our code imports

- **Status:** ACCEPTED (2026-10-25)
- **Context:** The model tests import `numpy` and `huggingface_hub`. Other packages pull them in already (`nemo-toolkit`, `transformers`). The core modules need `numpy` for the audio arrays, also in CI.
- **Options:**
  - **A.** Declare each package that our code imports: `numpy` as a main dependency (CI installs it), `huggingface-hub` in the `laptop` group.
  - **B.** Use the packages that other packages pull in, with no declaration.
- **Claude's preference:** A. With B, an update of NeMo or Transformers can remove a package that our code needs, with no change in our `pyproject.toml`. Weak point: a longer dependency list. [RUN] The lock keeps the same 177 packages and the same versions (`numpy` 2.5.4, `huggingface-hub` 2.3.0). Test that can show it is wrong: none known.
- **Decision:** A.
- **Reason (Aren's words):** "D028. Accept".
- **Revisit when:** —

## D-029. Threads and the segment queue

- **Status:** ACCEPTED (2026-10-25), option A
- **Context:** `ARCHITECTURE.md` §4. One capture thread for each source; one worker thread does ASR, then MT, then the output. The worker uses the GPU, so the models run one at a time. PLAN C2 asks what happens when a queue is full.
- **Options:**
  - **A.** A queue with no size limit. A slow worker shows as a larger `asr` step on each line (D-024).
  - **B.** A queue with a size limit. When it is full, the program stops with an error.
  - **C.** A queue with a size limit. When it is full, the oldest segment is removed. (Silent data loss, against R10.)
- **Claude's preference:** A. [RUN] ASR + MT need about 0.1–0.17 s for each segment after the warm-up, and each segment has at least 0.25 s of speech plus 0.5 s of silence. Weak point: with an overload, the latency and the memory grow with no limit, and the program does not stop. Test that can show it is wrong: in the live run or in C7, the `asr` step grows from line to line.
- **Decision:** A. One capture thread for each source, one worker thread, and a segment queue with no size limit.
- **Reason (Aren's words):** "D29. A" (after the more context above).
- **More context (2026-10-25, Aren asked for it):**
  - The capture thread puts each closed segment in the queue. The worker takes the segments one at a time. The queue holds the segments that wait.
  - The queue fills only when the worker is slower than the speech. [RUN] The worker needs 0.10–0.17 s for each segment (ASR 0.03 s + MT 0.07–0.13 s). A new segment comes at most once in 0.76 s (0.25 s of speech + 0.51 s of silence) (calc). Thus the worker is about 4–7 times faster than the fastest speech. With two sources (C4), it is about 2–3 times faster (calc).
  - Possible causes of an overload: a hot GPU that runs slower, another program on the GPU, or the C5 speaker model on the same worker [UNVERIFIED].
  - At the interview, A gives late lines but loses none; B stops the program; C loses lines with no message.
  - Memory: a 10 s segment is 640 KB, so 100 segments in the queue use 64 MB (calc).
- **Revisit when:** C4 (two sources on one worker) or C5 (a speaker model on the same worker).

## D-030. CUDA 12 cuBLAS for CTranslate2

- **Status:** ACCEPTED (2026-10-25), option A
- **Context:** The CTranslate2 4.8.3 wheels need the CUDA 12 cuBLAS. The install check used `LD_LIBRARY_PATH` [RUN]. The package `nvidia-cublas-cu12` puts `libcublas.so.12` and `libcublasLt.so.12` in `nvidia/cublas/lib/` [RUN].
- **Options:**
  - **A.** The `mt` adapter loads `libcublasLt.so.12` and `libcublas.so.12` from the package `nvidia-cublas-cu12` (with `ctypes`, `RTLD_GLOBAL`) before `import ctranslate2`. The file paths come from `importlib.metadata`. A missing file stops the program with an error.
  - **B.** The user sets `LD_LIBRARY_PATH` before the start (README, or a launcher script).
- **Claude's preference:** A. `uv run tir-asr` then works with no extra step, also at the interview. Weak points: a preload is less common; it depends on the file names in the package; it is [UNVERIFIED] that CTranslate2 then uses the loaded library. Test that can show it is wrong: the MT model test with no `LD_LIBRARY_PATH` fails to run CTranslate2 on `cuda`.
- **Decision:** A.
- **Reason (Aren's words):** "agree on D30".
- **Revisit when:** a new CTranslate2 version uses CUDA 13.

## D-031. Empty ASR text

- **Status:** ACCEPTED (2026-10-25)
- **Context:** A VAD segment can contain no words (a cough, a noise). Then the ASR text is empty, and MT has no input.
- **Options:**
  - **A.** Print a short block with no MT: the time, the label, `HY: (no text)`, and the latency line with `vad` and `asr` only.
  - **B.** Print no block. The shutdown line counts the empty texts.
- **Claude's preference:** A in C2, because each segment with no words is then visible, which helps to tune the VAD. The shutdown line also counts them. Weak point: noise blocks on the screen at the interview. Test that can show it is wrong: in the live run, many `(no text)` blocks make the screen hard to read.
- **Decision:** A now, for debugging. B for the delivery: C7 changes the code and its test, with no flag. (A flag for this would be a new configuration item that needs its own approval, R10.)
- **Reason (Aren's words):** "lets agree keeping the no text for now for debugging purposes but silencing it on production".
- **Revisit when:** C7 (live test).

## D-032. End of a test WAV clip

- **Status:** ACCEPTED (2026-10-25), option C (Aren)
- **Context:** Q-08. Clip 1 ends 150 ms after the speech, which is less than `vad_min_silence_ms`. Thus the last segment of a clip does not close.
- **Options:**
  - **A.** The test WAV source (D-025) adds 1.0 s of zeros after each clip. The `Endpointer` then closes the last segment as in live speech.
  - **B.** The `Endpointer` gets a `flush()` for the end of the input.
  - **C (Aren).** No added silence and no `flush()`. The test clips contain enough silence.
- **Claude's preference:** A, because the product then has no code that live input never uses (D-025). Weak points: digital zeros are not real room silence; 1.0 s is a test constant. Test that can show it is wrong: the end-to-end model test does not get one block for each clip.
- **Questions raised:** Claude (R14): clip 1 ends only 152 ms after its speech [RUN, T-INSTALL-04], so clip 1 alone gives no last block. Clip 2 ends 914 ms after its speech. If the test plays clip 1 and then clip 2, the gap is 152 + 480 = 632 ms, and both segments close (calc).
- **Decision:** C. The end-to-end test plays clip 1, then clip 2. A clip that ends with less than 512 ms of silence makes the test fail with a clear message, not a silent miss. The test WAV source gives only whole frames; it drops the last part of a clip that is shorter than one frame (32 ms).
- **Reason (Aren's words):** "D32 no need to pad since the clips do include silence".
- **Revisit when:** —

## D-033. Parameter `mt_beam_size`

- **Status:** ACCEPTED (2026-10-25)
- **Context:** CTranslate2 and Transformers need a beam size. R10: Aren approves each parameter.
- **Options:** 1 (greedy), 2 (the CTranslate2 default), 4.
- **Claude's preference:** 2. [RUN] Beam sizes 1 and 2 gave the same texts and the same times on 4 inputs (T-INSTALL-03). Weak point: no measured gain over 1. Test that can show it is wrong: in C3, beam size 1 gives the same chrF at a lower latency, or 4 gives a higher chrF within K1.
- **Decision:** new parameter `mt_beam_size = 2` (approved 2026-10-25, R10).
- **Reason (Aren's words):** "agree on D33".
- **Revisit when:** C3 numbers.

## D-034. Start, pause, and resume keys

- **Status:** ACCEPTED (2026-10-25): option A for the MVP
- **Context:** Aren: "listening begins after hitting a key and stops after hitting pause key with the option of resuming". The brief has no such feature (F1–F5), and its "Out of scope" list does not name it. R10 and tip T8: a feature that is not in the brief needs a decision.
- **Options:**
  - **A.** No keys. The program listens after the startup. Ctrl+C stops it (the brief).
  - **B.** A start key, and one key that pauses and resumes (Aren). During a pause, the capture thread drops the blocks, and the `Endpointer` drops its open segment. The screen shows "Paused" and "Listening".
  - **C.** A start key only. Ctrl+C stops the program.
- **Effect on performance (Aren's question):** no effect on the latency of a line is expected [UNVERIFIED]. A key thread waits on the terminal input and uses no CPU. After a long pause, the first segment can be slower if the GPU clocks down (Q-09). A long silence has the same effect.
- **Claude's preference:** A for the MVP (R2, T8), then B after M3 if the time allows. Weak points of B: more code and more tests (terminal raw mode, and Ctrl+C must still work); a rule for the open segment at a pause; the C5 speaker labels must stay the same across a pause; the time box (R16). Test that can show the preference is wrong: at the C7 rehearsal, the program shows lines of talk that nobody wanted (before the call starts, or during side talk).
- **Decision:** A for the MVP: no keys; Ctrl+C stops the program. We decide on option B after M3.
- **Reason (Aren's words):** "Leave decision for the keys after M3. you are right. it is not MVP".
- **Revisit when:** M3 is done (after C5).

## D-035. Chats for the C2 code: module groups

- **Status:** ACCEPTED (2026-10-25), option A
- **Context:** R3 (tip T3): "Develop and test one module in its own chat". `PLAN.md` v0.7 had all six skeleton modules in one chat (C2). Aren asked if each component gets its own chat.
- **Options:**
  - **A.** Three chats for module groups: C2b `types` + `segment`; C2c `asr` + `mt` adapters; C2d `audio` + `output` + `pipeline` + `cli` (M1). One git branch for each chat; Aren merges it into `main` when its tests pass.
  - **B.** One chat for all the skeleton code. Weak points: a long chat (T6, R4); it does not follow R3.
  - **C.** One chat for each module (7 chats). Weak point: too much overhead for the time budget (R16).
- **Claude's preference:** A. Each group has one clear contract part, and its tests can pass alone. Weak points: three handovers (about 10 min each); problems between the modules show only in C2d. Test that can show it is wrong: C2d finds a contract error between two modules, and the split costs more time than it saves.
- **Decision:** A. C2 ends after the install check, the contracts, and the test design. Inside each chat, each component has its own branch and its own tests (R3): C2b `c2b-segment`; C2c `c2c-asr`, `c2c-mt`; C2d `c2d-output`, `c2d-audio`, `c2d-pipeline`, `c2d-cli` (`PLAN.md` §5.2). Aren merges a branch into `main` only when its tests pass on their own and CI is green.
- **Reason (Aren's words):** "Agree on A". Then: "while I agreed on A for D35. We still will need separate branch and tests for each separate component (as R3 suggests)".
- **Revisit when:** C2d.


## D-036. Interface of the `segment` module (C2b)

- **Status:** ACCEPTED (2026-10-25), option A for each of the five parts
- **Context:** `ARCHITECTURE.md` v0.3 left five details open. We found them when we wrote the tests of C2b. Each detail changes how the other modules (C2d) use `segment`.
- **Parts, options, and Claude's preference** (A in each part):
  1. **Parameters in the code.**
     - **A.** A frozen dataclass `Params` in `config.py`. The §6 values are the defaults. `Endpointer(params, vad)` gets it. Tests make variants with `dataclasses.replace`.
     - **B.** Module constants. Tests use `monkeypatch`; the startup log needs a separate list of the parameter names.
     - Weak point of A: code can build a `Params` with other values. Only tests do this. T-CFG-01 compares `asdict(Params())` with the §6 table, so a new field without Aren's approval makes the test fail (R10). Test that can show A wrong: C2d finds that `cli.py` needs another shape for T-CFG-02.
  2. **Count of the short segments (rule 4).** `push` returns nothing for a segment under `vad_min_speech_ms`, so the pipeline cannot count it.
     - **A.** A public integer attribute `Endpointer.short_segments`.
     - **B.** `push` returns an event type (a segment or a "dropped" mark). Every caller must handle the new type.
     - Weak point of A: a mutable public attribute. The capture thread writes it, and the main thread reads it at shutdown (one integer, so the read is safe in CPython). Test that can show A wrong: T-PIPE-04 in C2d.
  3. **Who calls the VAD.**
     - **A.** `push(block)` calls `vad(block.samples)`. The `segment` module takes an `AudioBlock` and gives a `Segment` (§2 table).
     - **B.** `push(block, probability)`. The capture thread calls the VAD.
     - Weak point of A: the time of `push` includes the VAD time. [RUN] 0.19 ms for each frame on the CPU (T-MODEL-VAD-01). The Silero model keeps its state between calls, so C4 needs one adapter instance for each audio source. Test that can show A wrong: C4 or C5 needs the probabilities for another purpose.
  4. **Lengths.**
     - **A.** The silence, the minimum speech, and the maximum speech are counted in whole frames (audio time).
     - **B.** They come from the differences of the arrival times.
     - Weak point of A: a long silence in audio time and in arrival time can differ when blocks arrive late. `start`, `speech_end`, and `closed` still come from the arrival times, so the latency steps show the real delay. Test that can show A wrong: the C4 drift test finds a difference that changes a segment.
  5. **Place of `SegmentError`.**
     - **A.** In `segment/endpoint.py`. Each module has its own error class.
     - **B.** A shared `errors.py` with a base class.
     - Weak point of A: the pipeline cannot catch all module errors with one class. The pipeline stops on any exception (§2.6), so it needs no common class now. Test that can show A wrong: C2d needs a common class.
- **Decision:** A in all five parts. `ARCHITECTURE.md` v0.4 has the changes (§2.2, §4, §5).
- **Reason (Aren's words):** "Agree on your proposals" (parts 1 and 2). "Agree on the three details" (parts 3, 4, and 5).
- **Questions raised:** Claude asked Aren to decide parts 1 and 2 (the contract gap was clear). Claude put parts 3 to 5 in the report with the code, because the tests needed a choice.
- **Revisit when:** C2d (pipeline and CLI) and C4 (two sources).

## D-037. Interface of the `asr` and `mt` adapters (C2c)

- **Status:** ACCEPTED (2026-10-25), option A in parts 1 to 3
- **Context:** `ARCHITECTURE.md` §2.3 and §2.4 did not give the class names, the constructor, or the place of the warm-up call. The C2c tests need them.
- **Parts, options, and Claude's preference** (A in each part):
  1. **Class names.**
     - **A.** `NemoRnntTranscriber` and `Ct2NllbTranslator`, in the style of `SileroSpeechProbability`.
     - **B.** `Transcriber` and `Translator`, as §2.3 and §2.4 said. These are also the names of the Protocols in `types.py`.
     - Weak point of A: §2.3 and §2.4 need a correction. Fact that can show A wrong: none known.
  2. **Constructor.**
     - **A.** The constructor loads the model: `NemoRnntTranscriber(repo, filename)` and `Ct2NllbTranslator(params, model_dir)`. The defaults are module constants. The error tests give a wrong name. `Ct2NllbTranslator` reads `mt_compute_type` and `mt_beam_size` from `Params`.
     - **B.** Module constants only. The tests use `monkeypatch`.
     - Weak point of A: `repo`, `filename`, and `model_dir` look like parameters (R10). They are model locations, not tunable values. They are not in the §6 table and not in the startup log. Fact that can show A wrong: Aren wants them in §6.
  3. **Warm-up.**
     - **A.** The adapters have no warm-up method. The caller calls `transcribe` with 2 s of zeros and `translate` with `WARMUP_TEXT`, and measures the time. T-MODEL-ASR-01 and T-MODEL-MT-01 do the same.
     - **B.** The constructor does the warm-up.
     - Weak point of A: a caller can forget the warm-up. Fact that can show A wrong: T-E2E-01 shows a slow first line.
  4. **Constants** (information, no choice): branch `c2c-asr` adds `WARMUP_AUDIO_S` to `config.py`; branch `c2c-mt` adds `WARMUP_TEXT`, `MT_SRC_LANG`, and `MT_TGT_LANG`. No new tunable parameter.
- **Decision:** A in parts 1 to 3; part 4 as given. Aren added to part 3: the pipeline makes the warm-up call, and `cli.py` is only the `argparse` interface. `ARCHITECTURE.md` v0.5 has the changes (§2.3, §2.4, §2.6, §2.7).
- **Reason (Aren's words):** "I agree on Part1 and Part2". "No need for warmup in the constructor. Warm-up is something that will be called on the application bootstrap (the pipeline)". "Agree on Part4". "put warm-up call on pipeline. cli is only interface for argparse".
- **Questions raised:** Claude: §2.7 of v0.4 put the warm-up call in `cli.py`, and C2d could select `cli.py` or `pipeline.py`. Aren selected `pipeline.py`. The other startup steps of §2.7 (versions, CUDA check, model load, microphone) move out of `cli.py` too; C2d gives the details to Aren for review.
- **Revisit when:** C2d (pipeline and CLI).

## D-038. Test runs in C2c: on Aren's laptop only

- **Status:** ACCEPTED (2026-10-25), option A, for C2c only
- **Context:** D-006 (detail Q13): Claude runs `ruff` and the unit tests on a copy in the workspace before Claude asks Aren. Aren asked if C2c can skip this to save time. The C2c model tests run only on Aren's laptop in any case, because the workspace has no GPU.
- **Options:**
  - **A.** No workspace copy in C2c. Aren runs `ruff` and the unit tests on the laptop, with the commands that Claude gives.
  - **B.** Keep the D-006 detail: a workspace copy and a workspace run before each request to Aren.
- **Claude's preference:** A, for C2c. Weak points: a `ruff` error or a CI-only error reaches Aren or CI first, and costs one extra round trip; the CI-style check without the `laptop` group runs only in CI. Fact that can show A wrong: a CI failure that a workspace run would have found.
- **Decision:** A, for C2c only. Claude still runs `ruff` on the changed files only, in a scratch folder (no `uv` environment and no unit tests).
- **Reason (Aren's words):** "Should we only run the tests on my end to save time? I know the decision on D6 but if this saves time then we do it like that." Then: "confirm D38".
- **Questions raised:**
  - Claude (R14) named the main risk one time (the weak points above).
  - [RUN] The `ruff` cache can hide an import-sort error. The sort of an import of `tir_asr.<module>` depends on whether the module exists, and the cache does not see that change. The C2c commands use `--no-cache`. CI has no `ruff` cache.
- **Revisit when:** C2d starts (Aren decides again), or CI finds an error that a workspace run would have found.

## D-039. Smaller commits and the full git commands

- **Status:** ACCEPTED (2026-10-25)
- **Context:** The `c2c-asr` commit had the adapter, its tests, and three documents in one commit. Aren asked for smaller commits and for the full commands.
- **Decision:** Aren's rule, now in `RULES.md` v0.5, R12:
  - No bulk commits: one commit holds one logical change.
  - Claude gives the full command for each commit: `git add` with each file, `git commit -m` with the message, and `git push`.
  - A commit message has no co-author line.
- **Reason (Aren's words):** "add a rule that from now on we dont do this bulk commits and do smaller ones, and you give me the whole git add and push command with the message, and the message does not contain your co-authoring part".
- **Questions raised:** Claude: R13 puts an `ARCHITECTURE.md` change into the same commit as its code. The new rule keeps this: the code and its architecture text are one logical change. Decision entries and test results can go into separate commits.
- **Revisit when:** the number of commits costs too much of the time budget (R16).

## D-040. Interface of the `output` module (C2d)

- **Status:** ACCEPTED (2026-10-25)
- **Context:** `ARCHITECTURE.md` §2.5 did not give the function signatures, the cut or the rounding of the block time, the end of a block, or a test for the one write of each block (D-024). The tests of `c2d-output` need them.
- **Parts, options, and Claude's preference** (A in each part):
  1. **Signature.**
     - **A.** `format_block(line, session_start) -> str`. The block time is `Line.start` minus the session start (§2.5), and `Line` has no field for the session start.
     - **B.** A new `Line` field for the session start. Weak point: a change to `types.py` and one more value in each `Line`.
     - Weak point of A: each caller must give the session start.
  2. **Block time.**
     - **A.** Cut the seconds: 3671.9 s gives `[01:01:11]`.
     - **B.** Round the seconds: 3671.9 s gives `[01:01:12]`.
     - Weak point of A: the shown time can be up to 0.99 s before the true start. With B, the shown time can be after the start of the speech.
  3. **End of a block.**
     - **A.** One `\n` at the end, and no blank line between the blocks (the D-024 sample).
     - **B (Aren).** A blank line after each block. The blank line is part of the one write, so that the lines of two sources do not mix (C4).
     - Weak point of B: one more line on the screen for each block.
  4. **Total of an empty-text block** (information, no choice): the total goes from `speech_end` to the write, as in a normal block (D-023). Thus it includes the time after the ASR end, which no printed step shows.
  5. **Write.** A new test T-OUT-04: `write_block(line, session_start, stream)` makes one `write` call with the full block, then one `flush` call (D-024). No approved test covered the one write.
- **Decision:** A in parts 1 and 2; B in part 3 (Aren); part 4 as given; T-OUT-04 approved. `ARCHITECTURE.md` §2.5 gets the changes in the same commit as `output.py` (R13).
- **Reason (Aren's words):** "agree" (parts 1, 2, and 4). "add lines between blocks" (part 3). "approve the test" (part 5).
- **Revisit when:** C4 (two sources write to one terminal) or the C7 live test (the screen at the speed of speech).

## D-041. Microphone adapter test and audio contract (C2d)

- **Status:** ACCEPTED (2026-10-26), parts 1 to 5
- **Context:** T-AUDIO-01 had two options (`TESTS.md` §2.4). The probes in `scripts/probe_audio.py` measured a null sink, its monitor, and the default microphone on Aren's laptop (`TESTS.md`, "C2d audio probes"). Facts from `soundcard` 0.4.6 (`pulseaudio.py`) [SOURCE]:
  - `record(512)` returns an array of shape (512, 1), float32.
  - `default_microphone()` reads the default source of the server.
  - `get_microphone(id)` tries the exact id, then a part of the name, then a regex match. Thus a wrong id can select a different device with no error (against R10).
  - `record()` waits with no time limit. It raises `RuntimeError` only when the stream is in the FAILED state.
- **Parts, options, and Claude's preference:**
  1. **Test level.**
     - **A.** Live: the adapter reads 50 blocks from the default microphone.
     - **B (Aren).** Sim: a tone plays into a null sink (D-020), and the adapter captures its monitor. This moves a part of the C4 work forward.
     - Claude's preference: A, because it is the thinnest step for M1 (R2). Weak point of A: the test cannot see wrong content (a wrong scale or a wrong sample order) before C4.
  2. **How the test reaches the monitor.**
     - **a.** The test sets the monitor as the default source, then sets the old default back. Weak point: the session manager can store the default, so a crash during the test can leave the default changed [UNVERIFIED].
     - **b.** The adapter constructor gets an optional exact device id. With no id, it uses the default microphone.
     - Claude's preference: b. It does not change the system defaults, and C4 needs a device id for F1. Weak point: the sim test does not cover the default-microphone line; L-01 covers it. Fact that can show b is wrong: C4 needs a different selection method.
  3. **T-AUDIO-01 limits** (from the probe B numbers): blocks of (512,) float32; arrival times that increase; span ÷ (n − 1) = 32 ms ± 0.5 ms (probe B: +0.055 ms); no gap over 64 ms (probe B: 43.3 ms); a silent phase of zeros; a tone of 440 ± 1 Hz with RMS 0.1768 ± 10 % and no holes. Weak point: the RMS limit needs the sink volume and the stream volume at 100 %.
  4. **Samples outside [−1, 1].** The default microphone gave 22 samples outside [−1, 1] (min −1.0496). The source volume is 24 % (−36.85 dB), so the cause is not a volume over 100 % [RUN]. A possible cause is a full-scale input and the 48 → 16 kHz conversion [UNVERIFIED] (Q-11).
     - **A.** The adapter clips the samples to [−1, 1] and counts them. The shutdown line shows the count.
     - **B.** The adapter does not change the samples. The contract changes to: "normally in [−1, 1]; a loud input can give values a little outside".
     - Claude's preference: B for the MVP. It needs no code, and Silero VAD and NeMo take float input [UNVERIFIED for values outside [−1, 1]]. Weak point: a later module that needs [−1, 1] can fail. Fact that can show B is wrong: loud segments give ASR errors in C3.
  5. **Adapter interface** (Claude's proposal, the same style as the other adapters, D-037):
     1. `SoundcardMicrophone(device=None)` in `audio/soundcard_mic.py`. `AudioError` is in the same file.
     2. The constructor imports `soundcard` and selects the source, so that the errors come at startup. With a `device` id, it checks for an exact id among all sources, monitors included; a missing id gives `audio: no source with the exact id <id>`. The import is in the constructor, because `soundcard` connects to the server at import and, with no server, fails with a bare `AssertionError`. Weak point: the other adapters import at the top of the file.
     3. `blocks()` opens the stream, not the constructor. The stream keeps all audio from the moment it opens, with no limit; a stream that opened at startup would give the audio of the warm-up time later, in a burst, before "Listening". Weak point: a stream error comes after "Listening", not at startup.
     4. Each block has the label "Me" (C2). C4 changes the label for the system source.
     5. A (512, 1) array becomes (512,). Any other shape gives `audio: block has <n> samples, expected 512`.
     6. A `RuntimeError` from `soundcard` becomes `audio: recording failed: <cause>`.
     7. The attribute `name` gives the device name for the startup log (§2.7, step 5).
     8. T-IMPORT-01: `tir_asr.audio` (the package file) goes into `REQUIRED`.
- **Decision:** B in part 1 (Aren); b in part 2; the limits of part 3; B in part 4; points 1 to 8 of part 5. T-AUDIO-02 and T-AUDIO-03 are approved. `ARCHITECTURE.md` §2.1 and §3 get the changes in the same commit as the adapter (R13).
- **Reason (Aren's words):** "no let's simulate but we have to be careful and do it step-by-step and deliberate on it so we are sure it runs right" (part 1). "agree on your preferences" (parts 2 to 4). "I approve the tests and confirm your points" (part 5).
- **Revisit when:** C4 (device flags and two sources) or C3 (Q-11).

## D-042. Pipeline, startup, and stop (C2d)

- **Status:** ACCEPTED (2026-10-26)
- **Context:** `cli.py` is only the `argparse` interface, and the pipeline makes the warm-up calls (D-037). The six startup steps of `ARCHITECTURE.md` §2.7 need a new place. The pipeline is core: the unit tests give it fakes, so it cannot import the adapters (D-021). T-PIPE-02 and T-PIPE-04 check exit codes, and their owner was open.
- **Points, options, and Claude's preference:**
  1. **Who loads the adapters and prints the startup log.**
     - **A.** A new module `app.py`: it loads the adapters, prints the startup log, and calls the pipeline. `cli.main()` parses the arguments, then imports `app` (after the parse, so that `--help` imports nothing, T-CLI-01). `app.py` is in `ADAPTERS` of T-IMPORT-01.
     - **B.** `cli.py` loads the adapters. Weak point: against D-037.
     - **C.** `pipeline.py` loads the adapters with imports inside a function. Weak point: a core module hides `laptop` imports, and no unit test covers that part.
     - Claude's preference: A. Weak point: one more module than `PLAN.md` §4, with no unit test (T-E2E-01 and L-01 cover it).
     - The startup steps: (1) versions, GPU name, and parameters in `app.py`; the versions come from `importlib.metadata`, and the parameter lines from a core function `parameter_lines(params)` (T-CFG-02). (2) The CUDA check stays in the ASR constructor (T-MODEL-ERR-03), with no second check. (3) `app.py` loads MT first (cuBLAS preload, D-030), then ASR and VAD, and prints each load time and the VRAM. (4) `pipeline.warm_up()`; `app.py` prints the times. (5) `app.py` builds `SoundcardMicrophone()` and prints its name; the stream opens later (D-041). (6) `pipeline.run()` prints "Listening".
  2. **Owner of the exit codes.**
     - **A.** `run()` returns 0 or 1 and writes the error line. `cli` calls `sys.exit` with that value. T-PIPE-02 and T-PIPE-04 stay whole in `c2d-pipeline`.
     - **B.** `run()` raises the error; `cli` prints it and exits. The exit-code parts of the tests move to `c2d-cli`.
     - Claude's preference: A. Weak point: the core knows the program name.
  3. **Stop.**
     - Ctrl+C: the main thread prints the shutdown line and returns 0. The open segment and the segments in the queue are not processed; the shutdown line gives their number ("not processed").
     - End of the source (tests and the WAV source only, D-025): the capture thread puts an end mark in the queue. The worker finishes the segments in the queue, then the main thread prints the shutdown line and returns 0.
     - Shutdown line: `Stopped. Segments: <n>, short segments: <n>, empty texts: <n>, not processed: <n>.` "Segments" counts the blocks that the worker wrote.
     - Main risk (R14, named to Aren one time): a Ctrl+C right after the last phrase can lose that line. The Ctrl+C path has no unit test; L-02 covers it.
  4. **Warm-up.** `warm_up(transcriber, translator, clock)` is separate from `run()`, because T-PIPE-03 counts the MT calls. New test T-PIPE-05.
  5. **Session start.** `run()` takes the session start from the clock, prints "Listening. Press Ctrl+C to stop.", and only then starts the capture thread. The source opens its stream at its first block (D-041). Thus no block time is before the session start.
  6. **Error line.**
     - **A.** Check the module of the exception class. Weak point: the fake error of a unit test is not in a `tir_asr` module, so T-PIPE-02 cannot pass with its exact text.
     - **B.** A core module `errors.py` with a base class `TirError`. `AsrError`, `MtError`, `AudioError`, and `SegmentError` inherit from it (the revisit condition of D-036 part 5). A `TirError` gives `tir-asr: <message>`. Any other exception gives its traceback, then `tir-asr: <thread>: <type>: <message>`.
     - Claude's preference: B. Weak point: one line changes in each of four merged modules; their tests do not change.
  7. **Signature.** `run(source, vad, transcriber, translator, params, clock, out, err) -> int`. `run()` builds the `Endpointer` (§2.6). One capture thread and one worker thread (§4). The main thread waits on one event queue for "error" or "done".
- **Decision:** A in points 1 and 2; B in point 6; points 3, 4, 5, and 7 as proposed; T-PIPE-05 is new. The branch `c2d-pipeline` holds `errors.py`, `pipeline.py`, the four base-class lines, and T-PIPE-01 to T-PIPE-05. `app.py` and `parameter_lines` go to `c2d-cli`.
- **Reason (Aren's words):** "1. A is the best option", "2. A", "6. B", "continue" (points 3, 4, 5, 7, and T-PIPE-05). On the main risk of point 3: "accept point 3 risk".
- **Revisit when:** C4 (two capture threads on one worker), or L-02 shows lost lines at Ctrl+C.

## D-043. CLI, startup log, and the end-to-end test (C2d)

- **Status:** ACCEPTED (2026-10-26), points 1 to 6 and 2a
- **Context:** D-042 put the loading of the adapters and the startup log into a new module `app.py`, and `cli.py` is only the `argparse` interface (D-037). The branch `c2d-cli` needs the details, and T-CFG-02, T-CLI-01, and T-E2E-01 need exact texts.
- **Points and Claude's proposals:**
  1. **`cli.py`.** `main(argv=None) -> int` with `argparse` (`prog="tir-asr"`, no flags except `--help`). After the parse, it imports `app` and returns `app.main()`. `pyproject.toml` gets `[project.scripts] tir-asr = "tir_asr.cli:main"`. Weak point: after this change, `uv sync` must run one time, so that the command gets installed. It is [UNVERIFIED] that `uv.lock` does not change; if it must change, `uv sync --locked` in CI fails loudly.
  2. **Startup log (`app.py`).** Each line of the program starts with `startup: `, so that the lines are easy to find between the NeMo lines: the versions (from `importlib.metadata`), the GPU name, one line for each parameter (`parameter_lines`), each load time with the used GPU memory (`torch.cuda.mem_get_info()`, for the full device, so CTranslate2 is included), the warm-up times, and the microphone name. Then "Listening".
     - **2a (open).** Load order. Proposed first: MT first, for the cuBLAS preload. Claude found a conflict after Aren's answer: with MT first, a missing CUDA gives an error from CTranslate2 or torch, not the clean `asr: CUDA is not available` of §7 (point 4). The preload is inside the MT adapter, and it only needs to come before any `import ctranslate2`; no other module imports `ctranslate2`. [RUN] The model run of `c2d-pipeline` imported torch and NeMo before the MT adapter in one process, and T-MODEL-MT-01 passed with no `LD_LIBRARY_PATH`. New proposal: ASR first (with its CUDA check), then MT, then VAD; the GPU name after the ASR load; the used GPU memory after each load. Weak point: it differs from the handover advice "import the MT adapter first". Fact that can show it is wrong: T-E2E-01 fails at the MT load.
  3. **The about 185 NeMo load lines.**
     - **A.** Leave them for M1: no code, and nothing is hidden (R10). Decide again in C7, before the interview.
     - **B.** Set the NeMo log level to ERROR during the load. Weak point: it hides the warnings.
     - Claude's preference: A. Fact that can show it is wrong: in L-01, Aren cannot find the startup lines.
  4. **Errors and Ctrl+C during the startup.** A `TirError` gives `tir-asr: <message>` and exit code 1 (§7). Any other exception gives its traceback, then `tir-asr: startup: <type>: <message>` and exit code 1 (the rule of D-042 point 6). Ctrl+C before "Listening" gives `Stopped during the startup.` and exit code 0.
  5. **T-E2E-01.** A test WAV source in `tests/support/wav_source.py` (D-025) plays clip 1, then clip 2, at real-time speed. Each block gets its true `time.monotonic()` arrival, and the source drops a last part of a clip that is shorter than one frame (D-032). The test loads the models with the function of the program (`app.load_models`), so `app.py` gets coverage. Expected: 2 blocks in time order, label "Me", no `(no text)`, and each total < 5.0 s.
  6. **Unit tests.** T-CFG-02: `parameter_lines(Params())` in `config.py`. T-CLI-01: (a) `main(["--help"])` in a new process, with no `laptop` import; (b) the installed command. T-IMPORT-01: `tir_asr.cli` in `REQUIRED`, `tir_asr.app` in `ADAPTERS`.
- **Decision:** points 1 to 6 as proposed, with A in point 3. Point 2a: the new proposal (ASR, then MT, then VAD).
- **Reason (Aren's words):** "1. agree", "2. agree", "3. A", "4. agree", "5. agree", "6. agree". Point 2a: "agree on 2a".
- **Revisit when:** C7 (the NeMo lines at the interview), or T-E2E-01 fails at a model load.

## D-044. Ctrl+C: the main thread waits with a time limit (C2d)

- **Status:** ACCEPTED (2026-10-26), option A
- **Context:** In the first live run (2026-10-26), L-02 failed: Ctrl+C did not stop the program, and no shutdown line came (`test-results/c2d-live.txt`). The main thread waited in `events.get()` with no time limit (D-042). Probe C (`scripts/probe_sigint.py`, `test-results/c2d-probe-sigint.txt`) [RUN]:
  - The SIGINT handler stays `default_int_handler` after each startup step, and the main thread does not block SIGINT. Thus no library replaced or blocked the handler.
  - The process has 75–79 native threads after the ASR load (1 at the start).
  - Test 1, `get(timeout=0.5)` in a loop, got `KeyboardInterrupt`.
  - Test 2 (`get()` with no time limit) has no result: its message had no `flush`, so Aren did not see it (Claude's error). The live run L-02 is the same wait, and it failed.
  - In the workspace (one thread), both ways of waiting get `KeyboardInterrupt` [RUN].
  - Inference: Python handles a signal only when the main thread wakes up. With no time limit, the main thread does not wake up when another thread receives the signal.
- **Options:**
  - **A.** The main thread waits with `events.get(timeout=STOP_POLL_S)` in a loop, `STOP_POLL_S = 0.5` s. The time limit only wakes the main thread, so that Python can handle a waiting Ctrl+C; it changes nothing else. Weak points: Ctrl+C can take up to 0.5 s; the main thread wakes 2 times each second; it is a time limit in the code (R10), so it must be visible.
  - **B.** `signal.set_wakeup_fd` with a pipe, and `select()` on that pipe and on an event pipe. No time limit. Weak point: more code, harder to read.
  - **C.** Block SIGINT in all other threads. Weak point: the libraries make most of the threads.
- **Claude's preference:** A. Fact that can show it is wrong: T-E2E-02 still hangs after the fix.
- **Decision:** A. `STOP_POLL_S = 0.5` s is a named constant in `pipeline.py` (`ARCHITECTURE.md` §4 and §5), not a tunable parameter. New test T-E2E-02: the installed command gets SIGINT after "Listening" and must end within 10 s with exit code 0 and the shutdown line.
- **Reason (Aren's words):** "ok fix with A and I approve the test".
- **Revisit when:** T-E2E-02 hangs, or C4 changes the threads.

## D-045. Launcher script `run.sh` (C2d)

- **Status:** ACCEPTED (2026-10-26), option A
- **Context:** Aren asked for "a bash executable file for the command that runs the app". The program must start in the project folder (the MT model folder is relative, §2.4). All model tests ran with `HF_HUB_OFFLINE=1`. L-02 passed with `.venv/bin/tir-asr`, with no `uv run` in the signal path.
- **Options:**
  - **A.** `run.sh` in the project folder: `cd` to the folder of the script, `HF_HUB_OFFLINE=1`, then `exec .venv/bin/tir-asr "$@"`. Weak points: `uv sync` must run one time before; with `HF_HUB_OFFLINE=1`, a missing file in the Hugging Face cache gives an error, not a download (this is the wanted behaviour for K2).
  - **B.** The same, with `exec uv run tir-asr "$@"`. Weak points: `uv run` can sync the environment at each start (a download at the interview); `uv` is then in the Ctrl+C path, which L-02 did not test.
  - **C.** A, but with no `HF_HUB_OFFLINE`. Weak point: the Hugging Face libraries can try the network at the start [UNVERIFIED for this program]; with no network, that can be slow or fail.
- **Claude's preference:** A. Checks in the workspace with a fake program [RUN]: it works from another folder and through a symbolic link, it passes the arguments, `exec` leaves no extra shell, and a missing command gives exit code 1 with a message. `shellcheck` 0.11.0 has no findings. Fact that can show A is wrong: `./run.sh` fails on Aren's laptop where `.venv/bin/tir-asr` works.
- **Decision:** A.
- **Reason (Aren's words):** "agree on D45".
- **Revisit when:** C4 (device flags go through `"$@"`), or C8 (the README setup steps).

## D-046. Eval data: labels and how the eval uses them (C3)

- **Status:** ACCEPTED (2026-10-26), option B
- **Context:** WER needs the ASR text and the reference text of the same audio. Aren recorded S1–S3 (`docs/eval/scripts.md`) with one file for each side: `data/eval/raw/<s>.mic.wav` (Aren, "Me") and `data/eval/raw/<s>.call.wav` (Speaker 1 and Speaker 2; Google Meet for S1, Telegram for S2 and S3). The folder had no label files.
- **Facts [RUN, read-only check of the 6 files, 2026-10-26]:**
  - 48 kHz, mono, float32 (WAV format 3). Each mic file has the same length as its call file: S1 70.66 s, S2 62.81 s, S3 59.05 s.
    - **Correction (2026-10-26, D-048):** at this check, the S2 files and the S3 files had the names of the other script. Aren corrected the names. The correct lengths are S2 59.05 s and S3 62.81 s.
  - `s1.mic.wav` has 500 samples at |x| ≥ 0.999 (clipping, Q-11). The other 5 files have a peak of 0.62–0.99.
  - The call files have no echo of Aren's voice (5 places checked, correlation ≤ 0.07).
  - S1: the two sides speak at the same time three times, for 0.35–1.1 s (Aren's interruptions, on purpose). Source: a level check, not the VAD.
  - S1 call side: the pauses between Speaker 1 and Speaker 2 are 0.38–0.99 s. The pause s1-13 → s1-14 (0.38 s) is shorter than `vad_min_silence_ms`.
  - S1–S3 have 34 lines and 397 Armenian words: 15 lines on the mic side, 19 lines on the call side. Aren counts each line as one recording, so D-019 ("at least 20 recordings") is met. S4 can come later.
  - `data/eval/raw/s1.wav` is a mix that Aren made. The eval does not use it.
- **Options:**
  - **A.** The text of the full side, with no labels. Weak point: one number for each file only.
  - **B.** Labels by Aren in Audacity. Weak points: 20–30 min of the time budget [UNVERIFIED estimate]; manual errors in the times.
  - **C.** An automatic split into runs at silences of 1.5 s or more, with a count check. Weak points: a new eval constant; one number for two lines on the S1 call side; a long pause or a short turn gives a wrong count.
- **Claude's preference:** C. Fact that can show it is wrong: the run count fails on 2 or more of the 6 files.
- **Decision:** B, with these rules:
  1. **Label files:** one file for each script, `data/eval/raw/<s>.labels.txt`, exported from Audacity: start (s), tab, end (s), tab, line ID with no "†". One label for each line. Two labels can overlap (interruptions). The eval stops with an error on an unknown ID, a missing ID, a repeated ID, or a line in a different format.
  2. **Main numbers:** the program's VAD (`Params()`) cuts each full file into segments, as in the live program. The eval joins the texts of a file in time order and compares them with the reference lines of that side in script order. This gives WER, CER, and chrF for each file, each side, and the full set. A label error does not change these numbers.
  3. **Line view:** each segment goes to the line label with the largest time overlap on its side. This gives the numbers for each line and the segments of each line (Q15). The main numbers do not use the line view, because one segment can hold two lines (s1-13 + s1-14).
  4. **Interruptions:** S1 is not edited. Each side is in its own file, so an interruption does not mix two voices in the ASR input. The table shows S1 separately.
- **Reason (Aren's words):** "Let me do the labelling in audacity no problem just tell me how". "Ok I agree on D46".
- **Questions raised:**
  - Aren: do the two files need a mix into one file? Claude: no. The program has two sources (F1); a mix loses the side of each word; the C4 sim tests and C5 need the separate files; the resample is an eval step with a test.
  - Aren offered to edit the S1 interruptions out. Claude: keep them (point 4). Aren agreed.
  - Claude (R14) named the main risk of B one time: the time in the budget.
- **Revisit when:** the joined-text WER is lower than the true WER because the alignment matches words of different lines; or S4 gets recorded (then it gets its labels).

## D-047. Armenian text normalization for WER and CER (C3)

- **Status:** ACCEPTED (2026-10-26), rules 1 to 6 with option P1 and option N1
- **Context:** PLAN C3, step 1. WER and CER compare the ASR text with the reference text. Punctuation, case, and spelling variants must not count as word errors, except where we decide so.
- **Facts [RUN, Python `unicodedata`, Unicode 15.1; counts from the 44 lines of `docs/eval/scripts.md`]:**
  - The references have these marks: «։» U+0589 (102), «,» (62), «՞» U+055E (17), «՝» U+055D (4), « and » (1 pair), «՜» U+055C (1). They have no digits.
  - «՞» and «՜» are inside the word, on the stressed vowel («Լսո՞ւմ», «Վա՜յ»). A space in their place makes two words.
  - «և» U+0587 (15 times) is one character. NFKC changes it to «եւ». It has no capital form: the reference writes «Եվ», and `"Եվ".lower()` gives «եվ».
  - «՞» is the only mark that shows a question: a question also ends with «։» (s3-08). In S1–S3, 12 of the 34 lines have one «՞».
- **Rules, in this order:**
  1. Unicode NFKC (it also opens the ligatures U+FB13 to U+FB17).
  2. Lowercase.
  3. Delete «՜» U+055C, «՛» U+055B, «՟» U+055F, and «՚» U+055A, with no space. Keep «՞» U+055E.
  4. «եւ» → «եվ». After rule 1, this also covers «և». Assumption [UNVERIFIED]: modern spelling uses «ւ» only in «ու».
  5. One space for each other punctuation mark or symbol (Unicode categories P and S).
  6. One space between words, and no space at the start or at the end.
- **Options for «՞»:**
  - **P1.** Keep «՞» in the word. Weak points: a correct word with no «՞» counts as one full word error; WER then measures the words and the questions together; a «՞» on a different word gives two errors.
  - **P2.** Delete «՞» for WER and CER, and count the questions separately, for ASR («՞») and for MT («?»). Weak point: two numbers for the ASR decision.
  - **P3.** Move «՞» to its own word. Weak points: WER counts a mark as a word; a «՞» on a different word gives two errors.
- **Options for numbers:**
  - **N1.** No rule. The eval shows the number of words with digits for each model. Weak point: "8-ին" for «ութին» counts as an error, but the recognition was correct.
  - **N2.** A converter from digits to Armenian words, with the case endings. Weak points: more code and tests; the rules need a source; compound number words.
  - **N3.** A second reference with digits. Weak point: WER with two references is more complex.
- **Claude's preference:** P2. Fact that can show it is wrong: we cannot decide D-ASR from WER and the question count together. N1. Fact that can show it is wrong: a candidate writes 3 or more words with digits on S1–S3.
- **Decision:** rules 1 to 6, P1, N1. Function `normalize_hy` in `src/tir_asr/eval/normalize.py`. Tests T-NORM-01 to T-NORM-09 (`TESTS.md` §2.5).
- **Reason (Aren's words):** "6. I agree, but, U+055E is important as it shows that the sentence is a question so we must not get rid of it". "I am for option P1, let's keep the question mark, but we can get rid of the other symbols". On numbers: "Yes no rule for numbers".
- **Questions raised:**
  - Claude: the normalization changes only the two texts that WER and CER compare. The program output and the MT input keep «՞».
  - Claude: known limit of P1: an ASCII «?» in place of «՞» becomes a space, so the word does not match the reference word.
- **Revisit when:** a candidate writes 3 or more words with digits on S1–S3 (N2); the ASR outputs show «?» in place of «՞»; or a «՞» on a different word changes the ASR ranking.

## D-048. Eval references for the cut ends of S2 and S3 (C3)

- **Status:** ACCEPTED (2026-10-26), option A
- **Context:** Aren made the labels (D-046). Two recordings stop before the end of the last line:
  - s2-10 ("Me", mic side) stops after «Շնորհակալ». «եմ, ցտեսություն» is not in the audio.
  - s3-10 (Speaker 1, call side) stops inside the last word: the audio has «քե», not «քեզ».
  - [RUN] The last label of s1-14, s2-10, and s3-10 ends at the end of its file, so these sides end during speech. The VAD closes a segment only after `vad_min_silence_ms` of silence (D-027). The eval audio step needs a rule for the end of a file (proposal with that component).
  - Aren also corrected the S2 and S3 file names (correction in D-046), and he changed `docs/eval/scripts.md` so that the references agree with the recordings.
- **Options:**
  - **A.** Make the references the same as the audio (the rule "Changes" in `docs/eval/scripts.md`). s2-10: «Անպայման։ Շնորհակալ», "Definitely. Thank you". s3-10: «… Վաղն առավոտյան կզանգեմ քե»; the English does not change, because a translation of a part of a word has no correct form. A note under each table gives the original script text. Weak points: the table no longer shows the full text for a new recording; a part of a word in a reference is unusual (a model that writes «քեզ» gets one error).
  - **B.** Remove s2-10 and s3-10 from all numbers. Weak points: the main numbers then depend on the labels (against D-046 point 2); 2 lines fewer.
  - **C.** Record the two ends again. Weak points: time, the other speaker, and new labels.
- **Claude's preference:** A. All models get the same audio, so the effect on the comparison is equal (about 3 of 397 words). Fact that can show A is wrong: a new recording of S2 or S3 (for example in C5) needs the full text.
- **Decision:** A.
- **Reason (Aren's words):** "Agree on A for the cut ends". On the file names: "yes the wrong names were wrong".
- **Revisit when:** a new recording of S2 or S3 needs the full script text.

## D-049. C3 scope: the full shortlists, the eval components, and two dev dependencies (C3)

- **Status:** ACCEPTED (2026-10-26), option B
- **Context:** at 16:22, about 80 min remained in the C3 time box (2.5 h). The full shortlists (D-014, D-015) need 3 eval components and 5 more candidates, with installs, downloads, and adapters. The total time budget is already over (R16).
- **Options:**
  - **A.** Eval components; ASR-1 with RNNT and with CTC (same weights); MT NLLB-600M, and OPUS-MT only if time remains. ONNX-CTC, BuzzASR (ASR-5), and Seamless (ASR-2, MT-5) move to C6, only if the C3 numbers show that ASR or MT is the weakest link. The line view (D-046 point 3) moves to C6. Weak points: no end-to-end model and no other ASR weights measured; D-ASR chooses between two decoders of one model.
  - **B.** The full shortlists. Weak point: about 1.5–2 h more [UNVERIFIED estimate], over the time box and the budget.
  - **C.** Numbers for the current models only. Weak point: no comparison; D-ASR and D-MT only confirm the skeleton.
- **Claude's preference:** A. Fact that can show it is wrong: on our data, the WER of ASR-1 is much higher than its published WER (Common Voice 17.0: 9.90 %), so a candidate that moved to C6 can win.
- **Decision:** B, with these parts of the plan:
  1. `c3-metrics`: own edit distance for WER and CER; chrF from `sacrebleu` with its default values.
  2. `c3-data`: read a 48 kHz float32 WAV file and resample it to 16 kHz with `scipy.signal.resample_poly(x, 1, 3)`; add 1.0 s of zeros at the end of each file (the end rule of D-048); read the references from `docs/eval/scripts.md` and the labels.
  3. `c3-bakeoff`: the runner (model level), with the line view of D-046 point 3.
  4. Dev dependencies (D-028): `sacrebleu` (2.6.0, Apache-2.0) and `scipy` (BSD) [SOURCE: wheel METADATA].
- **Reason (Aren's words):** "No let's not cut on research. Will make cuts later." Earlier in C3: "Let's make sure that we stay under the time box for C3."
- **Questions raised:** Claude (R14) named the conflict with the time box one time: C3 goes over its time box by about 1.5–2 h [UNVERIFIED estimate], and the later cuts must cover this time (C6 is the first item to cut). Aren did not object. He also did not object to the 1.0 s end rule and the two dependencies.
- **Revisit when:** the total time comes near the budget (R16).
