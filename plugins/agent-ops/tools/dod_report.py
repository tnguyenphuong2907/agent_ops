"""One-screen Definition of Done facts of a task, so the closing role need not read the documents.

Usage: python3 "${CLAUDE_PLUGIN_ROOT}/tools/dod_report.py" TASK-ID
Prints statuses, review and QA results, review findings, "not checked" notes, open DRs, evidence,
check_task errors and the local check stamp. Changes nothing. Exit 1 when something blocks `done`.
Standard library only.
"""
from __future__ import annotations

import re
import sys
import tomllib
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_task  # noqa: E402
import close_task as ct  # noqa: E402
from _project import CONFIG_NAME  # noqa: E402

CUT = 220


# ---------- pure helpers (unit tested) ----------

def result_lines(body: str) -> list[str]:
    return [l.strip() for l in ct.COMMENT.sub("", body).splitlines() if l.strip().startswith("**Kết quả:**")]


def findings(review: str) -> list[tuple[str, str, str]]:
    """(number, severity, "Đã sửa?" cell) of every row of the review tables."""
    rows, col = [], None
    for line in ct.COMMENT.sub("", review).splitlines():
        if not line.startswith("|"):
            col = None
            continue
        row = check_task.cells(line)
        if "Đã sửa?" in row:
            col = (row.index("Đã sửa?"), len(row))
        elif col and not set("".join(row)) <= set("-: ") and len(row) > 1:
            fixed = row[-1] if col[0] == col[1] - 1 else (row[col[0]] if col[0] < len(row) else "")
            rows.append((row[0], row[1], fixed))
    return rows


def unchecked(qa: str) -> list[str]:
    """QA lines that admit something failed or was not verified."""
    return [l.strip() for l in ct.COMMENT.sub("", qa).splitlines()
            if re.search(r"(?i)chưa kiểm|❌|\bFailed\b", l)]


def only_under(paths: list[str], prefix: str) -> bool:
    return all(p.startswith(prefix) for p in paths)


# ---------- main ----------

def stamp_line() -> str:
    try:
        cfg = tomllib.loads((ct.REPO / CONFIG_NAME).read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return "không đọc được cấu hình"
    folder = cfg.get("merge", {}).get("local_stamp_dir")
    if not folder:
        return "dự án dùng CI (xem check của PR)"
    stamps = ct.REPO / ct.out("git", "rev-parse", "--git-common-dir") / folder
    head = ct.out("git", "rev-parse", "HEAD")
    if (stamps / head).is_file():
        return f"có dấu ở HEAD {head[:8]}"
    for sha in ct.out("git", "rev-list", "-n", "100", "HEAD").splitlines():
        if (stamps / sha).is_file():
            changed = ct.out("git", "diff", "--no-renames", "--name-only", sha, head).splitlines()
            scope = f"chỉ đổi {ct.MGMT}/" if only_under(changed, f"{ct.MGMT}/") else f"CÓ đổi ngoài {ct.MGMT}/"
            return f"chưa có ở HEAD {head[:8]}; gần nhất {sha[:8]}, sau đó {scope} (chạy lại script kiểm)"
    return f"không có dấu nào trong 100 commit gần nhất (HEAD {head[:8]})"


def main(argv: list[str]) -> int:
    if len(argv) != 1 or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0 if argv else 2
    tid = argv[0]
    task_md = ct.find_task(tid)
    tdir = task_md.parent
    text = task_md.read_text(encoding="utf-8")
    fm = ct.frontmatter(text)
    review, qa = ct.section(text, 4), ct.section(text, 5)
    blockers = []
    print(f"# DoD {tid}: status {fm.get('status', '?')}, làn {fm.get('lane', '?')}")
    rows = ct.subtask_rows(text, tid)
    print("Subtask: " + (", ".join(f"{s[-3:]}={st}" for s, st in rows) or "không có bảng"))
    needed = [("Review", review, "Approved")] + ([("QA", qa, "Passed")] if fm.get("qa") else [])
    for label, body, word in needed:
        lines = result_lines(body)
        print(f"{label}: " + (" / ".join(l[:CUT] for l in lines) or "chưa có dòng Kết quả"))
        if not ct.result_ok(body, word):
            blockers.append(f"{label} chưa ✅ {word}")
    found = findings(review)
    if found:
        print("Nhận xét review: " + ", ".join(f"{n} {s}" for s, n in Counter(f[1] for f in found).items()))
        print("Đã đóng: " + "; ".join(f"#{n} {s}: {fixed[:40] or 'TRỐNG'}" for n, s, fixed in found))
    notes = unchecked(qa)
    if notes:
        print("QA ghi chưa kiểm / lỗi:")
        print("\n".join(f"- {n[:CUT]}" for n in notes[:12]))
    drs = ct.open_drs(ct.section(text, 6))
    if drs:
        blockers.append("phiếu open: " + ", ".join(drs))
    evidence = [p for p in (tdir / "evidence").rglob("*") if p.is_file()]
    print(f"Bằng chứng: {len(evidence)} file")
    if fm.get("qa") and not evidence:
        blockers.append("không có bằng chứng QA")
    print(f"Kiểm local: {stamp_line()}")
    blockers += check_task.gate_errors(tdir, tid, "close")
    print("Chặn: " + ("không có (còn lại: DoD cần người đọc, theo management README)" if not blockers else ""))
    for b in blockers:
        print(f"- {b}")
    return 1 if blockers else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
