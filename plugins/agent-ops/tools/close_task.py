"""Close a task when review is Approved and QA Passed, without a model (D-219, token optimisation).

Usage: python3 "${CLAUDE_PLUGIN_ROOT}/tools/close_task.py" [TASK-ID]
  No TASK-ID: taken from the current branch name when it names exactly one task.
Shortcut in Claude Code: type `ct [TASK-ID]` (hooks/scripts/task_shortcuts.py).

Mechanical PM step (management README, task rules): checks the DoD boxes readable from files, then sets
`status: done` on task + subtask files, marks the subtask table, adds a history row to the task log and
the epic, updates the epic's task list, regenerates BOARD, runs build_inbox --check, commits and pushes.
Any failed check: nothing is changed, every failed check is reported. Standard library only.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _project import mgmt_rel, project_root  # noqa: E402

REPO = project_root()
os.environ.setdefault("AGENT_OPS_PROJECT_DIR", str(REPO))  # child tools find the project
MGMT = mgmt_rel(REPO)
TOOLS = Path(__file__).resolve().parent
TASKS = REPO / MGMT / "tasks"
DRS = REPO / MGMT / "decision-requests"
COMMENT = re.compile(r"<!--.*?-->", re.S)


def sh(*cmd: str, check: bool = True) -> subprocess.CompletedProcess:
    res = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True, check=False)
    if check and res.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd)} -> {res.returncode}: {(res.stderr or res.stdout).strip()[:300]}")
    return res


def out(*cmd: str) -> str:
    return sh(*cmd).stdout.strip()


# ---------- pure helpers (unit tested) ----------

def frontmatter(text: str) -> dict[str, str]:
    lines = text.splitlines()
    fm: dict[str, str] = {}
    if not lines or lines[0].strip() != "---":
        return fm
    for line in lines[1:]:
        if line.strip() == "---":
            break
        m = re.match(r"(\w+):\s*(.*?)\s*(?:#.*)?$", line)
        if m:
            fm[m.group(1)] = m.group(2).strip("'\"")
    return fm


def set_field(text: str, key: str, value: str) -> str:
    """Replace `key:` in the frontmatter, keeping a trailing `# comment`."""
    def repl(m: re.Match) -> str:
        return f"{m.group(1)}{value}{m.group(3) or ''}"
    head, sep, rest = text.partition("\n---")
    head = re.sub(rf"(?m)^({key}:\s*)([^#\n]*?)(\s+#.*)?$", repl, head, count=1)
    return head + sep + rest


def section(text: str, num: int) -> str:
    """Body of `## <num>. ...` up to the next `## ` heading."""
    m = re.search(rf"(?ms)^## {num}\.[^\n]*\n(.*?)(?=^## |\Z)", text)
    return m.group(1) if m else ""


def result_ok(body: str, word: str) -> bool:
    return any(line.strip().startswith(f"**Kết quả:** ✅ {word}") for line in COMMENT.sub("", body).splitlines())


def subtask_rows(text: str, tid: str) -> list[tuple[str, str]]:
    """(subtask id, status) from the Subtasks table: first and last cell of rows starting with `| <tid>-S`."""
    rows = []
    for line in text.splitlines():
        if line.startswith(f"| {tid}-S"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            rows.append((cells[0], cells[-1]))
    return rows


def add_history_row(text: str, row: str) -> str:
    """Insert `row` after the last table row of the `## ... Lịch sử` section (the last such heading)."""
    lines = text.splitlines()
    heads = [i for i, l in enumerate(lines) if l.startswith("## ") and "Lịch sử" in l]
    if not heads:
        raise ValueError("không thấy mục Lịch sử")
    i = heads[-1] + 1
    last = None
    while i < len(lines) and not lines[i].startswith("## "):
        if lines[i].startswith("|"):
            last = i
        i += 1
    if last is None:
        raise ValueError("mục Lịch sử không có bảng")
    lines.insert(last + 1, row)
    return "\n".join(lines) + ("\n" if text.endswith("\n") else "")


def mark_epic_row(text: str, tid: str, cell: str) -> tuple[str, list[str]]:
    """Set the status cell (3rd) of the task's row in `## Danh sách task`; return the new text and all statuses."""
    lines = text.splitlines()
    statuses, found = [], False
    in_list = False
    for i, line in enumerate(lines):
        if line.startswith("## "):
            in_list = line.startswith("## Danh sách task")
            continue
        if in_list and re.match(r"\| E\d\d-T\d\d ", line):
            cells = line.split("|")
            if cells[1].strip() == tid:
                cells[3] = f" {cell} "
                lines[i] = "|".join(cells)
                found = True
            statuses.append(cells[3].strip())
    if not found:
        raise ValueError(f"epic.md không có dòng {tid} trong Danh sách task")
    return "\n".join(lines) + ("\n" if text.endswith("\n") else ""), statuses


# ---------- main ----------

def find_task(tid: str) -> Path:
    hits = sorted(TASKS.glob(f"*/{tid}-*/task.md"))
    if len(hits) != 1:
        raise SystemExit(f"Dừng: tìm thấy {len(hits)} task.md cho {tid}.")
    return hits[0]


def infer_id(branch: str) -> str:
    ids = sorted(set(re.findall(r"E\d\d-T\d\d", branch)))
    if len(ids) != 1:
        raise SystemExit(f"Dừng: nhánh `{branch}` không nêu đúng một task, gõ rõ mã: ct E0x-Tyy.")
    return ids[0]


def open_drs(sec6: str) -> list[str]:
    bad = []
    for dr in sorted(set(re.findall(r"DR-\d{3}", COMMENT.sub("", sec6)))):
        files = list(DRS.glob(f"{dr}-*.md"))
        if files and frontmatter(files[0].read_text(encoding="utf-8")).get("status") == "open":
            bad.append(dr)
    return bad


def main(argv: list[str]) -> int:
    if any(a in ("-h", "--help") for a in argv):
        print(__doc__)
        return 0
    branch = out("git", "branch", "--show-current")
    tid = argv[0] if argv else infer_id(branch)
    task_md = find_task(tid)
    tdir = task_md.parent
    rel = lambda p: str(p.relative_to(REPO))  # noqa: E731
    text = task_md.read_text(encoding="utf-8")
    fm = frontmatter(text)

    fails: list[str] = []
    if branch == "main" or tid not in branch:
        fails.append(f"nhánh hiện tại `{branch}` phải khác main và chứa {tid}")
    dirty = [l[3:] for l in out("git", "status", "--porcelain", "--untracked-files=no").splitlines()]
    dirty = [p for p in dirty if not p.startswith(rel(tdir) + "/")]
    if dirty:
        fails.append("có thay đổi chưa commit ngoài thư mục task: " + ", ".join(dirty[:5]))
    if fm.get("status") == "done":
        fails.append("task đã `done`")
    if not result_ok(section(text, 4), "Approved"):
        fails.append("mục 4 chưa có `**Kết quả:** ✅ Approved`")
    has_qa = bool(fm.get("qa"))
    if has_qa:
        if not result_ok(section(text, 5), "Passed"):
            fails.append("mục 5 chưa có `**Kết quả:** ✅ Passed`")
        ev = tdir / "evidence"
        if not ev.is_dir() or not any(p.is_file() for p in ev.rglob("*")):
            fails.append("không có bằng chứng QA trong evidence/")
    rows = subtask_rows(text, tid)
    not_done = [s for s, st in rows if st.strip("*` ") != "done"]
    if not_done:
        fails.append("subtask chưa done: " + ", ".join(not_done))
    drs = open_drs(section(text, 6))
    if drs:
        fails.append("mục 6 còn phiếu open: " + ", ".join(drs))
    if fails:
        print(f"Không đóng {tid} (chưa sửa gì):")
        print("\n".join(f"- {f}" for f in fails))
        return 1

    today = date.today().isoformat()
    old = fm.get("status", "?")
    verdict = "review Approved, QA Passed" if has_qa else "review Approved, không có QA"
    changed: list[Path] = []

    text = set_field(text, "status", "done")
    log_md = tdir / "log.md"
    row = f"| {today} | close-task | {old} → done: {verdict} |"
    if log_md.exists():
        log_md.write_text(add_history_row(log_md.read_text(encoding="utf-8"), row), encoding="utf-8")
        changed.append(log_md)
    else:
        text = add_history_row(text, row)
    task_md.write_text(text, encoding="utf-8")
    changed.append(task_md)

    for sub in sorted(tdir.glob(f"{tid}-S*.md")):
        st = sub.read_text(encoding="utf-8")
        if frontmatter(st).get("status") not in (None, "done"):
            sub.write_text(set_field(st, "status", "done"), encoding="utf-8")
            changed.append(sub)

    epic_md = tdir.parent / "epic.md"
    etext, statuses = mark_epic_row(epic_md.read_text(encoding="utf-8"), tid, f"**done** {today} ({verdict})")
    epic_all_done = all(re.sub(r"[*`]", "", s).split()[0] == "done" for s in statuses if s)
    etext = add_history_row(etext, f"| {today} | close-task | {tid} `done` ({verdict}). Epic không đổi trạng thái |")
    epic_md.write_text(etext, encoding="utf-8")
    changed.append(epic_md)

    sh("python3", str(TOOLS / "build_board.py"))
    chk = sh("python3", str(TOOLS / "build_inbox.py"), "--check", check=False)
    chk_line = (chk.stdout.strip().splitlines() or ["(không có output)"])[-1]
    if chk.returncode != 0:
        print(f"Đã sửa file nhưng KHÔNG commit: build_inbox --check báo vấn đề:\n{chk.stdout.strip()[-800:]}")
        return 1

    co = [l for l in out("git", "log", "-1", "--format=%B").splitlines() if l.startswith("Co-Authored-By:")]
    msg = f"chore(tasks): QA passed, close {tid} [{tid}]" + ("\n\n" + "\n".join(co) if co else "")
    sh("git", "add", *[rel(p) for p in changed], f"{MGMT}/BOARD.md")
    sh("git", "commit", "-m", msg)
    sha = out("git", "rev-parse", "--short", "HEAD")
    push = sh("git", "push", "origin", "HEAD", check=False)
    pr = sh("gh", "pr", "view", "--json", "number", "-q", ".number", check=False).stdout.strip()

    print(f"Đã đóng {tid} ({old} → done): commit {sha}" + ("" if push.returncode == 0 else " — PUSH LỖI: "
                                                       + push.stderr.strip()[-200:]))
    print(f"build_inbox --check: {chk_line}")
    if epic_all_done:
        print(f"Mọi task của epic {tid[:3]} đã done: cân nhắc đóng epic (không tự đổi).")
    print(f"Bước tiếp: mp {pr}" if pr else "Bước tiếp: mở PR rồi gõ `mp <số PR>`.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
