"""Tests for build_inbox.check_reference_rules (D-101, DR-014 P2/P4). Run: python3 -I -m unittest discover management/tools/tests"""
import re
import sys
import unittest
from unittest import mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import build_inbox as bi  # noqa: E402

OK5 = "- [đã duyệt] D-101: x\n- [ngoài, đọc 2026-11-08] [Doc](https://example.com/a)\n"


def dr(sec3="", sec4="", sec5=OK5, sec6="", affects="[E01-T14]", related="[D-101, ADR-0002]", created="2026-11-08"):
    text = (f"---\nid: DR-X\ncreated: {created}\n---\n# T\n\n## 3. Phương án\n{sec3}\n## 4. Đề xuất\n{sec4}\n"
            f"## 5. Bằng chứng\n{sec5}\n## 6. Ảnh hưởng\n{sec6}\n## 7. Phản biện\nE09-T09 D-999\n")
    return {"_text": text, "created": created, "affects": [affects.strip("[]")], "related": related.strip("[]").split(", ")}


class P2(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(bi.check_reference_rules(dr(sec4="Theo D-101 và ADR-0002, task E01-T14.")), [])

    def test_missing_code_reported_with_line_and_code(self):
        d = dr(sec4="dòng một\nxem D-555 ở đây\n")
        msgs = bi.check_reference_rules(d)
        self.assertEqual(len(msgs), 1)
        line = d["_text"].split("\n").index("xem D-555 ở đây") + 1
        self.assertIn(f"dòng {line}", msgs[0])
        self.assertIn("D-555", msgs[0])

    def test_fixed_after_adding_to_related(self):
        d = dr(sec4="D-555")
        self.assertEqual(len(bi.check_reference_rules(d)), 1)
        d["related"].append("D-555")
        self.assertEqual(bi.check_reference_rules(d), [])

    def test_section_7_and_later_not_scanned(self):
        self.assertEqual(bi.check_reference_rules(dr()), [])  # fixture has E09-T09, D-999 in section 7

    def test_code_in_link_target_ignored_but_link_text_counts(self):
        self.assertEqual(bi.check_reference_rules(dr(sec4="[tài liệu](../adr/ADR-0009-x.md)")), [])
        self.assertEqual(len(bi.check_reference_rules(dr(sec4="[ADR-0009](../adr/x.md)"))), 1)

    def test_code_in_bare_filename_not_a_code(self):
        self.assertEqual(bi.check_reference_rules(dr(sec4="file ADR-0009-slug.md và E02-T05-S01-x.md")), [])

    def test_considered_section_counts(self):
        self.assertEqual(len(bi.check_reference_rules(dr(sec3="Đã cân nhắc: D-777"))), 1)

    def test_html_comment_ignored(self):
        self.assertEqual(bi.check_reference_rules(dr(sec4="<!-- D-888 -->")), [])

    def test_dr_code_not_p2(self):
        self.assertEqual(bi.check_reference_rules(dr(sec4="xem DR-014")), [])

    def test_subtask_needs_its_own_code_task_and_epic_too(self):
        self.assertEqual(len(bi.check_reference_rules(dr(sec4="E01-T14-S01"))), 1)  # parent task does not cover subtask
        self.assertEqual(bi.check_reference_rules(dr(sec4="E01-T14-S01", affects="E01-T14-S01")), [])
        self.assertEqual(len(bi.check_reference_rules(dr(sec4="E01"))), 1)  # task does not cover epic
        self.assertEqual(len(bi.check_reference_rules(dr(sec4="E01-T14", affects="E01-T14-S01"))), 1)

    def test_suffix_only_lowercase_slug_excluded(self):
        for text in ("D-555-P2", "E01-T15-S01-S03", "E09-T09-đề"):
            self.assertGreaterEqual(len(bi.check_reference_rules(dr(sec4=text))), 1, text)
        self.assertEqual(bi.REF_CODE_RE.findall("D-092-D-104"), ["D-092", "D-104"])
        self.assertEqual(bi.REF_CODE_RE.findall("E01-T15-S01-S03"), ["E01-T15-S01"])
        self.assertEqual(bi.REF_CODE_RE.findall("D-555-P2"), ["D-555"])
        self.assertEqual(bi.REF_CODE_RE.findall("ADR-0002-slug.md"), [])
        d = dr(sec4="D-101-D-104")
        msgs = bi.check_reference_rules(d)
        self.assertEqual(len(msgs), 1)
        self.assertIn("D-104", msgs[0])
        self.assertEqual(bi.check_reference_rules(dr(sec4="ADR-0009-slug.md")), [])

    def test_fenced_code_block_ignored_inline_code_counts(self):
        self.assertEqual(bi.check_reference_rules(dr(sec4="```\nD-555\n```\n")), [])
        self.assertEqual(len(bi.check_reference_rules(dr(sec4="xem `D-555`"))), 1)

    def test_line_numbers_kept_after_code_block(self):
        d = dr(sec4="```\na\nb\n```\nD-555\n")
        msgs = bi.check_reference_rules(d)
        self.assertIn(f"dòng {d['_text'].split(chr(10)).index('D-555') + 1}", msgs[0])

    def test_section_7_marker_inside_code_block_does_not_cut(self):
        d = dr(sec6="```\n## 7. x\n```\nD-555\n")
        self.assertEqual(len(bi.check_reference_rules(d)), 1)

    def test_missing_markers_reported(self):
        d = dr()
        d["_text"] = d["_text"].replace("## 3. Phương án", "## x")
        self.assertTrue(any("## 3." in m for m in bi.check_reference_rules(d)))
        d = dr()
        d["_text"] = d["_text"].replace("## 7. Phản biện", "## x")
        self.assertTrue(any("## 7." in m for m in bi.check_reference_rules(d)))

    def test_withdrawn_skipped_draft_checked(self):
        d = dr(sec4="D-555", sec5="https://a.b")
        d["status"] = "withdrawn"
        self.assertEqual(bi.check_reference_rules(d), [])
        for st in ("draft", "in_review"):
            d = dr(sec4="D-555")
            d["status"] = st
            self.assertEqual(len(bi.check_reference_rules(d)), 1, st)

    def test_codes_in_affects_free_text(self):
        self.assertEqual(bi.check_reference_rules(dr(sec4="E02", affects="Epic E02 (backend)")), [])


class P4(unittest.TestCase):
    def test_missing_label(self):
        d = dr(sec5="- ref\n- [Doc](https://example.com/a)\n")
        msgs = bi.check_reference_rules(d)
        self.assertEqual(len(msgs), 1)
        self.assertIn("P4", msgs[0])
        line = d["_text"].split("\n").index("- [Doc](https://example.com/a)") + 1
        self.assertIn(f"dòng {line}", msgs[0])

    def test_label_on_other_line_not_enough(self):
        self.assertEqual(len(bi.check_reference_rules(dr(sec5="[ngoài, đọc 2026-11-08]\nhttp://a.b/c\n"))), 1)

    def test_label_nfd_form_accepted(self):
        import unicodedata
        line = unicodedata.normalize("NFD", "[ngoài, đọc 2026-11-08] https://a.b/c")
        self.assertEqual(bi.check_reference_rules(dr(sec5=line)), [])

    def test_bad_date_and_bad_format(self):
        self.assertEqual(len(bi.check_reference_rules(dr(sec5="[ngoài, đọc 2026-13-45] https://a.b"))), 1)
        self.assertEqual(len(bi.check_reference_rules(dr(sec5="[ngoài, đọc 8/11] https://a.b"))), 1)

    def test_each_url_needs_its_own_label_before_it(self):
        two = "[ngoài, đọc 2026-11-08] [a](https://a.b) và [b](https://c.d)"
        msgs = bi.check_reference_rules(dr(sec5=two))
        self.assertEqual(len(msgs), 1)
        self.assertIn("https://c.d", msgs[0])
        ok = "[ngoài, đọc 2026-11-08] [a](https://a.b) và [ngoài, đọc 2026-11-09] [b](https://c.d)"
        self.assertEqual(bi.check_reference_rules(dr(sec5=ok)), [])

    def test_label_after_url_not_enough(self):
        self.assertEqual(len(bi.check_reference_rules(dr(sec5="https://a.b [ngoài, đọc 2026-11-08]"))), 1)

    def test_url_in_code_ignored(self):
        self.assertEqual(bi.check_reference_rules(dr(sec5="```\nhttps://a.b\n```\n")), [])
        self.assertEqual(bi.check_reference_rules(dr(sec5="lệnh `curl https://a.b`")), [])

    def test_url_outside_section_5_ignored(self):
        self.assertEqual(bi.check_reference_rules(dr(sec4="https://a.b/c")), [])


class Cutoff(unittest.TestCase):
    def test_old_and_boundary_dates_skipped(self):
        for created in ("2026-11-05", "2026-11-04"):
            d = dr(sec4="D-555", sec5="https://a.b", created=created)
            self.assertEqual(bi.check_reference_rules(d), [])

    def test_day_after_applies(self):
        d = dr(sec4="D-555", sec5="https://a.b", created="2026-11-06")
        self.assertEqual(len(bi.check_reference_rules(d)), 2)

    def test_parse_frontmatter_lists(self):
        import tempfile
        with tempfile.TemporaryDirectory() as t:
            f = Path(t) / "DR-X.md"
            f.write_text("---\nid: DR-X\ncreated: 2026-11-08\naffects: [E01-T14, E01-T14-S02]\nrelated: [D-101, ADR-0002]\n---\n"
                         "# T\n\n## 3. P\n## 4. Đ\nD-101 E01-T14-S02\n## 5. B\n## 6. A\n## 7. R\n", encoding="utf-8")
            self.assertEqual(bi.check_reference_rules(bi.parse(f)), [])


TEMPLATE_LINE = '- Ý kiến product-analyst (bắt buộc khi `topic: learning`; ghi "không áp dụng" nếu topic khác): <tóm tắt ý kiến, ngày, link>'


def learning(sec5, topic="learning", created="2026-11-08"):
    d = dr(sec5=sec5, created=created)
    d["topic"] = topic
    return d


class P6(unittest.TestCase):
    def test_missing_line_reported(self):
        msgs = bi.check_pa_opinion(learning("- Tài liệu: x\n"))
        self.assertEqual(len(msgs), 1)
        self.assertIn("P6", msgs[0])

    def test_template_line_untouched_reported_with_line(self):
        d = learning("- Tài liệu: x\n" + TEMPLATE_LINE + "\n")
        msgs = bi.check_pa_opinion(d)
        line = d["_text"].split("\n").index(TEMPLATE_LINE) + 1
        self.assertEqual(len(msgs), 1)
        self.assertIn(f"dòng {line}", msgs[0])

    def test_guidance_kept_without_content_reported(self):
        guide = TEMPLATE_LINE.split("):")[0] + "):"
        self.assertEqual(len(bi.check_pa_opinion(learning(guide))), 1)
        self.assertEqual(len(bi.check_pa_opinion(learning("- Ý kiến product-analyst:"))), 1)
        self.assertEqual(len(bi.check_pa_opinion(learning("- Ý kiến product-analyst: -"))), 1)

    def test_not_applicable_reported(self):
        self.assertEqual(len(bi.check_pa_opinion(learning("- Ý kiến product-analyst: không áp dụng"))), 1)

    def test_filled_passes_with_or_without_guidance(self):
        ok = "2026-11-08, đồng ý, [prd](../x.md)"
        self.assertEqual(bi.check_pa_opinion(learning("- Ý kiến product-analyst: " + ok)), [])
        kept = TEMPLATE_LINE.split("<")[0] + ok
        self.assertEqual(bi.check_pa_opinion(learning(kept)), [])

    def test_bold_dr002_form_accepted(self):
        for line in ("- **Ý kiến product-analyst (2026-11-08):** đồng ý A",
                     "- **Ý kiến product-analyst (2026-11-08, đồng ý A):**",
                     "* Ý kiến product-analyst: đồng ý",
                     "  - _Ý kiến product-analyst_: đồng ý"):
            self.assertEqual(bi.check_pa_opinion(learning(line)), [], line)

    def test_value_with_angle_chars_accepted(self):
        for v in ("<https://a.b>", "đồng ý<br>tiếp", "mức < B1 và > A2"):
            self.assertEqual(bi.check_pa_opinion(learning("- Ý kiến product-analyst: " + v)), [], v)

    def test_content_on_following_lines_belongs_to_bullet(self):
        self.assertEqual(bi.check_pa_opinion(learning("- **Ý kiến product-analyst:**\n  đồng ý A\n")), [])
        self.assertEqual(bi.check_pa_opinion(learning("- Ý kiến product-analyst:\n  - đồng ý A\n")), [])
        self.assertEqual(len(bi.check_pa_opinion(learning("- Ý kiến product-analyst:\n- Tài liệu: có chữ\n"))), 1)

    def test_paragraph_after_blank_line_does_not_belong_to_bullet(self):
        for opinion in (TEMPLATE_LINE, "- Ý kiến product-analyst:"):
            self.assertEqual(len(bi.check_pa_opinion(learning(opinion + "\n\n**Ghi chú:** x\n"))), 1, opinion)
            self.assertEqual(len(bi.check_pa_opinion(learning("- Tài liệu: x\n" + opinion + "\n\nĐoạn văn.\n"))), 1, opinion)
        self.assertEqual(bi.check_pa_opinion(learning("- Ý kiến product-analyst:\n\n  đồng ý A\n\n**Ghi chú:** x\n")), [])

    def test_parenthesized_not_applicable_reported(self):
        for v in ("(không áp dụng)", "(Không áp dụng).", "( không áp dụng )"):
            self.assertEqual(len(bi.check_pa_opinion(learning("- Ý kiến product-analyst: " + v))), 1, v)

    def test_only_punctuation_in_parens_is_empty(self):
        self.assertEqual(len(bi.check_pa_opinion(learning("- **Ý kiến product-analyst ():** "))), 1)

    def test_line_in_code_block_not_counted(self):
        self.assertEqual(len(bi.check_pa_opinion(learning("```\n- Ý kiến product-analyst: ok\n```\n"))), 1)

    def test_other_topic_old_dr_and_withdrawn_skipped(self):
        self.assertEqual(bi.check_pa_opinion(learning("- x", topic="ops")), [])
        self.assertEqual(bi.check_pa_opinion(learning("- x", created="2026-11-05")), [])
        d = learning("- x")
        d["status"] = "withdrawn"
        self.assertEqual(bi.check_pa_opinion(d), [])
        d = learning(TEMPLATE_LINE)
        d["status"] = "draft"
        self.assertEqual(len(bi.check_pa_opinion(d)), 1)

    def test_line_outside_section_5_not_counted(self):
        d = learning("- x\n")
        d["_text"] = d["_text"].replace("## 6. Ảnh hưởng\n", "## 6. Ảnh hưởng\n- Ý kiến product-analyst: ok\n")
        self.assertEqual(len(bi.check_pa_opinion(d)), 1)


class ThreeMinorsRound3(unittest.TestCase):
    """E01-T18-S03 (AC6): the 3 Minor of the E01-T14 round-3 review."""

    def test_p6_lazy_continuation_after_placeholder_is_not_content(self):
        lazy = TEMPLATE_LINE + "\nđây là dòng chữ liền ngay sau, không thụt lề\n"
        self.assertEqual(len(bi.check_pa_opinion(learning(lazy))), 1)
        self.assertEqual(len(bi.check_pa_opinion(learning("- Ý kiến product-analyst:\nchữ liền sau\n"))), 1)

    def test_p6_indented_continuation_still_counts(self):
        self.assertEqual(bi.check_pa_opinion(learning(TEMPLATE_LINE + "\n  đồng ý A, 2026-11-08\n")), [])

    def test_p6_dated_not_applicable_reported(self):
        for line in ("- Ý kiến product-analyst (2026-11-08): (không áp dụng)",
                     "- **Ý kiến product-analyst (2026-11-08):** (không áp dụng)",
                     "- Ý kiến product-analyst: 2026-11-08 không áp dụng"):
            self.assertEqual(len(bi.check_pa_opinion(learning(line))), 1, line)

    def test_p6_dated_real_opinion_still_accepted(self):
        self.assertEqual(bi.check_pa_opinion(learning("- **Ý kiến product-analyst (2026-11-08, đồng ý A):**")), [])

    def test_code_inside_date_prefix_is_not_a_code(self):
        self.assertEqual(bi.check_reference_rules(dr(sec4="file 2026-11-07-D-101 và 2026-11-07-E01-T14")), [])
        self.assertEqual(bi.REF_CODE_RE.findall("2026-11-07-D-101"), [])

    def test_adjacent_codes_after_digit_dash_still_match(self):
        self.assertEqual(bi.REF_CODE_RE.findall("D-092-D-104"), ["D-092", "D-104"])


class ExemptSection7(unittest.TestCase):
    """E01-T18-S04 (AC5, D-112): only DR-014 is exempt from the missing section-7 conclusion."""
    MSG = "chưa có kết luận phản biện (mục 7)"

    def meta(self, dr_id, status="decided", review=""):
        text = "---\n---\n# T\n\n## 2. a\n## 3. b\n## 4. c\n**Chọn: A**\n## 5. d\n## 6. e\n## 7. Phản biện\n## 8. f\n"
        return {"_text": text, "_path": Path("DR-X.md"), "_choice": "A", "_review": review, "id": dr_id,
                "status": status, "type": "2", "decided_as": "D-1", "created": "2026-01-01"}

    def setUp(self):
        patcher = mock.patch.object(bi, "NO_REVIEW_CONCLUSION_EXEMPT_IDS", frozenset({"DR-014"}))  # as set in `.agent-ops.toml`
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_dr014_not_reported(self):
        self.assertNotIn(self.MSG, bi.validate(self.meta("DR-014")))

    def test_other_dr_still_reported_in_every_status(self):
        for status in ("open", "provisional", "decided"):
            self.assertIn(self.MSG, bi.validate(self.meta("DR-015", status)), status)
        self.assertIn(self.MSG, bi.validate(self.meta("DR-015", review="⏳ chờ")))
        self.assertIn(self.MSG, bi.validate(self.meta(None)))

    def test_dr014_other_errors_still_reported(self):
        m = self.meta("DR-014")
        m["decided_as"] = ""
        self.assertIn("thiếu decided_as (D-xxx)", bi.validate(m))



class FromTemplateAndMain(unittest.TestCase):
    TEMPLATE = Path(__file__).resolve().parents[2] / "templates" / "decision-request.md"

    def template_dr(self, topic):
        import tempfile
        text = self.TEMPLATE.read_text(encoding="utf-8")
        text = re.sub(r"(?m)^topic:.*$", f"topic: {topic}", text, count=1)
        text = re.sub(r"(?m)^created:.*$", "created: 2026-11-08", text, count=1)
        text = re.sub(r"(?m)^status:.*$", "status: in_review", text, count=1)
        f = Path(tempfile.mkdtemp()) / "DR-X.md"
        f.write_text(text, encoding="utf-8")
        return bi.parse(f)

    def test_template_guidance_line_is_exact_template_text(self):
        self.assertIn(bi.PA_GUIDANCE, self.TEMPLATE.read_text(encoding="utf-8"))

    def test_template_learning_reports_p6_and_ops_does_not(self):
        self.assertEqual(len(bi.check_pa_opinion(self.template_dr("learning"))), 1)
        self.assertEqual(bi.check_pa_opinion(self.template_dr("ops")), [])

    def test_template_learning_with_paragraph_after_bullet_still_reported(self):
        d = self.template_dr("learning")
        d["_text"] = d["_text"].replace("\n## 6.", "\n**Ghi chú:** x\n\n## 6.", 1)
        self.assertEqual(len(bi.check_pa_opinion(d)), 1)
        d["_text"] = self.template_dr("learning")["_text"].replace("<tóm tắt ý kiến, ngày, link>\n\n", "<tóm tắt ý kiến, ngày, link>\n\n**Ghi chú:** x\n\n", 1)
        self.assertEqual(len(bi.check_pa_opinion(d)), 1)

    def test_template_has_no_p4_issue(self):
        self.assertFalse([m for m in bi.check_reference_rules(self.template_dr("ops")) if m.startswith("P4")])

    def test_main_check_runs_new_rules(self):
        import contextlib
        import io
        import tempfile
        d = Path(tempfile.mkdtemp())
        text = ("---\nid: DR-X\ntitle: t\nstatus: in_review\ncreated: 2026-11-08\ntopic: learning\naffects: [E01-T14]\n"
                "related: [D-101]\n---\n# T\n\n## 3. P\n## 4. Đ\nD-555\n## 5. B\nhttps://a.b\n## 6. A\n## 7. R\n")
        (d / "DR-X.md").write_text(text, encoding="utf-8")
        old_dir, old_argv = bi.DR_DIR, sys.argv
        out = io.StringIO()
        try:
            bi.DR_DIR, sys.argv = d, ["build_inbox.py", "--check"]
            with contextlib.redirect_stdout(out):
                rc = bi.main()
        finally:
            bi.DR_DIR, sys.argv = old_dir, old_argv
        self.assertEqual(rc, 1)
        for rule in ("P2:", "P4:", "P6:"):
            self.assertIn(rule, out.getvalue())


if __name__ == "__main__":
    unittest.main()
