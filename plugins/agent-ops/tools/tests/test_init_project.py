"""Tests for init_project.py: a fresh repository must pass the tool checks right after init."""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]


def run(root, tool, *args):
    env = {k: v for k, v in os.environ.items() if k != "CLAUDE_PROJECT_DIR"}
    env["AGENT_OPS_PROJECT_DIR"] = str(root)
    return subprocess.run([sys.executable, str(TOOLS / tool), *args], env=env, capture_output=True, text=True)


class InitProject(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve()
        subprocess.run(["git", "init", "-q", "-b", "trunk", str(self.root)], check=True)

    def assert_checks_clean(self):
        for tool in ("build_board.py", "build_inbox.py"):
            res = run(self.root, tool, "--check")
            self.assertEqual(res.returncode, 0, res.stdout + res.stderr)

    def test_empty_repo_passes_checks(self):
        res = run(self.root, "init_project.py")
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assert_checks_clean()
        self.assertIn('base = "trunk"', (self.root / ".agent-ops.toml").read_text(encoding="utf-8"))

    def test_custom_management_dir(self):
        res = run(self.root, "init_project.py", "--management", "ops/pm")
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assert_checks_clean()
        self.assertFalse((self.root / "management").exists())

    def test_never_overwrites(self):
        (self.root / "management").mkdir()
        (self.root / "management" / "README.md").write_text("mine\n", encoding="utf-8")
        run(self.root, "init_project.py")
        res = run(self.root, "init_project.py")
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertNotIn("tạo ", res.stdout)
        self.assertEqual((self.root / "management" / "README.md").read_text(encoding="utf-8"), "mine\n")

    def test_broken_config_stops(self):
        (self.root / ".agent-ops.toml").write_text("[merge\n", encoding="utf-8")
        self.assertEqual(run(self.root, "init_project.py").returncode, 2)
        self.assertFalse((self.root / "management").exists())

    def test_management_outside_project_rejected(self):
        self.assertEqual(run(self.root, "init_project.py", "--management", "../x").returncode, 2)


if __name__ == "__main__":
    unittest.main()
