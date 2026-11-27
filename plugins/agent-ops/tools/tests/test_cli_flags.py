"""Tests for build_inbox CLI flags (E01-T18-S02, AC7). Run as a subprocess against a temp copy so the real Inbox is never touched."""
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path

TOOL = Path(__file__).resolve().parents[1] / "build_inbox.py"


class CliFlags(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        (root / "management" / "tools").mkdir(parents=True)
        (root / "management" / "decision-requests").mkdir()
        self.tool = root / "management" / "tools" / "build_inbox.py"
        for name in ("build_inbox.py", "check_docs.py", "build_board.py", "_project.py"):  # --check loads its sibling tools by path
            shutil.copy(TOOL.with_name(name), root / "management" / "tools" / name)
        self.inbox = root / "management" / "DECISIONS-INBOX.md"
        self.inbox.write_text("SENTINEL\n", encoding="utf-8")
        self.root = root
        patcher = mock.patch.dict(os.environ, {"AGENT_OPS_PROJECT_DIR": str(root)})
        patcher.start()
        self.addCleanup(patcher.stop)

    def run_tool(self, *flags: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, "-I", str(self.tool), *flags], capture_output=True, text=True, check=False)

    def digest(self) -> str:
        return hashlib.sha256(self.inbox.read_bytes()).hexdigest()

    def test_unknown_flag_errors_and_keeps_inbox(self):
        before = self.digest()
        for flag in ("--foo", "--chek", "--chec", "-x"):
            r = self.run_tool(flag)
            self.assertNotEqual(r.returncode, 0, flag)
            self.assertIn("usage", r.stderr.lower(), flag)
            self.assertEqual(self.digest(), before, flag)

    def test_unknown_flag_next_to_check_still_errors(self):
        r = self.run_tool("--check", "--foo")
        self.assertNotEqual(r.returncode, 0)

    def test_help_prints_usage_rc0_and_keeps_inbox(self):
        before = self.digest()
        for flag in ("--help", "-h"):
            r = self.run_tool(flag)
            self.assertEqual(r.returncode, 0, flag)
            self.assertIn("--check", r.stdout)
            self.assertEqual(self.digest(), before, flag)

    def test_no_flag_still_writes_and_check_still_checks(self):
        r = self.run_tool()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotEqual(self.inbox.read_text(encoding="utf-8"), "SENTINEL\n")
        self.inbox.write_text("SENTINEL\n", encoding="utf-8")
        subprocess.run([sys.executable, "-I", str(self.tool.with_name("build_board.py"))], check=True, capture_output=True)
        r = self.run_tool("--check")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.inbox.read_text(encoding="utf-8"), "SENTINEL\n")


if __name__ == "__main__":
    unittest.main()
