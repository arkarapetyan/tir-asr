# Handover 00 → S1 (side chat: export format)

**Date:** 2026-10-23

## Goal of this chat

Learn the format of the full data export of Claude. Decide if we need a converter that makes one unedited `.md` file for each chat (deliverable D3, D-011).

## Current state

- Aren requested the full data export on 2026-10-23 (Settings > Privacy > Export data). The download link comes by email and expires after 24 hours.
- **Caution:** the export contains all of Aren's chats, also chats outside this project. The archive stays outside the repository and is never committed.

## Input from Aren

- The file names in the export archive.
- The keys (the structure) of one conversation of this project. Not the content of other chats.

## Read list

1. `docs/handovers/00b-export-format.md` (this file)
2. `RULES.md` (R15)
3. `DECISIONS.md` (D-011)

## First task

1. Ask for access to `/home/aren/dev/armenian-asr`.
2. Look at the format that Aren gives.
3. If each chat is already one Markdown file: record this in D-011. No converter is necessary.
4. If not: propose a converter (options, weak points). It must keep the text unedited. Tests first (R5).

## Do not

- Do not read the content of chats outside this project (R4).
- Do not change any text of a chat. A converter only changes the format.
- After each remote write, compare checksums.
