"""Tests for build_inbox short-form DRs (D-116). Run: python3 -m unittest discover management/tools/tests"""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import build_inbox as bi  # noqa: E402

BOXES_OK = "".join(f"- [x] điều kiện {i}\n" for i in range(1, 6))


def make(*, status="in_review", typ="2", boxes=BOXES_OK, verdict="⏳", decided_as="", form="short"):
    text = (
        f"---\nid: DR-900\ntitle: \"Câu hỏi?\"\nform: {form}\ntype: {typ}\nstatus: {status}\ntopic: security\n"
        f"created: 2026-11-08\ndeadline: 2026-11-20\ndecided_as: {decided_as}\naffects: []\nrelated: [D-072]\n---\n"
        "# DR-900 — Câu hỏi?\n\n## 1. Vấn đề\nSót.\n\n## 2. Cách sửa\n**Chọn: áp D-072 mục 7**\nLàm.\n\n"
        f"## 3. Điều kiện phiếu ngắn\n{boxes}\n## 4. Cách đảo lại\nBỏ.\n\n"
        f"## 5. Kiểm nhanh\n**Kết luận:** {verdict}\n**Lời nhắn cho PO:** ok\n\n"
        "## Lịch sử\n| Thời gian | Ai | Thay đổi |\n|---|---|---|\n"
    )
    tmp = Path(tempfile.mkdtemp()) / "DR-900-x.md"
    tmp.write_text(text, encoding="utf-8")
    return bi.parse(tmp)


class ShortForm(unittest.TestCase):
    def test_in_review_ok(self):
        self.assertEqual(bi.check_dr(make()), [])

    def test_provisional_with_check_ok(self):
        self.assertEqual(bi.check_dr(make(status="provisional", verdict="✅ đủ 5 điều kiện", decided_as="D-999")), [])

    def test_missing_box(self):
        boxes = BOXES_OK.replace("- [x] điều kiện 5", "- [ ] điều kiện 5")
        self.assertTrue(any("4/5" in m for m in bi.check_dr(make(boxes=boxes))))

    def test_type_1_rejected(self):
        self.assertTrue(any("loại 2" in m for m in bi.check_dr(make(typ="1"))))

    def test_open_rejected(self):
        self.assertTrue(any("không chuyển open" in m for m in bi.check_dr(make(status="open", verdict="✅"))))

    def test_escalated_cannot_be_provisional(self):
        msgs = bi.check_dr(make(status="provisional", verdict="⬆️ thiếu điều kiện 5", decided_as="D-999"))
        self.assertTrue(any("⬆️" in m for m in msgs))

    def test_provisional_needs_verdict(self):
        msgs = bi.check_dr(make(status="provisional", decided_as="D-999"))
        self.assertTrue(any("kiểm nhanh" in m for m in msgs))

    def test_full_form_unaffected(self):
        d = make(form="")
        self.assertFalse(d["_short"])
        self.assertTrue(any("thiếu mục ## 6." in m for m in bi.check_dr(d)))


if __name__ == "__main__":
    unittest.main()
