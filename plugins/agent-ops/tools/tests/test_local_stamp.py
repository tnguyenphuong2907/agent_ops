import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import merge_pr  # noqa: E402
from _project import ConfigError, parse_local_stamp_dir, parse_merge_settings  # noqa: E402


class LocalStamp(unittest.TestCase):
    def test_config_key(self):
        text = '[merge]\nrequired_checks = []\nlocal_stamp_dir = "local-check"\n'
        self.assertEqual(parse_merge_settings(text), ("main", []))
        self.assertEqual(parse_local_stamp_dir(text), "local-check")
        self.assertIsNone(parse_local_stamp_dir("[merge]\n"))
        with self.assertRaises(ConfigError):
            parse_merge_settings('[merge]\nlocal_stamp_dir = ""\n')

    def test_gate(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            stamps = Path(tmp, ".git", "local-check")
            stamps.mkdir(parents=True)
            (stamps / "abc").write_text("scan\n")
            with mock.patch.object(merge_pr, "REPO", Path(tmp)), mock.patch.object(merge_pr, "out", return_value=".git"):
                merge_pr.check_stamp("local-check", "abc")
                with self.assertRaises(merge_pr.Skip):
                    merge_pr.check_stamp("local-check", "def")
