"""Mechanical checks on a task before review or close, without a model.

Usage: python3 "${CLAUDE_PLUGIN_ROOT}/tools/check_task.py" TASK-ID [--stage review|close] [--base REF]
  review: design self-check tables (templates/design-selfcheck.md) of subtasks with `selfcheck:` are filled,
          and subtasks with `plan: opus` have their "## Kế hoạch" section.
  close (default): also every review finding has "Đã sửa?" filled and the result lines are there.
Errors exit 1. Warnings (stale AC ranges, leftover "waiting for" wording) only print.
Broken anchors are covered by build_inbox --check. Standard library only.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import close_task as ct  # noqa: E402

REQUIRED = {"api": [f"H{i}" for i in range(1, 8)], "ui": [f"M{i}" for i in range(1, 7)]}
ROLES = "PO|pm|architect|product-analyst|ui-designer|code-reviewer|db-reviewer|db-designer|idea-reviewer|qa"
WAITING = re.compile(rf"(?i)\bchờ\s+(?:{ROLES}|DR-\d{{3}})\b")
AC_RANGE = re.compile(r"\b([A-Z]\w*)-AC1\s*(?:\.\.|–|…)\s*(?:AC)?(\d+)")
BLANK = {"", "-", "—", "…", "..."}


def cells(line: str) -> list[str]:
    return [c.strip() for c in re.split(r"(?<!\\)\|", line.strip().strip("|"))]


# ---------- pure checks (unit tested) ----------

def selfcheck_errors(name: str, text: str) -> list[str]:
    """Problems in the self-check table of one subtask file; none when it declares no `selfcheck:`."""
    kinds = [k for k in re.split(r"[,\s]+", ct.frontmatter(text).get("selfcheck", "")) if k]
    if not kinds:
        return []
    unknown = [k for k in kinds if k not in REQUIRED]
    if unknown:
        return [f"{name}: `selfcheck` lạ: {', '.join(unknown)} (dùng api | ui)"]
    m = re.search(r"(?ms)^## Tự kiểm[^\n]*\n(.*?)(?=^## |\Z)", ct.COMMENT.sub("", text))
    answers: dict[str, str] = {}
    for line in (m.group(1) if m else "").splitlines():
        if line.startswith("|"):
            row = cells(line)
            if len(row) >= 3 and re.fullmatch(r"[HM]\d+", row[0]):
                answers[row[0]] = row[-1]
    errors = []
    for key in (k for kind in kinds for k in REQUIRED[kind]):
        if key not in answers:
            errors.append(f"{name}: bảng Tự kiểm thiếu dòng {key}")
        elif answers[key] in BLANK:
            errors.append(f"{name}: Tự kiểm {key} chưa trả lời")
        elif re.fullmatch(r"(?i)không áp dụng(\s+vì)?[\s.:…—-]*", answers[key]):
            errors.append(f"{name}: Tự kiểm {key} ghi không áp dụng nhưng thiếu lý do")
    return errors


def plan_errors(name: str, text: str) -> list[str]:
    """A subtask marked `plan: opus` needs a written plan before anyone codes it."""
    kind = ct.frontmatter(text).get("plan", "")
    if not kind:
        return []
    if kind != "opus":
        return [f"{name}: `plan` lạ: {kind} (dùng opus hoặc để trống)"]
    m = re.search(r"(?ms)^## Kế hoạch[^\n]*\n(.*?)(?=^## |\Z)", ct.COMMENT.sub("", text))
    body = [l.strip() for l in (m.group(1) if m else "").splitlines() if not l.lstrip().startswith(">")]
    if all(l in BLANK for l in body):
        return [f"{name}: `plan: opus` nhưng mục Kế hoạch còn trống"]
    return []


def unclosed_findings(review: str) -> list[str]:
    """Rows of review tables whose "Đã sửa?" cell is empty or still waiting."""
    errors, col, table = [], None, 0
    for line in ct.COMMENT.sub("", review).splitlines():
        if not line.startswith("|"):
            col = None
            continue
        row = cells(line)
        if "Đã sửa?" in row:
            col = row.index("Đã sửa?")
            last = col == len(row) - 1
            table += 1
            continue
        if col is None or set("".join(row)) <= set("-: "):
            continue
        # A literal pipe inside a comment shifts columns, so read the last column from the end.
        value = row[-1] if last else (row[col] if col < len(row) else "")
        if value in BLANK or re.match(r"(?i)(chờ\b|⏳|mở\b)", value):
            errors.append(f"mục 4 bảng {table} #{row[0]}: cột \"Đã sửa?\" chưa đóng")
    return errors


def ac_maxima(sec1: str) -> dict[str, int]:
    """Highest AC number per prefix (`F02` of `F02-AC7`) named in section 1."""
    best: dict[str, int] = {}
    for prefix, num in re.findall(r"\b([A-Z]\w*)-AC(\d+)", AC_RANGE.sub("", sec1)):
        best[prefix] = max(best.get(prefix, 0), int(num))
    return best


def line_warnings(where: str, line: str, maxima: dict[str, int]) -> list[str]:
    found = []
    for prefix, end in AC_RANGE.findall(line):
        if int(end) < maxima.get(prefix, 0):
            found.append(f"{where}: dải {prefix}-AC1..{end} cũ, mục 1 đã tới AC{maxima[prefix]}")
    m = WAITING.search(line)
    if m:
        found.append(f"{where}: còn chữ \"{m.group(0)}\"")
    return found


def added_lines(diff: str) -> list[tuple[str, int, str]]:
    """(path, line number, text) of every added line in a `git diff -U0` output."""
    result, path, num = [], "", 0
    for line in diff.splitlines():
        if line.startswith("+++ "):
            path = line[6:] if line.startswith("+++ b/") else ""
        elif line.startswith("@@"):
            m = re.search(r"\+(\d+)", line)
            num = int(m.group(1)) if m else 0
        elif line.startswith("+") and path:
            result.append((path, num, line[1:]))
            num += 1
    return result


# ---------- task level ----------

def gate_errors(tdir: Path, tid: str, stage: str) -> list[str]:
    """Self-check tables, plus review findings at close. close_task.py runs this before closing."""
    errors = []
    for sub in sorted(tdir.glob(f"{tid}-S*.md")):
        text = sub.read_text(encoding="utf-8")
        errors += selfcheck_errors(sub.name, text) + plan_errors(sub.name, text)
    if stage == "close":
        errors += unclosed_findings(ct.section((tdir / "task.md").read_text(encoding="utf-8"), 4))
    return errors


def warnings(task_md: Path, tid: str, base: str | None) -> list[str]:
    text = task_md.read_text(encoding="utf-8")
    maxima = ac_maxima(ct.section(text, 1))
    found, num = [], None
    for i, line in enumerate(text.splitlines(), 1):
        if line.startswith("## "):
            m = re.match(r"## (\d+)\.", line)
            num = int(m.group(1)) if m else num
        if num in (1, 2) and not line.lstrip().startswith(">"):
            found += line_warnings(f"task.md:{i}", line, maxima)
    contract = task_md.parent / "contract.md"
    if contract.is_file():
        for i, line in enumerate(contract.read_text(encoding="utf-8").splitlines(), 1):
            if not line.lstrip().startswith(">"):
                found += line_warnings(f"contract.md:{i}", line, maxima)
    if base:
        mb = ct.sh("git", "merge-base", base, "HEAD", check=False)
        if mb.returncode != 0:
            found.append(f"không so được với `{base}`: bỏ qua quét file đã đổi")
        else:
            diff = ct.out("git", "-c", "core.quotepath=false", "diff", "-U0", mb.stdout.strip(), "--", "*.md")
            for path, i, line in added_lines(diff):
                # Management files keep history on purpose; only product docs are scanned.
                if not path.startswith(f"{ct.MGMT}/"):
                    found += line_warnings(f"{path}:{i}", line, maxima)
    flows = ct.REPO / ct.MGMT / "flows.md"
    if flows.is_file():
        for i, line in enumerate(flows.read_text(encoding="utf-8").splitlines(), 1):
            if re.search(rf"(?i)chốt ở {tid}\b", line):
                found.append(f"{ct.MGMT}/flows.md:{i}: còn \"chốt ở {tid}\"")
    return found


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="check_task.py", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("task_id")
    parser.add_argument("--stage", choices=("review", "close"), default="close")
    parser.add_argument("--base", help="git ref to diff against (default: [merge] base)")
    args = parser.parse_args(argv)
    task_md = ct.find_task(args.task_id)
    errors = gate_errors(task_md.parent, args.task_id, args.stage)
    if args.stage == "close":
        text = task_md.read_text(encoding="utf-8")
        if not ct.result_ok(ct.section(text, 4), "Approved"):
            errors.append("mục 4 chưa có `**Kết quả:** ✅ Approved`")
        if ct.frontmatter(text).get("qa") and not ct.result_ok(ct.section(text, 5), "Passed"):
            errors.append("mục 5 chưa có `**Kết quả:** ✅ Passed`")
    try:
        base = args.base or ct.merge_settings(ct.REPO)[0]
    except ct.ConfigError as e:
        # Only warnings need the base here; merge gates stay strict in merge_pr.py / close_task.py.
        print(f"cảnh báo: {e} (bỏ quét file đã đổi; bản plugin đang chạy có thể cũ hơn cấu hình)")
        base = None
    for w in warnings(task_md, args.task_id, base):
        print(f"cảnh báo: {w}")
    for e in errors:
        print(f"lỗi: {e}")
    print(f"check_task {args.task_id} ({args.stage}): {len(errors)} lỗi")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
