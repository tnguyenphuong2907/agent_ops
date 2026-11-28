"""Record the start or end of a subtask in one command, without a model.

Usage: python3 "${CLAUDE_PLUGIN_ROOT}/tools/task_step.py" SUBTASK-ID start|done [--role R] [--commit SHA] [--note TEXT]
  start: subtask ready (or returned from in_review / in_qa) -> in_progress; a `ready` task follows.
  done:  in_progress -> in_review; refuses an unfilled self-check table or a missing plan.
Writes the status, the subtask table row, a history row stamped with the clock, `actual_hours`
(added across rounds) and, with --note, a progress line. Does not commit. Standard library only.
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_task  # noqa: E402
import close_task as ct  # noqa: E402

TIME = "%Y-%m-%d %H:%M"
FROM = {"start": ("ready", "in_review", "in_qa"), "done": ("in_progress",)}
TO = {"start": "in_progress", "done": "in_review"}


# ---------- pure helpers (unit tested) ----------

def put_field(text: str, key: str, value: str) -> str:
    """Set `key:` in the frontmatter, also when it is empty; keeps a trailing `# comment`."""
    head, sep, rest = text.partition("\n---")
    def repl(m: re.Match) -> str:
        comment = f"   {m.group(1).strip()}" if m.group(1) else ""
        return f"{key}: {value}{comment}"
    head, n = re.subn(rf"(?m)^{key}:[ \t]*[^#\n]*?([ \t]*#[^\n]*)?$", repl, head, count=1)
    if not n:
        head += f"\n{key}: {value}"
    return head + sep + rest


def set_row_status(text: str, sub_id: str, status: str) -> str:
    """Last cell of the `| <sub_id> | ... |` row of the subtask table."""
    def repl(m: re.Match) -> str:
        return f"{m.group(1)} {status} |"
    return re.sub(rf"(?m)^(\| {sub_id} \|(?:.*\|)?)[^|\n]*\|[ \t]*$", repl, text, count=1)


def started_at(history: str, sub_id: str) -> datetime | None:
    """Clock of the latest history row that moved the subtask to in_progress."""
    rows = re.findall(rf"(?m)^\| (\d{{4}}-\d\d-\d\d \d\d:\d\d) \|[^|\n]*\| {sub_id} [^|\n]*→ in_progress", history)
    return datetime.strptime(rows[-1], TIME) if rows else None


def add_progress(text: str, line: str) -> str:
    """Append `line` at the end of the `## Tiến trình` section, replacing a lone `-` placeholder."""
    m = re.search(r"(?ms)^## Tiến trình[^\n]*\n(.*?)(?=^## |\Z)", text)
    if not m:
        return text.rstrip("\n") + f"\n\n## Tiến trình  ·  _dev_\n{line}\n"
    body = re.sub(r"(?m)^-[ \t]*$\n?", "", m.group(1)).rstrip("\n")
    return text[:m.start(1)] + f"{body}\n{line}\n\n" + text[m.end(1):]


# ---------- main ----------

def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="task_step.py", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("subtask_id")
    parser.add_argument("action", choices=("start", "done"))
    parser.add_argument("--role")
    parser.add_argument("--commit")
    parser.add_argument("--note")
    args = parser.parse_args(argv)
    sid = args.subtask_id
    if not re.fullmatch(r"E\d\d-T\d\d-S\d\d", sid):
        print(f"Dừng: `{sid}` không phải mã subtask.")
        return 2
    task_md = ct.find_task(sid[:-4])
    subs = sorted(task_md.parent.glob(f"{sid}-*.md"))
    if len(subs) != 1:
        print(f"Dừng: tìm thấy {len(subs)} file cho {sid}.")
        return 2
    sub = subs[0]
    text = sub.read_text(encoding="utf-8")
    fm = ct.frontmatter(text)
    old, new = fm.get("status", "?"), TO[args.action]
    if old not in FROM[args.action]:
        print(f"Dừng: {sid} đang `{old}`, `{args.action}` chỉ chạy từ {' | '.join(FROM[args.action])}.")
        return 1
    errors = check_task.plan_errors(sub.name, text)
    if args.action == "done":
        errors += check_task.selfcheck_errors(sub.name, text)
    if errors:
        print("\n".join(f"lỗi: {e}" for e in errors))
        return 1

    now = datetime.now().replace(second=0, microsecond=0)
    role = args.role or fm.get("assignee") or "dev"
    log_md = task_md.parent / "log.md"
    task_text = task_md.read_text(encoding="utf-8")
    history = log_md.read_text(encoding="utf-8") if log_md.exists() else task_text
    text = put_field(text, "status", new)
    hours = None
    if args.action == "done":
        begin = started_at(history, sid)
        if begin:
            hours = round((now - begin).total_seconds() / 3600, 1)
            try:
                total = float(fm.get("actual_hours") or 0) + hours
            except ValueError:
                total = hours
            text = put_field(text, "actual_hours", f"{total:g}")
        if args.commit:
            text = put_field(text, "commit", args.commit)
    if args.note:
        span = f"{now.strftime(TIME)}" + (f", {hours:g} h" if hours is not None else "")
        commit = f"; commit {args.commit}" if args.commit else ""
        text = add_progress(text, f"- {role} ({span}{commit}): {args.note}")

    rows = [f"| {now.strftime(TIME)} | {role} | {sid} {old} → {new} |"]
    task_text = set_row_status(task_text, sid, new)
    if args.action == "start" and ct.frontmatter(task_text).get("status") == "ready":
        task_text = put_field(task_text, "status", "in_progress")
        rows.append(f"| {now.strftime(TIME)} | {role} | {sid[:-4]} ready → in_progress |")
    history = history if log_md.exists() else task_text
    for row in rows:
        history = ct.add_history_row(history, row)
    if log_md.exists():
        log_md.write_text(history, encoding="utf-8")
    else:
        task_text = history
    sub.write_text(text, encoding="utf-8")
    task_md.write_text(task_text, encoding="utf-8")
    print(f"{sid}: {old} → {new} ({now.strftime(TIME)}" + (f", {hours:g} h" if hours is not None else "") + ")")
    if args.action == "done" and hours is None:
        print("cảnh báo: không thấy dòng bắt đầu trong Lịch sử, không tính actual_hours.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
