"""Merge eligible PRs into the base branch and clean up afterwards, without a model (token optimisation).

Usage: python3 "${CLAUDE_PLUGIN_ROOT}/tools/merge_pr.py" [PR ...]
  No PR numbers: every open PR into the base branch, plus merged PRs whose branch is still local.
Running this command (or typing `mp [PR ...]` in Claude Code, see hooks/scripts/task_shortcuts.py)
is the PO's explicit OK to merge. A PR that fails a gate is skipped with a reason, never forced.

Gates per open PR: not draft, targets the base branch (`[merge] base`, default main); every task in the branch name has status `done` on the PR
branch; conflicts only in generated files (BOARD, INBOX) are resolved by regenerating them; every check
run of the exact head SHA is completed and green, and every name in
`[merge] required_checks` is present. The list is read from `.agent-ops.toml` on origin/<base>; the run stops
when that file is unreadable or does not declare the key (write `required_checks = []` to require none).
Standard library only; shells out to git and gh.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _project import CONFIG_NAME, ConfigError, merge_settings, mgmt_rel, parse_merge_settings, project_root  # noqa: E402

REPO = project_root()
os.environ.setdefault("AGENT_OPS_PROJECT_DIR", str(REPO))  # child tools find the project
MGMT = mgmt_rel(REPO)
TOOLS = Path(__file__).resolve().parent
GENERATED = {f"{MGMT}/BOARD.md", f"{MGMT}/DECISIONS-INBOX.md"}
OK_CONCLUSIONS = {"success", "skipped", "neutral"}
CI_TIMEOUT = 900
CI_STABLE_WAIT = 60


class Skip(Exception):
    """The PR fails a gate; the message is the reason shown in the report."""


def sh(*cmd: str, check: bool = True) -> subprocess.CompletedProcess:
    res = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True, check=False)
    if check and res.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd)} -> {res.returncode}: {(res.stderr or res.stdout).strip()[:300]}")
    return res


def out(*cmd: str) -> str:
    return sh(*cmd).stdout.strip()


# ---------- pure helpers (unit tested) ----------

def task_ids(branch: str, existing: set[str] | None = None) -> list[str]:
    """Task IDs named in a branch: `E03-T26-T28-x` -> E03-T26, E03-T28 and, if a task dir exists, E03-T27.

    `existing` is the set of task IDs that have a directory; middle IDs of a range are kept only if listed.
    """
    ids: list[str] = []
    for m in re.finditer(r"E(\d\d)((?:-T\d\d)+)", branch):
        epic = m.group(1)
        nums = [int(t) for t in re.findall(r"T(\d\d)", m.group(2))]
        for i, n in enumerate(nums):
            ids.append(f"E{epic}-T{n:02d}")
            if i + 1 < len(nums):
                for mid in range(n + 1, nums[i + 1]):
                    tid = f"E{epic}-T{mid:02d}"
                    if existing is not None and tid in existing:
                        ids.append(tid)
    return list(dict.fromkeys(ids))


def frontmatter_status(text: str) -> str | None:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    for line in lines[1:]:
        if line.strip() == "---":
            break
        m = re.match(r"status:\s*['\"]?([\w-]+)", line)
        if m:
            return m.group(1)
    return None


def ci_verdict(runs: list[dict], required: list[str]) -> str | None:
    """None when green; otherwise the reason to skip. `runs` are completed check runs."""
    names = {r.get("name") for r in runs}
    missing = [c for c in required if c not in names]
    if missing:
        return "thiếu check bắt buộc: " + ", ".join(f"`{c}`" for c in missing)
    bad = [r for r in runs if r.get("conclusion") not in OK_CONCLUSIONS]
    if bad:
        return "CI trượt: " + ", ".join(f"{r.get('name')}={r.get('conclusion')} {r.get('html_url', '')}" for r in bad)
    return None


# ---------- git/gh steps ----------

def check_runs(sha: str) -> list[dict]:
    lines = out("gh", "api", "--paginate", f"repos/{{owner}}/{{repo}}/commits/{sha}/check-runs",
                "-q", ".check_runs[] | @json").splitlines()
    return [json.loads(line) for line in lines if line]


def wait_ci(sha: str, required: list[str]) -> None:
    """Done when every check is completed and the count is unchanged after CI_STABLE_WAIT seconds."""
    deadline = time.monotonic() + CI_TIMEOUT
    prev = -1
    while True:
        runs = check_runs(sha)
        done = bool(runs) and all(r.get("status") == "completed" for r in runs)
        if done and len(runs) == prev:
            reason = ci_verdict(runs, required)
            if reason:
                raise Skip(reason)
            return
        if time.monotonic() > deadline:
            pending = [r.get("name") for r in runs if r.get("status") != "completed"]
            raise Skip(f"CI chưa xong sau {CI_TIMEOUT}s: {', '.join(pending) or 'chưa có check'}")
        prev = len(runs) if done else -1
        print(f"  … chờ CI {sha[:8]} ({len(runs)} check)", file=sys.stderr, flush=True)
        time.sleep(CI_STABLE_WAIT if done else 30)


def check_tasks(branch: str) -> None:
    ref = f"origin/{branch}"
    paths = out("git", "ls-tree", "-r", "--name-only", ref, f"{MGMT}/tasks").splitlines()
    by_id: dict[str, str] = {}
    for p in paths:
        m = re.search(r"/(E\d\d-T\d\d)-[^/]*/task\.md$", p)
        if m:
            by_id[m.group(1)] = p
    for tid in task_ids(branch, set(by_id)):
        if tid not in by_id:
            raise Skip(f"không tìm thấy task.md của {tid}")
        status = frontmatter_status(out("git", "show", f"{ref}:{by_id[tid]}"))
        if status != "done":
            raise Skip(f"{tid} chưa `done` ({status}); review/QA xong thì chạy /close-task {tid}")


def resolve_conflict(branch: str, base: str) -> str:
    """Merge the base branch into the branch; regenerate BOARD/INBOX if only they conflict. Returns new head SHA."""
    sh("git", "switch", branch)
    try:
        sh("git", "pull", "--ff-only", "origin", branch)
        if sh("git", "merge", "--no-edit", f"origin/{base}", check=False).returncode == 0:
            sh("git", "push", "origin", branch)
            return out("git", "rev-parse", "HEAD")
        conflicted = set(out("git", "diff", "--name-only", "--diff-filter=U").splitlines())
        if not conflicted <= GENERATED:
            sh("git", "merge", "--abort")
            raise Skip("xung đột ở file không phải file sinh: " + ", ".join(sorted(conflicted - GENERATED)))
        sh("python3", str(TOOLS / "build_board.py"))
        sh("python3", str(TOOLS / "build_inbox.py"))
        sh("git", "add", *sorted(conflicted))
        sh("git", "commit", "--no-edit")
        chk = sh("python3", str(TOOLS / "build_inbox.py"), "--check", check=False)
        if chk.returncode != 0:
            last = (chk.stdout.strip().splitlines() or [""])[-1]
            raise Skip(f"build_inbox --check báo vấn đề sau khi gộp {base} (commit gộp chưa push): {last}")
        sh("git", "push", "origin", branch)
        return out("git", "rev-parse", "HEAD")
    finally:
        sh("git", "switch", base, check=False)


def pr_view(n: int) -> dict:
    fields = "number,state,isDraft,baseRefName,headRefName,headRefOid,mergeable"
    for _ in range(6):  # mergeable is UNKNOWN for a few seconds after a push to main
        pr = json.loads(out("gh", "pr", "view", str(n), "--json", fields))
        if pr["mergeable"] != "UNKNOWN" or pr["state"] != "OPEN":
            return pr
        time.sleep(5)
    return pr


def merge_open(pr: dict, base: str, required: list[str]) -> str:
    n, branch = pr["number"], pr["headRefName"]
    if pr["isDraft"]:
        raise Skip("PR đang draft")
    if pr["baseRefName"] != base:
        raise Skip(f"base là {pr['baseRefName']}, không phải {base}")
    check_tasks(branch)
    sha = pr["headRefOid"]
    if pr["mergeable"] == "CONFLICTING":
        sha = resolve_conflict(branch, base)
    wait_ci(sha, required)
    res = sh("gh", "pr", "merge", str(n), "--merge", "--delete-branch", "--match-head-commit", sha, check=False)
    if res.returncode != 0:
        raise Skip(f"gh pr merge lỗi (head đổi sau khi kiểm CI?): {res.stderr.strip()[:200]}")
    sh("git", "branch", "-d", branch, check=False)
    return "merged"


def delete_local(branch: str) -> str:
    if sh("git", "show-ref", "--verify", "--quiet", f"refs/heads/{branch}", check=False).returncode != 0:
        return "merge tay, nhánh local đã không còn"
    res = sh("git", "branch", "-d", branch, check=False)
    if res.returncode != 0:
        return f"merge tay, GIỮ nhánh local ({res.stderr.strip().splitlines()[-1][:120]})"
    return "merge tay, đã xoá nhánh local"


def gate_checks(base: str) -> list[str]:
    """Required check names as committed on origin/<base>: no checked-out or unpushed config can loosen them."""
    res = sh("git", "show", f"origin/{base}:{CONFIG_NAME}", check=False)
    if res.returncode != 0:
        raise ConfigError(f"origin/{base} không có {CONFIG_NAME}; commit file có `[merge] required_checks` lên {base}")
    remote_base, required = parse_merge_settings(res.stdout)
    if remote_base != base:
        raise ConfigError(f"merge.base trên origin/{base} là {remote_base}, khác {base} ở cây làm việc")
    if required is None:
        raise ConfigError(f"origin/{base}:{CONFIG_NAME} chưa khai `[merge] required_checks` (ghi [] nếu không bắt buộc check nào)")
    return required


def targets(args: list[str], base: str) -> list[int]:
    if args:
        return sorted({int(a.lstrip("#")) for a in args})
    open_prs = json.loads(out("gh", "pr", "list", "--state", "open", "--base", base, "--json", "number"))
    merged = json.loads(out("gh", "pr", "list", "--state", "merged", "--base", base, "--limit", "30",
                            "--json", "number,headRefName"))
    local = {b for b in out("git", "for-each-ref", "--format=%(refname:short)", "refs/heads").splitlines()}
    nums = {p["number"] for p in open_prs} | {p["number"] for p in merged if p["headRefName"] in local}
    return sorted(nums)


def main(argv: list[str]) -> int:
    if any(a in ("-h", "--help") for a in argv):
        print(__doc__)
        return 0
    if out("git", "status", "--porcelain", "--untracked-files=no"):
        print("Dừng: có thay đổi chưa commit ở repo chính (không stash, không xoá). Commit hoặc dọn rồi chạy lại.")
        return 2
    try:
        base = merge_settings(REPO)[0]
    except ConfigError as e:
        print(f"Dừng: {e}")
        return 2
    sh("git", "switch", base)
    sh("git", "fetch", "--prune", "origin")
    try:
        required = gate_checks(base)
    except ConfigError as e:
        print(f"Dừng: {e}")
        return 2
    rows: list[tuple[int, str, str, str]] = []
    for n in targets(argv, base):
        try:
            pr = pr_view(n)
        except RuntimeError as e:
            rows.append((n, "?", "bỏ qua", f"không đọc được PR: {e}"))
            continue
        branch = pr["headRefName"]
        if pr["state"] == "MERGED":
            rows.append((n, branch, "merge tay", ""))
            continue
        if pr["state"] != "OPEN":
            rows.append((n, branch, "bỏ qua", f"PR {pr['state']} chưa merge"))
            continue
        print(f"#{n} {branch}: kiểm cổng…", file=sys.stderr, flush=True)
        try:
            rows.append((n, branch, merge_open(pr, base, required), ""))
            sh("git", "fetch", "origin", base)  # next PR may now conflict on BOARD
        except Skip as e:
            rows.append((n, branch, "bỏ qua", str(e)))
        except RuntimeError as e:
            sh("git", "switch", base, check=False)
            rows.append((n, branch, "bỏ qua", f"lỗi lệnh: {e}"))

    sh("git", "switch", base)
    sh("git", "pull", "--ff-only", "origin", base)
    sh("git", "fetch", "--prune", "origin")
    rows = [(n, b, delete_local(b) if r == "merge tay" else r, why) for n, b, r, why in rows]
    chk = sh("python3", str(TOOLS / "build_inbox.py"), "--check", check=False)
    chk_line = (chk.stdout.strip().splitlines() or ["(không có output)"])[-1]
    head = out("git", "log", "-1", "--format=%h %s")

    report = [f"| PR | nhánh | kết quả | lý do |", "|---|---|---|---|"]
    report += [f"| #{n} | {b} | {r} | {why} |" for n, b, r, why in rows] or ["| - | - | không có PR nào cần xử lý | |"]
    report.append(f"{base}: {head}")
    report.append(f"build_inbox --check: {chk_line}" + ("" if chk.returncode == 0 else " (CÓ VẤN ĐỀ, chưa sửa)"))
    any_merged = any(r == "merged" or r.startswith("merge tay") for _, _, r, _ in rows)
    if any_merged:
        report.append(f"Nên chạy `/clear` trước khi sang việc mới; tóm tắt đã lưu ở `{MGMT}/HANDOFF.md`.")
    print("\n".join(report))

    if rows:
        handoff = [f"# Handoff ({date.today().isoformat()}, sau merge_pr.py)", ""]
        handoff += [f"- #{n} {b}: {r}" + (f" ({why})" if why else "") for n, b, r, why in rows]
        handoff += [f"- Trạng thái {base}: {head}; build_inbox --check: {chk_line}",
                    "- Bước tiếp: chọn task `ready` kế tiếp theo backlog (PM)."]
        (REPO / MGMT / "HANDOFF.md").write_text("\n".join(handoff[:15]) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
