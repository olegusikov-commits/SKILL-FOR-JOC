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
        self.assertIn("git add docs/specs/SPEC-001-recurring.md docs/specs/SPEC-001-recurring.html AGENTS.md CLAUDE.md", out)
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
        spec = os.path.join(self.mem, "spec", "SPEC-001-recurring", "SPEC.md")
        code, out = self.run_tool("publish", "--dry-run", spec)
        self.assertEqual(code, 0)
        self.assertIn("would move", out)
        self.assertTrue(os.path.exists(spec))
        self.assertFalse(os.path.exists(os.path.join(self.root, "AGENTS.md")))

    def test_publish_refuses_a_draft_or_local_links_unless_forced(self):
        adr = os.path.join(self.mem, "adr", "ADR-001-outbox.md")
        code, out = self.run_tool("publish", adr)
        self.assertEqual(code, 1)
        self.assertIn("status is 'proposed'", out)
        self.assertTrue(os.path.exists(adr))
        self.assertFalse(os.path.exists(os.path.join(self.root, "AGENTS.md")), "nothing moved → no block")
        spec = self.write(".claude/tl-memory/spec/SPEC-002-x/SPEC.md",
                          SPEC.replace("SPEC-001", "SPEC-002") + "[D-3](queries/D-3-volume.sql)\n")
        self.write(".claude/tl-memory/spec/SPEC-002-x/queries/D-3-volume.sql", "SELECT 1")
        code, out = self.run_tool("publish", spec)
        self.assertEqual(code, 1)
        self.assertIn("will not exist for the team: queries/D-3-volume.sql", out)
        code, _ = self.run_tool("publish", "--force", adr)
        self.assertEqual(code, 0)
        self.assertTrue(os.path.exists(os.path.join(self.root, "docs", "adr", "ADR-001-outbox.md")))

    def test_missing_file_is_skipped_and_index_still_runs(self):
        spec = os.path.join(self.mem, "spec", "SPEC-001-recurring", "SPEC.md")
        html = os.path.join(self.mem, "spec", "SPEC-001-recurring", "SPEC.html")
        code, out = self.run_tool("publish", spec, html)
        self.assertEqual(code, 0, out)
        self.assertIn("SKIP", out)
        self.assertIn("docs/specs/SPEC-001-recurring.md", self.read(".claude/tl-memory/KNOWLEDGE.md"))

    def test_index_refreshes_the_agents_block_when_a_published_document_changes(self):
        self.run_tool("publish", os.path.join(self.mem, "spec", "SPEC-001-recurring", "SPEC.md"))
        path = os.path.join(self.root, "docs", "specs", "SPEC-001-recurring.md")
        with open(path, encoding="utf-8") as f:
            text = f.read()
        with open(path, "w", encoding="utf-8") as f:
            f.write(text.replace("status=approved", "status=review"))
        self.run_tool("index")
        self.assertIn("| אפיון | review |", self.read("AGENTS.md"))

    def test_damaged_markers_are_not_overwritten(self):
        self.write("AGENTS.md", "# AGENTS\n\n" + tl_knowledge.BLOCK_BEGIN + "\nישן\n\n## כללי הצוות\nחשוב\n")
        self.run_tool("publish", os.path.join(self.mem, "spec", "SPEC-001-recurring", "SPEC.md"))
        _, out = self.run_tool("block")
        self.assertIn("markers are damaged", out)
        self.assertIn("## כללי הצוות", self.read("AGENTS.md"))

    def test_next_id_counts_local_and_published(self):
        self.write("docs/adr/ADR-007-old.md", "# old")
        code, out = self.run_tool("next-id", "adr")
        self.assertEqual((code, out.strip()), (0, "ADR-008"))
        self.assertEqual(self.run_tool("next-id", "SPEC")[1].strip(), "SPEC-002")

    def test_area_is_not_truncated_and_semicolons_do_not_cut_values(self):
        long_area = ", ".join(f"src/module_{i}/file.py" for i in range(12)) + ", dbo.auto_decisions"
        self.write(".claude/tl-memory/design/d.md",
                   f"<!-- tl-meta: type=design; id=; status=approved; date=2026-10-17; area={long_area}; "
                   "title=שלב א; שלב ב -->\n# d\n")
        self.run_tool("index")
        text = self.read(".claude/tl-memory/KNOWLEDGE.md")
        self.assertIn("dbo.auto_decisions", text)
        self.assertIn("שלב א; שלב ב", text)

    def test_root_is_found_from_a_subfolder(self):
        os.makedirs(os.path.join(self.root, ".claude", "tech-lead-kit"))
        sub = os.path.join(self.root, "src", "pkg")
        os.makedirs(sub)
        self.assertEqual(tl_knowledge.find_root(sub), os.path.abspath(self.root))

    def test_import_variants_and_bom_are_respected(self):
        with open(os.path.join(self.root, "CLAUDE.md"), "w", encoding="utf-8-sig") as f:
            f.write("# Team\n\n@./AGENTS.md\n")
        self.run_tool("publish", os.path.join(self.mem, "spec", "SPEC-001-recurring", "SPEC.md"))
        self.assertEqual(self.read("CLAUDE.md").count("AGENTS.md"), 1)
        with open(os.path.join(self.root, "CLAUDE.md"), "rb") as f:
            self.assertTrue(f.read().startswith(b"\xef\xbb\xbf"))

    def test_check_report_keeps_its_name(self):
        path = self.write(".claude/tl-memory/spec/SPEC-001-recurring/CHECK-2026-10-17.md",
                          "<!-- tl-meta: type=spec-check; id=SPEC-001; status=final; date=2026-10-17; "
                          "area=cheques; title=בדיקה -->\n# בדיקה\n")
        self.run_tool("publish", path)
        self.assertTrue(os.path.exists(os.path.join(self.root, "docs", "specs", "checks",
                                                    "SPEC-001-CHECK-2026-10-17.md")))

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
                          "Server=prod-db01;Database=x;Password=secret1\n[שאילתה](queries/Q-1.sql)\n"
                          "[מקומי](../adr/ADR-001-outbox.md)\n")
        code, out = self.run_tool("check", path)
        self.assertEqual(code, 1)
        for expected in ("status is 'draft'", "/tl-design", "refers to .claude/", "secret",
                         "will not exist for the team: queries/Q-1.sql",
                         "will not exist for the team: ../adr/ADR-001-outbox.md"):
            self.assertIn(expected, out)

    def test_nothing_to_publish_writes_no_agents_file(self):
        os.remove(os.path.join(self.mem, "PROJECT_CONTEXT.md"))
        _, out = self.run_tool("block")
        self.assertIn("skipped", out)
        self.assertFalse(os.path.exists(os.path.join(self.root, "AGENTS.md")))



class StyleTests(unittest.TestCase):
    def test_style_notes(self):
        text = ("<!-- tl-meta: type=design; id=; status=draft; date=2026-10-19; area=x; title=t -->\n"
                "# תכנון\n## 1. רקע\nהשינוי ישפר משמעותית את הביצועים.\n"
                "## 2. ריק\n## 3. מספרים\nזמן תגובה יורד משמעותית מ-900 ל-300 ms.\n"
                "Значительно быстрее. TBD\nIt is important to note that it works.\n"
                "```sql\nSELECT 1 -- efficient\n```\n")
        notes = "\n".join(f"{no}: {m}" for no, m in tl_knowledge.style_issues(text))
        self.assertIn("4: 'משמעותית' without a number", notes)
        self.assertIn("5: empty section", notes)
        self.assertIn("8: 'Значительно' without a number", notes)
        self.assertIn("8: placeholder", notes)
        self.assertIn("9: filler 'It is important to note'", notes)
        self.assertNotIn("efficient", notes)
        self.assertNotRegex(notes, r"(?m)^7: '")  # a number on the line makes the word acceptable

    def test_style_is_advice_only(self):
        root = tempfile.mkdtemp()
        try:
            path = os.path.join(root, "x.md")
            with open(path, "w", encoding="utf-8") as f:
                f.write("# t\nэто эффективно\n")
            out = io.StringIO()
            with redirect_stdout(out):
                code = tl_knowledge.main(["style", path, "--root", root])
            self.assertEqual(code, 0)
            self.assertIn("1 note(s)", out.getvalue())
        finally:
            shutil.rmtree(root)


class StatusTests(unittest.TestCase):
    """`status`: where am I — open flows, documents waiting for approval, open plan tasks, kit updated."""

    def setUp(self):
        self.root = tempfile.mkdtemp()
        kit = os.path.join(self.root, ".claude", "tech-lead-kit")
        os.makedirs(kit)
        with open(os.path.join(kit, "VERSION"), "w") as f:
            f.write("2.0.0\n")
        with open(os.path.join(kit, "CHANGELOG.md"), "w", encoding="utf-8") as f:
            f.write("# Что нового\n\n## 2.0.0 — 2026-10-19\n- навигатор /tl-go\n\n## 1.3.1 — 2026-10-18\n- старое\n")
        self.write(".claude/tl-memory/PROJECT_CONTEXT.md", CONTEXT)
        self.write(".claude/tl-memory/kit-state.json", json.dumps({"kit_version": "1.3.1"}))
        self.write(".claude/tl-memory/adr/ADR-001-outbox.md", ADR)
        self.write(".claude/tl-memory/spec/SPEC-002-svc/FLOW.md",
                   "<!-- tl-meta: type=flow; id=SPEC-002; status=active; date=2026-10-19; area=cheques-api; "
                   "title=שירות שליפת שיקים -->\n# FLOW\n- [x] 0 Вход\n- [ ] 4 Требование — ждёт утверждения\n"
                   "- [ ] 6 Код\n\nДальше: «утверждаю» → /tl-implement SPEC-002\n")
        self.write(".claude/tl-memory/spec/SPEC-003-old/FLOW.md",
                   "<!-- tl-meta: type=flow; id=SPEC-003; status=done; date=2026-10-01; area=x; title=old -->\n")
        self.write(".claude/tl-memory/design/2026-10-19-svc.md",
                   "<!-- tl-meta: type=design; id=; status=approved; date=2026-10-19; area=api; title=svc -->\n"
                   "- [x] T1 каркас\n- [ ] T2 API\n- [ ] T3 тесты\n")

    def tearDown(self):
        shutil.rmtree(self.root)

    def write(self, relpath, text):
        path = os.path.join(self.root, *relpath.split("/"))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(text)

    def status(self, *extra):
        out = io.StringIO()
        with redirect_stdout(out):
            code = tl_knowledge.main(["status", *extra, "--root", self.root])
        self.assertEqual(code, 0)
        return out.getvalue()

    def test_where_am_i(self):
        out = self.status()
        self.assertIn("Kit обновлён: 1.3.1 → 2.0.0", out)
        self.assertIn("навигатор /tl-go", out)
        self.assertNotIn("старое", out)
        self.assertIn("SPEC-002 שירות שליפת שיקים · этап: 4 Требование — ждёт утверждения", out)
        self.assertIn("дальше: «утверждаю» → /tl-implement SPEC-002", out)
        self.assertNotIn("SPEC-003", out)
        self.assertIn("ADR ADR-001 Outbox · proposed", out)
        self.assertIn("1/3 задач", out)

    def test_mark_init(self):
        self.status("--mark-init")
        out = self.status()
        self.assertNotIn("Kit обновлён", out)
        os.remove(os.path.join(self.root, ".claude", "tl-memory", "PROJECT_CONTEXT.md"))
        self.assertIn("/tl-init", self.status())

if __name__ == "__main__":
    unittest.main()
