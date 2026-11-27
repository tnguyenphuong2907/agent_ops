"""Tests for build_inbox P-LAI: the 'phương án lai' line must name an option letter present in the options table."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import build_inbox as bi  # noqa: E402

LABEL = "**Đã cân nhắc phương án lai / để sau?**"
TABLE = "| Tiêu chí | A. Giữ | B′. Lai | C. Bỏ |\n|---|---|---|---|\n| Công sức | 1 | 2 | 3 |\n"


def make(line=f"{LABEL} có: C là lai", *, table=TABLE, created="2026-11-20", status="in_review", extra=""):
    text = (
        f"---\nid: DR-902\ntitle: \"Q?\"\ntype: 2\nstatus: {status}\ntopic: ops\ncreated: {created}\n"
        "deadline: 2026-12-20\naffects: []\nrelated: []\n---\n# DR-902 — Q?\n\n## 1. Câu hỏi\nx\n\n## 2. Tóm tắt\nx\n\n"
        f"## 3. Phương án\n{line}\n\n{table}{extra}\n## 4. Đề xuất\n**Chọn: A**\n\n## 5. Bằng chứng\nx\n"
    )
    tmp = Path(tempfile.mkdtemp()) / "DR-902-x.md"
    tmp.write_text(text, encoding="utf-8")
    return bi.parse(tmp)


def errs(meta):
    return [m for m in bi.check_hybrid_line(meta) if "P-LAI" in m]


class HybridLine(unittest.TestCase):
    # Case 1: many samples / lines
    def test_letter_in_table_ok(self):
        self.assertEqual(errs(make()), [])

    def test_prime_letter_ok_and_ascii_apostrophe(self):
        self.assertEqual(errs(make(f"{LABEL} có: B' là lai")), [])
        self.assertEqual(errs(make(f"{LABEL} Có. B′ là lai")), [])

    def test_no_letter_reports_line_number(self):
        r = errs(make(f"{LABEL} có: gộp hai ý lại"))
        self.assertEqual(len(r), 1)
        self.assertIn("dòng 21", r[0])

    def test_letter_not_in_table(self):
        self.assertEqual(len(errs(make(f"{LABEL} có: D là lai"))), 1)

    def test_word_starting_with_capital_is_not_a_letter(self):
        self.assertEqual(len(errs(make(f"{LABEL} có: Cả hai đều lai, Bỏ qua"))), 1)

    def test_khong_needs_no_letter(self):
        self.assertEqual(errs(make(f"{LABEL} không: hai phương án loại nhau")), [])

    # Case 2: bold / italic
    def test_italic_and_bold_value(self):
        self.assertEqual(errs(make(f"{LABEL} **có**: C là lai")), [])
        self.assertEqual(errs(make(f"**Đã cân nhắc phương án lai / để sau?** _có_ A")), [])

    def test_bold_header_cell(self):
        t = TABLE.replace("A. Giữ", "**A.** Giữ")
        self.assertEqual(errs(make(f"{LABEL} có: A", table=t)), [])

    # Case 3: empty cell
    def test_empty_value(self):
        self.assertEqual(len(errs(make(LABEL))), 1)

    def test_placeholder_value(self):
        self.assertEqual(len(errs(make(f"{LABEL} <có/không; nếu có nêu phương án lai>"))), 1)

    def test_no_table_headers(self):
        self.assertEqual(len(errs(make(table="| Tiêu chí | Giữ | Bỏ |\n|---|---|---|\n"))), 1)

    # Case 4: wrong value
    def test_wrong_start(self):
        self.assertEqual(len(errs(make(f"{LABEL} chưa rõ, C"))), 1)

    def test_letter_only_in_fenced_code_ignored(self):
        self.assertEqual(len(errs(make(extra="", line=f"```\n{LABEL} có: C\n```\n{LABEL} có: gộp"))), 1)

    # Case 5: date / status thresholds
    def test_decided_and_superseded_skipped(self):
        for st in ("decided", "superseded"):
            self.assertEqual(errs(make(f"{LABEL} có: gộp", status=st)), [])

    def test_withdrawn_skipped(self):
        self.assertEqual(errs(make(f"{LABEL} có: gộp", status="withdrawn")), [])

    def test_open_and_provisional_checked(self):
        for st in ("open", "provisional", "draft"):
            self.assertEqual(len(errs(make(f"{LABEL} có: gộp", status=st))), 1)

    def test_old_ticket_skipped(self):
        self.assertEqual(errs(make(f"{LABEL} có: gộp", created="2026-11-05")), [])

    def test_no_line_skipped(self):
        self.assertEqual(errs(make("Không có dòng lai")), [])


if __name__ == "__main__":
    unittest.main()
