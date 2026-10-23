"""Change chats from the Claude data export into one Markdown file for each chat.

Contract: ARCHITECTURE.md §8.1. Decision: D-012 (option B: text blocks of the main branch only).
The tool changes only the format. It does not change the text.

Usage: uv run python scripts/export_chats.py <EXPORT> chats/manifest.toml
"""

import json
import re
import sys
import tomllib
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT_ID = "00000000-0000-4000-8000-000000000000"
SENDERS = ("human", "assistant")
NO_TEXT = "(This message has no text blocks.)"
FILE_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\.md")


class ExportError(Exception):
    """An error in the export or in the manifest. The tool stops and writes no file."""


def get(obj, key, kind, where):
    """Return obj[key]. Stop if obj is not an object, the key is missing, or the type is wrong."""
    if not isinstance(obj, dict):
        raise ExportError(f"{where}: the value has the wrong type (expected an object)")
    if key not in obj:
        raise ExportError(f"{where}: key '{key}' is missing")
    value = obj[key]
    if not isinstance(value, kind):
        raise ExportError(f"{where}: key '{key}' has the wrong type")
    return value


def load_manifest(path):
    """Return a list of (title, file name) from the manifest."""
    try:
        data = tomllib.loads(path.read_bytes().decode("utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as err:
        raise ExportError(f"manifest {path}: not valid TOML ({err})") from err
    entries = get(data, "chat", list, "manifest")
    if not entries:
        raise ExportError("manifest: no [[chat]] entries")
    result = []
    for number, entry in enumerate(entries, 1):
        where = f"manifest entry {number}"
        title = get(entry, "title", str, where)
        file = get(entry, "file", str, where)
        if not FILE_NAME.fullmatch(file):
            raise ExportError(f"{where}: '{file}' is not a plain file name that ends in .md")
        result.append((title, file))
    for index, label in ((0, "title"), (1, "file")):
        counts = Counter(entry[index] for entry in result)
        for value, count in counts.items():
            if count > 1:
                raise ExportError(f"manifest: two entries have the same {label} '{value}'")
    return result


def load_export(path):
    """Return the list of chats in the export."""
    try:
        data = json.loads(path.read_bytes())
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as err:
        raise ExportError(f"export {path}: not valid JSON ({err})") from err
    if not isinstance(data, list):
        raise ExportError("export: the value has the wrong type (expected a list of chats)")
    return data


def find_chat(chats, title):
    """Return the one chat with this title."""
    names = [get(c, "name", str, f"export chat {n}") for n, c in enumerate(chats, 1)]
    matches = [c for c, name in zip(chats, names, strict=True) if name == title]
    if len(matches) != 1:
        found = "no chat" if not matches else f"{len(matches)} chats"
        raise ExportError(f"manifest title '{title}' matches {found} in the export")
    return matches[0]


def created(message, where):
    value = get(message, "created_at", str, where)
    try:
        return datetime.fromisoformat(value)
    except ValueError as err:
        raise ExportError(f"{where}: created_at '{value}' is not an ISO time") from err


def main_branch(messages, where):
    """Return the messages on the path from the root to the newest leaf, in tree order."""
    if not messages:
        raise ExportError(f"{where} has no messages")
    by_id = {}
    for number, message in enumerate(messages, 1):
        uuid = get(message, "uuid", str, f"{where}, message {number}")
        if uuid in by_id:
            raise ExportError(f"{where}: two messages have the same uuid '{uuid}'")
        by_id[uuid] = message
    for uuid, message in by_id.items():
        parent = get(message, "parent_message_uuid", str, f"{where}, message {uuid}")
        if parent != ROOT_ID and parent not in by_id:
            raise ExportError(f"{where}: parent message '{parent}' is not in the chat")
    for uuid in by_id:
        steps, current = 0, uuid
        while current != ROOT_ID:
            steps += 1
            if steps > len(by_id):
                raise ExportError(f"{where}: the parent chain of message '{uuid}' has a loop")
            current = by_id[current]["parent_message_uuid"]
    parents = {m["parent_message_uuid"] for m in by_id.values()}
    leaves = [m for uuid, m in by_id.items() if uuid not in parents]
    times = [(created(m, f"{where}, message {m['uuid']}"), m) for m in leaves]
    newest = max(t for t, _ in times)
    top = [m for t, m in times if t == newest]
    if len(top) > 1:
        raise ExportError(f"{where}: two leaf messages have the same newest created_at")
    chain, current = [], top[0]
    while True:
        chain.append(current)
        if current["parent_message_uuid"] == ROOT_ID:
            break
        current = by_id[current["parent_message_uuid"]]
    chain.reverse()
    return chain


def fence(text):
    """Put the text in a code fence. The fence is longer than each backtick sequence in it."""
    longest = max((len(run) for run in re.findall(r"`+", text)), default=0)
    ticks = "`" * max(3, longest + 1)
    body = text if text.endswith("\n") else text + "\n"
    return f"{ticks}text\n{body}{ticks}"


def render(chat_obj, where):
    """Return (Markdown text, number of messages) for one chat."""
    title = get(chat_obj, "name", str, where)
    uuid = get(chat_obj, "uuid", str, where)
    created_at = get(chat_obj, "created_at", str, where)
    updated_at = get(chat_obj, "updated_at", str, where)
    messages = get(chat_obj, "chat_messages", list, where)
    branch = main_branch(messages, where)
    other_blocks = Counter()
    parts = []
    for number, message in enumerate(branch, 1):
        mwhere = f"{where}, message {message['uuid']}"
        sender = get(message, "sender", str, mwhere)
        if sender not in SENDERS:
            raise ExportError(f"{mwhere}: sender '{sender}' is not 'human' or 'assistant'")
        parts.append(f"## {number}. {sender} · {get(message, 'created_at', str, mwhere)}")
        texts = []
        for block in get(message, "content", list, mwhere):
            kind = get(block, "type", str, mwhere)
            if kind == "text":
                texts.append(get(block, "text", str, mwhere))
            else:
                other_blocks[kind] += 1
        if not texts:
            parts.append(NO_TEXT)
        for text in texts:
            parts.append(fence(text) if sender == "human" else text)
    side = len(messages) - len(branch)
    blocks = ", ".join(f"{kind} {other_blocks[kind]}" for kind in sorted(other_blocks)) or "none"
    header = [
        f"# {title}",
        "\n".join(
            [
                f"- Chat ID: `{uuid}`",
                f"- Created: {created_at}",
                f"- Updated: {updated_at}",
                f"- Messages in this file: {len(branch)}",
            ]
        ),
        "\n".join(
            [
                "> **Note:** This file has only the text blocks of the main branch of the chat.",
                "> The text is not changed. Human text is in code fences.",
                f"> Not in this file: {side} messages in side branches.",
                f"> Blocks of other types in the main branch: {blocks}.",
                "> The original chat in the Claude app has all blocks.",
            ]
        ),
    ]
    return "\n\n".join(header + parts) + "\n", len(branch)


def build(export_path, manifest_path):
    """Return a list of (output path, Markdown text, number of messages). Write nothing."""
    entries = load_manifest(manifest_path)
    chats = load_export(export_path)
    outputs = []
    for title, file in entries:
        chat_obj = find_chat(chats, title)
        markdown, count = render(chat_obj, f"chat '{title}'")
        outputs.append((manifest_path.parent / file, markdown, count))
    return outputs


def main(argv):
    if len(argv) != 2:
        print("export_chats: usage: export_chats.py <EXPORT> <MANIFEST>", file=sys.stderr)
        return 1
    try:
        outputs = build(Path(argv[0]), Path(argv[1]))
    except ExportError as err:
        print(f"export_chats: {err}", file=sys.stderr)
        return 1
    for path, markdown, count in outputs:
        path.write_text(markdown, encoding="utf-8", newline="")
        print(f"export_chats: wrote {path.name}: {count} messages")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
