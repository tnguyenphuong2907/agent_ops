# Changelog

## 0.3.0

- Design self-check: `templates/design-selfcheck.md` (API H1–H7, UI M1–M6), subtask frontmatter `selfcheck:` and section `## Tự kiểm`.
- `tools/check_task.py`: self-check tables, unclosed review findings, stale AC ranges, leftover waiting wording. `close_task.py` now stops on the first two. **Action needed:** a project with tool shims adds one for `check_task.py`; an open task with an empty "Đã sửa?" cell must fill it before `ct`.
- Rules: AC cite source IDs, briefs carry review criteria and closing owner (limit 16 lines), hold dependent work while a DR is open, grep old wording after each decision.

## 0.2.0

- `tools/init_project.py` + `/agent-ops:init`: scaffold a new project (config, project profile, process rules, decision policy, lessons, decision log) from `templates/project/`. Never overwrites.
- `[merge] base` and `[merge] required_checks` replace the hardcoded `main` and `scan`. **Action needed:** a project that relied on the `scan` gate must add `required_checks = ["scan"]`; `merge_pr.py` reads the list from `.agent-ops.toml` on origin/<base> and stops when the key is missing (`[]` requires none), so a project that has not declared it cannot be merged by `mp` (merge that first PR by hand). `merge_pr.py` and `close_task.py` stop on an unreadable `.agent-ops.toml`.
- `[inbox.topics]` and `[inbox] analyst_topics` replace the hardcoded topic list and the `learning` rule. **Action needed:** projects using the `learning` topic must declare both.
- Generated headers of BOARD and DECISIONS-INBOX name the tool instead of a project path (regenerate once).
- Removed ticket IDs of the source project from tool messages; the hybrid-option error prefix is now `P-LAI`.

## 0.1.0

- First extraction from the Study English project (D-222).
- `tools/`: build_board, build_inbox, check_docs, close_task, merge_pr, retro_stats, token_stats; project discovery in `_project.py` (env `AGENT_OPS_PROJECT_DIR`, `CLAUDE_PROJECT_DIR`, git toplevel) and config in `.agent-ops.toml`.
- `hooks/`: `task_shortcuts.py` (`ct`, `mp`), `ctx_guard.py`, `no-unbounded-wait.sh` (hooks.json).
- `templates/` and `commands/` made project-neutral.
- 12 agents, 14 shared skills, 9 commands.
