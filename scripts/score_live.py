"""Score the output of a recorded live run against an eval script (C7, D-064, D-065).

The people in the call read a script of docs/eval/scripts.md (C7: script S5). The program
output was saved with `tee` (for example test-results/c7-live-p1.txt). This script reads the
blocks of that output (output.py format), joins the texts of each side in the order of the
output, and compares them with the reference lines of the same side in script order, as the C3
main numbers do (D-046 point 2): WER and CER on the Armenian text (D-047), chrF on the English
text. Side "mic" is the label "Me"; side "call" is every other label.

It also counts the blocks, the empty texts (D-031), the "#" marks (Seamless writes "#err" for a
hesitation sound, C7), the HY lines with Latin letters, the question marks U+055E, the speaker
labels, and the totals. The growth of the totals compares the mean of the first third of the
blocks with the mean of the last third (L-07: "the totals do not grow").

Usage:
    uv run --no-sync python scripts/score_live.py test-results/c7-live-p1.txt --script s5

This is a research tool (as scripts/bakeoff.py). The program does not use it.
"""

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from tir_asr.eval.data import read_references
from tir_asr.eval.metrics import cer, chrf, wer

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_MD = ROOT / "docs" / "eval" / "scripts.md"
HEAD = re.compile(r"^\[(\d\d):(\d\d):(\d\d)\] (.+)$")
TOTAL = re.compile(r"\| Total (\d+\.\d\d)s\]$")
LATIN = re.compile(r"[A-Za-z]")
NO_TEXT = "(no text)"
QUESTION_MARK = "՞"


@dataclass
class Block:
    label: str
    seconds: int
    hy: str
    en: str
    total: float

    @property
    def side(self) -> str:
        return "mic" if self.label == "Me" else "call"


def parse_blocks(text: str) -> list[Block]:
    """The blocks of the program output, in the order of the output. Other lines are ignored."""
    blocks = []
    head = None
    hy = en = ""
    for line in text.splitlines():
        if match := HEAD.match(line):
            head, hy, en = match, "", ""
        elif head is not None and line.startswith(" HY: "):
            hy = line.removeprefix(" HY: ")
        elif head is not None and line.startswith(" EN: "):
            en = line.removeprefix(" EN: ")
        elif head is not None and (total := TOTAL.search(line)):
            hours, minutes, seconds = (int(head.group(n)) for n in (1, 2, 3))
            seconds += hours * 3600 + minutes * 60
            blocks.append(Block(head.group(4), seconds, hy, en, float(total.group(1))))
            head = None
    return blocks


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else float("nan")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("output", type=Path, help="the saved program output")
    parser.add_argument("--script", required=True, help="the script ID, for example s5")
    parser.add_argument("--scripts-md", type=Path, default=SCRIPTS_MD)
    args = parser.parse_args(argv)

    blocks = parse_blocks(args.output.read_text(encoding="utf-8"))
    if not blocks:
        print(f"score_live: no blocks in {args.output}", file=sys.stderr)
        return 1
    lines = read_references(args.scripts_md, args.script)
    name = args.output.name
    print(f"file {name}; script {args.script}: {len(lines)} lines; {len(blocks)} blocks")

    for side in ("mic", "call"):
        refs = [line for line in lines if line.side == side]
        side_blocks = [b for b in blocks if b.side == side]
        texts = [b for b in side_blocks if b.hy != NO_TEXT]
        hy_hyp = " ".join(b.hy for b in texts)
        en_hyp = " ".join(b.en for b in texts)
        hy_ref = " ".join(line.hy for line in refs)
        en_ref = " ".join(line.en for line in refs)
        labels = sorted({b.label for b in side_blocks})
        print(
            f"side {side}: {len(refs)} reference lines; {len(side_blocks)} blocks, "
            f"{len(side_blocks) - len(texts)} empty texts; labels {labels}"
        )
        word_rate = wer([hy_ref], [hy_hyp]) * 100
        char_rate = cer([hy_ref], [hy_hyp]) * 100
        score = chrf([en_ref], [en_hyp])
        print(f"  WER {word_rate:.1f} %, CER {char_rate:.1f} %, chrF {score:.1f}")
        latin = sum(bool(LATIN.search(b.hy)) for b in texts)
        print(
            f"  '#' marks: HY {hy_hyp.count('#')}, EN {en_hyp.count('#')}; HY lines with Latin "
            f"letters {latin}; question marks {QUESTION_MARK} {hy_hyp.count(QUESTION_MARK)} "
            f"(reference {hy_ref.count(QUESTION_MARK)})"
        )

    totals = [b.total for b in blocks]
    third = max(1, len(totals) // 3)
    print(
        f"totals: min {min(totals):.2f} s, mean {mean(totals):.2f} s, max {max(totals):.2f} s; "
        f"mean of the first third {mean(totals[:third]):.2f} s, "
        f"of the last third {mean(totals[-third:]):.2f} s"
    )
    for b in blocks:
        if "#" in b.hy or "#" in b.en or LATIN.search(b.hy):
            print(f"  mark or Latin: [{b.seconds} s] {b.label}: HY {b.hy!r}; EN {b.en!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
