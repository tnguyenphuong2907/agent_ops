"""Tests for _project.merge_settings: the `[merge]` config that drives merge gates."""
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
        self.assertEqual(self.settings(None), ("main", []))
        self.assertEqual(self.settings('[paths]\nmanagement = "m"\n'), ("main", []))

    def test_configured(self):
        self.assertEqual(self.settings('[merge]\nbase = "develop"\nrequired_checks = ["scan"]\n'),
                         ("develop", ["scan"]))

    def test_bad_config_raises(self):
        for text in ("[merge\n", 'merge = "x"\n', '[merge]\nbase = ""\n', '[merge]\nrequired_checks = "scan"\n',
                     '[merge]\nrequired_checks = [1]\n', '[merge]\nrequired_check = ["scan"]\n'):
            with self.subTest(text=text), self.assertRaises(_project.ConfigError):
                self.settings(text)


if __name__ == "__main__":
    unittest.main()
