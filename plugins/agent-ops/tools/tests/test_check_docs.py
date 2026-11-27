"""Tests for check_docs: relative links + anchors (S03, AC3), BOARD drift (S04, AC4), stale proposals (S04, AC5)."""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import check_docs as cd  # noqa: E402

TOOLS = Path(cd.__file__).parent


class Repo(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        for d in ("management/decision-requests", "management/tools", "docs/a"):
            (self.root / d).mkdir(parents=True)
        patcher = mock.patch.dict(os.environ, {"AGENT_OPS_PROJECT_DIR": str(self.root)})
        patcher.start()
        self.addCleanup(patcher.stop)

    def write(self, rel: str, text: str) -> Path:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def links(self) -> list[str]:
        return cd.check_links(self.root)


class Slug(unittest.TestCase):
    def test_github_rules_keep_vietnamese(self):
        self.assertEqual(cd.slug("10. Hồ sơ quyết định cho PO  ·  _pm điền_"), "10-hồ-sơ-quyết-định-cho-po----_pm-điền_")
        self.assertEqual(cd.slug("⚠️ Đang chờ Product Owner"), "-đang-chờ-product-owner")
        self.assertEqual(cd.slug("Dùng `code` và [link](x.md)"), "dùng-code-và-link")

    def test_duplicate_headings_get_numeric_suffix_and_code_blocks_are_skipped(self):
        text = "# A\n## Lặp\n## Lặp\n```\n# Không phải mục\n```\n<a name=\"neo\"></a>\n"
        self.assertEqual(cd.anchors_of(text), {"a", "lặp", "lặp-1", "neo"})


class LinkCheck(Repo):
    """AC3"""

    def test_valid_links_not_reported(self):
        self.write("docs/a/target.md", "# Mục Một\n## Hồ sơ & PO\n")
        self.write("docs/a/dir/x.txt", "x")
        self.write("management/m.md", "[a](../docs/a/target.md) [b](../docs/a/target.md#mục-một) "
                   "[c](../docs/a/target.md#hồ-sơ--po) [d](../docs/a/dir) [e](#tiêu-đề)\n# Tiêu đề\n"
                   "[w](https://x.y/z) [m](mailto:a@b.c) [e%20](../docs/a/target.md#M%E1%BB%A5c-m%E1%BB%99t)\n")
        self.assertEqual(self.links(), [])

    def test_missing_file_reported_with_file_line_and_link(self):
        self.write("docs/m.md", "ok\n\n[x](a/missing.md)\n")
        self.assertEqual(self.links(), ["docs/m.md:3: link hỏng, không có file: a/missing.md"])

    def test_missing_anchor_reported_for_other_file_and_same_file(self):
        self.write("docs/a/t.md", "# Có\n")
        self.write("docs/m.md", "[x](a/t.md#không-có)\n[y](#cũng-không)\n")
        got = self.links()
        self.assertEqual(len(got), 2)
        self.assertIn("docs/m.md:1: link hỏng, không có mục: a/t.md#không-có", got)
        self.assertIn("docs/m.md:2: link hỏng, không có mục: #cũng-không", got)

    def test_links_in_code_blocks_inline_code_and_comments_ignored(self):
        self.write("docs/m.md", "```\n[x](nope.md)\n```\n`[y](nope.md)`\n<!-- [z](nope.md) -->\n<!--\n[w](nope.md)\n-->\n[ok](m.md)\n")
        self.assertEqual(self.links(), [])

    def test_only_management_and_docs_scanned(self):
        self.write("other/m.md", "[x](nope.md)\n")
        self.assertEqual(self.links(), [])

    def test_anchor_on_non_markdown_file_not_checked(self):
        self.write("docs/code.py", "x")
        self.write("docs/m.md", "[x](code.py#L10)\n")
        self.assertEqual(self.links(), [])


class BoardDrift(Repo):
    """AC4"""

    def setUp(self):
        super().setUp()
        shutil.copy(TOOLS / "build_board.py", self.root / "management" / "tools" / "build_board.py")
        shutil.copy(TOOLS / "_project.py", self.root / "management" / "tools" / "_project.py")
        self.write("management/tasks/E01-x/E01-T01-a/task.md", "---\nid: E01-T01\nepic: E01\ntitle: A\nstatus: ready\n---\n")
        board = cd._load_sibling("build_board")
        self.write("management/BOARD.md", board.generate(self.root, "note PM"))

    def test_clean_board_not_reported(self):
        self.assertEqual(cd.check_board(self.root), [])

    def test_hand_edit_outside_pm_block_reported(self):
        path = self.root / "management" / "BOARD.md"
        path.write_text(path.read_text(encoding="utf-8").replace("### ready", "### done"), encoding="utf-8")
        got = cd.check_board(self.root)
        self.assertEqual(len(got), 1)
        self.assertIn("BOARD.md", got[0])

    def test_edit_inside_pm_block_allowed_and_task_status_change_reported(self):
        path = self.root / "management" / "BOARD.md"
        path.write_text(path.read_text(encoding="utf-8").replace("note PM", "ghi chú khác"), encoding="utf-8")
        self.assertEqual(cd.check_board(self.root), [])
        task = self.root / "management/tasks/E01-x/E01-T01-a/task.md"
        task.write_text(task.read_text(encoding="utf-8").replace("ready", "done"), encoding="utf-8")
        self.assertEqual(len(cd.check_board(self.root)), 1)


class StaleProposal(Repo):
    """AC5"""

    def dr(self, n: int, status: str) -> None:
        self.write(f"management/decision-requests/DR-{n:03d}-x.md", f"---\nid: DR-{n:03d}\nstatus: {status}\n---\n")

    def test_decided_ticket_warns_with_file_line_and_dr(self):
        self.dr(26, "decided")
        self.write("docs/m.md", "# T\n> Trạng thái: đề xuất (DR-026)\n")
        got = cd.check_stale_proposals(self.root)
        self.assertEqual(len(got), 1)
        self.assertIn("docs/m.md:2", got[0])
        self.assertIn("DR-026", got[0])

    def test_open_missing_and_other_text_not_reported(self):
        self.dr(27, "open")
        self.write("docs/m.md", "> Trạng thái: đề xuất (DR-027)\n> Trạng thái: đề xuất (DR-099)\n"
                   "> Trạng thái: accepted (DR-026)\nTrạng thái: đề xuất (DR-026)\n```\n> Trạng thái: đề xuất (DR-026)\n```\n")
        self.dr(26, "decided")
        self.assertEqual(cd.check_stale_proposals(self.root), [])


class InboxAnchor(unittest.TestCase):
    def test_dossier_link_uses_the_real_heading_slug(self):
        import build_inbox as bi
        meta = {"_path": bi.DR_DIR / "DR-001-x.md", "id": "DR-001", "_dossier": True,
                "_text": "# T\n## 10. Hồ sơ quyết định cho PO  ·  _pm điền_\n"}
        self.assertTrue(bi.row_link(meta).endswith("#" + cd.slug("10. Hồ sơ quyết định cho PO  ·  _pm điền_") + ")"))
        self.assertIn(cd.slug("10. Hồ sơ quyết định cho PO  ·  _pm điền_"), cd.anchors_of(meta["_text"]))


class CliIntegration(Repo):
    """`build_inbox.py --check` runs the docs checks: rc 1 on errors, rc 0 with only warnings."""

    def setUp(self):
        super().setUp()
        for name in ("build_inbox.py", "check_docs.py", "build_board.py", "_project.py"):
            shutil.copy(TOOLS / name, self.root / "management" / "tools" / name)
        self.write("management/DECISIONS-INBOX.md", "# Inbox\n")
        self.write("management/BOARD.md", "x\n")
        self.run_tool_write_board()

    def run_tool_write_board(self) -> None:
        subprocess.run([sys.executable, "-I", str(self.root / "management/tools/build_board.py")], check=True, capture_output=True)

    def check(self) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, "-I", str(self.root / "management/tools/build_inbox.py"), "--check"],
                              capture_output=True, text=True, check=False)

    def test_clean_repo_rc0(self):
        r = self.check()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_broken_link_rc1_and_named(self):
        self.write("docs/m.md", "[x](nope.md)\n")
        r = self.check()
        self.assertEqual(r.returncode, 1)
        self.assertIn("docs/m.md:1", r.stdout)

    def test_board_drift_rc1(self):
        (self.root / "management" / "BOARD.md").write_text("sửa tay\n", encoding="utf-8")
        self.assertEqual(self.check().returncode, 1)

    def test_stale_proposal_is_warning_only(self):
        self.write("management/decision-requests/DR-001-x.md", "---\nid: DR-001\nstatus: decided\n---\n")
        self.write("docs/m.md", "> Trạng thái: đề xuất (DR-001)\n")
        r = self.check()
        self.assertIn("Cảnh báo", r.stdout)
        self.assertIn("DR-001", r.stdout)


if __name__ == "__main__":
    unittest.main()


class ManualActions(Repo):
    """Inbox "Việc bạn cần làm" items: warn when their tasks are all done, unknown, or missing."""

    def task(self, tid: str, status: str):
        self.write(f"management/tasks/E01-x/{tid}-slug/task.md", f"---\nid: {tid}\nstatus: {status}\n---\n# {tid}\n")

    def inbox(self, body: str) -> list[str]:
        self.write("management/DECISIONS-INBOX.md", f"# Inbox\n\n## 🧰 Việc\n<!-- manual:start -->\n{body}\n<!-- manual:end -->\n")
        return cd.check_manual_actions(self.root)

    def test_item_of_done_task_warns_with_line(self):
        self.task("E01-T01", "done")
        msgs = self.inbox("- **E01-T01:** nạp credit\n  - dòng con")
        self.assertEqual(len(msgs), 1)
        self.assertIn("DECISIONS-INBOX.md:5:", msgs[0])
        self.assertIn("đã done (E01-T01)", msgs[0])

    def test_item_with_one_open_task_is_fine_and_subtask_ids_map_to_task(self):
        self.task("E01-T01", "done")
        self.task("E01-T07", "ready")
        self.assertEqual(self.inbox("- E01-T01 xong, còn E01-T07-S02 chờ"), [])

    def test_unknown_task_and_missing_task_warn(self):
        msgs = self.inbox("- E09-T99 gì đó\n- việc không mã")
        self.assertEqual(len(msgs), 2)
        self.assertIn("không tồn tại: E09-T99", msgs[0])
        self.assertIn("không gắn mã task", msgs[1])

    def test_no_task_marker_and_placeholder_are_skipped(self):
        self.task("E01-T01", "done")
        self.assertEqual(self.inbox("- Sau E01-T01 (không task): đổi key"), [])
        self.assertEqual(self.inbox("- —"), [])

    def test_missing_inbox_or_markers_is_silent(self):
        self.assertEqual(cd.check_manual_actions(self.root), [])
        self.write("management/DECISIONS-INBOX.md", "# Inbox\n- E01-T01\n")
        self.assertEqual(cd.check_manual_actions(self.root), [])


S12 = "one two three four five six seven eight nine ten eleven twelve"
S11 = "one two three four five six seven eight nine ten eleven"


class DuplicateSentences(Repo):
    """D-142 P2 as changed by D-154: a passage of >= 12 words (sliding window) in >= 2 files of CLAUDE.md, .claude/skills/, docs/07-security/."""

    def setUp(self):
        super().setUp()
        self.write(".agent-ops.toml", '[check_docs]\ndup_scope = ["CLAUDE.md", ".claude/skills", "docs/07-security"]\n')

    def dups(self, allowlist: list[dict] | None = None) -> list[str]:
        return cd.check_duplicate_sentences(self.root, allowlist if allowlist is not None else [])

    def entry(self, files: tuple[str, str], start: str) -> dict:
        return {"files": files, "start": start, "kind": cd.KIND_DEBT}

    def test_12_words_in_two_files_is_error(self):
        self.write("CLAUDE.md", f"{S12}.\n")
        self.write("docs/07-security/a.md", f"{S12}.\n")
        self.assertEqual(len(self.dups()), 1)
        errors, _ = cd.run(self.root)
        self.assertTrue(any("trùng ở" in e for e in errors))

    def test_11_words_not_reported(self):
        self.write("CLAUDE.md", f"{S11}.\n")
        self.write(".claude/skills/x/SKILL.md", f"{S11}.\n")
        self.assertEqual(self.dups(), [])

    def test_same_passage_twice_in_one_file_not_reported(self):
        self.write("CLAUDE.md", f"{S12}.\n\n{S12}.\n")
        self.assertEqual(self.dups(), [])

    def test_file_outside_scope_not_reported(self):
        self.write("CLAUDE.md", f"{S12}.\n")
        self.write("docs/a/other.md", f"{S12}.\n")
        self.assertEqual(self.dups(), [])

    def test_different_sentence_cuts_report_one_error_ll014(self):
        words = "alpha bravo charlie delta echo foxtrot golf hotel india juliet kilo lima mike november".split()
        self.write("CLAUDE.md", " ".join(words[:6]) + ". " + " ".join(words[6:]) + ".\n")
        self.write("docs/07-security/a.md", " ".join(words[:3]) + "; " + " ".join(words[3:10]) + ", " + " ".join(words[10:]) + "\n")
        errors = self.dups()
        self.assertEqual(len(errors), 1)  # 3 adjacent windows merge into one passage
        self.assertIn("14 từ", errors[0])

    def test_arrow_and_comma_between_words_ignored(self):
        self.write("CLAUDE.md", "a1 → b2 → c3 → d4 → e5 → f6 → g7 → h8 → i9 → j10 → k11 → l12\n")
        self.write("docs/07-security/a.md", "a1, b2, c3 d4 e5, f6 g7 h8 → i9 j10 k11 l12\n")
        self.assertEqual(len(self.dups()), 1)

    def test_allowlist_entry_suppresses_by_pair_and_start(self):
        self.write("CLAUDE.md", f"{S12}.\n")
        self.write("docs/07-security/a.md", f"{S12}.\n")
        entry = self.entry(("docs/07-security/a.md", "CLAUDE.md"), S12.capitalize() + ".")  # order and case do not matter
        self.assertEqual(self.dups([entry]), [])

    def test_allowlist_entry_for_other_pair_does_not_suppress(self):
        self.write("CLAUDE.md", f"{S12}.\n")
        self.write("docs/07-security/a.md", f"{S12}.\n")
        self.write("docs/07-security/b.md", f"{S12}.\n")
        errors = self.dups([self.entry(("CLAUDE.md", "docs/07-security/a.md"), S12)])
        self.assertEqual(len(errors), 2)  # CLAUDE.md vs b.md and a.md vs b.md

    def test_editing_first_word_breaks_key_and_is_reported(self):
        self.write("CLAUDE.md", f"{S12} thirteen fourteen.\n")
        self.write("docs/07-security/a.md", f"{S12} thirteen fourteen.\n")
        entry = self.entry(("CLAUDE.md", "docs/07-security/a.md"), S12)
        self.assertEqual(self.dups([entry]), [])
        self.write("docs/07-security/a.md", f"{S12.replace('one', 'uno', 1)} thirteen fourteen.\n")  # first word changed
        errors = self.dups([entry])
        self.assertEqual(len(errors), 2)  # new passage starts later; old key matches nothing
        self.assertTrue(any("không còn khớp" in e for e in errors))

    def test_stale_entry_is_error_after_cleanup(self):
        self.write("CLAUDE.md", f"{S12}.\n")
        self.write("docs/07-security/a.md", "Cleaned: see the link.\n")
        errors = self.dups([self.entry(("CLAUDE.md", "docs/07-security/a.md"), S12)])
        self.assertEqual(len(errors), 1)
        self.assertIn("không còn khớp", errors[0])

    # Counter-example kinds of D-142 P4 (multi-sample, bold/italic, empty, wrong value, date threshold).
    def test_many_sentences_per_line_and_many_lines(self):
        other = S12.replace("one", "uno")
        self.write("CLAUDE.md", f"Short one. {S12}. {other}.\n- {S11} x.\n")
        self.write(".claude/skills/x/SKILL.md", f"Intro text.\n{other}. Tail.\n\n{S12}!\n")
        self.assertGreaterEqual(len(self.dups()), 2)

    def test_bold_italic_bullet_and_case_ignored(self):
        self.write("CLAUDE.md", f"- **{S12}**.\n")
        self.write("docs/07-security/a.md", f"> _{S12.upper()}_.\n")
        self.assertEqual(len(self.dups()), 1)

    def test_empty_files_and_empty_cells(self):
        self.write("CLAUDE.md", "")
        self.write("docs/07-security/a.md", f"| | | {S12} |\n|---|---|---|\n")
        self.write("docs/07-security/b.md", f"|  | {S12} | |\n")
        self.assertEqual(len(self.dups()), 1)

    def test_missing_scope_dirs_do_not_crash(self):
        self.assertEqual(self.dups(), [])

    def test_wrong_value_one_word_changed_in_middle_not_reported(self):
        self.write("CLAUDE.md", f"{S12}.\n")
        self.write("docs/07-security/a.md", f"{S12.replace('six', '6')}.\n")
        self.assertEqual(self.dups(), [])

    def test_code_fence_and_comment_ignored(self):
        self.write("CLAUDE.md", f"```\n{S12}.\n```\n<!-- {S12}. -->\n")
        self.write("docs/07-security/a.md", f"{S12}.\n")
        self.assertEqual(self.dups(), [])
