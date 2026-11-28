"""Print the brief skeleton for handing one subtask to an agent, without a model.

Usage: python3 "${CLAUDE_PLUGIN_ROOT}/tools/brief.py" SUBTASK-ID [--round N] [--plan]
Prints the state snapshot (task-management § Giao việc) and the four lines brief_guard.py requires,
filled from the task files. Replace every `<điền …>` before spawning; the hook denies leftovers.
--plan: planning run for a `plan: opus` subtask. Standard library only.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_task  # noqa: E402
import close_task as ct  # noqa: E402
import dod_report  # noqa: E402

ROW = re.compile(r"^[ \t]*status:")


def pending_drs(task_text: str) -> list[str]:
    """`DR-xxx (status)` of every decision request of section 6 that is not decided."""
    found = []
    for dr in sorted(set(re.findall(r"DR-\d{3}", ct.COMMENT.sub("", ct.section(task_text, 6))))):
        files = list(ct.DRS.glob(f"{dr}-*.md"))
        status = ct.frontmatter(files[0].read_text(encoding="utf-8")).get("status", "?") if files else "không thấy file"
        if status != "decided":
            found.append(f"{dr} ({status})")
    return found


def open_findings(task_text: str) -> list[str]:
    return [f"#{num} {severity}" for num, severity, fixed in dod_report.findings(ct.section(task_text, 4))
            if fixed in check_task.BLANK or re.match(r"(?i)(chờ\b|⏳|mở\b)", fixed)]


def done_list(tdir: Path, tid: str) -> tuple[list[str], list[str]]:
    """(done subtasks with commit, other subtasks with status)."""
    done, other = [], []
    for sub in sorted(tdir.glob(f"{tid}-S*.md")):
        fm = ct.frontmatter(sub.read_text(encoding="utf-8"))
        sid = "-".join(sub.name.split("-")[:3])
        status = fm.get("status", "?")
        if status == "done":
            done.append(sid[-3:] + (f" (commit {fm['commit']})" if fm.get("commit") else ""))
        else:
            other.append(f"{sid[-3:]} {status}")
    return done, other


def build(sub_id: str, rnd: int, plan: bool) -> str:
    tid = sub_id[:-4]
    task_md = ct.find_task(tid)
    tdir = task_md.parent
    subs = sorted(tdir.glob(f"{sub_id}-*.md"))
    if len(subs) != 1:
        raise SystemExit(f"Dừng: tìm thấy {len(subs)} file cho {sub_id}.")
    text = task_md.read_text(encoding="utf-8")
    fm = ct.frontmatter(subs[0].read_text(encoding="utf-8"))
    done, other = done_list(tdir, tid)
    drs, findings = pending_drs(text), open_findings(text)
    kinds = [k for k in re.split(r"[,\s]+", fm.get("selfcheck", "")) if k]
    criteria = [f"bảng Tự kiểm {k}" for k in kinds] + ["<điền điểm riêng của lượt này>"]
    outputs = []
    if plan:
        outputs.append('mục "Kế hoạch" của file subtask, không sửa code')
    else:
        if kinds:
            outputs.append(f"bảng Tự kiểm đã điền, `check_task.py {tid} --stage review` đạt")
        outputs.append(f"`task_step.py {sub_id} done`")
    outputs.append("báo cáo ≤ 200 từ có dòng `Tool:`")
    lines = ["Chế độ: lập kế hoạch"] if plan else []
    lines += [
        f"{sub_id}, vòng {rnd}: <điền việc cần làm một câu>",
        f"Trạng thái: {ct.frontmatter(text).get('status', '?')}; xong: {', '.join(done) or 'chưa có'}; "
        f"còn: {', '.join(other) or 'không'}",
        f"Còn mở: {', '.join(findings) + ' (mục 4)' if findings else 'không có'}",
        f"Đọc: `ctx_pack.py {sub_id}` (chạy riêng, không gộp lệnh khác; in theo phần, `--part N`); "
        f"mục khác của task: `task_section.py {tid} <mục>`",
        f"Quyết định đang treo: {', '.join(drs) + ' <điền phần phải làm lại>' if drs else 'không có'}",
        f"Reviewer sẽ kiểm: {'; '.join(criteria)}",
        f"Đầu ra bắt buộc: {'; '.join(outputs)}",
        'Đóng việc: <điền ai đánh dấu "Đã sửa?" và ai ghi dòng "**Kết quả:**">',
    ]
    return "\n".join(lines) + "\n"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="brief.py", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("subtask_id")
    parser.add_argument("--round", type=int, default=1)
    parser.add_argument("--plan", action="store_true")
    args = parser.parse_args(argv)
    if not re.fullmatch(r"E\d\d-T\d\d-S\d\d", args.subtask_id):
        print(f"Dừng: `{args.subtask_id}` không phải mã subtask.")
        return 2
    sys.stdout.write(build(args.subtask_id, args.round, args.plan))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
