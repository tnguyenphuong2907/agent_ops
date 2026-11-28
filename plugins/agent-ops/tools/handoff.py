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


def bullets(text: str) -> list[str]:
    """Blocks of the file: a line plus its indented continuation lines; headings and blanks dropped."""
    blocks: list[str] = []
    for line in text.splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        if line[:1] in " \t" and blocks:
            blocks[-1] += "\n" + line
        else:
            blocks.append(line)
    return blocks


def carried(old: str, prs: set[int]) -> list[str]:
    """Old blocks still worth keeping; `prs` are the PR numbers the new report covers."""
    keep = []
    for block in bullets(old):
        row = PR_ROW.match(block)
        if row and (int(row.group(1)) in prs or row.group(2).startswith("merge")):
            continue
        if STATE.match(block) or block == DEFAULT_NEXT or DONE.match(block):
            continue
        keep.append(block)
    return keep


def compose(old: str, source: str, fresh: list[str], prs: set[int] = frozenset(), today: str = "") -> str:
    """New file text. Carried blocks are never cut; fresh lines are cut first to stay within MAX_LINES."""
    kept = carried(old, set(prs))
    kept = [k for k in kept if k not in fresh]
    tail = [] if any(NEXT.search(b) for b in kept + fresh) else [DEFAULT_NEXT]
    head = [f"# Handoff ({today or date.today().isoformat()}, sau {source})", ""]
    used = len(head) + len(tail) + sum(b.count("\n") + 1 for b in kept)
    room = max(MAX_LINES - used, 1)
    if len(fresh) > room:
        fresh = fresh[:room - 1] + [f"- … ({len(fresh) - room + 1} dòng bị lược)"]
    return "\n".join(head + kept + fresh + tail) + "\n"


def write(path: Path, source: str, fresh: list[str], prs: set[int] = frozenset()) -> int:
    """Write the file; returns its line count so the caller can warn above MAX_LINES."""
    old = path.read_text(encoding="utf-8") if path.is_file() else ""
    text = compose(old, source, fresh, prs)
    path.write_text(text, encoding="utf-8")
    return len(text.splitlines())
