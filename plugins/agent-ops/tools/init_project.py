"""Create the files agent-ops expects in a project. Only missing files are written; nothing is overwritten.

Usage: python3 "${CLAUDE_PLUGIN_ROOT}/tools/init_project.py" [--management DIR] [--base BRANCH]
  --management DIR  management directory (default `management`; ignored when `.agent-ops.toml` exists)
  --base BRANCH     merge base branch (default: origin/HEAD, else local main/master, else
                     current branch; ignored when the config exists)
The copies belong to the project: later plugin updates do not change them. Stdlib only.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import tomllib
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
from _project import CONFIG_NAME, DEFAULT_BASE_BRANCH, DEFAULT_MANAGEMENT, mgmt_rel, project_root  # noqa: E402

SCAFFOLD = TOOLS.parent / "templates" / "project"
EMPTY_DIRS = ("tasks", "decision-requests")
SAFE_VALUE_RE = re.compile(r"[\w./-]+")  # values are pasted into TOML strings


def default_base(root: Path) -> str:
    def git(*args: str) -> str:
        res = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=False)
        return res.stdout.strip() if res.returncode == 0 else ""

    remote = git("symbolic-ref", "--short", "refs/remotes/origin/HEAD")
    if remote:
        return remote.removeprefix("origin/")
    for name in (DEFAULT_BASE_BRANCH, "master"):
        if git("rev-parse", "--verify", "--quiet", f"refs/heads/{name}"):
            return name
    return git("branch", "--show-current") or DEFAULT_BASE_BRANCH


def write_missing(path: Path, text: str, root: Path, created: list[str], kept: list[str]) -> None:
    name = path.relative_to(root).as_posix()
    if not path.parent.resolve().is_relative_to(root):
        raise ValueError(f"{name} trỏ ra ngoài dự án (symlink); không ghi")
    if path.exists() or path.is_symlink():
        kept.append(name)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    created.append(name)


def init(root: Path, management: str, base: str) -> tuple[list[str], list[str]]:
    """Write the scaffold under `root`; returns (created, kept) relative paths."""
    created: list[str] = []
    kept: list[str] = []
    config = root / CONFIG_NAME
    if config.exists():
        try:
            tomllib.loads(config.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as e:
            raise ValueError(f"{CONFIG_NAME} không đọc được; sửa file rồi chạy lại") from e
        management = mgmt_rel(root)
    text = (SCAFFOLD / "agent-ops.toml").read_text(encoding="utf-8").format(management=management, base=base)
    write_missing(config, text, root, created, kept)
    profile = ".claude/project-profile.md"
    write_missing(root / profile, (SCAFFOLD / profile).read_text(encoding="utf-8"), root, created, kept)
    source = SCAFFOLD / "management"
    for item in sorted(source.rglob("*")):
        if item.is_file():
            body = item.read_text(encoding="utf-8").replace("management/", f"{management}/")
            write_missing(root / management / item.relative_to(source), body, root, created, kept)
    for name in EMPTY_DIRS:
        write_missing(root / management / name / ".gitkeep", "", root, created, kept)
    return created, kept


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter,
                                     allow_abbrev=False)
    parser.add_argument("--management", default=DEFAULT_MANAGEMENT)
    parser.add_argument("--base")
    args = parser.parse_args(argv)
    root = project_root()
    management = args.management.strip("/")
    if not management or not (root / management).resolve().is_relative_to(root):
        parser.error("--management phải là thư mục con của dự án")
    base = args.base or default_base(root)
    if not all(SAFE_VALUE_RE.fullmatch(v) for v in (management, base)):
        parser.error("--management và --base chỉ gồm chữ, số, `_ . / -`")
    try:
        created, kept = init(root, management, base)
    except ValueError as e:
        print(f"Dừng: {e}")
        return 2
    for name in created:
        print(f"tạo      {name}")
    for name in kept:
        print(f"giữ      {name} (đã có)")
    env = {**os.environ, "AGENT_OPS_PROJECT_DIR": str(root)}
    for tool in ("build_board.py", "build_inbox.py"):
        mgmt = root / mgmt_rel(root)
        target = mgmt / ("BOARD.md" if tool == "build_board.py" else "DECISIONS-INBOX.md")
        if not target.exists() and subprocess.run([sys.executable, str(TOOLS / tool)], env=env, check=False).returncode:
            return 1
    print("\nBước tiếp: điền .claude/project-profile.md, thêm tên check CI vào [merge] required_checks.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
