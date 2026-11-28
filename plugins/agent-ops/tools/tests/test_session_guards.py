"""Tests for the handoff helper, brief, prepare_close, dr_apply, task_section, signatures and PR text."""
import contextlib
import importlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
ct = importlib.import_module("close_task")
handoff = importlib.import_module("handoff")
pack = importlib.import_module("ctx_pack")
brief = importlib.import_module("brief")
prep = importlib.import_module("prepare_close")
dr = importlib.import_module("dr_apply")
section = importlib.import_module("task_section")
stats = importlib.import_module("token_stats")

OLD = """# Handoff (2026-01-01, sau rà soát)

- #266 (E07-T12) đã merge; main abc.
- VIỆC TIẾP: sửa rào chắn.
  chi tiết ở file kế hoạch.
- #7 docs/x: bỏ qua (CI đỏ)
- #8 feat/y: merged
- Trạng thái main: 1234abcd msg; build_inbox --check: ok
- [x] việc đã xong
"""


class Handoff(unittest.TestCase):
    def test_keeps_open_lines_only(self):
        text = handoff.compose(OLD, "merge_pr.py", ["- #9 feat/z: merged"], {9}, "2026-01-02")
        self.assertIn("- VIỆC TIẾP: sửa rào chắn.\n  chi tiết ở file kế hoạch.", text)
        self.assertIn("#7 docs/x: bỏ qua", text)
        self.assertIn("- #9 feat/z: merged", text)
        for gone in ("#8 feat/y", "1234abcd", "việc đã xong", "sau rà soát", handoff.DEFAULT_NEXT):
            self.assertNotIn(gone, text)

    def test_skipped_row_replaced_by_new_report(self):
        text = handoff.compose(OLD, "merge_pr.py", ["- #7 docs/x: merged"], {7})
        self.assertNotIn("CI đỏ", text)

    def test_default_next_when_nothing_carried(self):
        self.assertIn(handoff.DEFAULT_NEXT, handoff.compose("", "merge_pr.py", ["- #1 a: merged"], {1}))

    def test_new_lines_cut_first(self):
        old = "".join(f"- việc {i}\n" for i in range(8))
        text = handoff.compose(old, "merge_pr.py", [f"- #{i} b: merged" for i in range(20)])
        self.assertEqual(len(text.splitlines()), handoff.MAX_LINES)
        self.assertIn("việc 7", text)
        self.assertIn("bị lược", text)


class HandoffReview(unittest.TestCase):
    def test_close_lines_never_cut(self):
        old = "".join(f"- việc {i}\n" for i in range(12))
        fresh = ["- Đã đóng E09-T01", "- Bước tiếp: làm X"]
        text = handoff.compose(old, "close_task.py", fresh)
        self.assertTrue(all(line in text for line in fresh), text)

    def test_waiting_lines_drop_after_merge(self):
        old = "- Đã đóng E09-T01; chờ PO: mp 300.\n- Bước tiếp: chờ merge #300\n- Đã đóng E09-T02; chờ PO: mp 301.\n"
        text = handoff.compose(old, "merge_pr.py", ["- #300 a: merged", "- #301 b: bỏ qua (x)"], {300, 301})
        self.assertNotIn("mp 300", text)
        self.assertNotIn("merge #300", text)
        self.assertIn("mp 301", text)

    def test_hand_written_note_kept_after_merge(self):
        note = "- E09-T02 chờ merge #300; sau đó PM chia E09-T03"
        self.assertIn(note, handoff.compose(note, "merge_pr.py", ["- #300 a: merged"], {300}))

    def test_next_step_heading_kept(self):
        text = handoff.compose("## Bước tiếp\nlàm X\n", "merge_pr.py", ["- #1 a: merged"], {1})
        self.assertIn("- Bước tiếp\nlàm X", text)
        self.assertNotIn(handoff.DEFAULT_NEXT, text)


class Pack(unittest.TestCase):
    def test_parts_are_limited_in_bytes(self):
        parts = pack.split_parts(["đường dẫn tiếng Việt ữ ề\n" * 5000, "ỹ" * 40_000])
        self.assertTrue(all(len(p.encode()) <= pack.PART_BYTES < 30_000 for p in parts))
        self.assertEqual("".join(parts), "đường dẫn tiếng Việt ữ ề\n" * 5000 + "ỹ" * 40_000)

    def test_python_signatures(self):
        src = ("import x\n\n@router.get(\n    '/a')\nasync def get(\n    a: int,\n) -> None:\n    secret = 1\n\n"
               "class A(B):\n    name: str\n    def f(self):\n        return 1\n")
        got = "\n".join(pack.signatures("a.py", src))
        for want in ("@router.get(", "    a: int,", "class A(B):", "name: str", "def f(self):"):
            self.assertIn(want, got)
        self.assertNotIn("secret", got)
        self.assertNotIn("return 1", got)

    def test_ts_and_unreadable(self):
        self.assertEqual(pack.signatures("a.ts", "const a = 1\nexport function f() {\n}\n"), ["2: export function f() {"])
        self.assertEqual(pack.signatures("a.py", "def ("), [])

    def test_headings(self):
        self.assertEqual(pack.headings("## A\nx\n### B\ny\n## C\n"),
                         ["- A (dòng 1–4)", "  - B (dòng 3–4)", "- C (dòng 5–5)"])


class Sections(unittest.TestCase):
    def test_number_and_title(self):
        text = "## 1. Yêu cầu\na\n## 3. Tiến trình\nb\n## 7. Trao đổi · 8. Lịch sử\nc\n"
        self.assertEqual(section.find_sections(text, "3"), [(3, 4)])
        self.assertEqual(section.find_sections(text, "8"), [(5, 6)])
        self.assertEqual(section.find_sections(text, "tiến trình"), [(3, 4)])
        self.assertEqual(section.find_sections(text, "9"), [])


class PrBody(unittest.TestCase):
    def test_body(self):
        text = "---\ntitle: \"T\"\n---\n| E09-T01-S01 | Làm A | dev | 1 | done |\n"
        body = ct.pr_body("E09-T01", text, "review Approved", True)
        self.assertIn("- E09-T01-S01: Làm A", body)
        self.assertIn("Claude Code", body)
        self.assertNotIn("Claude Code", ct.pr_body("E09-T01", text, "x", False))


def task_text(result="✅ Approved", fixed="đã sửa", dr_link="") -> str:
    return f"""---
id: E09-T01
status: in_review
qa:
---
## Subtasks
| ID | Tiêu đề | Người làm | h | Trạng thái |
|---|---|---|---|---|
| E09-T01-S01 | A | dev | 1 | in_review |

## 4. Review
**Kết quả:** {result}

| # | Mức độ | Đã sửa? |
|---|---|---|
| 1 | Minor | {fixed} |

## 6. Cần quyết định
{dr_link}

## 7. Trao đổi

## 8. Lịch sử
| Ngày | Ai | Thay đổi |
|---|---|---|
| 2026-01-01 | pm | tạo |
"""


class Project(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.tdir = self.root / "management/tasks/E09-x/E09-T01-y"
        self.drs = self.root / "management/decision-requests"
        for d in (self.tdir, self.drs):
            d.mkdir(parents=True)
        for name, value in (("REPO", self.root), ("TASKS", self.root / "management/tasks"),
                            ("DRS", self.drs), ("MGMT", "management")):
            patch = mock.patch.object(ct, name, value)
            patch.start()
            self.addCleanup(patch.stop)
        self.task = self.tdir / "task.md"
        self.sub = self.tdir / "E09-T01-S01-a.md"
        self.task.write_text(task_text(), encoding="utf-8")
        self.sub.write_text("---\nid: E09-T01-S01\nstatus: in_review\ncommit: abc\nselfcheck:\nplan:\n---\n", encoding="utf-8")

    def run_main(self, module, args):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = module.main(args)
        return code, out.getvalue()

    def test_prepare_close_moves_subtasks(self):
        code, out = self.run_main(prep, ["E09-T01"])
        self.assertEqual(code, 0, out)
        self.assertIn("status: done", self.sub.read_text(encoding="utf-8"))
        text = self.task.read_text(encoding="utf-8")
        self.assertIn("| E09-T01-S01 | A | dev | 1 | done |", text)
        self.assertIn("E09-T01-S01 in_review → done", text)

    def test_prepare_close_refuses_and_keeps_files(self):
        for bad in (task_text(result="🔁 Changes requested"), task_text(fixed="")):
            self.task.write_text(bad, encoding="utf-8")
            code, _ = self.run_main(prep, ["E09-T01"])
            self.assertEqual(code, 1)
            self.assertEqual(self.task.read_text(encoding="utf-8"), bad)
        self.task.write_text(task_text(), encoding="utf-8")
        self.sub.write_text("---\nstatus: in_progress\n---\n", encoding="utf-8")
        self.assertEqual(self.run_main(prep, ["E09-T01"])[0], 1)

    def test_prepare_close_needs_last_result_approved(self):
        self.task.write_text(task_text(result="✅ Approved\n**Kết quả:** 🔁 Changes requested"), encoding="utf-8")
        self.assertEqual(self.run_main(prep, ["E09-T01"])[0], 1)

    def test_brief_has_guard_lines_and_open_items(self):
        (self.drs / "DR-001-a.md").write_text("---\nstatus: open\n---\n", encoding="utf-8")
        self.task.write_text(task_text(fixed="", dr_link="- [DR-001](x)"), encoding="utf-8")
        text = brief.build("E09-T01-S01", 2, False)
        for want in ("Quyết định đang treo: DR-001 (open)", "Reviewer sẽ kiểm:", "Đầu ra bắt buộc:",
                     "Đóng việc:", "Còn mở: #1 Minor", "<điền"):
            self.assertIn(want, text)
        self.assertLessEqual(len(text.splitlines()), 16)
        self.assertTrue(brief.build("E09-T01-S01", 1, True).startswith("Chế độ: lập kế hoạch"))

    def make_dr(self, status="provisional", type_="2"):
        path = self.drs / "DR-001-a.md"
        path.write_text(f"""---
id: DR-001
type: {type_}   # architect
status: {status}
affects: [E09, E09-T01, E09-T01-S01]
decided_as:
---
## 7. Phản biện
**Lưu ý khi làm:** (không chặn)
- E09-T01: đổi cấu hình.
- PM: thêm backlog.

## 10. Hồ sơ
**architect đề xuất:** C — nâng hạn | không đổi schema.

### Quyết định
- Lựa chọn:
- Ghi nhận: D-xxx

## Lịch sử
| Thời gian | Ai | Thay đổi |
|---|---|---|
| 2026-01-01 | architect | soạn |
""", encoding="utf-8")
        (self.root / "management/decisions.md").write_text(
            "| ID | Ngày | Quyết định | Áp dụng | Ghi chú |\n|---|---|---|---|---|\n"
            "| D-007 | 2026-01-01 | x | E09 | |\n\n## Tra cứu\n| D-001 | D-007 | y |\n", encoding="utf-8")
        return path

    def test_dr_apply(self):
        path = self.make_dr()
        ok = mock.Mock(returncode=0, stdout="0 vấn đề")
        with mock.patch.object(ct, "sh", return_value=ok):
            code, out = self.run_main(dr, ["DR-001", "--tokens", "85K"])
        self.assertEqual(code, 0, out)
        decisions = (self.root / "management/decisions.md").read_text(encoding="utf-8").splitlines()
        self.assertTrue(decisions[3].startswith("| D-008 |"), decisions)
        self.assertIn("phương án C:** nâng hạn \\| không đổi schema.", decisions[3])
        text = path.read_text(encoding="utf-8")
        for want in ("decided_as: D-008", "- Lựa chọn: C (áp dụng tạm)", "- Ghi nhận: D-008 (⏳ tạm)", "~85K token"):
            self.assertIn(want, text)
        task = self.task.read_text(encoding="utf-8")
        self.assertIn("  - PM: thêm backlog.", task.split("## 7.")[1].split("## 8.")[0])

    def test_proposal_with_composite_choice(self):
        m = dr.PROPOSAL.search("**architect đề xuất:** A + T1 — giữ link cũ.")
        self.assertEqual(m.groups(), ("A + T1", "giữ link cũ."))

    def test_dr_apply_other_choice_needs_summary(self):
        path = self.make_dr()
        before = path.read_text(encoding="utf-8")
        self.assertEqual(self.run_main(dr, ["DR-001", "--choice", "A"])[0], 1)
        self.assertEqual(path.read_text(encoding="utf-8"), before)

    def test_relink(self):
        src = self.drs / "DR-001-a.md"
        got = dr.relink("- xem [a](../../docs/a.md#x), [b](#muc), [c](https://x.y)", src, self.tdir / "log.md")
        self.assertIn("(../../../../docs/a.md#x)", got)
        self.assertIn("(../../../decision-requests/DR-001-a.md#muc)", got)
        self.assertIn("(https://x.y)", got)

    def test_prepare_close_row_only_subtask(self):
        row = "| E09-T01-S01 | A | dev | 1 | in_review |\n"
        self.task.write_text(task_text().replace(row, row + "| E09-T01-S02 | B | dev | 0 | ready |\n"), encoding="utf-8")
        self.assertEqual(self.run_main(prep, ["E09-T01"])[0], 1)
        self.task.write_text(task_text().replace(row, row + "| E09-T01-S02 | B | dev | 0 | in_review |\n"), encoding="utf-8")
        self.assertEqual(self.run_main(prep, ["E09-T01"])[0], 0)
        self.assertIn("| E09-T01-S02 | B | dev | 0 | done |", self.task.read_text(encoding="utf-8"))

    def test_dr_apply_refuses(self):
        for status, type_ in (("open", "2"), ("provisional", "1")):
            path = self.make_dr(status, type_)
            before = path.read_text(encoding="utf-8")
            self.assertEqual(self.run_main(dr, ["DR-001"])[0], 1)
            self.assertEqual(path.read_text(encoding="utf-8"), before)


class SessionNoise(unittest.TestCase):
    def test_errors_and_big_outputs(self):
        def line(i, content, role="assistant"):
            msg = {"id": f"m{i}", "content": content, "usage": {"input_tokens": 1}}
            return json.dumps({"type": role, "timestamp": "2026-01-01T00:00:00Z", "message": msg})
        use = {"type": "tool_use", "id": "t1", "name": "Bash", "input": {"command": "cat a | head"}}
        res = {"type": "tool_result", "tool_use_id": "t1", "is_error": True, "content": "x" * 31_000}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "s.jsonl"
            path.write_text("\n".join([line(1, [use]), line(2, [res], "user"), line(2, [res], "user")]), encoding="utf-8")
            run = stats.parse_run(path)
            self.assertEqual((len(run["errors"]), len(run["big"])), (1, 1))
            self.assertIn("| 0. phiên chính  | 1 | 1 |", stats.render_session(path))


if __name__ == "__main__":
    unittest.main()
