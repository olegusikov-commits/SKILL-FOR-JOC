import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "kit", ".claude", "tech-lead-kit", "scripts"))
import tl_knowledge  # noqa: E402

SPEC = ("<!-- tl-meta: type=spec; id=SPEC-001; status=approved; version=1.0; date=2026-10-17; "
        "area=src/rules.py, cheques; title=מושכים קבועים -->\n# SPEC-001: מושכים קבועים\n\nטקסט.\n")
ADR = ("<!-- tl-meta: type=adr; id=ADR-001; status=proposed; date=2026-10-10; area=antifraud, MQ; "
       "title=Outbox -->\n# ADR-001: Outbox\n")
CONTEXT = ("# PROJECT_CONTEXT\n\n<!-- tl-agents:begin -->\n- בדיקות: `python -m unittest`\n"
           "- מסדי נתונים: meet-chequemis (PROD לקריאה בלבד)\n<!-- tl-agents:end -->\n")


class KnowledgeTests(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.mem = os.path.join(self.root, ".claude", "tl-memory")
        self.write(".claude/tl-memory/spec/SPEC-001-recurring/SPEC.md", SPEC)
        self.write(".claude/tl-memory/spec/SPEC-001-recurring/SPEC.html", "<html>rendered</html>")
        self.write(".claude/tl-memory/spec/SPEC-001-recurring/REQUEST.md",
                   "<!-- tl-meta: type=request; id=SPEC-001; status=draft; date=2026-10-16; area=; title=x -->\n")
        self.write(".claude/tl-memory/spec/SPEC-001-recurring/queries/Q-1.sql", "SELECT 1")
        self.write(".claude/tl-memory/adr/ADR-001-outbox.md", ADR)
        self.write(".claude/tl-memory/design/2026-10-10-no-meta.md", "# תכנון בלי מטא\n")
        self.write(".claude/tl-memory/PROJECT_CONTEXT.md", CONTEXT)

    def tearDown(self):
        shutil.rmtree(self.root)

    def write(self, relpath, text):
        path = os.path.join(self.root, *relpath.split("/"))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(text)
        return path

    def read(self, relpath):
        with open(os.path.join(self.root, *relpath.split("/")), encoding="utf-8", newline="") as f:
            return f.read()

    def run_tool(self, *argv):
        out = io.StringIO()
        with redirect_stdout(out):
            code = tl_knowledge.main([*argv, "--root", self.root])
        return code, out.getvalue()

    def test_index_lists_documents_and_missing_meta(self):
        code, _ = self.run_tool("index")
        self.assertEqual(code, 0)
        text = self.read(".claude/tl-memory/KNOWLEDGE.md")
        self.assertIn("| אפיון | SPEC-001 | מושכים קבועים | approved |", text)
        self.assertIn("SPEC.md (+html) · מקומי", text)
        self.assertIn("| ADR | ADR-001 |", text)
        self.assertNotIn("| טופס דרישה |", text, "the request is hidden once its spec exists")
        self.assertIn(".claude/tl-memory/design/2026-10-10-no-meta.md", text)
        self.assertLess(text.index("SPEC-001"), text.index("ADR-001"), "specs first")

    def test_publish_moves_spec_with_html_and_updates_agents_files(self):
        code, out = self.run_tool("publish", os.path.join(self.mem, "spec", "SPEC-001-recurring", "SPEC.md"))
        self.assertEqual(code, 0, out)
        self.assertTrue(os.path.exists(os.path.join(self.root, "docs", "specs", "SPEC-001-recurring.md")))
        self.assertTrue(os.path.exists(os.path.join(self.root, "docs", "specs", "SPEC-001-recurring.html")))
        self.assertFalse(os.path.exists(os.path.join(self.mem, "spec", "SPEC-001-recurring", "SPEC.md")))
        self.assertTrue(os.path.exists(os.path.join(self.mem, "spec", "SPEC-001-recurring", "REQUEST.md")))
        knowledge = self.read(".claude/tl-memory/KNOWLEDGE.md")
        self.assertIn("docs/specs/SPEC-001-recurring.md (+html) · פורסם", knowledge)
        agents = self.read("AGENTS.md")
        self.assertIn(tl_knowledge.BLOCK_BEGIN, agents)
        self.assertIn("[SPEC-001: מושכים קבועים](docs/specs/SPEC-001-recurring.md)", agents)
        self.assertIn("meet-chequemis (PROD לקריאה בלבד)", agents)
        self.assertNotIn("ADR-001", agents, "local (unpublished) documents stay out of the block")
        self.assertNotIn("/tl-", agents)
        self.assertNotIn(".claude/", agents)
        self.assertIn("@AGENTS.md", self.read("CLAUDE.md"))
        self.assertIn("git add docs/specs/SPEC-001-recurring.md", out)
        self.assertFalse(os.path.exists(os.path.join(self.root, ".git")), "never runs git")

    def test_block_is_idempotent_and_keeps_team_content_and_crlf(self):
        self.write("AGENTS.md", "# AGENTS\r\n\r\nכללי הצוות.\r\n")
        self.write("CLAUDE.md", "# Team\r\n\r\n@AGENTS.md\r\n")
        self.run_tool("publish", os.path.join(self.mem, "spec", "SPEC-001-recurring", "SPEC.md"))
        first = self.read("AGENTS.md")
        self.assertTrue(first.startswith("# AGENTS\r\n\r\nכללי הצוות."))
        self.assertNotIn("\n", first.replace("\r\n", ""), "CRLF kept")
        _, out = self.run_tool("block")
        self.assertIn("unchanged", out)
        self.assertEqual(self.read("AGENTS.md"), first)
        self.assertEqual(self.read("CLAUDE.md").count("@AGENTS.md"), 1)

    def test_publish_refuses_to_overwrite_a_changed_published_file(self):
        self.write("docs/specs/SPEC-001-recurring.md", SPEC + "\nתיקון של חבר צוות\n")
        code, out = self.run_tool("publish", os.path.join(self.mem, "spec", "SPEC-001-recurring", "SPEC.md"))
        self.assertEqual(code, 1)
        self.assertIn("exists and differs", out)
        self.assertTrue(os.path.exists(os.path.join(self.mem, "spec", "SPEC-001-recurring", "SPEC.md")))

    def test_dry_run_changes_nothing(self):
        code, out = self.run_tool("publish", "--dry-run", os.path.join(self.mem, "adr", "ADR-001-outbox.md"))
        self.assertEqual(code, 0)
        self.assertIn("would move", out)
        self.assertTrue(os.path.exists(os.path.join(self.mem, "adr", "ADR-001-outbox.md")))
        self.assertFalse(os.path.exists(os.path.join(self.root, "AGENTS.md")))

    def test_unpublishable_type(self):
        code, out = self.run_tool("publish", os.path.join(self.mem, "spec", "SPEC-001-recurring", "REQUEST.md"))
        self.assertEqual(code, 1)
        self.assertIn("cannot be published", out)

    def test_config_changes_folders(self):
        self.write(".claude/tl-memory/publish.json", json.dumps({"docs_root": "documentation",
                                                                  "folders": {"spec": "requirements"}}))
        self.run_tool("publish", os.path.join(self.mem, "spec", "SPEC-001-recurring", "SPEC.md"))
        self.assertTrue(os.path.exists(os.path.join(self.root, "documentation", "requirements",
                                                    "SPEC-001-recurring.md")))

    def test_check_finds_what_must_not_be_shared(self):
        path = self.write(".claude/tl-memory/design/d.md",
                          "<!-- tl-meta: type=design; status=draft; date=2026-10-17; area=x; title=t -->\n"
                          "ראה /tl-design ו-.claude/tl-memory/adr/ADR-001.md\n"
                          "Server=prod-db01;Database=x;Password=secret1\n[שאילתה](queries/Q-1.sql)\n")
        code, out = self.run_tool("check", path)
        self.assertEqual(code, 1)
        for expected in ("status is 'draft'", "/tl-design", "refers to .claude/", "secret",
                         "does not exist here: queries/Q-1.sql"):
            self.assertIn(expected, out)

    def test_nothing_to_publish_writes_no_agents_file(self):
        os.remove(os.path.join(self.mem, "PROJECT_CONTEXT.md"))
        _, out = self.run_tool("block")
        self.assertIn("skipped", out)
        self.assertFalse(os.path.exists(os.path.join(self.root, "AGENTS.md")))


if __name__ == "__main__":
    unittest.main()
