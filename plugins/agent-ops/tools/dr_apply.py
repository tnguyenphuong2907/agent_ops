"""Record a provisional (type 2) decision request in one command, without a model.

Usage: python3 "${CLAUDE_PLUGIN_ROOT}/tools/dr_apply.py" DR-xxx [--choice X] [--summary TEXT] [--tokens NK]
Requires `status: provisional`, `type: 2` and an empty `decided_as`. Appends the next D row (⏳ tạm) to
decisions.md, sets `decided_as`, fills the "Quyết định" block, adds a history row (with the token
count), copies "Lưu ý khi làm" into section 7 of every unfinished task in `affects`, then runs
build_inbox. Choice and summary default to the "architect đề xuất" line. Standard library only.
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import close_task as ct  # noqa: E402
import task_step  # noqa: E402

PROPOSAL = re.compile(r"(?m)^\*\*architect đề xuất:\*\*[ \t]*(.+?)[ \t]+—[ \t]+(.*)$")
D_ID = re.compile(r"(?m)^\| D-(\d{3,}) \| \d{4}-")


def notes(dr_text: str) -> list[str]:
    """Bullet lines under every "Lưu ý khi làm" label."""
    out: list[str] = []
    for m in re.finditer(r"(?m)^\*\*Lưu ý khi làm:?\*\*[^\n]*\n((?:[ \t]*\n|[ \t]*(?:[-*]|\d+\.) [^\n]*\n|[ \t]+\S[^\n]*\n)+)",
                         ct.COMMENT.sub("", dr_text) + "\n"):
        out += [l.rstrip() for l in m.group(1).splitlines() if l.strip()]
    return out


def affected_tasks(affects: str) -> list[str]:
    return sorted(set(re.findall(r"E\d\d-T\d\d", affects)))


def add_row(decisions: str, row: str) -> str:
    """Insert after the last decision row (rows starting `| D-nnn | <date>`)."""
    lines = decisions.splitlines()
    last = max((i for i, l in enumerate(lines) if D_ID.match(l)), default=None)
    if last is None:
        raise ValueError("decisions.md không có dòng quyết định nào")
    lines.insert(last + 1, row)
    return "\n".join(lines) + "\n"


def add_note(text: str, line: str) -> str:
    """Append `line` at the end of the `## 7. ...` section."""
    m = re.search(r"(?ms)^## 7\.[^\n]*\n(.*?)(?=^## |\Z)", text)
    if not m:
        raise ValueError("không thấy mục 7")
    body = m.group(1).rstrip("\n")
    return text[:m.start(1)] + (f"{body}\n" if body else "") + f"{line}\n\n" + text[m.end(1):]


def fill_decision(text: str, choice: str, did: str) -> str:
    text = re.sub(r"(?m)^- Lựa chọn:[ \t]*$", f"- Lựa chọn: {choice} (áp dụng tạm)", text, count=1)
    return re.sub(r"(?m)^- Ghi nhận:[ \t]*(D-(?:xxx)?)?[ \t]*$", f"- Ghi nhận: {did} (⏳ tạm)", text, count=1)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="dr_apply.py", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("dr_id")
    parser.add_argument("--choice")
    parser.add_argument("--summary")
    parser.add_argument("--tokens", help="tokens spent on the request, e.g. 85K")
    args = parser.parse_args(argv)
    files = list(ct.DRS.glob(f"{args.dr_id}-*.md"))
    if not re.fullmatch(r"DR-\d{3}", args.dr_id) or len(files) != 1:
        print(f"Dừng: tìm thấy {len(files)} phiếu cho {args.dr_id}.")
        return 2
    dr_md = files[0]
    text = dr_md.read_text(encoding="utf-8")
    fm = ct.frontmatter(text)
    proposal = PROPOSAL.search(text)
    choice = args.choice or (proposal and proposal.group(1).replace("*", "").strip())
    summary = args.summary or (proposal and proposal.group(2).strip())
    errors = []
    if fm.get("status") != "provisional":
        errors.append(f"status là `{fm.get('status')}`, cần `provisional`")
    if fm.get("type") != "2":
        errors.append("chỉ áp phiếu `type: 2`; loại 1 chờ PO (`/decide`)")
    if fm.get("decided_as") not in (None, "", "null", "~"):
        errors.append(f"đã có decided_as: {fm['decided_as']}")
    if not choice:
        errors.append("không đọc được phương án, truyền --choice")
    if not summary:
        errors.append("không đọc được tóm tắt, truyền --summary")
    if errors:
        print("Dừng (chưa sửa gì):\n" + "\n".join(f"- {e}" for e in errors))
        return 1

    decisions_md = ct.REPO / ct.MGMT / "decisions.md"
    decisions = decisions_md.read_text(encoding="utf-8")
    did = f"D-{max(map(int, D_ID.findall(decisions)), default=0) + 1:03d}"
    today = date.today().isoformat()
    affects = fm.get("affects", "").strip("[]")
    cell = summary.replace("|", "\\|")
    row = f"| {did} | {today} | **⏳ tạm (agent), loại 2, {args.dr_id} phương án {choice}:** {cell} | {affects} | {args.dr_id} |"
    writes: dict[Path, str] = {decisions_md: add_row(decisions, row)}

    text = task_step.put_field(text, "decided_as", did)
    text = fill_decision(text, choice, did)
    spent = f"; ~{args.tokens.lstrip('~')} token" if args.tokens else ""
    text = ct.add_history_row(text, f"| {today} | dr-apply | Ghi {did} (⏳ tạm), phương án {choice}{spent} |")
    writes[dr_md] = text

    found = notes(text)
    skipped = []
    if found:
        for tid in affected_tasks(affects):
            hits = sorted(ct.TASKS.glob(f"*/{tid}-*/task.md"))
            if len(hits) != 1 or ct.frontmatter(hits[0].read_text(encoding="utf-8")).get("status") == "done":
                skipped.append(tid)
                continue
            target = hits[0].parent / "log.md"
            target = target if target.is_file() else hits[0]
            line = f"- {today} dr-apply: {args.dr_id} = {choice} ({did}, ⏳ tạm). Lưu ý khi làm:\n" + "\n".join(
                "  " + n for n in found)
            try:
                writes[target] = add_note(target.read_text(encoding="utf-8"), line)
            except ValueError:
                skipped.append(tid)
    for path, body in writes.items():
        path.write_text(body, encoding="utf-8")
    print(f"{args.dr_id} → {did} (⏳ tạm, phương án {choice}); sửa {len(writes)} file")
    if skipped:
        print("Chưa chép lưu ý (task done, thiếu mục 7 hoặc không thấy): " + ", ".join(skipped))
    if not found:
        print("Phiếu không có mục `Lưu ý khi làm`.")
    code = 0
    for extra in ([], ["--check"]):
        res = ct.sh("python3", str(ct.TOOLS / "build_inbox.py"), *extra, check=False)
        if extra or res.returncode:
            print((res.stdout.strip().splitlines() or ["(build_inbox không in gì)"])[-1])
        code = code or res.returncode
    return 1 if code else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
