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

- **Status:** PROPOSED
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
- **Decision:** (Aren)
- **Reason (Aren's words):** (Aren)

## D-010. Pin the CI actions to commit SHAs

- **Status:** PROPOSED
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
- **Decision:** (Aren)
- **Reason (Aren's words):** (Aren)
