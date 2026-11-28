"""Tests for brief_guard.py: allowed and denied agent spawns."""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("brief_guard", HERE / "brief_guard.py")
guard = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(guard)

LINES = "Quyết định đang treo: không có\n- **Reviewer sẽ kiểm:** AC\nĐầu ra bắt buộc: commit\nĐóng việc: qa\n"


def call(role="backend-dev", model="sonnet", prompt="Làm E09-T01-S02\n" + LINES) -> dict:
    return {"subagent_type": f"agent-ops:{role}", "model": model, "prompt": prompt}


class Guard(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.task = self.root / "management" / "tasks" / "E09-x" / "E09-T01-y"
        self.task.mkdir(parents=True)
        (self.root / ".agent-ops.toml").write_text("", encoding="utf-8")

    def problems(self, **kw):
        return guard.problems(call(**kw), self.root)

    def plan_file(self, body: str):
        (self.task / "E09-T01-S02-z.md").write_text(
            f"---\nplan: opus\n---\n## Kế hoạch\n{body}\n", encoding="utf-8")

    def test_complete_brief_passes(self):
        self.assertEqual(self.problems(), [])

    def test_missing_lines(self):
        found = self.problems(prompt="Làm E09-T01-S02\nĐóng việc: qa")
        self.assertIn("Reviewer sẽ kiểm", found[0])
        self.assertNotIn("`Đóng việc:`", found[0])

    def test_out_of_scope(self):
        for kw in ({"role": "pm", "prompt": "E09-T01"}, {"model": "haiku", "prompt": "E09-T01"},
                   {"prompt": "không có mã task"}):
            self.assertEqual(self.problems(**kw), [])
        self.assertEqual(guard.problems({"subagent_type": "Explore", "prompt": "E09-T01"}, self.root), [])

    def test_opus_dev_needs_reason_reviewer_does_not(self):
        self.assertIn("Lý do opus", self.problems(model="opus")[0])
        self.assertEqual(self.problems(model="opus", prompt="E09-T01\nLý do opus: bug nhiều tầng\n" + LINES), [])
        self.assertEqual(self.problems(model="opus", role="code-reviewer"), [])

    def test_plan_run(self):
        prompt = "Chế độ: lập kế hoạch\nSubtask E09-T01-S02"
        self.assertEqual(self.problems(model="opus", prompt=prompt), [])
        self.assertIn("opus", self.problems(model="sonnet", prompt=prompt)[0])

    def test_plan_required_before_code(self):
        self.plan_file("")
        self.assertIn("kế hoạch", self.problems()[0])
        self.plan_file("1. handler.py")
        self.assertEqual(self.problems(), [])

    def test_script_denies_and_survives_garbage(self):
        env = os.environ | {"CLAUDE_PROJECT_DIR": str(self.root)}
        def run(stdin):
            return subprocess.run([sys.executable, str(HERE / "brief_guard.py")], input=stdin, env=env,
                                  capture_output=True, text=True, check=True).stdout
        out = json.loads(run(json.dumps({"tool_input": call(prompt="E09-T01")})))
        self.assertEqual(out["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertEqual(run("not json"), "")


if __name__ == "__main__":
    unittest.main()
