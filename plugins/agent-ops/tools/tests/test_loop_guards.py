"""Tests for build_inbox.check_loop_guards (D-110, F7). Run: python3 -m unittest discover management/tools/tests"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import build_inbox as bi  # noqa: E402

R1 = (
    "**Bài toán gốc:** việc thật\n**Ràng buộc bỏ được:** ràng buộc X\n**Phương án bỏ ràng buộc:** B\n\n"
    "| Tiêu chí | A. Một | B. Hai |\n|---|---|---|\n| Tác dụng | x | y |\n"
)
HIST1 = "| 2026-11-08 | architect | Soạn |\n| 2026-11-08 | decision-reviewer | Vòng 1 |\n"


def dr(*, r1=R1, sec7="### Vòng 1 (2026-11-08)\n**Kết luận:** ✅ ok\n", sec9="", hist=HIST1,
       status="open", created="2026-11-08"):
    text = (f"---\nid: DR-X\nstatus: {status}\ncreated: {created}\n---\n# T\n\n## 3. Phương án\n{r1}\n"
            f"## 4. Đề xuất\n\n## 7. Phản biện\n{sec7}\n## 8. Phản hồi\n\n## 9. Hỏi thêm\n{sec9}\n"
            f"## 10. Hồ sơ\n\n## Lịch sử\n| Thời gian | Ai | Thay đổi |\n|---|---|---|\n{hist}")
    return {"_text": text, "status": status, "created": created}


class LoopGuards(unittest.TestCase):
    def test_valid_round_1(self):
        self.assertEqual(bi.check_loop_guards(dr()), [])

    def test_explain_flow_not_double_counted(self):
        d = dr(sec7="### Vòng 1 (2026-11-08)\n**Kết luận:** ✅\n### Vòng 2 (2026-11-09)\n**Kết luận:** ✅ ok\n",
               sec9="**Trả lời (decision-reviewer, 2026-11-09):** ...\n",
               hist=HIST1 + "| 2026-11-09 | decision-reviewer | Vòng 2 |\n")
        self.assertEqual(bi.review_rounds(d["_text"]), 2)
        self.assertEqual(bi.check_loop_guards(d), [])
        self.assertEqual(bi._last(bi._section(d["_text"], "## 7.", "## 8."), r"\*\*Kết luận:\*\*[ \t]*([^\n]+)"), "✅ ok")

    def test_template_heading_not_counted(self):
        d = dr(sec7="### Vòng 1 (YYYY-MM-DD)\n", hist="| 2026-11-08 | architect | Soạn |\n")
        self.assertEqual(bi.review_rounds(d["_text"]), 0)

    def test_over_two_rounds(self):
        d = dr(sec7="### Vòng 1 (a)\n### Vòng 2 (b)\n### Vòng 3 (c)\n")
        self.assertTrue(any("vòng 3 > 2" in m for m in bi.check_loop_guards(d)))

    def test_round_2_in_review(self):
        d = dr(sec7="### Vòng 1 (a)\n### Vòng 2 (b)\n", status="in_review")
        self.assertTrue(any("chuyển open" in m for m in bi.check_loop_guards(d)))

    def test_missing_or_placeholder_r1(self):
        miss = R1.replace("**Ràng buộc bỏ được:** ràng buộc X\n", "")
        self.assertTrue(any("thiếu dòng" in m for m in bi.check_loop_guards(dr(r1=miss))))
        ph = R1.replace("việc thật", "<việc thật>")
        self.assertTrue(any("<…>" in m for m in bi.check_loop_guards(dr(r1=ph))))
        bad = R1.replace("bỏ ràng buộc:** B", "bỏ ràng buộc:** Z")
        self.assertTrue(any("không khớp" in m for m in bi.check_loop_guards(dr(r1=bad))))

    def test_old_dr_skipped(self):
        self.assertEqual(bi.check_loop_guards(dr(r1="", created="2026-11-05")), [])

    def r1_with(self, value, cols="| Tiêu chí | A. Một | B. Hai |"):
        r1 = R1.replace("bỏ ràng buộc:** B", f"bỏ ràng buộc:** {value}").replace("| Tiêu chí | A. Một | B. Hai |", cols)
        return bi.check_loop_guards(dr(r1=r1))

    def test_f7_1_option_letter(self):
        for ok in ("B", "**B**", "A"):
            self.assertEqual(self.r1_with(ok), [], ok)
        for bad in ("b", "`Z`", "không có", "Bỏ hết", "A′", "C′"):
            self.assertTrue(self.r1_with(bad), bad)
        self.assertEqual(self.r1_with("A′", "| Tiêu chí | A′. Một | B. Hai |"), [])
        self.assertTrue(self.r1_with("A", "| Tiêu chí | A′. Một | B. Hai |"))
        self.assertTrue(self.r1_with("A2", "| Tiêu chí | A1. Một | A2. Hai |") == [])
        self.assertTrue(self.r1_with("A", "| Tiêu chí | A1. Một | A2. Hai |"))
        self.assertEqual(self.r1_with("A", "| Tiêu chí | **A.** Một | `B` Hai |"), [])
        self.assertEqual(self.r1_with("B", "| Tiêu chí | **A.** Một | `B` Hai |"), [])

    def test_f7_2_code_and_comments_ignored(self):
        sec7 = ("### Vòng 1 (2026-11-08)\n**Kết luận:** ✅\n```\n### Vòng 2\n### Vòng 3\n```\n"
                "<!--\n### Vòng 2\n-->\n")
        d = dr(sec7=sec7)
        self.assertEqual(bi.review_rounds(d["_text"]), 1)
        self.assertEqual(bi.check_loop_guards(d), [])
        d = dr(sec7=sec7, status="in_review")
        self.assertEqual(bi.check_loop_guards(d), [])
        d = dr(sec9="<!-- Trả lời (decision-reviewer, x) -->\n```\nTrả lời (decision-reviewer\n```\n")
        self.assertEqual(bi.review_rounds(d["_text"]), 1)

    def test_f7_3_boundary_date(self):
        self.assertEqual(bi.check_loop_guards(dr(r1="", created="2026-11-07")), [])
        self.assertTrue(bi.check_loop_guards(dr(r1="", created="2026-11-08")))

    def test_f7_4_bad_created(self):
        for c in ("", "08/11/2026", "2026-1-8"):
            self.assertTrue(any("created" in m for m in bi.check_loop_guards(dr(created=c))), c)
        self.assertEqual(bi.check_loop_guards({"_text": "", "status": "open"})[0][:7], "created")


if __name__ == "__main__":
    unittest.main()
