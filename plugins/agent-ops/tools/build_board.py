#!/usr/bin/env python3
"""Generate management/BOARD.md from task/epic frontmatter and decision tickets.

Usage: python3 management/tools/build_board.py            # rewrite BOARD.md
       python3 management/tools/build_board.py --check    # rc 1 if BOARD.md differs from the generated text

Everything outside the PM block (between PM_BEGIN and PM_END) is generated: do not edit it by hand.
The PM block of the existing BOARD.md is carried over unchanged. Stdlib only.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _project import mgmt_rel, project_root  # noqa: E402

ROOT = project_root()
PM_BEGIN = "<!-- PM:BEGIN -->"
PM_END = "<!-- PM:END -->"
PM_PLACEHOLDER = "_(chưa có ghi chú)_"
PENDING_STATUSES = ("open", "provisional")
# Display order of the task groups; unknown statuses are appended after these, alphabetically.
STATUS_ORDER = ("in_progress", "in_review", "in_qa", "ready", "blocked", "backlog", "done")
COLUMNS = ("ID", "Tiêu đề", "Epic", "Người làm", "Ưu tiên", "Ngày dự kiến")
EMPTY = "—"
FRONTMATTER_RE = re.compile(r"^---\r?\n(.*?)\r?\n---\r?\n", re.S)


def read_frontmatter(path: Path) -> dict[str, str]:
    """Flat `key: value` pairs of the leading frontmatter; quotes and trailing `# comment` removed."""
    m = FRONTMATTER_RE.match(path.read_text(encoding="utf-8"))
    meta: dict[str, str] = {}
    if not m:
        return meta
    for line in m.group(1).splitlines():
        if ":" not in line or line.startswith((" ", "\t", "#")):
            continue
        key, value = line.split(":", 1)
        value = re.sub(r"\s+#.*$", "", value).strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        meta[key.strip()] = value
    return meta


def cell(value: str) -> str:
    return (value or EMPTY).replace("|", "\\|").replace("\n", " ")


PM_BLOCK_RE = re.compile(r"^" + re.escape(PM_BEGIN) + r"[ \t]*\r?\n(.*?)^" + re.escape(PM_END) + r"[ \t]*$", re.S | re.M)


def extract_pm_block(board_text: str) -> str:
    """Text between the marker lines (each marker alone on its line); placeholder when absent or empty."""
    m = PM_BLOCK_RE.search(board_text)
    return (m.group(1).strip("\n") if m else "") or PM_PLACEHOLDER


def load_tasks(root: Path) -> list[dict[str, str]]:
    tasks = []
    for path in sorted((root / mgmt_rel(root) / "tasks").glob("**/task.md")):
        meta = read_frontmatter(path)
        meta["_rel"] = path.relative_to(root / mgmt_rel(root)).as_posix()
        meta.setdefault("id", path.parent.name)
        tasks.append(meta)
    return sorted(tasks, key=lambda t: t["id"])


def load_epics(root: Path) -> list[dict[str, str]]:
    epics = []
    for path in sorted((root / mgmt_rel(root) / "tasks").glob("*/epic.md")):
        meta = read_frontmatter(path)
        meta["_rel"] = path.relative_to(root / mgmt_rel(root)).as_posix()
        meta.setdefault("id", path.parent.name)
        epics.append(meta)
    return sorted(epics, key=lambda e: e["id"])


def load_pending_drs(root: Path) -> list[dict[str, str]]:
    """Tickets waiting for the PO (status open or provisional), by id."""
    drs = []
    for path in sorted((root / mgmt_rel(root) / "decision-requests").glob("DR-*.md")):
        meta = read_frontmatter(path)
        if meta.get("status") in PENDING_STATUSES:
            meta["_rel"] = "decision-requests/" + path.name
            meta.setdefault("id", path.stem)
            drs.append(meta)
    return sorted(drs, key=lambda d: d["id"])


def task_table(tasks: list[dict[str, str]]) -> list[str]:
    lines = ["| " + " | ".join(COLUMNS) + " |", "|" + "---|" * len(COLUMNS)]
    for t in tasks:
        row = (f"[{t['id']}]({t['_rel']})", t.get("title", ""), t.get("epic", ""),
               t.get("assignee", ""), t.get("priority", ""), t.get("planned_date", ""))
        lines.append("| " + " | ".join(cell(c) if i else c for i, c in enumerate(row)) + " |")
    return lines


def epic_section(epics: list[dict[str, str]], tasks: list[dict[str, str]]) -> list[str]:
    lines = ["## Epic", "", "| Epic | Tiến độ (task done/tổng) | Trạng thái |", "|---|---|---|"]
    for e in epics:
        mine = [t for t in tasks if t.get("epic") == e["id"]]
        done = sum(1 for t in mine if t.get("status") == "done")
        lines.append(f"| [{e['id']}]({e['_rel']}) {cell(e.get('title', ''))} | {done}/{len(mine)} | {cell(e.get('status', ''))} |")
    return lines


def pending_section(drs: list[dict[str, str]]) -> list[str]:
    lines = ["## ⚠️ Đang chờ Product Owner", ""]
    if not drs:
        lines.append("Không có phiếu DR `open` hoặc `provisional`.")
    for d in drs:
        deadline = d.get("deadline", "")
        suffix = f" — hạn {deadline}" if deadline else ""
        lines.append(f"- [{d['id']}]({d['_rel']}) ({d.get('status', '')}) {d.get('title', '')}{suffix}")
    lines += ["", "Chi tiết mọi phiếu: [DECISIONS-INBOX.md](DECISIONS-INBOX.md)."]
    return lines


def status_sections(tasks: list[dict[str, str]]) -> list[str]:
    by_status: dict[str, list[dict[str, str]]] = {}
    for t in tasks:
        by_status.setdefault(t.get("status", "") or "(thiếu status)", []).append(t)
    known = [s for s in STATUS_ORDER if s in by_status]
    unknown = sorted(s for s in by_status if s not in STATUS_ORDER)
    lines: list[str] = []
    for status in known + unknown:
        group = by_status[status]
        lines += ["", f"### {status} ({len(group)})", ""] + task_table(group)
    return lines


def generate(root: Path, pm_block: str) -> str:
    tasks = load_tasks(root)
    out = [
        "# Bảng công việc",
        "",
        f"> **Sinh tự động** bằng `build_board.py` (plugin agent-ops) từ frontmatter `task.md`, `epic.md` và phiếu DR "
        f"trong `{mgmt_rel(root)}/`. Không sửa tay, trừ khối ghi chú của PM giữa `{PM_BEGIN}` và `{PM_END}` (được giữ nguyên khi sinh lại).",
        "",
        *epic_section(load_epics(root), tasks),
        "",
        *pending_section(load_pending_drs(root)),
        "",
        "## Ghi chú của PM",
        "",
        PM_BEGIN,
        pm_block,
        PM_END,
        "",
        f"## Task theo trạng thái ({len(tasks)})",
        *status_sections(tasks),
    ]
    return "\n".join(out) + "\n"


def board_path(root: Path) -> Path:
    return root / mgmt_rel(root) / "BOARD.md"


def generate_for(root: Path) -> str:
    """Generated text using the PM block already in BOARD.md (placeholder when the file is missing)."""
    path = board_path(root)
    return generate(root, extract_pm_block(path.read_text(encoding="utf-8")) if path.exists() else PM_PLACEHOLDER)


def board_mismatch(root: Path) -> str | None:
    """None when BOARD.md equals the regenerated text; otherwise a one-line message."""
    path = board_path(root)
    if not path.exists():
        m = mgmt_rel(root)
        return f"{m}/BOARD.md không tồn tại; chạy python3 {m}/tools/build_board.py"
    if path.read_text(encoding="utf-8") != generate_for(root):
        m = mgmt_rel(root)
        return f"{m}/BOARD.md lệch bản sinh lại (sửa tay ngoài khối PM, hoặc task/phiếu đổi); chạy python3 {m}/tools/build_board.py"
    return None


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="build_board.py", allow_abbrev=False, description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="do not write; rc 1 if BOARD.md is out of date")
    args = parser.parse_args(argv)
    if args.check:
        msg = board_mismatch(ROOT)
        print(msg or "BOARD.md khớp bản sinh")
        return 1 if msg else 0
    board_path(ROOT).write_text(generate_for(ROOT), encoding="utf-8")
    print(f"Đã ghi {board_path(ROOT).relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
