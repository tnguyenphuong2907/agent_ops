"""Tests for build_inbox.check_frontmatter and topic normalization (E01-T18-S01, CR-18, CR-9)."""
import contextlib
import io
import sys
import tempfile
import types
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import build_inbox as bi  # noqa: E402

BODY = "# T\n\n## 3. P\n## 4. Đ\n## 5. B\n- Ý kiến product-analyst: 2026-11-08 đồng ý\n## 6. A\n## 7. R\n"


def write_dr(directory: Path, name: str, front: str) -> Path:
    path = directory / name
    path.write_text(f"---\n{front}\n---\n{BODY}", encoding="utf-8")
    return path


def front(**over: str) -> str:
    base = {"id": "DR-X", "title": "t", "status": "draft", "created": "2026-11-08", "topic": "learning"}
    base.update(over)
    return "\n".join(f"{k}: {v}" for k, v in base.items())


def parsed(**over: str) -> dict:
    with tempfile.TemporaryDirectory() as t:
        return bi.parse(write_dr(Path(t), "DR-X.md", front(**over)))


class Frontmatter(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(bi.check_frontmatter(parsed()), [])

    def test_created_list_reported_not_crash(self):
        msgs = bi.check_frontmatter(parsed(created="[x]"))
        self.assertEqual(len(msgs), 1)
        self.assertIn("created", msgs[0])

    def test_created_not_a_real_date(self):
        msgs = bi.check_frontmatter(parsed(created="2026-13-45"))
        self.assertEqual(len(msgs), 1)
        self.assertIn("created", msgs[0])

    def test_created_bad_format(self):
        self.assertEqual(len(bi.check_frontmatter(parsed(created="8/11/2026"))), 1)

    def test_status_list_and_unknown(self):
        for v in ("[draft]", "nope", ""):
            msgs = bi.check_frontmatter(parsed(status=v))
            self.assertEqual(len(msgs), 1, v)
            self.assertIn("status", msgs[0])

    def test_topic_bad_values(self):
        for v in ("[]", "nonsense", "[learning, nonsense]"):
            msgs = bi.check_frontmatter(parsed(topic=v))
            self.assertTrue(msgs and all("topic" in m for m in msgs), v)

    def test_topic_normalized(self):
        for v in ("Learning", "'learning'", '"Learning"', "[learning]", "[Learning, ops]", "[ 'learning' , \"ops\" ]"):
            d = parsed(topic=v)
            self.assertIn("learning", bi.topics_of(d), v)
            self.assertEqual(bi.check_frontmatter(d), [], v)


class P6UsesNormalizedTopic(unittest.TestCase):
    def test_all_spellings_are_checked_as_learning(self):
        empty = "- Ý kiến product-analyst: không áp dụng\n"
        for v in ("Learning", "'learning'", "[learning, ops]"):
            with tempfile.TemporaryDirectory() as t:
                d = bi.parse(write_dr(Path(t), "DR-X.md", front(topic=v)))
                d["_text"] = d["_text"].replace("- Ý kiến product-analyst: 2026-11-08 đồng ý\n", empty)
                self.assertEqual(len(bi.check_pa_opinion(d)), 1, v)

    def test_other_topic_still_skipped(self):
        d = parsed(topic="[ops, ux]")
        d["_text"] = d["_text"].replace("2026-11-08 đồng ý", "không áp dụng")
        self.assertEqual(bi.check_pa_opinion(d), [])


class MainDoesNotCrash(unittest.TestCase):
    def run_main(self, fronts: dict[str, str], check: bool) -> tuple[int, str, str]:
        """Returns (rc, stdout, inbox text or "")."""
        out = io.StringIO()
        with tempfile.TemporaryDirectory() as t:
            d = Path(t)
            for name, f in fronts.items():
                write_dr(d, name, f)
            old = (bi.DR_DIR, bi.INBOX, bi.ROOT, sys.argv)
            real_docs_checks = bi._docs_checks
            bi._docs_checks = lambda: types.SimpleNamespace(run=lambda root: ([], []))  # docs checks have own tests
            try:
                bi.DR_DIR, bi.INBOX, bi.ROOT = d, d / "INBOX.md", d
                sys.argv = ["build_inbox.py"] + (["--check"] if check else [])
                with contextlib.redirect_stdout(out):
                    rc = bi.main()
                inbox = bi.INBOX.read_text(encoding="utf-8") if bi.INBOX.exists() else ""
            finally:
                bi.DR_DIR, bi.INBOX, bi.ROOT, sys.argv = old
                bi._docs_checks = real_docs_checks
        return rc, out.getvalue(), inbox

    BAD = {
        "DR-A.md": front(id="DR-A", created="[x]"),
        "DR-B.md": front(id="DR-B", status="[draft]"),
        "DR-C.md": front(id="DR-C", created="2026-13-45"),
        "DR-D.md": front(id="DR-D", topic="[bad]"),
    }

    def test_check_one_line_per_error_no_traceback(self):
        rc, out, _ = self.run_main(self.BAD, check=True)
        self.assertEqual(rc, 1)
        for key, field in (("DR-A", "created"), ("DR-B", "status"), ("DR-C", "created"), ("DR-D", "topic")):
            lines = [x for x in out.splitlines() if x.startswith(key + ":")]
            self.assertEqual(len(lines), 1, out)
            self.assertIn(field, lines[0])

    def test_build_writes_inbox_without_crash(self):
        rc, out, inbox = self.run_main({**self.BAD, "DR-E.md": front(id="DR-E", status="open", topic="[Learning, ops]")}, False)
        self.assertEqual(rc, 0)
        self.assertIn("DR-E", inbox)
        for key in ("DR-A", "DR-B", "DR-C", "DR-D"):  # CR1: invalid tickets are never hidden
            self.assertIn(key, inbox)
            self.assertTrue(any(x.startswith("Cảnh báo") and f"{key}:" in x for x in out.splitlines()), out)

    def test_open_ticket_with_bad_date_stays_visible_and_flagged(self):
        _, _, inbox = self.run_main({"DR-A.md": front(id="DR-A", status="open", created="2026-13-45", topic="nonsense")}, False)
        self.assertIn("**Cần bạn quyết:** 1", inbox)
        self.assertIn("Phiếu lỗi frontmatter:** 1", inbox)
        self.assertLess(inbox.index("## ⚠️"), inbox.index("## 🔴"))
        self.assertIn("created", inbox)
        self.assertIn("### nonsense", inbox)

    def test_list_valued_fields_do_not_crash(self):
        bad = {"DR-A.md": front(id="[x]", status="open", type="[1]", deadline="[x]"),
               "DR-B.md": front(id="DR-B", status="open", deadline="[y]"),
               "DR-C.md": front(id="DR-C", status="open", deadline="2026-12-01")}
        rc, out, inbox = self.run_main(bad, True)
        self.assertEqual(rc, 1)
        self.assertIn("DR-A:", out)
        _, _, inbox = self.run_main(bad, False)
        self.assertIn("DR-A.md", inbox)
        self.assertIn("DR-B", inbox)
        self.assertIn("DR-C", inbox)

    def test_duplicate_id_reported_with_both_files(self):
        dup = {"DR-A.md": front(id="DR-X"), "DR-B.md": front(id="DR-X")}
        rc, out, _ = self.run_main(dup, True)
        self.assertEqual(rc, 1)
        line = next(x for x in out.splitlines() if x.startswith("DR-X:") and "trùng" in x)
        self.assertIn("DR-A.md", line)
        self.assertIn("DR-B.md", line)

    def test_missing_and_empty_id_reported_with_stem_label(self):
        no_id = front().replace("id: DR-X\n", "")
        for name, f in (("DR-M.md", no_id), ("DR-N.md", front(id=""))):
            rc, out, inbox = self.run_main({name: f}, True)
            stem = name[:-3]
            self.assertEqual(rc, 1, name)
            self.assertTrue(any(x.startswith(stem + ":") and "id" in x for x in out.splitlines()), out)
            self.assertNotIn(".md:", out)
            _, _, inbox = self.run_main({name: f}, False)
            self.assertIn(f"[{stem}](", inbox)
            self.assertNotIn(f"[{name}]", inbox)

    def test_empty_ids_are_not_duplicates(self):
        _, out, _ = self.run_main({"DR-M.md": front(id=""), "DR-N.md": front(id="")}, True)
        self.assertNotIn("trùng", out)

    def test_missing_topic_reported(self):
        d = parsed()
        del d["topic"]
        self.assertEqual(len(bi.check_frontmatter(d)), 1)

    def test_no_warning_section_when_all_valid(self):
        _, _, inbox = self.run_main({"DR-A.md": front(id="DR-A", status="open")}, False)
        self.assertNotIn("Phiếu lỗi frontmatter", inbox)

    def test_inner_quotes_kept(self):
        self.assertEqual(parsed(title="\"Có nên giữ màn 'Hôm nay'\"")["title"], "Có nên giữ màn 'Hôm nay'")
        self.assertEqual(parsed(title="'a'")["title"], "a")


if __name__ == "__main__":
    unittest.main()
