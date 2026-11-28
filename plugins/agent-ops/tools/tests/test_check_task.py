"""Tests for check_task.py pure checks: one passing and one failing case per rule."""
import importlib.util
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("check_task", ROOT / "tools" / "check_task.py")
chk = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(chk)


def subtask(kind: str, rows: dict[str, str]) -> str:
    body = "\n".join(f"| {k} | q | {v} |" for k, v in rows.items())
    return f"---\nid: E09-T01-S01\nselfcheck: {kind}   # api | ui\n---\n\n## Tự kiểm  ·  _người làm_\n| # | q | a |\n|---|---|---|\n{body}\n\n## Kết quả\n"


def filled(kind: str) -> dict[str, str]:
    return {k: "2.1.4" for k in chk.REQUIRED[kind]}


class SelfCheck(unittest.TestCase):
    def test_no_field_is_ignored(self):
        self.assertEqual(chk.selfcheck_errors("s", "---\nselfcheck:     # api | ui\n---\n"), [])

    def test_filled_passes(self):
        rows = filled("api") | {"H6": "không áp dụng vì chỉ đọc", "H7": r"a \| b"}
        self.assertEqual(chk.selfcheck_errors("s", subtask("api", rows)), [])

    def test_missing_blank_and_reasonless(self):
        rows = filled("ui") | {"M2": "", "M3": "Không áp dụng", "M4": "không áp dụng vì …"}
        del rows["M6"]
        errors = chk.selfcheck_errors("s", subtask("ui", rows))
        self.assertEqual([re.search(r"M\d", e).group(0) for e in errors], ["M2", "M3", "M4", "M6"])

    def test_both_kinds_and_unknown_kind(self):
        self.assertEqual(len(chk.selfcheck_errors("s", subtask("api, ui", filled("api")))), 6)
        self.assertIn("lạ", chk.selfcheck_errors("s", subtask("db", {}))[0])

    def test_template_tables_match_required_ids(self):
        text = (ROOT / "templates" / "design-selfcheck.md").read_text(encoding="utf-8")
        self.assertEqual(re.findall(r"(?m)^\| ([HM]\d+) \|", text), chk.REQUIRED["api"] + chk.REQUIRED["ui"])

    def test_subtask_template_has_no_error(self):
        text = (ROOT / "templates" / "subtask.md").read_text(encoding="utf-8")
        self.assertEqual(chk.selfcheck_errors("s", text), [])


class Findings(unittest.TestCase):
    HEAD = "| # | Mức độ | Nhận xét | Đã sửa? |\n|---|---|---|---|\n"

    def test_closed(self):
        self.assertEqual(chk.unclosed_findings(self.HEAD + "| 1 | Minor | a | b | ✅ 2.1 |\n"), [])

    def test_empty_and_waiting(self):
        body = self.HEAD + "| 1 | Minor | a | |\n| 2 | Minor | b | Chờ DR-077 |\n| 3 | Nit | c | để PO quyết |\n"
        self.assertEqual([e.split(":")[0] for e in chk.unclosed_findings(body)], ["mục 4 bảng 1 #1", "mục 4 bảng 1 #2"])

    def test_other_tables_ignored(self):
        self.assertEqual(chk.unclosed_findings(self.HEAD + "\n| AC | Kết quả |\n|---|---|\n| AC1 | |\n"), [])


class Warnings(unittest.TestCase):
    def test_stale_range(self):
        maxima = chk.ac_maxima("F02-AC1 ... F02-AC26 và F02-AC1..25")
        self.assertEqual(maxima, {"F02": 26})
        self.assertEqual(len(chk.line_warnings("x", "đủ F02-AC1..25", maxima)), 1)
        self.assertEqual(chk.line_warnings("x", "đủ F02-AC1..26, F02-AC21–AC23", maxima), [])

    def test_waiting_wording(self):
        self.assertEqual(len(chk.line_warnings("x", "chờ product-analyst duyệt", {})), 1)
        self.assertEqual(chk.line_warnings("x", "người học chờ phản hồi", {}), [])

    def test_added_lines(self):
        diff = "+++ b/docs/a.md\n@@ -1 +3,2 @@\n-old\n+one\n+two\n+++ /dev/null\n@@ -1 +0,0 @@\n-x\n"
        self.assertEqual(chk.added_lines(diff), [("docs/a.md", 3, "one"), ("docs/a.md", 4, "two")])


if __name__ == "__main__":
    unittest.main()
