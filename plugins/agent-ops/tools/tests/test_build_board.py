"""Tests for build_board: BOARD.md generated from task/epic frontmatter + DR status (E01-T31-S01, S02; AC1, AC2)."""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import build_board as bb  # noqa: E402

TOOL = Path(bb.__file__)


def make_root(tmp: str) -> Path:
    root = Path(tmp)
    (root / "management" / "decision-requests").mkdir(parents=True)
    return root


def add_task(root: Path, epic_dir: str, name: str, **fm: str) -> None:
    d = root / "management" / "tasks" / f"{epic_dir}-x" / name
    d.mkdir(parents=True, exist_ok=True)
    lines = "\n".join(f"{k}: {v}" for k, v in fm.items())
    (d / "task.md").write_text(f"---\n{lines}\n---\n# body\n", encoding="utf-8")


def add_epic(root: Path, epic: str, status: str = "in_progress") -> None:
    d = root / "management" / "tasks" / f"{epic}-x"
    d.mkdir(parents=True, exist_ok=True)
    (d / "epic.md").write_text(f'---\nid: {epic}\ntitle: "Epic {epic}"\nstatus: {status}\n---\n', encoding="utf-8")


def add_dr(root: Path, n: int, status: str, deadline: str = "") -> None:
    (root / "management" / "decision-requests" / f"DR-{n:03d}-x.md").write_text(
        f'---\nid: DR-{n:03d}\ntitle: "Câu hỏi {n}"\nstatus: {status}\ndeadline: {deadline}\n---\n', encoding="utf-8")


class BoardFixture(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = make_root(tmp.name)

    def board(self) -> str:
        return bb.generate_for(self.root)


class GenerateFromFrontmatter(BoardFixture):
    """AC1"""

    def setUp(self):
        super().setUp()
        add_epic(self.root, "E01")
        add_task(self.root, "E01", "E01-T01-a", id="E01-T01", epic="E01", title='"Một | hai"', status="done",
                 assignee="architect", priority="P1", planned_date="2026-11-01  # ghi chú")
        add_task(self.root, "E01", "E01-T02-b", id="E01-T02", epic="E01", title="Hai", status="ready",
                 assignee="", priority="P2", planned_date="")
        add_task(self.root, "E01", "E01-T03-c", id="E01-T03", epic="E01", title="Ba", status="weird")

    def test_every_task_listed_under_its_status(self):
        text = self.board()
        sections = {h: body for h, body in (s.split("\n", 1) for s in text.split("\n### ")[1:])}
        done = next(b for h, b in sections.items() if h.startswith("done"))
        ready = next(b for h, b in sections.items() if h.startswith("ready"))
        self.assertIn("E01-T01", done)
        self.assertNotIn("E01-T01", ready)
        self.assertIn("E01-T02", ready)
        self.assertTrue(any(h.startswith("weird") and "E01-T03" in b for h, b in sections.items()))

    def test_columns_values_and_escaping(self):
        row = next(line for line in self.board().splitlines() if line.startswith("| [E01-T01]"))
        self.assertIn("(tasks/E01-x/E01-T01-a/task.md)", row)
        self.assertIn("Một \\| hai", row)
        self.assertIn("architect", row)
        self.assertIn("P1", row)
        self.assertIn("2026-11-01 |", row)
        self.assertNotIn("ghi chú", row)

    def test_missing_values_shown_as_dash(self):
        row = next(line for line in self.board().splitlines() if line.startswith("| [E01-T02]"))
        self.assertTrue(row.endswith("| — | P2 | — |"), row)

    def test_epic_progress(self):
        self.assertIn("| 1/3 | in_progress |", self.board())

    def test_order_follows_status_priority_then_id(self):
        text = self.board()
        self.assertLess(text.index("### ready"), text.index("### done"))
        self.assertLess(text.index("### done"), text.index("### weird"))

    def test_generating_twice_is_stable_and_has_no_history_paragraph(self):
        path = self.root / "management" / "BOARD.md"
        path.write_text(self.board(), encoding="utf-8")
        first = path.read_text(encoding="utf-8")
        self.assertEqual(self.board(), first)
        self.assertNotIn("Cập nhật lần cuối", first)


class PmBlock(BoardFixture):
    """AC1: the hand-written block survives regeneration."""

    def test_pm_block_preserved_byte_for_byte(self):
        add_task(self.root, "E01", "E01-T01-a", id="E01-T01", epic="E01", title="A", status="done")
        note = "**Giai đoạn:** G1\n\n- việc PO: nạp credit | `code`\n"
        path = self.root / "management" / "BOARD.md"
        path.write_text(f"cũ\n{bb.PM_BEGIN}\n{note}{bb.PM_END}\ncũ\n", encoding="utf-8")
        out = self.board()
        self.assertIn(f"{bb.PM_BEGIN}\n{note.rstrip()}\n{bb.PM_END}", out)
        path.write_text(out, encoding="utf-8")
        self.assertEqual(self.board(), out)

    def test_markers_quoted_in_header_are_not_mistaken_for_the_block(self):
        path = self.root / "management" / "BOARD.md"
        path.write_text(self.board(), encoding="utf-8")
        path.write_text(path.read_text(encoding="utf-8").replace(bb.PM_PLACEHOLDER, "ghi chú thật"), encoding="utf-8")
        self.assertIn("ghi chú thật", self.board())

    def test_placeholder_when_board_missing_or_without_markers(self):
        self.assertIn(bb.PM_PLACEHOLDER, self.board())
        (self.root / "management" / "BOARD.md").write_text("không có marker\n", encoding="utf-8")
        self.assertIn(bb.PM_PLACEHOLDER, self.board())


class PendingForPo(BoardFixture):
    """AC2"""

    def test_open_and_provisional_listed_decided_not(self):
        add_dr(self.root, 1, "open", deadline="2026-12-01")
        add_dr(self.root, 2, "provisional")
        add_dr(self.root, 3, "decided")
        add_dr(self.root, 4, "draft")
        add_dr(self.root, 5, "withdrawn")
        text = self.board()
        self.assertIn("[DR-001](decision-requests/DR-001-x.md)", text)
        self.assertIn("hạn 2026-12-01", text)
        self.assertIn("[DR-002]", text)
        for n in ("003", "004", "005"):
            self.assertNotIn(f"DR-{n}", text)
        self.assertIn("(DECISIONS-INBOX.md)", text)

    def test_none_pending_message(self):
        add_dr(self.root, 3, "decided")
        self.assertIn("Không có phiếu DR", self.board())


class Cli(BoardFixture):
    def run_tool(self, *flags: str) -> subprocess.CompletedProcess:
        (self.root / "management" / "tools").mkdir(exist_ok=True)
        tool = self.root / "management" / "tools" / "build_board.py"
        shutil.copy(TOOL, tool)
        shutil.copy(TOOL.with_name("_project.py"), tool.with_name("_project.py"))
        patcher = mock.patch.dict(os.environ, {"AGENT_OPS_PROJECT_DIR": str(self.root)})
        patcher.start()
        self.addCleanup(patcher.stop)
        return subprocess.run([sys.executable, "-I", str(tool), *flags], capture_output=True, text=True, check=False)

    def test_write_then_check_clean_and_hand_edit_detected(self):
        add_task(self.root, "E01", "E01-T01-a", id="E01-T01", epic="E01", title="A", status="done")
        self.assertNotEqual(self.run_tool("--check").returncode, 0)  # no BOARD yet
        self.assertEqual(self.run_tool().returncode, 0)
        self.assertEqual(self.run_tool("--check").returncode, 0)
        path = self.root / "management" / "BOARD.md"
        path.write_text(path.read_text(encoding="utf-8").replace("| E01 |", "| E09 |"), encoding="utf-8")
        self.assertEqual(self.run_tool("--check").returncode, 1)

    def test_unknown_flag_rc2(self):
        self.assertEqual(self.run_tool("--foo").returncode, 2)


if __name__ == "__main__":
    unittest.main()
