"""Move a task's reviewed subtasks to `done` before closing, without a model.

Usage: python3 "${CLAUDE_PLUGIN_ROOT}/tools/prepare_close.py" TASK-ID
Requires: last review result Approved, QA Passed when the task has `qa`, every "Đã sửa?" cell closed,
check_task (close) clean, and no subtask still before `in_review`. Then sets `in_review` / `in_qa`
subtasks (file, table row, history) to `done`. Any failed check: nothing changes. Does not commit;
run close_task.py next. Standard library only.
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
import dod_report  # noqa: E402
import task_step  # noqa: E402

REVIEWED = ("in_review", "in_qa")


def verdict_errors(task_text: str) -> list[str]:
    errors = []
    results = dod_report.result_lines(ct.section(task_text, 4))
    if not results or not results[-1].startswith("**Kết quả:** ✅ Approved"):
        errors.append("dòng `**Kết quả:**` cuối của mục 4 chưa là ✅ Approved")
    if ct.frontmatter(task_text).get("qa"):
        qa = dod_report.result_lines(ct.section(task_text, 5))
        if not qa or not qa[-1].startswith("**Kết quả:** ✅ Passed"):
            errors.append("dòng `**Kết quả:**` cuối của mục 5 chưa là ✅ Passed")
    return errors


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="prepare_close.py", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("task_id")
    args = parser.parse_args(argv)
    tid = args.task_id
    task_md = ct.find_task(tid)
    tdir = task_md.parent
    text = task_md.read_text(encoding="utf-8")
    errors = verdict_errors(text) + check_task.gate_errors(tdir, tid, "close")
    move: list[tuple[Path, str, str, str]] = []
    for sub in sorted(tdir.glob(f"{tid}-S*.md")):
        body = sub.read_text(encoding="utf-8")
        status = ct.frontmatter(body).get("status", "?")
        sid = "-".join(sub.name.split("-")[:3])
        if status in REVIEWED:
            move.append((sub, sid, status, body))
        elif status != "done":
            errors.append(f"{sid} đang `{status}`, chưa qua review")
    if errors:
        print(f"Chưa chuẩn bị đóng {tid} (chưa sửa gì):")
        print("\n".join(f"- {e}" for e in errors))
        return 1
    log_md = tdir / "log.md"
    history = log_md.read_text(encoding="utf-8") if log_md.exists() else None
    now = datetime.now().strftime(task_step.TIME)
    for sub, sid, status, body in move:
        row = f"| {now} | prepare-close | {sid} {status} → done |"
        text = task_step.set_row_status(text, sid, "done")
        if history is None:
            text = ct.add_history_row(text, row)
        else:
            history = ct.add_history_row(history, row)
    # A row left behind by an earlier manual change still has to match the file.
    for sid, status in ct.subtask_rows(text, tid):
        if status.strip("*` ") != "done" and list(tdir.glob(f"{sid}-*.md")):
            text = task_step.set_row_status(text, sid, "done")
    for sub, _, _, body in move:
        sub.write_text(task_step.put_field(body, "status", "done"), encoding="utf-8")
    task_md.write_text(text, encoding="utf-8")
    if history is not None:
        log_md.write_text(history, encoding="utf-8")
    print(f"{tid}: chuyển done " + (", ".join(sid for _, sid, _, _ in move) or "không subtask nào (đã done)"))
    print(f"Bước tiếp: close_task.py {tid} --pr --handoff")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
