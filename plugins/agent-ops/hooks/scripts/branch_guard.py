"""PreToolUse hook on Bash: stop creating a branch that would track the base branch.

`git switch -c feat/x origin/main` sets origin/main as the upstream of feat/x, so a later push or pull
aims at the base branch. Such commands need `--no-track`. Any internal error lets the call pass.
Standard library only.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

CREATE = {"switch": {"-c", "-C", "--create", "--force-create"}, "checkout": {"-b", "-B"}, "worktree": {"-b", "-B"}}
GIT_VALUE_OPTS = {"-C", "-c", "--git-dir", "--work-tree"}


HEREDOC = re.compile(r"<<-?[ \t]*(['\"]?)([A-Za-z_]\w*)\1")


def segments(command: str) -> list[list[str]]:
    """Words of each simple command; quoted text stays one word, comments and heredoc bodies are skipped."""
    out: list[list[str]] = [[]]
    word, quote, started, pending = "", "", False, []
    text = command.replace("\\\n", " ")
    i = 0

    def end_word() -> None:
        nonlocal word, started
        if started:
            out[-1].append(word)
        word, started = "", False

    while i < len(text):
        ch = text[i]
        if quote:
            if ch == quote:
                quote = ""
            elif ch == "\\" and quote == '"' and i + 1 < len(text):
                i += 1
                word += text[i]
            else:
                word += ch
        elif ch in "'\"":
            quote, started = ch, True
        elif ch == "\\" and i + 1 < len(text):
            i += 1
            word, started = word + text[i], True
        elif ch == "#" and not started:
            end = text.find("\n", i)
            i = len(text) if end < 0 else end
            continue
        elif text.startswith("<<", i) and not text.startswith("<<<", i) and (m := HEREDOC.match(text, i)):
            end_word()
            pending.append(m.group(2))
            i = m.end()
            continue
        elif ch == "\n":
            end_word()
            out.append([])
            while pending:
                m = re.compile(rf"(?m)^\t*{pending.pop(0)}$").search(text, i + 1)
                i = m.end() if m else len(text)
        elif ch in ";&|()":
            end_word()
            out.append([])
        elif ch.isspace():
            end_word()
        else:
            word, started = word + ch, True
        i += 1
    end_word()
    return out


def new_branch(rest: list[str], flags: set[str]) -> str | None:
    """Name given to a create option, in the forms `-c x`, `-cx` and `--create=x`."""
    for i, a in enumerate(rest):
        if a in flags:
            return rest[i + 1] if i + 1 < len(rest) else None
        for flag in flags:
            if flag.startswith("--") and a.startswith(flag + "="):
                return a[len(flag) + 1:]
            if not flag.startswith("--") and a.startswith(flag) and len(a) > len(flag):
                return a[len(flag):]
    return None


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
    name = new_branch(rest, CREATE[sub])
    return name is not None and name != base


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
