"""Rewrite `<mgmt>/HANDOFF.md` without losing the next steps already written there. Standard library only.

`merge_pr.py` and `close_task.py --handoff` share this: bullets of the old file are carried over unless
a tool wrote them (merged PR rows, state line, default next step) or they are marked done
(`- [x]`, `- ~~...`, `- ✅`).
"""
from __future__ import annotations

import re
from datetime import date
from pathlib import Path

MAX_LINES = 15
DEFAULT_NEXT = "- Bước tiếp: chọn task `ready` kế tiếp theo backlog (PM)."
PR_ROW = re.compile(r"^- #(\d+) [\w./-]+: (.*)$")
STATE = re.compile(r"^- Trạng thái [\w./-]+: [0-9a-f]{7,}")
DONE = re.compile(r"^[-*] (\[[xX]\]|~~|✅)")
NEXT = re.compile(r"(?i)bước tiếp|việc tiếp")
WAITING = re.compile(r"(?i)chờ (?:PO: mp|merge) #?(\d+)")


def bullets(text: str) -> list[str]:
    """Blocks of the file: a line plus its indented continuation lines.

    Blanks and headings are dropped, except a "next step" section heading, which becomes a bullet.
    """
    blocks: list[str] = []
    for line in text.splitlines():
        if line.startswith("##") and NEXT.search(line):
            blocks.append("- " + line.lstrip("# "))
        elif not line.strip() or line.startswith("#"):
            continue
        elif line[:1] in " \t" and blocks:
            blocks[-1] += "\n" + line
        else:
            blocks.append(line)
    return blocks


def carried(old: str, prs: set[int], merged: set[int] = frozenset()) -> list[str]:
    """Old blocks still worth keeping; `prs` are the PR numbers the new report covers, `merged` those now merged."""
    keep = []
    for block in bullets(old):
        row = PR_ROW.match(block)
        if row and (int(row.group(1)) in prs or row.group(2).startswith("merge")):
            continue
        waiting = WAITING.search(block)
        if waiting and int(waiting.group(1)) in merged:
            continue
        if STATE.match(block) or block == DEFAULT_NEXT or DONE.match(block):
            continue
        keep.append(block)
    return keep


def compose(old: str, source: str, fresh: list[str], prs: set[int] = frozenset(), today: str = "") -> str:
    """New file text. Only fresh PR rows are cut to stay within MAX_LINES; every other line is kept."""
    merged = {int(m.group(1)) for line in fresh if (m := PR_ROW.match(line)) and m.group(2).startswith("merge")}
    kept = [k for k in carried(old, set(prs), merged) if k not in fresh]
    tail = [] if any(NEXT.search(b) for b in kept + fresh) else [DEFAULT_NEXT]
    head = [f"# Handoff ({today or date.today().isoformat()}, sau {source})", ""]
    rows = [line for line in fresh if PR_ROW.match(line)]
    used = len(head) + len(tail) + sum(b.count("\n") + 1 for b in kept) + len(fresh) - len(rows)
    room = max(MAX_LINES - used, 1)
    if len(rows) > room:
        dropped = set(rows[room - 1:])
        first = fresh.index(rows[room - 1])
        fresh = [line for line in fresh if line not in dropped]
        fresh.insert(first, f"- … ({len(dropped)} dòng PR bị lược)")
    return "\n".join(head + kept + fresh + tail) + "\n"


def write(path: Path, source: str, fresh: list[str], prs: set[int] = frozenset()) -> int:
    """Write the file; returns its line count so the caller can warn above MAX_LINES."""
    old = path.read_text(encoding="utf-8") if path.is_file() else ""
    text = compose(old, source, fresh, prs)
    path.write_text(text, encoding="utf-8")
    return len(text.splitlines())
