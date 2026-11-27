"""UserPromptSubmit hook: remind to /clear when the main-session context is large .

Reads the hook JSON on stdin, takes `transcript_path`, finds the last assistant usage and,
when input context (input + cache read + cache write) exceeds the threshold, prints a hook
JSON with a short reminder for the model (additionalContext) and the user (systemMessage).
Never blocks: any error exits 0 silently. Standard library only.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

DEFAULT_THRESHOLD = 150_000
TAIL_BYTES = 4_000_000


def last_context(path: Path) -> int | None:
    """Context size of the last assistant message with usage, scanning the file tail."""
    with path.open("rb") as f:
        f.seek(0, os.SEEK_END)
        size = f.tell()
        f.seek(max(0, size - TAIL_BYTES))
        lines = f.read().decode("utf-8", errors="replace").splitlines()
    for line in reversed(lines):
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        msg = rec.get("message") if isinstance(rec, dict) else None
        usage = msg.get("usage") if isinstance(msg, dict) and rec.get("type") == "assistant" else None
        if isinstance(usage, dict):
            return (usage.get("input_tokens", 0) + usage.get("cache_read_input_tokens", 0)
                    + usage.get("cache_creation_input_tokens", 0))
    return None


def main() -> int:
    try:
        THRESHOLD = int(os.environ.get("CTX_GUARD_THRESHOLD", DEFAULT_THRESHOLD))
        payload = json.load(sys.stdin)
        ctx = last_context(Path(payload["transcript_path"]))
    except Exception:  # noqa: BLE001 - a reminder hook must never break the prompt
        return 0
    if ctx is None or ctx <= THRESHOLD:
        return 0
    k = ctx // 1000
    print(json.dumps({
        "systemMessage": f"Ngữ cảnh phiên chính ~{k}K token (> {THRESHOLD // 1000}K): nên /clear sau việc đang làm.",
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": (
                f"[ctx_guard] Ngữ cảnh phiên chính ~{k}K token, vượt ngưỡng {THRESHOLD // 1000}K (luật tiết kiệm token). "
                "Xong việc đang làm thì ghi HANDOFF.md trong thư mục quản lý của dự án và nhắc PO chạy /clear "
                "(việc tiếp nhỏ, cùng chủ đề: /compact). Không dừng việc."
            ),
        },
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
