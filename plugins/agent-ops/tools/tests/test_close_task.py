"""Tests for close_task.py pure helpers (D-219 token optimisation)."""
import importlib.util
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location("close_task", Path(__file__).resolve().parents[1] / "close_task.py")
ct = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ct)

TASK = """---
id: E09-T01
status: in_qa          # backlog | ready | in_progress | in_review | in_qa | done | blocked
qa: qa
actual_hours:
---

## Subtasks
| ID | Tiêu đề | Người làm | Ước lượng (h) | Trạng thái |
|---|---|---|---|---|
| E09-T01-S01 | A | dev | 1 | done |
| E09-T01-S02 | B | dev | 1 | in_review |

## 4. Review  ·  _chủ sở hữu: code-reviewer_
**Kết quả:** ⏳ Chờ review  <!-- ✅ Approved | 🔁 Changes requested -->

## 5. Nghiệm thu QA  ·  _chủ sở hữu: qa_
**Kết quả:** ✅ Passed (2026-11-26)

## 6. ⚠️ Cần quyết định
<!-- - [DR-012](x) -->
Không có.

## 8. Lịch sử
| Thời gian | Ai | Thay đổi |
|---|---|---|
| 2026-11-25 | pm | tạo |
"""

EPIC = """# E09

## Danh sách task
| ID | Tiêu đề | Trạng thái | Ngày dự kiến | Phụ thuộc |
|---|---|---|---|---|
| E09-T01 | A | in_qa | | |
| E09-T02 | B | **done** 2026-11-20 (review Approved, QA Passed) | | |

## Lịch sử
| Ngày | Ai | Thay đổi |
|---|---|---|
| 2026-11-20 | pm | x |
"""


class Helpers(unittest.TestCase):
    def test_frontmatter_strips_comment(self):
        fm = ct.frontmatter(TASK)
        self.assertEqual((fm["status"], fm["qa"], fm["actual_hours"]), ("in_qa", "qa", ""))

    def test_set_field_keeps_comment(self):
        out = ct.set_field(TASK, "status", "done")
        self.assertIn("status: done          # backlog", out)
        self.assertEqual(out.count("status:"), 1)

    def test_result_ignores_template_comment(self):
        self.assertFalse(ct.result_ok(ct.section(TASK, 4), "Approved"))
        self.assertTrue(ct.result_ok(ct.section(TASK, 5), "Passed"))

    def test_subtask_rows(self):
        self.assertEqual(ct.subtask_rows(TASK, "E09-T01"), [("E09-T01-S01", "done"), ("E09-T01-S02", "in_review")])

    def test_add_history_row(self):
        out = ct.add_history_row(TASK, "| new |")
        self.assertTrue(out.rstrip().endswith("| 2026-11-25 | pm | tạo |\n| new |"))
        out = ct.add_history_row(EPIC, "| e |")
        self.assertTrue(out.rstrip().endswith("| 2026-11-20 | pm | x |\n| e |"))

    def test_mark_epic_row(self):
        out, statuses = ct.mark_epic_row(EPIC, "E09-T01", "**done** 2026-11-26 (ok)")
        self.assertIn("| E09-T01 | A | **done** 2026-11-26 (ok) | | |", out)
        self.assertEqual(statuses[1], "**done** 2026-11-20 (review Approved, QA Passed)")
        with self.assertRaises(ValueError):
            ct.mark_epic_row(EPIC, "E09-T09", "x")

    def test_infer_id(self):
        self.assertEqual(ct.infer_id("feat/E04-T68-s0-cap"), "E04-T68")
        with self.assertRaises(SystemExit):
            ct.infer_id("chore/close-task-script")


if __name__ == "__main__":
    unittest.main()
