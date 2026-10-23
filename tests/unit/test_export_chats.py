"""Tests for scripts/export_chats.py (TESTS.md §2.2, contract ARCHITECTURE.md §8.1, D-012).

The tests run the script as a command on test data that each test makes.
The test data is not real chat text.
"""

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "export_chats.py"
ROOT = "00000000-0000-4000-8000-000000000000"
NO_TEXT = "(This message has no text blocks.)"


# --- test data -------------------------------------------------------------------------------


def text(t):
    return {"type": "text", "text": t, "citations": [], "start_timestamp": None, "flags": None}


def tool_use(command):
    return {"type": "tool_use", "id": "toolu_1", "name": "Bash", "input": {"command": command}}


def tool_result(output):
    return {
        "type": "tool_result",
        "tool_use_id": "toolu_1",
        "name": "Bash",
        "is_error": False,
        "content": [{"type": "text", "text": output}],
    }


def thinking(summary):
    return {"type": "thinking", "thinking": "", "summaries": [{"summary": summary}]}


def msg(uuid, parent, sender, minute, blocks, placeholder=""):
    created = f"2026-10-23T10:{minute:02d}:00.000000Z"
    return {
        "uuid": uuid,
        "parent_message_uuid": parent,
        "sender": sender,
        "created_at": created,
        "updated_at": created,
        "text": placeholder,
        "content": blocks,
        "attachments": [],
        "files": [],
    }


def chat(name, messages, uuid="chat-0001"):
    return {
        "uuid": uuid,
        "name": name,
        "summary": "",
        "created_at": "2026-10-23T10:00:00.000000Z",
        "updated_at": "2026-10-23T11:00:00.000000Z",
        "account": {"uuid": "ACCOUNT-SECRET-0001"},
        "chat_messages": messages,
    }


def simple_chat(name="Test chat", uuid="chat-0001"):
    return chat(
        name,
        [
            msg("m1", ROOT, "human", 1, [text("HUMAN-TOKEN")]),
            msg("m2", "m1", "assistant", 2, [text("ASSISTANT-TOKEN")]),
        ],
        uuid=uuid,
    )


def branch_chat():
    """2 roots and 1 edit. Main branch: m3, m4, m7, m8. Side branches: m1, m2, m5, m6."""
    messages = {
        "m1": msg("m1", ROOT, "human", 1, [text("SIDE-ROOT-HUMAN")]),
        "m2": msg("m2", "m1", "assistant", 2, [text("SIDE-ROOT-ASSISTANT")]),
        "m3": msg(
            "m3",
            ROOT,
            "human",
            3,
            [
                text("MAIN-1-HUMAN"),
                {"type": "injected_prompt_block", "prompt": "INJECTED-TOKEN"},
                {"type": "document", "file_uuid": "f1", "title": "DOC-TITLE-TOKEN"},
            ],
        ),
        "m4": msg(
            "m4",
            "m3",
            "assistant",
            4,
            [
                thinking("THINK-SUMMARY-TOKEN"),
                tool_use("TOOL-INPUT-TOKEN"),
                tool_result("TOOL-RESULT-TOKEN"),
                text("MAIN-2-ASSISTANT"),
            ],
        ),
        "m5": msg("m5", "m4", "human", 5, [text("SIDE-EDIT-HUMAN")]),
        "m6": msg("m6", "m5", "assistant", 6, [tool_use("SIDE-TOOL-TOKEN")]),
        "m7": msg("m7", "m4", "human", 7, [text("MAIN-3-HUMAN")]),
        "m8": msg(
            "m8",
            "m7",
            "assistant",
            8,
            [text("MAIN-4-ASSISTANT")],
            placeholder="PLACEHOLDER-TOKEN This block is not supported on your current device yet.",
        ),
    }
    order = ["m8", "m1", "m5", "m3", "m7", "m2", "m6", "m4"]  # not the tree order
    return chat("Branch chat", [messages[k] for k in order])


# --- helpers ---------------------------------------------------------------------------------


def toml_manifest(entries):
    lines = []
    for title, file in entries:
        lines += ["[[chat]]", f"title = {json.dumps(title)}", f"file = {json.dumps(file)}", ""]
    return "\n".join(lines)


def run(tmp_path, export, manifest):
    """Write the export and the manifest, run the script, return (process, chats folder)."""
    export_file = tmp_path / "archive" / "conversations.json"
    export_file.parent.mkdir(exist_ok=True)
    if isinstance(export, str):
        export_file.write_text(export, encoding="utf-8")
    else:
        export_file.write_text(json.dumps(export, ensure_ascii=False), encoding="utf-8")
    chats_dir = tmp_path / "chats"
    chats_dir.mkdir(exist_ok=True)
    manifest_file = chats_dir / "manifest.toml"
    if isinstance(manifest, str):
        manifest_file.write_text(manifest, encoding="utf-8")
    else:
        manifest_file.write_text(toml_manifest(manifest), encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), str(export_file), str(manifest_file)],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return proc, chats_dir


def read(path):
    return path.read_bytes().decode("utf-8")


def md_files(chats_dir):
    return sorted(p.name for p in chats_dir.glob("*.md"))


def fenced_blocks(md):
    """Content of each backtick code fence, with the CommonMark rule for the fence end."""
    lines = md.split("\n")
    blocks, i = [], 0
    while i < len(lines):
        opening = re.fullmatch(r" {0,3}(`{3,})[^`]*", lines[i])
        if not opening:
            i += 1
            continue
        closing = re.compile(r" {0,3}`{" + str(len(opening.group(1))) + r",}[ \t]*")
        body, i = [], i + 1
        while i < len(lines) and not closing.fullmatch(lines[i]):
            body.append(lines[i])
            i += 1
        blocks.append("".join(line + "\n" for line in body))
        i += 1
    return blocks


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


# --- tests -----------------------------------------------------------------------------------

HARD_TEXTS = [
    "Բարև, ինչպե՞ս ես։ Ես խոսում եմ հայերեն։",
    "# Heading\n\n- item *em* **bold**\n\n| a | b |\n|---|---|\n| 1 | 2 |",
    "<details><summary>x</summary>\n\n<b>html</b> &amp; &lt;\n</details>",
    "line one\r\nline two\r\n",
    "spaces at the end   \nnext line  ",
    "```python\nprint(1)\n```\n\n````\nfour\n````",
]


def test_export_01_text_does_not_change(tmp_path):
    messages, parent = [], ROOT
    for t in HARD_TEXTS:
        for sender in ("human", "assistant"):
            uuid = f"m{len(messages) + 1}"
            messages.append(msg(uuid, parent, sender, len(messages) + 1, [text(t)]))
            parent = uuid
    proc, chats_dir = run(tmp_path, [chat("Hard", messages)], [("Hard", "00-hard.md")])
    assert proc.returncode == 0, proc.stderr
    md = read(chats_dir / "00-hard.md")
    for t in HARD_TEXTS:
        assert md.count(t) >= 2, repr(t)  # once for each sender


def test_export_02_human_text_is_in_one_fence(tmp_path):
    human = "start\n```\ninside three\n```\n````\ninside four\n````\nend"
    messages = [
        msg("m1", ROOT, "human", 1, [text(human)]),
        msg("m2", "m1", "assistant", 2, [text("plain reply")]),
    ]
    proc, chats_dir = run(tmp_path, [chat("Fence", messages)], [("Fence", "00-fence.md")])
    assert proc.returncode == 0, proc.stderr
    assert fenced_blocks(read(chats_dir / "00-fence.md")) == [human + "\n"]


def test_export_03_main_branch_only_in_tree_order(tmp_path):
    proc, chats_dir = run(tmp_path, [branch_chat()], [("Branch chat", "00-branch.md")])
    assert proc.returncode == 0, proc.stderr
    md = read(chats_dir / "00-branch.md")
    main = ["MAIN-1-HUMAN", "MAIN-2-ASSISTANT", "MAIN-3-HUMAN", "MAIN-4-ASSISTANT"]
    positions = [md.index(t) for t in main]
    assert positions == sorted(positions)
    for t in ["SIDE-ROOT-HUMAN", "SIDE-ROOT-ASSISTANT", "SIDE-EDIT-HUMAN"]:
        assert t not in md
    assert len(re.findall(r"^## \d+\. ", md, flags=re.M)) == 4


def test_export_04_note_tells_what_is_not_in_the_file(tmp_path):
    proc, chats_dir = run(tmp_path, [branch_chat()], [("Branch chat", "00-branch.md")])
    assert proc.returncode == 0, proc.stderr
    md = read(chats_dir / "00-branch.md")
    note = "\n".join(line for line in md.splitlines() if line.startswith(">"))
    assert "4 messages in side branches" in note
    for part in [
        "document 1",
        "injected_prompt_block 1",
        "thinking 1",
        "tool_result 1",
        "tool_use 1",
    ]:
        assert part in note, part
    for t in [
        "INJECTED-TOKEN",
        "DOC-TITLE-TOKEN",
        "THINK-SUMMARY-TOKEN",
        "TOOL-INPUT-TOKEN",
        "TOOL-RESULT-TOKEN",
        "SIDE-TOOL-TOKEN",
        "PLACEHOLDER-TOKEN",
        "not supported on your current device",
        "ACCOUNT-SECRET-0001",
    ]:
        assert t not in md, t


def test_export_05_only_manifest_chats(tmp_path):
    export = [
        simple_chat("Chat A", "chat-a"),
        chat("Chat B", [msg("b1", ROOT, "human", 1, [text("OTHER-B-TOKEN")])], uuid="chat-b"),
        chat("Chat C", [msg("c1", ROOT, "human", 1, [text("OTHER-C-TOKEN")])], uuid="chat-c"),
    ]
    proc, chats_dir = run(tmp_path, export, [("Chat A", "00-a.md")])
    assert proc.returncode == 0, proc.stderr
    assert md_files(chats_dir) == ["00-a.md"]
    for path in tmp_path.rglob("*.md"):
        assert "OTHER-B-TOKEN" not in read(path)
        assert "OTHER-C-TOKEN" not in read(path)


def test_export_06_header_headings_and_terminal_line(tmp_path):
    proc, chats_dir = run(tmp_path, [simple_chat()], [("Test chat", "00-test.md")])
    assert proc.returncode == 0, proc.stderr
    md = read(chats_dir / "00-test.md")
    assert md.startswith("# Test chat\n")
    for part in [
        "chat-0001",
        "2026-10-23T10:00:00.000000Z",
        "2026-10-23T11:00:00.000000Z",
        "Messages in this file: 2",
        "## 1. human · 2026-10-23T10:01:00.000000Z",
        "## 2. assistant · 2026-10-23T10:02:00.000000Z",
    ]:
        assert part in md, part
    assert "00-test.md" in proc.stdout
    assert "2 messages" in proc.stdout


def test_export_07_message_with_no_text_block(tmp_path):
    messages = [
        msg("m1", ROOT, "human", 1, [text("question")]),
        msg("m2", "m1", "assistant", 2, [tool_use("ls"), tool_result("out")]),
    ]
    proc, chats_dir = run(tmp_path, [chat("Tools", messages)], [("Tools", "00-tools.md")])
    assert proc.returncode == 0, proc.stderr
    md = read(chats_dir / "00-tools.md")
    heading = "## 2. assistant · 2026-10-23T10:02:00.000000Z"
    assert heading in md
    assert md.split(heading, 1)[1].lstrip("\n").startswith(NO_TEXT)


def test_export_08_same_input_same_output(tmp_path):
    proc, chats_dir = run(tmp_path, [branch_chat()], [("Branch chat", "00-branch.md")])
    assert proc.returncode == 0, proc.stderr
    out = chats_dir / "00-branch.md"
    first = out.read_bytes()
    out.write_text("changed by hand", encoding="utf-8")
    proc, _ = run(tmp_path, [branch_chat()], [("Branch chat", "00-branch.md")])
    assert proc.returncode == 0, proc.stderr
    assert out.read_bytes() == first


def test_export_09_input_does_not_change(tmp_path):
    export_file = tmp_path / "archive" / "conversations.json"
    export_file.parent.mkdir()
    export_file.write_text(json.dumps([branch_chat()], indent=1), encoding="utf-8")
    chats_dir = tmp_path / "chats"
    chats_dir.mkdir()
    manifest_file = chats_dir / "manifest.toml"
    manifest_file.write_text(toml_manifest([("Branch chat", "00-branch.md")]), encoding="utf-8")
    before = (sha256(export_file), sha256(manifest_file))
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), str(export_file), str(manifest_file)],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    assert (sha256(export_file), sha256(manifest_file)) == before


def _no_content():
    c = simple_chat()
    del c["chat_messages"][1]["content"]
    return [c]


def _content_is_string():
    c = simple_chat()
    c["chat_messages"][1]["content"] = "text"
    return [c]


def _parent_not_in_chat():
    c = simple_chat()
    c["chat_messages"][1]["parent_message_uuid"] = "m-unknown"
    return [c]


def _loop():
    return [
        chat(
            "Test chat",
            [
                msg("m1", "m2", "human", 1, [text("a")]),
                msg("m2", "m1", "assistant", 2, [text("b")]),
                msg("m3", "m1", "human", 3, [text("c")]),
            ],
        )
    ]


def _same_newest_time():
    return [
        chat(
            "Test chat",
            [
                msg("m1", ROOT, "human", 1, [text("a")]),
                msg("m2", "m1", "assistant", 2, [text("b")]),
                msg("m3", "m1", "assistant", 2, [text("c")]),
            ],
        )
    ]


def _bad_sender():
    c = simple_chat()
    c["chat_messages"][1]["sender"] = "system"
    return [c]


OK_MANIFEST = [("Test chat", "00-test.md")]

ERROR_CASES = {
    "1-export-not-json": ("{not json", OK_MANIFEST, "not valid JSON"),
    "1-manifest-not-toml": ([simple_chat()], "title = ", "not valid TOML"),
    "2-key-missing": (_no_content(), OK_MANIFEST, "is missing"),
    "2-wrong-type": (_content_is_string(), OK_MANIFEST, "wrong type"),
    "3-file-with-path": ([simple_chat()], [("Test chat", "../00-test.md")], "plain file name"),
    "3-file-not-md": ([simple_chat()], [("Test chat", "00-test.txt")], "plain file name"),
    "4-same-title": (
        [simple_chat()],
        [("Test chat", "00-a.md"), ("Test chat", "00-b.md")],
        "same title",
    ),
    "4-same-file": (
        [simple_chat(), simple_chat("Other chat", "chat-0002")],
        [("Test chat", "00-a.md"), ("Other chat", "00-a.md")],
        "same file",
    ),
    "5-no-match": ([simple_chat()], [("Missing chat", "00-test.md")], "matches no chat"),
    "5-two-matches": (
        [simple_chat(), simple_chat(uuid="chat-0002")],
        OK_MANIFEST,
        "matches 2 chats",
    ),
    "6-no-messages": ([chat("Test chat", [])], OK_MANIFEST, "has no messages"),
    "7-parent-not-in-chat": (_parent_not_in_chat(), OK_MANIFEST, "is not in the chat"),
    "7-loop": (_loop(), OK_MANIFEST, "loop"),
    "8-same-newest-time": (_same_newest_time(), OK_MANIFEST, "same newest created_at"),
    "9-bad-sender": (_bad_sender(), OK_MANIFEST, "sender"),
    "second-chat-has-error": (
        [simple_chat("Good chat", "chat-good"), *_bad_sender()],
        [("Good chat", "00-good.md"), ("Test chat", "01-bad.md")],
        "sender",
    ),
}


@pytest.mark.parametrize("case", ERROR_CASES)
def test_export_10_errors_stop_the_tool(tmp_path, case):
    export, manifest, cause = ERROR_CASES[case]
    proc, chats_dir = run(tmp_path, export, manifest)
    assert proc.returncode == 1
    assert proc.stderr.startswith("export_chats:")
    assert cause in proc.stderr
    assert md_files(chats_dir) == []
