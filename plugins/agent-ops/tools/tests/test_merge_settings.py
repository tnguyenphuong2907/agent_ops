"""Tests for _project.merge_settings: the `[merge]` config that drives merge gates."""
import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _project  # noqa: E402


class MergeSettings(unittest.TestCase):
    def settings(self, text):
        with tempfile.TemporaryDirectory() as d:
            if text is not None:
                (Path(d) / ".agent-ops.toml").write_text(text, encoding="utf-8")
            return _project.merge_settings(Path(d))

    def test_defaults(self):
        self.assertEqual(self.settings(None), ("main", None))
        self.assertEqual(self.settings('[paths]\nmanagement = "m"\n'), ("main", None))
        self.assertEqual(self.settings("[merge]\nrequired_checks = []\n"), ("main", []))

    def test_configured(self):
        self.assertEqual(self.settings('[merge]\nbase = "develop"\nrequired_checks = ["scan"]\n'),
                         ("develop", ["scan"]))

    def test_bad_config_raises(self):
        for text in ("[merge\n", 'merge = "x"\n', '[merge]\nbase = ""\n', '[merge]\nrequired_checks = "scan"\n',
                     '[merge]\nrequired_checks = [1]\n', '[merge]\nrequired_check = ["scan"]\n'):
            with self.subTest(text=text), self.assertRaises(_project.ConfigError):
                self.settings(text)


class GateChecks(unittest.TestCase):
    """merge_pr.gate_checks reads the gate from origin/<base>, never from the working tree."""

    def setUp(self):
        spec = importlib.util.spec_from_file_location("merge_pr", Path(__file__).resolve().parents[1] / "merge_pr.py")
        self.mp = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.mp)

    def gate(self, remote_text, rc=0):
        calls = []

        def fake_sh(*cmd, check=True):
            calls.append(cmd)
            return subprocess.CompletedProcess(cmd, rc, remote_text, "")

        self.mp.sh = fake_sh
        try:
            return self.mp.gate_checks("main")
        finally:
            self.assertEqual(calls, [("git", "show", "origin/main:.agent-ops.toml")])

    def test_declared(self):
        self.assertEqual(self.gate('[merge]\nrequired_checks = ["scan"]\n'), ["scan"])
        self.assertEqual(self.gate("[merge]\nrequired_checks = []\n"), [])

    def test_stops(self):
        for text, rc in (("", 0), ('[merge]\nbase = "main"\n', 0), ("[merge\n", 0), ("", 128),
                         ('[merge]\nbase = "dev"\nrequired_checks = []\n', 0)):
            with self.subTest(text=text, rc=rc), self.assertRaises(self.mp.ConfigError):
                self.gate(text, rc)


if __name__ == "__main__":
    unittest.main()
