import html.parser
import io
import json
import os
import re
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "kit", ".claude", "skills", "tl-requirements", "scripts"))
import spec_tool  # noqa: E402

SAMPLE = os.path.join(ROOT, "tests", "fixtures", "spec_sample.md")


def sample():
    with open(SAMPLE, encoding="utf-8") as f:
        return f.read()


def messages(text):
    findings, summary = spec_tool.lint(text)
    return [f["level"] + " " + f["message"] for f in findings], summary


class TagBalance(html.parser.HTMLParser):
    VOID = {"meta", "br", "img", "hr", "input", "link", "rect", "path", "line", "circle", "polygon"}

    def __init__(self):
        super().__init__()
        self.stack, self.errors, self.ids = [], [], []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            self.ids.append(attrs["id"])
        if tag not in self.VOID:
            self.stack.append(tag)

    def handle_startendtag(self, tag, attrs):
        if "id" in dict(attrs):
            self.ids.append(dict(attrs)["id"])

    def handle_endtag(self, tag):
        if tag in self.VOID:
            return
        if not self.stack or self.stack[-1] != tag:
            self.errors.append(f"unexpected </{tag}>, open: {self.stack[-3:]}")
            return
        self.stack.pop()


class LintTests(unittest.TestCase):
    def test_sample_is_clean(self):
        msgs, summary = messages(sample())
        self.assertEqual(msgs, [])
        self.assertEqual((summary["req"], summary["ac"], summary["dt"], summary["questions"]), (2, 3, 1, 1))

    def test_missing_meta_is_error(self):
        msgs, _ = messages(sample().split("\n", 1)[1])
        self.assertTrue(any("tl-meta" in m and m.startswith("ERROR") for m in msgs))

    def test_req_without_ac(self):
        text = sample().replace("| AC-003 | REQ-002 |", "| AC-003 | REQ-001 |")
        msgs, _ = messages(text)
        self.assertIn("ERROR REQ-002 has no acceptance criterion (no AC row names it)", msgs)
        self.assertTrue(any("REQ-002 lists AC-003" in m for m in msgs))

    def test_ac_with_unknown_req(self):
        msgs, _ = messages(sample().replace("| AC-002 | REQ-001 |", "| AC-002 | REQ-009 |"))
        self.assertIn("ERROR AC-002 refers to REQ-009, which is not defined", msgs)

    def test_duplicate_id(self):
        msgs, _ = messages(sample().replace("| REQ-002 | עצירות", "| REQ-001 | עצירות"))
        self.assertTrue(any("REQ-001 is defined twice" in m for m in msgs))

    def test_decision_table_needs_else_row(self):
        msgs, _ = messages(sample().replace("| 3 | אחרת |", "| 3 | `channel = 'ATM'` |"))
        self.assertIn("ERROR DT-1 has no 'אחרת' (else) row", msgs)

    def test_traceability_rows_are_references_not_definitions(self):
        msgs, _ = messages(sample())
        self.assertFalse(any("defined twice" in m for m in msgs))

    def test_question_without_answer(self):
        text = sample().replace("| כן — ב-3 יש גל הונאה באוגוסט |", "|  |")
        msgs, _ = messages(text)
        self.assertIn("WARN Q-1 has no proposed answer", msgs)

    def test_vague_words_and_placeholders(self):
        text = sample().replace("## 1. תקציר\n", "## 1. תקציר\nהמערכת תגיב מהר ובאופן סביר וכו'. <שם>\n")
        msgs, _ = messages(text)
        self.assertTrue(any("'סביר'" in m for m in msgs))
        self.assertTrue(any("'וכו''" in m for m in msgs))
        self.assertTrue(any("placeholder left: <שם>" in m for m in msgs))

    def test_comparison_in_code_is_not_a_placeholder(self):
        text = sample().replace("## 1. תקציר\n", "## 1. תקציר\nתנאי `a <= 5 and b > 3` ותנאי `x <> 'A'`\n")
        msgs, _ = messages(text)
        self.assertFalse(any("placeholder" in m for m in msgs))

    def test_approved_with_pending_assumptions(self):
        text = sample().replace("status=review", "status=approved").replace(
            "[הנחה] | AC-003", "[הנחה — ממתין לאישור] | AC-003")
        msgs, _ = messages(text)
        self.assertTrue(any("still wait for approval" in m for m in msgs))

    def test_cli_exit_codes_and_json(self):
        tmp = tempfile.mkdtemp()
        bad = os.path.join(tmp, "bad.md")
        with open(bad, "w", encoding="utf-8") as f:
            f.write(sample().replace("| AC-002 | REQ-001 |", "| AC-002 | REQ-009 |"))
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(spec_tool.main(["lint", SAMPLE]), 0)
            self.assertEqual(spec_tool.main(["lint", bad, "--json"]), 1)
        data = json.loads(out.getvalue().split("\n", 1)[1])
        self.assertGreater(data["summary"]["errors"], 0)
        shutil.rmtree(tmp)


class RenderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = spec_tool.render(sample(), "SPEC.md")

    def test_tags_balanced_and_ids_unique(self):
        parser = TagBalance()
        parser.feed(self.html)
        self.assertEqual(parser.errors, [])
        self.assertEqual(parser.stack, [])
        self.assertEqual(len(parser.ids), len(set(parser.ids)), "duplicate ids")

    def test_rtl_and_self_contained(self):
        self.assertIn('<html lang="he" dir="rtl">', self.html)
        self.assertNotRegex(self.html, r'(src|href)="https?://')
        self.assertNotIn("<script", self.html)

    def test_ids_defined_once_and_linked(self):
        self.assertEqual(self.html.count('id="REQ-001"'), 1)
        self.assertEqual(self.html.count('id="AC-001"'), 1)
        self.assertIn('href="#REQ-001"', self.html)
        self.assertIn('id="DT-1"', self.html)

    def test_decision_table_rows_marked(self):
        self.assertIn('class="dt', self.html)
        self.assertIn('<tr class="else">', self.html)
        self.assertIn('<tr class="new">', self.html)

    def test_tags_header_and_toc(self):
        self.assertIn('<span class="src">מקור: קוד rules.py:14</span>', self.html)
        self.assertIn('<span class="assume">הנחה</span>', self.html)
        self.assertIn("לבדיקה", self.html)
        self.assertIn('<nav class="toc"', self.html)
        self.assertIn("<code>accounts.status &lt;&gt; &#x27;ACTIVE&#x27;</code>".replace("&#x27;", "'"), self.html)
        self.assertIn("<svg", self.html)
        self.assertNotIn("tl-meta", self.html)

    def test_escaping(self):
        out = spec_tool.render("# t\n\nטקסט <script>alert(1)</script> **מודגש**\n", "x.md")
        self.assertIn("&lt;script&gt;", out)
        self.assertIn("<strong>מודגש</strong>", out)

    def test_lists_nested_and_checkboxes(self):
        out = spec_tool.render("# t\n\n- א\n  - ב\n- [ ] ג\n- [x] ד\n\n1. one\n2. two\n", "x.md")
        self.assertRegex(out, r"<ul><li>א<ul><li>ב</li></ul></li>")
        self.assertIn("☐", out)
        self.assertIn("☑", out)
        self.assertIn("<ol><li>one</li><li>two</li></ol>", out)

    def test_russian_is_ltr(self):
        out = spec_tool.render("<!-- tl-meta: type=spec; status=draft; lang=ru -->\n# Тест\n", "x.md")
        self.assertIn('<html lang="ru" dir="ltr">', out)
        self.assertIn("черновик", out)


class NewTests(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.root)

    def run_new(self, *args):
        out = io.StringIO()
        with redirect_stdout(out):
            code = spec_tool.main(["new", *args, "--root", self.root])
        return code, out.getvalue().strip()

    def test_creates_numbered_request(self):
        code, path = self.run_new("recurring-payers", "--title", "מושכים קבועים")
        self.assertEqual(code, 0)
        self.assertTrue(path.endswith(os.path.join("SPEC-001-recurring-payers", "REQUEST.md")))
        with open(path, encoding="utf-8") as f:
            text = f.read()
        self.assertTrue(text.startswith("<!-- tl-meta: type=request; id=SPEC-001;"))
        self.assertIn("# טופס דרישה: מושכים קבועים", text)
        self.assertNotIn("YYYY-MM-DD", text)
        self.assertNotIn("template:", text)

    def test_numbering_counts_published_specs(self):
        os.makedirs(os.path.join(self.root, "docs", "specs"))
        open(os.path.join(self.root, "docs", "specs", "SPEC-004-x.md"), "w").close()
        self.run_new("a")
        _, path = self.run_new("b")
        self.assertIn("SPEC-006-b", path)

    def test_bad_slug(self):
        out = io.StringIO()
        with redirect_stdout(out), redirect_stdout(io.StringIO()):
            sys.stderr, old = io.StringIO(), sys.stderr
            try:
                self.assertEqual(spec_tool.main(["new", "אאא", "--root", self.root]), 2)
            finally:
                sys.stderr = old


class TemplatesFollowConventions(unittest.TestCase):
    def test_spec_template_block_lints_structurally(self):
        path = os.path.join(ROOT, "kit", ".claude", "skills", "tl-requirements", "references", "spec-template.md")
        with open(path, encoding="utf-8") as f:
            block = re.search(r"```markdown\n(.*)\n```", f.read(), re.S).group(1)
        findings, summary = spec_tool.lint(block)
        errors = [f["message"] for f in findings if f["level"] == "ERROR"]
        self.assertEqual(errors, [], "the template itself must satisfy the structural rules")
        self.assertEqual((summary["req"], summary["ac"], summary["dt"]), (1, 1, 1))


if __name__ == "__main__":
    unittest.main()
