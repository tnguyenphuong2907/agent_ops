"""PreToolUse hook on agent spawns: stop a task brief that skips the project's rules.

For `agent-ops:*` agents (except pm and haiku runs) whose prompt names a task:
- the brief carries the four lines of task-management § Giao việc (write "không có" when empty);
- a dev run on opus states `Lý do opus:`; execution defaults to sonnet;
- a planning run (`Chế độ: lập kế hoạch`) uses opus;
- a subtask marked `plan: opus` is not coded before its "## Kế hoạch" section is written.
Denies with the reason so the main session fixes and resends. Any internal error lets the call pass.
Standard library only.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

PREFIX = "agent-ops:"
DEV_ROLES = {"backend-dev", "frontend-dev"}
LABELS = ("Quyết định đang treo", "Reviewer sẽ kiểm", "Đầu ra bắt buộc", "Đóng việc")
TASK = re.compile(r"\bE\d\d-T\d\d")
SUBTASK = re.compile(r"\bE\d\d-T\d\d-S\d\d\b")
PLAN_RUN = re.compile(r"(?im)^\W*Chế độ:\W*lập kế hoạch")
OPUS_REASON = re.compile(r"(?im)^\W*Lý do opus:[ \t*]*\S")


def problems(tool_input: dict, root: Path) -> list[str]:
    agent = str(tool_input.get("subagent_type") or "")
    model = str(tool_input.get("model") or "")
    prompt = str(tool_input.get("prompt") or "")
    role = agent.removeprefix(PREFIX)
    if not agent.startswith(PREFIX) or role == "pm" or model == "haiku" or not TASK.search(prompt):
        return []
    if PLAN_RUN.search(prompt):
        return [] if model == "opus" else ["lượt lập kế hoạch phải truyền model `opus`"]
    found = []
    missing = [l for l in LABELS if not re.search(rf"(?im)^\W*{l}[^:\n]*:", prompt)]
    if missing:
        found.append("brief thiếu dòng: " + "; ".join(f"`{m}:`" for m in missing) + " (không có gì thì ghi `không có`)")
    if role in DEV_ROLES:
        if model == "opus" and not OPUS_REASON.search(prompt):
            found.append("dev chạy opus cần dòng `Lý do opus:` (mặc định sonnet; subtask khó thì opus lập kế hoạch rồi sonnet code)")
        first = SUBTASK.search(prompt)
        if first:
            from _project import mgmt_dir
            import check_task
            for sub in mgmt_dir(root).glob(f"tasks/*/*/{first.group(0)}-*.md"):
                if check_task.plan_errors(sub.name, sub.read_text(encoding="utf-8")):
                    found.append(f"{first.group(0)} có `plan: opus` mà chưa có kế hoạch hợp lệ: spawn lượt "
                                 "`Chế độ: lập kế hoạch` (model opus) trước")
    return found


def main() -> int:
    try:
        payload = json.load(sys.stdin)
        root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or payload.get("cwd") or ".").resolve()
        os.environ["AGENT_OPS_PROJECT_DIR"] = str(root)
        if not (root / ".agent-ops.toml").is_file():
            return 0
        found = problems(payload.get("tool_input") or {}, root)
    except Exception:  # noqa: BLE001 - a guard bug must not block all agent spawns
        return 0
    if found:
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": "[brief_guard] " + " | ".join(found),
        }}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
