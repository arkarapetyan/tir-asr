# Handover S1 → end of C8 (final chat export)

**Date:** 2026-10-23

## Goal

Make deliverable D3 after the last message of C8: one `.md` file for each chat of the Project, in `chats/`.

## Current state

- S1 measured the export format (D-012). The export is one JSON file with all chats. It is not one Markdown file for each chat.
- `scripts/export_chats.py` converts the chats that `chats/manifest.toml` names. It writes only the text blocks of the main branch, with no change (D-012, option B).
  - Contract: `ARCHITECTURE.md` §8.1. Tests: `TESTS.md` §2.2.
- The manifest has only C0 now (`00-kickoff.md`). Run 1 of T-EXPORT-11 used the C0 export of 2026-10-23.
- The time for S1 is not part of the 20-hour budget (Aren, D-012).

## Steps after the last message of C8

1. Aren requests the full data export (Settings > Privacy > Export data). The download link expires after 24 hours.
2. Aren extracts the archive outside the repository.
3. Add one `[[chat]]` entry to `chats/manifest.toml` for each chat of the Project (C0–C8, S1, and each other side chat):
   - `title`: the chat title in the app.
   - `file`: `NN-<phase>.md`, the same name as the handover of that chat.
4. Run the converter:

   ```bash
   uv run python scripts/export_chats.py <ARCHIVE>/conversations.json chats/manifest.toml > test-results/final-export.txt 2>&1; echo "exit=$?" >> test-results/final-export.txt
   ```

5. If the converter stops, read the cause in `test-results/final-export.txt`. For example, when two chats have the same title, rename one chat in the app and export again.
6. Open each file on GitHub. Compare its messages with the app (T-EXPORT-11, run 2).

## Read list

1. `docs/handovers/00c-export-converter.md` (this file)
2. `ARCHITECTURE.md` §8.1
3. `DECISIONS.md` (D-011, D-012)

## Do not

- Do not commit the export archive. It contains all of Aren's chats, also chats outside this Project.
- Do not edit the text in `chats/*.md`. To change a file, run the converter again.
- Claude does not read the archive (R4). Aren runs the converter on the laptop.
