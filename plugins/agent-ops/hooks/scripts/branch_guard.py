"""PreToolUse hook on Bash: stop creating a branch that would track the base branch.

`git switch -c feat/x origin/main` sets origin/main as the upstream of feat/x, so a later push or pull
aims at the base branch. Such commands need `--no-track`. Any internal error lets the call pass.
Standard library only.
"""
from __future__ import annotations

import json
import os
import shlex
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

CREATE = {"switch": {"-c", "-C", "--create", "--force-create"}, "checkout": {"-b", "-B"}, "worktree": {"-b", "-B"}}
SEPARATORS = {";", "&&", "||", "|", "&", "(", ")", "\n"}
GIT_VALUE_OPTS = {"-C", "-c", "--git-dir", "--work-tree"}


def segments(command: str) -> list[list[str]]:
    """Words of each simple command; quoted text stays one word."""
    lex = shlex.shlex(command.replace("\\\n", " ").replace("\n", " ; "), posix=True, punctuation_chars=";&|()")
    lex.whitespace_split = True
    out, cur = [], []
    for word in lex:
        if word and set(word) <= set(";&|()"):
            out.append(cur)
            cur = []
        else:
            cur.append(word)
    return out + [cur]


def tracks_base(words: list[str], base: str) -> bool:
    if "git" not in words:
        return False
    args = words[words.index("git") + 1:]
    while args and args[0].startswith("-"):
        args = args[2:] if args[0] in GIT_VALUE_OPTS else args[1:]
    if not args:
        return False
    sub, rest = args[0], args[1:]
    if "--no-track" in rest or f"origin/{base}" not in rest:
        return False
    if sub == "branch":
        names = [a for a in rest if not a.startswith("-")]
        return len(names) == 2 and names[1] == f"origin/{base}" and names[0] != base
    if sub not in CREATE:
        return False
    for i, a in enumerate(rest[:-1]):
        if a in CREATE[sub]:
            return rest[i + 1] != base
    return False


def main() -> int:
    try:
        payload = json.load(sys.stdin)
        command = str((payload.get("tool_input") or {}).get("command") or "")
        if "origin/" not in command:
            return 0
        root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or payload.get("cwd") or ".").resolve()
        if not (root / ".agent-ops.toml").is_file():
            return 0
        from _project import merge_settings
        base = merge_settings(root)[0]
        hit = any(tracks_base(words, base) for words in segments(command))
    except Exception:  # noqa: BLE001 - a guard bug must not block all commands
        return 0
    if hit:
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": f"[branch_guard] nhánh mới sẽ theo dõi origin/{base}: thêm `--no-track` "
                                        f"(vd `git switch -c <nhánh> --no-track origin/{base}`).",
        }}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
