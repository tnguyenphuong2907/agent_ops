# Changelog

## 0.1.0

- First extraction from the Study English project (D-222).
- `tools/`: build_board, build_inbox, check_docs, close_task, merge_pr, retro_stats, token_stats; project discovery in `_project.py` (env `AGENT_OPS_PROJECT_DIR`, `CLAUDE_PROJECT_DIR`, git toplevel) and config in `.agent-ops.toml`.
- `hooks/`: `task_shortcuts.py` (`ct`, `mp`), `ctx_guard.py`, `no-unbounded-wait.sh` (hooks.json).
- `templates/` and `commands/` made project-neutral.
- Not yet in this version: agents and skills (still in the project's `.claude/`).
