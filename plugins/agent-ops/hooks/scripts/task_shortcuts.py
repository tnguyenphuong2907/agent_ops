"""UserPromptSubmit hook: zero-token shortcuts for mechanical PM chores.

  mp [PR ...]    -> tools/merge_pr.py   (merge + clean up; typing it is the PO's OK to merge)
  ct [TASK-ID]   -> tools/close_task.py (close a task after review Approved + QA Passed)

A matching prompt is blocked (never sent to the model, so it costs no tokens) and the script's report is
shown to the PO as the block reason. Any other prompt passes through untouched. Standard library only.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

SHORTCUTS = {
    "mp": (re.compile(r"^\s*mp((?:\s+#?\d+)*)\s*$"), "merge_pr.py"),
    "ct": (re.compile(r"^\s*ct((?:\s+E\d\d-T\d\d)?)\s*$", re.I), "close_task.py"),
}


def match(prompt: str) -> tuple[str, list[str]] | None:
    for pattern, script in SHORTCUTS.values():
        m = pattern.match(prompt)
        if m:
            return script, m.group(1).upper().split() if "close_task" in script else m.group(1).split()
    return None


def main() -> int:
    try:
        hit = match(json.load(sys.stdin).get("prompt", ""))
    except Exception:  # noqa: BLE001 - a broken payload must not block the prompt
        return 0
    if not hit:
        return 0
    script, args = hit
    root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
    plugin = Path(os.environ.get("CLAUDE_PLUGIN_ROOT") or Path(__file__).resolve().parents[2])
    env = {**os.environ, "AGENT_OPS_PROJECT_DIR": str(root)}
    res = subprocess.run([sys.executable, str(plugin / "tools" / script), *args],
                         cwd=root, capture_output=True, text=True, check=False, env=env)
    text = res.stdout.strip() or res.stderr.strip()[-600:] or f"({Path(script).name} không in gì)"
    if res.returncode not in (0, 1):
        text += f"\n[{Path(script).name} thoát mã {res.returncode}] {res.stderr.strip()[-600:]}"
    print(json.dumps({"decision": "block", "reason": text}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
