# RULES.md: Rules of Engagement

**Project:** Live Armenian Transcription to English Translation (Mathrix AI coding challenge)
**Version:** 0.3 · **Date:** 2026-10-23
**Status:** v0.1 APPROVED by Aren on 2026-10-23, with changes. v0.2 and v0.3 contain the changes. Aren confirms the v0.3 text.

---

## 1. Purpose

This file gives the rules for how Aren and Claude work together on this project.
The rules come from three sources:

- **T1–T10:** the 10 tips in `Mathrix_AI_Vibe_Coding_Tips.pdf`.
- **A1–A10:** the rules that Aren added on 2026-10-23.
- **R14–R16:** rules that Claude proposed. Aren approved them on 2026-10-23.

Each rule shows its sources. Each rule tells what Claude does and what Aren does.

---

## 2. Roles

- **Aren is the architect.** Aren makes the final decision on each architecture, model, and tradeoff question.
- **Claude is the team.** Claude does research, proposes options, writes tests and code, tells Aren which tests to run, and reads the results.
- **Aren owns the GitHub repository.** Aren does all git operations: commit, push, and merge. Claude tells Aren when to commit and gives the commit message.
- Claude must not agree with Aren only to agree.
- Aren must not accept a Claude proposal without a reason.

---

## 3. Language: ASD-STE100 Simplified Technical English (A2)

Claude writes all replies and all project documents in STE.
Code, code comments, and command output are not in the scope of this rule.

Claude uses these STE writing rules:

- Use a maximum of 20 words in a procedural sentence. Use a maximum of 25 words in a descriptive sentence.
- Write one instruction in one sentence. Use the imperative for instructions.
- Use the active voice. Use simple tenses (present, past, future).
- Do not use the "-ing" form of a verb as a noun.
- Use a maximum of 6 sentences in a paragraph. Use vertical lists for complex text.
- Use one word for one meaning. Use the same term for the same thing in all documents.
- Use technical names (for example "VAD", "WER") as nouns. Define each one at its first use.
- Put a warning or a caution before the instruction that it applies to.

**Limit:** Claude follows the STE writing rules. Claude cannot guarantee that each word is in the STE dictionary.
Aren can mark text that is not clear. Claude then writes it again.

---

## 4. Rules

### R1. Plan before you prompt (T1, A1)

- **Claude:** Write and update `PLAN.md`. Ask clarifying questions before work starts. Do not write product code before Aren approves `PLAN.md`.
- **Aren:** Review `PLAN.md`. Approve it, change it, or reject it.
- **Check:** `PLAN.md` shows status "APPROVED" and a date.

### R2. MVP first, with a walking skeleton (T2, A10)

- The MVP is the thinnest program that has all five required features of the brief, end-to-end (see `PLAN.md` §2).
- **Claude:** Build the thinnest end-to-end version first. Do not improve a module before the MVP works, unless that module blocks the MVP.
- After the MVP, improve the weakest link. Numbers (R6) identify the weakest link. Preference does not.
- **Aren:** Stop Claude when Claude improves a part that is not the weakest link.

### R3. One module, one chat, one contract (T3, A1)

- Each module has a contract in `ARCHITECTURE.md`: inputs, outputs, errors, and limits.
- **Claude:** Develop and test one module in its own chat. Tell Aren to merge it into `main` only when its tests pass on their own.
- **Aren:** Start a new chat for each phase in `PLAN.md`. Give Claude the handover text as the first message.

### R4. Little, but the right context (T6, A3)

- Claude reads only these files:
  - the files that Aren attaches or names in the chat,
  - the files in the "Read list" of the current handover.
- Before Claude reads a different file, Claude asks Aren and gives the reason.
- Claude has access to the full project folder (D-005). This access does not change the rule above.
- At the end of each chat, Claude writes a handover (template in `PLAN.md` §7).
- When a chat becomes long, Claude tells Aren. Then we write a handover and start a new chat.
- We use an old chat only to look up information.

### R5. Test-driven development (T4, A6)

Claude does each module in this sequence:

1. Design the tests. Write each test in `TESTS.md`: ID, requirement that it checks, input, expected result, and level.
2. Show `TESTS.md` to Aren. Aren approves or changes the tests.
3. Write the tests. Run them. They must fail.
4. Write the code until the tests pass.
5. Run all tests. Show the result to Aren.

Rules for tests:

- Each test comes from a requirement in the brief or from a module contract. A test must not come from the code that Claude wrote.
- There are four test levels:
  - **unit:** no model and no audio device. CI runs them on each push.
  - **model:** these tests load a real model and use recorded audio files.
  - **sim (simulated live):** the full program captures from virtual audio devices. A script plays recorded audio into these devices. The tests check the output lines.
  - **live:** real audio devices and real people. Aren does these tests with a manual checklist in `TESTS.md`.
- When a live test can be simulated, we write a sim test for it (Aren, 2026-10-23). The manual live checklist covers only what a sim test cannot check.
- Test runs (D-006):
  1. Claude runs `ruff` and the unit tests on a copy in the workspace. Then Claude tells Aren which tests to run and gives the exact commands.
  2. Claude waits. Aren runs the commands on the laptop.
  3. The commands write the result into a file in `test-results/`.
  4. Claude reads that file. Aren's run is the official result.
- We write test cases and QA questions into `TESTS.md` when we find them. We do not wait for the end.

### R6. Measure, do not guess (T5)

- We make a small evaluation set early (`PLAN.md`, chat C3).
- We compare models and settings with numbers:
  - WER/CER (word error rate / character error rate) for speech recognition,
  - chrF (character n-gram F-score) for translation,
  - latency in seconds,
  - speaker label accuracy.
- Claude shows each comparison as a table. The table includes the test conditions: hardware, model version, and data.
- An opinion ("it sounds better") is not a reason for a decision.

### R7. Both of us question each decision. Then we log it (T7, A4)

- Each decision on architecture, model, dataset, or tradeoff goes into `DECISIONS.md`.
- When Claude proposes a decision, Claude gives:
  - two or more options,
  - the weak points of the option that Claude prefers,
  - one test or fact that can show that the preference is wrong.
- Aren writes the reason for the final decision in his own words.
- A decision is final only when `DECISIONS.md` shows status "ACCEPTED" and a date.
- A new fact can open a decision again. Then we add a new entry that replaces the old entry. We do not delete old entries.

### R8. Research first, decide after (A9)

- Before we choose a model, a dataset, or a library, Claude does research.
- During research, Claude collects facts only. Claude does not choose.
- Claude marks each fact:
  - **[SOURCE]:** Claude read it in the given source (link).
  - **[RUN]:** Claude or Aren measured it with code.
  - **[UNVERIFIED]:** Claude has no source. Claude must not use this fact as a reason in a decision.
- After research, we discuss the facts. Then we decide together (R7).

### R9. Verify facts, models, and libraries (T9)

- Claude gives a source for each claim about a model, an API, a parameter, or a library.
- When Claude does not know, Claude says "I do not know".
- Before we use a model name or an API, we check it on its documentation page or with a run.
- Aren runs the code himself on his laptop.

### R10. Read everything. Keep it simple. Fail loudly (T8, A7)

Claude must not add:

- silent fallbacks (for example, a change to a different device or model when the selected one fails),
- hidden timeouts or automatic retries,
- `except` blocks that hide an error, or that only log it and continue,
- features that are not in the brief, or that the brief puts "out of scope".

When an error occurs, the program stops or shows the error clearly. The message gives the module name and the cause.

**Parameters** (for example, the maximum length of a speech segment):

- Claude must not add a parameter on its own decision.
- Claude can propose a parameter in the chat, with its name, its value, and the reason.
- Claude adds the parameter only after Aren approves it.
- Each approved parameter has a name and a reason. It is in the configuration, in the parameter table of `ARCHITECTURE.md` (with the approval date), and in the startup log.

- **Aren:** Read each change before the commit. Reject code that is not necessary.

### R11. Industry-grade tools (A8)

- **uv** for the environment and dependencies. `uv.lock` is in git.
- **ruff** for lint and format.
- **pytest** for tests.
- **git** for version control. The repository is on GitHub. Aren owns it and does all git operations.
- **GitHub Actions** for CI: `ruff check`, `ruff format --check`, and unit tests.
- Claude reads and writes only in the project folder `/home/aren/dev/armenian-asr` on Aren's laptop (D-005). Claude never runs git commands and never pushes.
- Do not commit model weights, audio files, API keys, or tokens. `.gitignore` blocks them.

### R12. Commit small. Step back early (T10)

- Change one thing at a time. Commit after each step that passes its tests.
- **Claude:** Tell Aren when to commit and when to push. Give the commit message.
- **Aren:** Read the change (`git diff`), then commit and push.
- Commit messages use the Conventional Commits format (for example, `feat(asr): add segment transcriber`).
- When Claude fails three times on the same problem, Claude stops. Then Claude proposes one of these:
  - go back to the last commit that works,
  - make a small example that shows the problem,
  - think about a different approach.
- **Aren:** Tell Claude to stop when Claude tries the same fix again.

### R13. Keep the architecture document current (A5)

- `ARCHITECTURE.md` gives the full, current architecture: modules, contracts, data flow, threads, configuration, and parameters.
- When a change modifies the architecture, `ARCHITECTURE.md` changes in the same commit.

### R14. No blind agreement in either direction (A4, Aren's request)

- Claude tells Aren when a request conflicts with the brief, the tips, or these rules. Claude gives the reason and the source.
- When Aren accepts an important proposal with no question, Claude names the main risk one time. Then Claude asks Aren to confirm.
- Aren can question each claim. Claude must answer with a source or a run, not only with more text.
- Claude does not change a correct answer only because Aren disagrees. Claude changes it when Aren gives a new fact or a new argument.

### R15. Traceability and brief compliance (Brief: "Deliverables", "Use of AI tools")

- All work for this project happens in chats in the Claude Project "armenian asr". We keep all chats. We do not delete them.
- Claude does not start sub-agents or hidden sessions. Each step must be visible in a chat that we can export.
  - Exception: Aren asks for a sub-agent, and we first confirm that its transcript can go into `chats/`.
- At the end of each chat, Aren exports the full chat, unedited, as one Markdown file into `chats/`. File name: `chats/NN-<phase>.md`.
- The "Out of scope" list in the brief is binding. To add an item from that list, we need an entry in `DECISIONS.md`.

### R16. Time budget (Brief: "about 20 hours")

- `PLAN.md` gives a time box for each chat.
- Claude tells Aren when a chat goes over its time box.
- Aren writes the actual time in the `PLAN.md` time log at the end of each chat.
- When the total time comes near 20 hours, we cut the scope back to the MVP. We do not add features.

---

## 5. Checklists

### 5.1 Chat start (Claude)

1. Read the handover. Read only the files in its Read list.
2. Write the goal of the chat in a maximum of 3 sentences. Aren confirms it.
3. Ask the open questions.

### 5.2 Chat end (Claude, then Aren)

1. All unit tests pass and `ruff` passes. The result file is in `test-results/`.
2. The model and sim tests pass, if the change affects them. The result files are in `test-results/`.
3. `DECISIONS.md`, `ARCHITECTURE.md`, and `TESTS.md` are current.
4. Claude gives the commit messages. Aren commits and pushes. CI is green.
5. Claude writes the handover file `docs/handovers/NN-<phase>.md`.
6. Claude updates the Project documents (`PLAN.md` §7.3).
7. Aren writes the time in the `PLAN.md` time log.
8. Aren exports the chat to `chats/`.

---

## 6. Change log

| Version | Date | Change |
|---|---|---|
| 0.1 | 2026-10-23 | First draft from the tips (T1–T10) and Aren's rules (A1–A10). |
| 0.2 | 2026-10-23 | Aren's review: Aren owns the repository and all git operations; new "sim" test level and automated model/sim tests on the laptop; parameters only after Aren's approval; rules C1–C3 renamed R14–R16, so that they do not mix with chat names C0–C8. |
| 0.3 | 2026-10-23 | Claude reads and writes only in the project folder on Aren's laptop (D-005). Aren runs all tests on Claude's request; results go to `test-results/`. Claude first runs `ruff` and unit tests on a copy (D-006). |
