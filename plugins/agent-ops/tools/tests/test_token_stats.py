"""Tests for token_stats.py context-fill metrics (E03-T29, D-217). Uses a fake transcript in a temp dir."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location("token_stats", Path(__file__).resolve().parents[1] / "token_stats.py")
ts = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ts)


def tool_use(uid: str, name: str, **inp) -> dict:
    return {"type": "tool_use", "id": uid, "name": name, "input": inp}


def tool_result(uid: str, text: str, as_list: bool = False) -> dict:
    content = [{"type": "text", "text": text}] if as_list else text
    return {"type": "tool_result", "tool_use_id": uid, "content": content}


def assistant(mid: str, blocks: list) -> dict:
    usage = {"input_tokens": 1, "cache_read_input_tokens": 10, "cache_creation_input_tokens": 5, "output_tokens": 2}
    return {"type": "assistant", "timestamp": "2026-11-26T10:00:00Z", "message": {"id": mid, "usage": usage, "content": blocks}}


def user(blocks) -> dict:
    return {"type": "user", "timestamp": "2026-11-26T10:00:00Z", "message": {"content": blocks}}


class ContextFill(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name) / "s1" / "subagents"
        self.dir.mkdir(parents=True)

    def run_lines(self, lines: list) -> dict:
        path = self.dir / "agent-a.jsonl"
        path.write_text("\n".join(json.dumps(x) for x in lines), encoding="utf-8")
        return ts.parse_run(path)

    def test_buckets(self):
        run = self.run_lines([
            user("Làm E03-T29"),
            assistant("m1", [
                tool_use("a", "Read", file_path="/r/management/tasks/E03/E03-T29-x/task.md"),
                tool_use("b", "Bash", command="sed -n 1,40p management/tasks/E03/x/task.md"),
                tool_use("c", "Bash", command="git log --oneline | grep E03"),
                tool_use("d", "Grep", pattern="D-217"),
                tool_use("e", "Bash", command="cat CLAUDE.md"),
                tool_use("f", "Bash", command="grep -n D-094 CLAUDE.md"),
                tool_use("g", "Bash", command="ls management/tasks"),
            ]),
            user([
                tool_result("a", "x" * 400), tool_result("b", "y" * 80, as_list=True),
                tool_result("c", "z" * 40), tool_result("d", "w" * 40),
                tool_result("e", "q" * 4000), tool_result("f", "v" * 8), tool_result("g", "u" * 4000),
            ]),
        ])
        self.assertEqual(run["task_md"], 100 + 20)
        self.assertEqual(run["grep"], 10 + 10 + 2)  # grep of CLAUDE.md counts as grep, not a re-read
        self.assertEqual(run["claude_md_reads"], 1)
        self.assertEqual(run["task"], "E03-T29")

    def test_render_has_fill_line_and_column(self):
        run = self.run_lines([user("x"), assistant("m1", [])])
        out = ts.render([run], "agent")
        self.assertIn("đọc `task.md` 0", out)
        self.assertIn("task.md/lượt (tv)", out)

    def test_writes_are_not_reads_and_other_readers_count(self):
        run = self.run_lines([
            user("x"),
            assistant("m1", [
                tool_use("a", "Bash", command="cat >> management/tasks/E03/x/task.md <<'EOF'"),
                tool_use("b", "Bash", command="sed -i 's/a/b/' management/tasks/E03/x/task.md"),
                tool_use("c", "Bash", command="git show HEAD:management/tasks/E03/x/task.md"),
                tool_use("d", "Bash", command="less management/tasks/E03/x/task.md"),
                tool_use("e", "Bash", command="grep -n '^## ' management/tasks/E03/x/task.md"),
                tool_use("f", "Read", file_path="/r/CLAUDE.md", offset=10, limit=20),
            ]),
            user([
                tool_result("a", "a" * 400), tool_result("b", "b" * 400), tool_result("c", "c" * 40),
                tool_result("d", "d" * 40), tool_result("e", "e" * 40), tool_result("f", "f" * 400),
            ]),
        ])
        self.assertEqual(run["task_md"], 10 + 10)  # git show + less; cat >> and sed -i are writes
        self.assertEqual(run["grep"], 10)  # grep on task.md is a grep, not a section read
        self.assertEqual(run["claude_md_reads"], 1)  # a partial Read is still a re-read

    def test_error_and_odd_results(self):
        run = self.run_lines([
            user("x"),
            assistant("m1", [tool_use("a", "Grep", pattern="x"), tool_use("b", "Grep", pattern="y")]),
            user([{"type": "tool_result", "tool_use_id": "a", "is_error": True, "content": "e" * 40},
                  {"type": "tool_result", "tool_use_id": "b", "content": ["not-a-dict", {"type": "image"}]}]),
        ])
        self.assertEqual(run["grep"], 10)

    def test_render_by_task_and_empty(self):
        run = self.run_lines([user("Làm E03-T29"), assistant("m1", [])])
        self.assertIn("| E03-T29 |", ts.render([run], "task"))
        self.assertIn("Không có lượt agent", ts.render([], "agent"))

    def test_task_md_name_must_match_exactly(self):
        run = self.run_lines([
            user("x"),
            assistant("m1", [tool_use("a", "Read", file_path="/r/docs/subtask.md.bak")]),
            user([tool_result("a", "x" * 400)]),
        ])
        self.assertEqual(run["task_md"], 0)


class MainSession(unittest.TestCase):
    def test_render_main(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            def call(mid, ctx):
                return {"type": "assistant", "timestamp": "2026-11-26T10:00:00Z",
                        "message": {"id": mid, "usage": {"cache_read_input_tokens": ctx, "output_tokens": 3}}}
            lines = [call("a", 100_000), call("a", 100_000), call("b", 200_000)]  # "a" repeated: counted once
            (root / "s1.jsonl").write_text("\n".join(json.dumps(x) for x in lines), encoding="utf-8")
            (root / "old.jsonl").write_text(json.dumps(dict(call("c", 1), timestamp="2026-01-01T00:00:00Z")), encoding="utf-8")
            out = ts.render_main(root, "2026-11-01")
            self.assertIn("Phiên: 1; gọi model: 2", out)
            self.assertIn("50% số lần gọi, 67% token ngữ cảnh", out)
            self.assertEqual(ts.render_main(root / "none", None), "")


if __name__ == "__main__":
    unittest.main()
