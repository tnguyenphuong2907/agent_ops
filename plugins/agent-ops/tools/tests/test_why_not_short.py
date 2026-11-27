"""Tests for build_inbox D-135: full-form type-2 DRs must state why the short form does not fit."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import build_inbox as bi  # noqa: E402

MSG = "Vì sao không phiếu ngắn"


def make(*, typ="2", created="2026-11-11", line="**Vì sao không phiếu ngắn:** có hai hướng PO có lý do chọn",
         status="in_review"):
    text = (
        f"---\nid: DR-901\ntitle: \"Q?\"\ntype: {typ}\nstatus: {status}\ntopic: ops\ncreated: {created}\n"
        "deadline: 2026-11-20\naffects: []\nrelated: []\n---\n# DR-901 — Q?\n\n## 1. Câu hỏi\nx\n\n## 2. Tóm tắt\nx\n\n"
        "## 3. Phương án\nx\n\n## 4. Đề xuất\n**Chọn: A**\nPhân loại: **Loại 2**\n" + line + "\n\n"
        "## 5. Bằng chứng\nx\n\n## 6. Ảnh hưởng\nx\n\n## 7. Phản biện\n\n## 8. Phản hồi\n\n## Lịch sử\n"
    )
    tmp = Path(tempfile.mkdtemp()) / "DR-901-x.md"
    tmp.write_text(text, encoding="utf-8")
    return bi.parse(tmp)


def has(meta):
    return any(MSG in m for m in bi.validate(meta))


class WhyNotShort(unittest.TestCase):
    def test_present_ok(self):
        self.assertFalse(has(make()))

    def test_missing(self):
        self.assertTrue(has(make(line="")))

    def test_placeholder(self):
        self.assertTrue(has(make(line="**Vì sao không phiếu ngắn:** <điều kiện nào>")))

    def test_type_1_exempt(self):
        self.assertFalse(has(make(typ="1", line="")))

    def test_old_ticket_exempt(self):
        self.assertFalse(has(make(created="2026-11-08", line="")))

    def test_draft_exempt(self):
        self.assertFalse(has(make(status="draft", line="")))


if __name__ == "__main__":
    unittest.main()
