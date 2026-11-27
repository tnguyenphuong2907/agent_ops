"""Project discovery shared by every agent-ops tool. Stdlib only.

Project root, in order: env AGENT_OPS_PROJECT_DIR, env CLAUDE_PROJECT_DIR, `git rev-parse --show-toplevel` from cwd, cwd.
Config: `.agent-ops.toml` at the project root, e.g.

    plugin_path = "../agent-ops/plugins/agent-ops"   # used by the shims in <management>/tools
    [paths]
    management = "management"                         # default
    [merge]
    base = "main"                                     # default
    required_checks = []                              # check-run names a PR must have (default: none)
"""
from __future__ import annotations

import os
import subprocess
import tomllib
from pathlib import Path

CONFIG_NAME = ".agent-ops.toml"
DEFAULT_MANAGEMENT = "management"
DEFAULT_BASE_BRANCH = "main"


def project_root() -> Path:
    for var in ("AGENT_OPS_PROJECT_DIR", "CLAUDE_PROJECT_DIR"):
        value = os.environ.get(var)
        if value:
            return Path(value).resolve()
    try:
        out = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=True).stdout.strip()
        if out:
            return Path(out).resolve()
    except (OSError, subprocess.CalledProcessError):
        pass
    return Path.cwd().resolve()


def load_config(root: Path | None = None) -> dict:
    """Parsed `.agent-ops.toml` of the project, or {} when missing or unreadable."""
    path = (root or project_root()) / CONFIG_NAME
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return {}


class ConfigError(Exception):
    """`.agent-ops.toml` cannot be trusted for a gate."""


def merge_settings(root: Path | None = None) -> tuple[str, list[str]]:
    """(base branch, required check names) from `[merge]`. Strict: these drive merge gates.

    Unlike `load_config`, a file that exists but cannot be read or parsed raises, so a typo never
    silently drops a required check. A missing file means the defaults.
    """
    path = (root or project_root()) / CONFIG_NAME
    try:
        config = tomllib.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        config = {}
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as e:
        raise ConfigError(f"không đọc được {CONFIG_NAME}: {e}") from e
    section = config.get("merge", {})
    if not isinstance(section, dict):
        raise ConfigError(f"{CONFIG_NAME}: [merge] phải là bảng")
    unknown = sorted(set(section) - {"base", "required_checks"})
    if unknown:
        raise ConfigError(f"{CONFIG_NAME}: [merge] có khoá lạ: {', '.join(unknown)}")
    base = section.get("base", DEFAULT_BASE_BRANCH)
    checks = section.get("required_checks", [])
    if not isinstance(base, str) or not base.strip():
        raise ConfigError(f"{CONFIG_NAME}: merge.base phải là chuỗi không rỗng")
    if not isinstance(checks, list) or not all(isinstance(c, str) and c for c in checks):
        raise ConfigError(f"{CONFIG_NAME}: merge.required_checks phải là danh sách tên check")
    return base.strip(), checks


def mgmt_rel(root: Path | None = None) -> str:
    """Management directory relative to the project root, posix style (default `management`)."""
    value = load_config(root).get("paths", {}).get("management", DEFAULT_MANAGEMENT)
    return str(value).strip("/") or DEFAULT_MANAGEMENT


def mgmt_dir(root: Path | None = None) -> Path:
    root = root or project_root()
    return root / mgmt_rel(root)


def moved_paths(root: Path | None = None) -> list[Path]:
    """Absolute prefixes listed in `[links] moved` of `.agent-ops.toml`.

    Files under these prefixes moved into the plugin; old links to them stay valid history.
    """
    root = root or project_root()
    return [(root / str(p)).resolve() for p in load_config(root).get("links", {}).get("moved", [])]


def is_moved(dest: Path, root: Path | None = None) -> bool:
    dest = dest.resolve()
    return any(dest == m or m in dest.parents for m in moved_paths(root))
