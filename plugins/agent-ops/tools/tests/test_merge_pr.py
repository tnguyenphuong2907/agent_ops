"""Tests for merge_pr.py pure helpers (D-219 token optimisation)."""
import importlib.util
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location("merge_pr", Path(__file__).resolve().parents[1] / "merge_pr.py")
mp = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mp)


class TaskIds(unittest.TestCase):
    def test_single(self):
        self.assertEqual(mp.task_ids("feat/E04-T68-s0-cap-paid-used"), ["E04-T68"])

    def test_range_keeps_existing_middle(self):
        self.assertEqual(mp.task_ids("chore/E03-T26-T28-x", {"E03-T26", "E03-T27", "E03-T28"}),
                         ["E03-T26", "E03-T27", "E03-T28"])

    def test_range_drops_missing_middle(self):
        self.assertEqual(mp.task_ids("chore/E03-T26-T28-x", {"E03-T26", "E03-T28"}), ["E03-T26", "E03-T28"])

    def test_subtask_suffix_ignored(self):
        self.assertEqual(mp.task_ids("docs/E13-T04-S05-verify-pages"), ["E13-T04"])

    def test_no_task(self):
        self.assertEqual(mp.task_ids("docs/2026-11-24-plan"), [])
        self.assertEqual(mp.task_ids("docs/LL-019-design-drift"), [])


class Frontmatter(unittest.TestCase):
    def test_status(self):
        self.assertEqual(mp.frontmatter_status("---\nid: E03-T31\nstatus: done\n---\n# x"), "done")
        self.assertEqual(mp.frontmatter_status("---\nstatus: \"in-review\"\n---"), "in-review")

    def test_status_outside_frontmatter_ignored(self):
        self.assertIsNone(mp.frontmatter_status("---\nid: x\n---\nstatus: done"))
        self.assertIsNone(mp.frontmatter_status("# no frontmatter"))


class CiVerdict(unittest.TestCase):
    def test_green(self):
        self.assertIsNone(mp.ci_verdict([{"name": "scan", "conclusion": "success"},
                                         {"name": "fe", "conclusion": "skipped"}]))

    def test_missing_scan(self):
        self.assertIn("scan", mp.ci_verdict([{"name": "be", "conclusion": "success"}]))

    def test_failure(self):
        self.assertIn("be=failure", mp.ci_verdict([{"name": "scan", "conclusion": "success"},
                                                   {"name": "be", "conclusion": "failure"}]))


class ShortcutPattern(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location(
            "shortcut", Path(__file__).resolve().parents[2] / "hooks/scripts/task_shortcuts.py")
        self.hook = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.hook)

    def test_matches(self):
        for p in ("mp", " mp ", "mp 252", "mp #252 253"):
            self.assertEqual(self.hook.match(p)[0], "merge_pr.py", p)

    def test_ct(self):
        self.assertEqual(self.hook.match("ct"), ("close_task.py", []))
        self.assertEqual(self.hook.match("ct e03-t31"), ("close_task.py", ["E03-T31"]))
        self.assertIsNone(self.hook.match("ct E03-T31 nhé"))

    def test_no_match(self):
        for p in ("mp nhé", "mpx", "merge mp", "xem mp 252 giúp"):
            self.assertIsNone(self.hook.match(p), p)


if __name__ == "__main__":
    unittest.main()
