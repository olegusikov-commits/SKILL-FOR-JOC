import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KIT = os.path.join(ROOT, "kit", ".claude")
sys.path.insert(0, os.path.join(KIT, "tech-lead-kit", "scripts"))
import tl_doctor  # noqa: E402

EXCLUDE = ("# tech-lead-kit\n.claude/tech-lead-kit/\n.claude/skills/tl-*/\n.claude/commands/tl-*.md\n"
           ".claude/agents/tl-*.md\n.claude/tl-memory/\n")


class DoctorTests(unittest.TestCase):
    """A project with the real kit installed; each test adds one thing that competes with it."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.root = os.path.join(self.tmp, "proj")
        self.home = os.path.join(self.tmp, "user", ".claude")
        shutil.copytree(KIT, os.path.join(self.root, ".claude"),
                        ignore=shutil.ignore_patterns("__pycache__"))
        self.write("proj/.claude/CLAUDE.md", "# Project instructions\n\n@tech-lead-kit/CORE.md\n")
        self.write("proj/.git/info/exclude", EXCLUDE)
        os.makedirs(self.home)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def write(self, rel, text):
        path = os.path.join(self.tmp, *rel.split("/"))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)

    def items(self, level=None):
        rep = tl_doctor.run(self.root, self.home)
        return [i for i in rep.items if level is None or i["level"] == level]

    def texts(self, level):
        return "\n".join(i["text"] for i in self.items(level))

    def test_clean_install_has_no_errors_or_warnings(self):
        self.assertEqual(self.items("ERROR"), [])
        self.assertEqual(self.items("WARN"), [])
        self.assertIn("Tech Lead Kit", self.texts("INFO"))

    def test_missing_core_import_is_an_error(self):
        self.write("proj/.claude/CLAUDE.md", "# Project instructions\n")
        self.assertIn("does not import @tech-lead-kit/CORE.md", self.texts("ERROR"))

    def test_missing_guide_and_command_are_errors(self):
        os.remove(os.path.join(self.root, ".claude", "tech-lead-kit", "KIT_GUIDE.md"))
        os.remove(os.path.join(self.root, ".claude", "commands", "tl-spec.md"))
        errors = self.texts("ERROR")
        self.assertIn("KIT_GUIDE.md", errors)
        self.assertIn("/tl-spec", errors)

    def test_missing_skill_named_in_core_is_an_error(self):
        shutil.rmtree(os.path.join(self.root, ".claude", "skills", "tl-engineering-standards"))
        self.assertIn("tl-engineering-standards", self.texts("ERROR"))

    def test_not_installed(self):
        shutil.rmtree(os.path.join(self.root, ".claude", "tech-lead-kit"))
        self.assertIn("not installed", self.texts("ERROR"))

    def test_foreign_skill_in_project_and_user_folder(self):
        self.write("proj/.claude/skills/code-writer/SKILL.md",
                   "---\nname: code-writer\ndescription: Writes production code fast\n---\n")
        self.write("user/.claude/agents/reviewer.md", "---\nname: reviewer\ndescription: Reviews any code\n---\n")
        warns = self.texts("WARN")
        self.assertIn("skill 'code-writer' (not from the kit) — Writes production code fast", warns)
        self.assertIn("agent 'reviewer' (user folder", warns)
        self.assertEqual(self.items("ERROR"), [])

    def test_same_name_in_user_folder_is_an_error(self):
        self.write("user/.claude/skills/tl-engineering-standards/SKILL.md",
                   "---\nname: tl-engineering-standards\ndescription: old copy\n---\n")
        self.assertIn("exists both in the kit and in the user folder", self.texts("ERROR"))

    def test_other_instructions_are_reported_but_not_the_kit_block(self):
        self.write("proj/CLAUDE.md", "@AGENTS.md\n")
        self.write("proj/AGENTS.md", "<!-- tech-lead-kit:begin -->\nknowledge\n<!-- tech-lead-kit:end -->\n")
        self.assertEqual(self.items("WARN"), [])
        self.write("proj/CLAUDE.md", "@AGENTS.md\nAlways write comments in English.\n")
        self.write("user/.claude/CLAUDE.md", "Commit after every change.\n")
        warns = self.texts("WARN")
        self.assertIn("CLAUDE.md: 1 lines of other instructions", warns)
        self.assertIn("personal instructions", warns)

    def test_mcp_servers(self):
        self.write("proj/.mcp.json", json.dumps({"mcpServers": {
            "meet-checkov": {"command": "x"}, "pg-tools": {"command": "postgres-mcp"},
            "jira": {"command": "jira-mcp"}}}))
        self.write("user/.claude.json", json.dumps({"projects": {self.root: {"mcpServers": {
            "meet-chequemis": {"command": "y"}}}}}))
        warns = self.texts("WARN")
        self.assertIn("'pg-tools' (.mcp.json) looks like a database server", warns)
        self.assertIn("'jira' (.mcp.json) — another MCP server", warns)
        info = self.texts("INFO")
        self.assertIn("'meet-chequemis' configured in ~/.claude.json (this project)", info)
        self.assertNotIn("is not configured", info)

    def test_settings_hooks_plugins_and_blocking_deny(self):
        self.write("proj/.claude/settings.local.json", json.dumps({
            "hooks": {"PreToolUse": []}, "enabledPlugins": {"superpowers@x": True},
            "permissions": {"deny": ["Bash(python:*)", "Bash(rm:*)"]}}))
        warns = self.texts("WARN")
        self.assertIn("has hooks (PreToolUse)", warns)
        self.assertIn("enables plugins: superpowers@x", warns)
        self.assertIn("denies 'Bash(python:*)'", warns)
        self.assertNotIn("Bash(rm:*)", warns)

    def test_git_exclude(self):
        self.write("proj/.git/info/exclude", "")
        self.assertIn("not hidden from git", self.texts("WARN"))
        self.write("proj/.git/info/exclude", ".claude/\n")
        self.assertNotIn("not hidden from git", self.texts("WARN"))

    def test_cli_exit_code_and_json(self):
        out = io.StringIO()
        with redirect_stdout(out):
            code = tl_doctor.main(["--root", self.root, "--home", self.home, "--json"])
        self.assertEqual(code, 0)
        self.assertIsInstance(json.loads(out.getvalue()), list)
        self.write("proj/.claude/CLAUDE.md", "")
        with redirect_stdout(io.StringIO()):
            self.assertEqual(tl_doctor.main(["--root", self.root, "--home", self.home]), 1)


class KitToolsFirstTests(unittest.TestCase):
    """The rule that makes Claude use the kit's own tools must stay in place."""

    def read(self, rel):
        with open(os.path.join(KIT, rel), encoding="utf-8") as f:
            return f.read()

    def test_core_rule(self):
        core = self.read("tech-lead-kit/CORE.md")
        self.assertIn("## Kit tools first", core)
        rule = core.split("## Kit tools first", 1)[1].split("\n## ", 1)[0]
        for needle in ("Before the first edit of any code", "`tl-engineering-standards`", "`tl-researcher`",
                       "`tl-architect-reviewer`", "not\n  built-in general agents"):
            self.assertIn(needle, rule)

    def test_implement_loads_standards_first(self):
        text = self.read("commands/tl-implement.md")
        step0 = text.split("0. ", 1)[1].split("\n1. ", 1)[0]
        self.assertIn("`tl-engineering-standards`", step0)
        self.assertIn("SMALL", step0)
        self.assertIn("Стандарты kit:", text)

    def test_init_runs_doctor(self):
        self.assertIn("scripts/tl_doctor.py", self.read("commands/tl-init.md"))
        self.assertIn("tl_doctor.py", self.read("tech-lead-kit/KIT_GUIDE.md"))


if __name__ == "__main__":
    unittest.main()
