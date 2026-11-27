import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _project import is_moved  # noqa: E402


def test_is_moved_matches_prefix_only(tmp_path: Path) -> None:
    (tmp_path / ".agent-ops.toml").write_text('[links]\nmoved = [".claude/agents"]\n', encoding="utf-8")
    assert is_moved(tmp_path / ".claude/agents/pm.md", tmp_path)
    assert is_moved(tmp_path / ".claude/agents", tmp_path)
    assert not is_moved(tmp_path / ".claude/agents-x/pm.md", tmp_path)
    assert not is_moved(tmp_path / ".claude/skills/a/SKILL.md", tmp_path)


def test_is_moved_without_config(tmp_path: Path) -> None:
    assert not is_moved(tmp_path / ".claude/agents/pm.md", tmp_path)
