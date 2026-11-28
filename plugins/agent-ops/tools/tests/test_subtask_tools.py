"""Tests for ctx_pack, task_step, dod_report, plan errors and the session view of token_stats."""
import contextlib
import importlib
import io
import json
import re
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
ct = importlib.import_module("close_task")
chk = importlib.import_module("check_task")
pack = importlib.import_module("ctx_pack")
step = importlib.import_module("task_step")
dod = importlib.import_module("dod_report")
stats = importlib.import_module("token_stats")


def sub(plan: str = "", body: str = "", status: str = "ready") -> str:
    return (f"---\nid: E09-T01-S02\nstatus: {status}\nassignee: backend-dev\nactual_hours:\n"
            f"selfcheck:                # api | ui\nplan: {plan}   # opus\ncommit:\n---\n\n"
            f"## Việc cần làm\n- Phụ trách: F09-AC2 (lưới server), 4.\n\n"
            f"## Kế hoạch  ·  _planner_\n> hướng dẫn\n{body}\n\n## Tiến trình  ·  _dev_\n-\n\n## Kết quả\n-\n")


class Plan(unittest.TestCase):
    def test_no_plan_flag(self):
        self.assertEqual(chk.plan_errors("s", sub()), [])

    def test_flag_without_plan(self):
        for body in ("", "-", "<!-- soon -->"):
            self.assertIn("còn trống", chk.plan_errors("s", sub("opus", body))[0])

    def test_flag_with_plan_and_bad_value(self):
        self.assertEqual(chk.plan_errors("s", sub("opus", "1. handler.py")), [])
        self.assertIn("lạ", chk.plan_errors("s", sub("sonnet"))[0])

    def test_templates_pass(self):
        text = (TOOLS.parent / "templates" / "subtask.md").read_text(encoding="utf-8")
        self.assertEqual(chk.plan_errors("s", text), [])


class Pack(unittest.TestCase):
    def test_who(self):
        self.assertTrue(pack.for_subtask("S01–S03, S06", "S02"))
        self.assertTrue(pack.for_subtask("mọi vai (chỉ AC của mình)", "S05"))
        self.assertTrue(pack.for_subtask("", "S05"))
        self.assertFalse(pack.for_subtask("S04, S06", "S05"))

    def test_owned_acs(self):
        self.assertEqual(pack.owned_acs(sub()), {("F09", 2), ("F09", 4)})
        self.assertEqual(pack.owned_acs("không có"), set())

    def test_excerpt_narrows_acs(self):
        lines = ["head", "- [ ] **F09-AC1** — a", "- [ ] **F09-AC2** — b", "tail"]
        out = pack.excerpt(lines, 1, 99, {("F09", 2)})
        self.assertEqual(out[:3], ["1: head", "3: - [ ] **F09-AC2** — b", "4: tail"])
        self.assertIn("bỏ 1", out[3])

    def test_parts_stay_below_limit(self):
        parts = pack.split_parts(["a" * 25 + "\n", "b\n" * 20], limit=20)
        self.assertTrue(all(len(p) <= 20 for p in parts))
        self.assertEqual("".join(parts), "a" * 25 + "\n" + "b\n" * 20)


class Step(unittest.TestCase):
    TASK = ("---\nid: E09-T01\nstatus: ready\n---\n\n## Subtasks\n| ID | Tiêu đề | Trạng thái |\n|---|---|---|\n"
            "| E09-T01-S02 | a \\| b | ready |\n| E09-T01-S03 | c | ready |\n")
    LOG = "## 8. Lịch sử\n| Thời gian | Ai | Thay đổi |\n|---|---|---|\n| 2026-01-01 00:00 | pm | tạo |\n"

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)
        (self.dir / "task.md").write_text(self.TASK, encoding="utf-8")
        (self.dir / "log.md").write_text(self.LOG, encoding="utf-8")
        self.sub = self.dir / "E09-T01-S02-x.md"
        patch = mock.patch.object(step.ct, "find_task", lambda tid: self.dir / "task.md")
        patch.start()
        self.addCleanup(patch.stop)

    def run_step(self, *args):
        with contextlib.redirect_stdout(io.StringIO()):
            return step.main(["E09-T01-S02", *args])

    def read(self, name):
        return (self.dir / name).read_text(encoding="utf-8")

    def test_start_then_done(self):
        self.sub.write_text(sub(), encoding="utf-8")
        self.assertEqual(self.run_step("start"), 0)
        task = self.read("task.md")
        self.assertIn("status: in_progress", task)
        self.assertIn("| a \\| b | in_progress |", task)
        self.assertIn("| c | ready |", task)
        self.assertIn("E09-T01 ready → in_progress", self.read("log.md"))
        self.assertEqual(self.run_step("done", "--commit", "abc1234", "--note", "xong"), 0)
        text = self.sub.read_text(encoding="utf-8")
        fm = ct.frontmatter(text)
        self.assertEqual((fm["status"], fm["actual_hours"], fm["commit"]), ("in_review", "0", "abc1234"))
        self.assertIn("selfcheck:                # api | ui", text)
        self.assertIn("(", text.split("## Tiến trình")[1])
        self.assertNotIn("\n-\n\n## Kết quả\n-\n\n-", text)

    def test_refuses_wrong_state_and_missing_plan(self):
        self.sub.write_text(sub(status="backlog"), encoding="utf-8")
        self.assertEqual(self.run_step("start"), 1)
        self.sub.write_text(sub("opus"), encoding="utf-8")
        self.assertEqual(self.run_step("start"), 1)
        self.assertEqual(self.read("task.md"), self.TASK)

    def test_put_field_empty_value_keeps_next_line(self):
        text = "---\nactual_hours:\nselfcheck:  # c\n---\n"
        self.assertEqual(step.put_field(text, "actual_hours", "1"), "---\nactual_hours: 1\nselfcheck:  # c\n---\n")

    def test_started_at_takes_latest(self):
        history = ("| 2026-01-01 10:00 | d | E09-T01-S02 ready → in_progress |\n"
                   "| 2026-01-02 11:00 | d | E09-T01-S02 in_review → in_progress |\n")
        self.assertEqual(step.started_at(history, "E09-T01-S02"), datetime(2026, 1, 2, 11, 0))


class Dod(unittest.TestCase):
    def test_parsers(self):
        review = ("**Kết quả:** ✅ Approved\n| # | Mức | Nhận xét | Đã sửa? |\n|---|---|---|---|\n"
                  "| 1 | Minor | a \\| b | |\n| 2 | Nit | c | ✅ |\n")
        self.assertEqual(dod.findings(review), [("1", "Minor", ""), ("2", "Nit", "✅")])
        self.assertEqual(dod.result_lines(review), ["**Kết quả:** ✅ Approved"])
        self.assertEqual(len(dod.unchecked("ok\nSafari **chưa kiểm**\n❌ AC2")), 2)
        self.assertTrue(dod.only_under(["management/a"], "management/"))
        self.assertFalse(dod.only_under(["management/a", "backend/b"], "management/"))


class Session(unittest.TestCase):
    def test_render_and_pick(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            def call(mid, model, **usage):
                return json.dumps({"type": "assistant", "timestamp": "2026-11-28T00:00:00Z",
                                   "message": {"id": mid, "model": model, "usage": usage, "content": []}})
            (root / "aaa1.jsonl").write_text(call("m", "big", output_tokens=200_000), encoding="utf-8")
            subs = root / "aaa1" / "subagents"
            subs.mkdir(parents=True)
            (subs / "agent-x.jsonl").write_text(call(
                "n", "small", cache_creation_input_tokens=500_000,
                cache_creation={"ephemeral_1h_input_tokens": 500_000}), encoding="utf-8")
            self.assertEqual(stats.find_session(root, "last"), root / "aaa1.jsonl")
            self.assertEqual(stats.find_session(root, "aaa"), root / "aaa1.jsonl")
            self.assertIsNone(stats.find_session(root, "zzz"))
            out = stats.render_session(root / "aaa1.jsonl")
            self.assertIn("2.00M", out)
            self.assertIn("| big | 1 | 1.00M | 50% |", out)
            self.assertIn("| small | 1 | 1.00M | 50% |", out)


if __name__ == "__main__":
    unittest.main()
