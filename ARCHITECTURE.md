# ARCHITECTURE.md

**Project:** tir-asr · **Version:** 0.1 (template) · **Date:** 2026-10-23
**Status:** TEMPLATE. Chat C2 writes the first real version (RULES.md R13). §8 is complete (S1, D-012).

---

## 1. Overview

(C2) One paragraph and one diagram: the path from the audio devices to the terminal lines.

## 2. Modules and contracts

Each module has one contract. Each contract gives the inputs, the outputs, the errors, and the limits.

| Module | Input | Output | Errors (fail loudly, R10) | Limits |
|---|---|---|---|---|
| `audio` | (C2, C4) | | | |
| `segment` | (C2) | | | |
| `asr` | (C2) | | | |
| `mt` | (C2) | | | |
| `speakers` | (C5) | | | |
| `output` | (C2) | | | |

## 3. Data types

(C2) The data types that go between the modules, with their fields and units.

## 4. Data flow, threads, and queues

(C2) Which thread does what. Which queues connect the threads. What happens when a queue is full.

## 5. Configuration

(C2) The command-line flags and the configuration values.

## 6. Parameters

Only Aren adds a parameter (RULES.md R10). The startup log shows each parameter.

| Name | Value | Unit | Reason | Approved by Aren (date) |
|---|---|---|---|---|
| | | | | |

## 7. Error behaviour

(C2) For each error: the module, the message, and what the program does (stop or show).

## 8. Tools outside the package

These tools are not part of the `tir_asr` package. The program does not use them.

### 8.1 `scripts/export_chats.py`: chat export to Markdown (D-012)

- **Purpose:** deliverable D3. The tool changes chats from the Claude data export into one Markdown file for each chat. It changes only the format. It does not change the text.
- **Command:** `uv run python scripts/export_chats.py <EXPORT> chats/manifest.toml`
- **Input:**
  - `EXPORT`: the conversations JSON file from the Claude data export. The file stays outside the repository. The tool only reads it.
  - `chats/manifest.toml`: one `[[chat]]` table for each chat, with two keys:
    - `title`: the chat title in the app.
    - `file`: the output file name, for example `00-kickoff.md`.
- **Output:** for each manifest entry, the file `<file>` in the folder of the manifest. The tool replaces a file that exists. Git shows each change.
  - **Header:** the chat title, the chat ID, `created_at`, `updated_at`, and the number of messages in the file.
  - **Note:** the file has only the text blocks of the main branch, with no change. The note gives the number of messages in side branches, and the number of blocks of each other type in the main branch. The original chat in the app has all blocks.
  - **Messages:** each message of the main branch, in tree order. A heading gives the number, the sender, and `created_at`. Then each `text` block of `content` follows:
    - `human`: in a code fence. The fence has more backticks than the longest backtick sequence in the text.
    - `assistant`: as Markdown, with no change.
    - A message with no text block gets the line "(This message has no text blocks.)".
  - **Terminal:** one line for each file, with the file name and the number of messages.
- **Main branch:** the path from the root to the leaf message with the newest `created_at`. The root is the parent ID `00000000-0000-4000-8000-000000000000` (**[RUN]** in C0).
- **Not used:** `message.text` (it has a placeholder in place of the tool calls), `account`, `attachments`, `files`, and all blocks that are not `text`.
- **Errors (fail loudly, R10):** the tool stops with exit code 1 and the message `export_chats: <cause>`. If one chat has an error, the tool writes no file. Causes:
  1. The export is not valid JSON, or the manifest is not valid TOML.
  2. A key is missing, or a value has the wrong type (for example, a chat has no `chat_messages`).
  3. A manifest `file` is not a plain file name that ends in `.md`.
  4. Two manifest entries have the same `title` or the same `file`.
  5. A manifest `title` matches no chat, or two or more chats.
  6. A chat has no messages.
  7. A parent message ID is not in the chat and is not the root ID, or the parent chain has a loop.
  8. Two leaf messages have the same newest `created_at`.
  9. A sender is not `human` or `assistant`.
- **Limits:**
  - Only the Python standard library (`json`, `tomllib`). No new dependency.
  - The tool does not show tool calls, tool results, thinking summaries, injected prompts, documents, or side branches (D-012, option B).
  - **[RUN]** The format facts come from one chat (C0). The final export after C8 can have a different format.

## 9. Change log

| Version | Date | Change |
|---|---|---|
| 0.0 | 2026-10-23 | Template. |
| 0.1 | 2026-10-23 | New §8: contract of `scripts/export_chats.py` (S1, D-012). The change log is now §9. |
