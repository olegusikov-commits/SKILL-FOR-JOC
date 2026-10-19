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
        tl_doctor.apply_limits(self.root)
        self.saved_env = os.environ.pop("MCP_TOOL_TIMEOUT", None)  # the shell of the test run must not count

    def tearDown(self):
        shutil.rmtree(self.tmp)
        if self.saved_env is not None:
            os.environ["MCP_TOOL_TIMEOUT"] = self.saved_env

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

    def test_mcp_servers_and_data_sources(self):
        self.write("proj/.mcp.json", json.dumps({"mcpServers": {
            "orders-db": {"command": "x"}, "pg-tools": {"command": "postgres-mcp"},
            "jira": {"command": "jira-mcp"}}}))
        self.write("user/.claude.json", json.dumps({"projects": {self.root: {"mcpServers": {
            "billing": {"command": "mssql-mcp"}}}}}))
        self.write("proj/.claude/tl-memory/data-sources.json", json.dumps({"sources": [
            {"alias": "orders-test", "access": "mcp", "server": "orders-db", "engine": "sqlserver", "env": "TEST"},
            {"alias": "billing-prod", "access": "mcp", "server": "billing", "engine": "db2-zos", "env": "PROD"}]}))
        warns = self.texts("WARN")
        self.assertIn("'pg-tools' (.mcp.json) looks like a database server but is not in data-sources.json", warns)
        self.assertIn("'jira' (.mcp.json) — another MCP server", warns)
        self.assertNotIn("orders-db", warns)
        info = self.texts("INFO")
        self.assertIn("'billing' configured in ~/.claude.json (this project) (registered data source)", info)
        self.assertIn("data source 'orders-test': mcp orders-db · sqlserver · TEST", info)

    def test_builtin_agents(self):
        self.assertIn("agents outside the kit denied in this project", self.texts("INFO"))
        self.write("proj/.claude/settings.local.json", json.dumps({"env": {"MCP_TOOL_TIMEOUT": "60000"},
                                                                    "permissions": {"deny": ["Task(Explore)"]}}))
        warns = self.texts("WARN")
        self.assertIn("built-in agents Plan, general-purpose are allowed", warns)
        self.assertNotIn("denies 'Task(Explore)'", warns)       # denying a built-in agent does not block the kit
        self.write("proj/.claude/settings.local.json", json.dumps({"env": {"MCP_TOOL_TIMEOUT": "60000"},
                                                                    "permissions": {"deny": ["Agent(tl-researcher)"]}}))
        self.assertIn("denies 'Agent(tl-researcher)'", self.texts("WARN"))
        added = tl_doctor.apply_limits(self.root)
        self.assertIn("Agent(Explore)", added)
        self.assertNotIn("allowed", " ".join(i["text"] for i in self.items("WARN") if i["area"] == "agents"))

    def test_foreign_agents_denied_in_this_project(self):
        self.write("user/.claude/agents/sql.md", "---\nname: sql-expert\ndescription: Writes SQL fast\n---\n")
        self.write("user/.claude/agents/planner.md", "---\nname: planner\ndescription: Plans work\n---\n")
        self.write("proj/.claude/agents/helper.md", "---\nname: helper\ndescription: x\n---\n")
        self.write("user/.claude/settings.json", json.dumps({"enabledPlugins": {"superpowers@mkt": True}}))
        self.write("user/.claude/plugins/cache/mkt/superpowers/1.0/agents/code-reviewer.md",
                   "---\nname: code-reviewer\ndescription: reviews\n---\n")
        warns = self.texts("WARN")
        self.assertIn("agents outside the kit are allowed here: helper (project), planner (user), sql-expert (user), "
                      "superpowers:code-reviewer (plugin)", warns)
        added = tl_doctor.apply_limits(self.root, self.home, keep=["planner"])
        self.assertEqual(sorted(k for k in added if k.startswith("Agent(")),
                         ["Agent(helper)", "Agent(sql-expert)", "Agent(superpowers:code-reviewer)"])
        with open(os.path.join(self.root, ".claude", "settings.local.json"), encoding="utf-8") as f:
            deny = json.load(f)["permissions"]["deny"]
        self.assertFalse([r for r in deny if "tl-" in r], "kit agents are never denied")
        self.assertIn("planner (user)", self.texts("WARN"))
        self.assertEqual(tl_doctor.apply_limits(self.root, self.home, keep=["planner"]), {})
        user_settings = os.path.join(self.home, "settings.json")
        with open(user_settings, encoding="utf-8") as f:
            self.assertNotIn("deny", f.read(), "the user folder is never changed")

    def test_invalid_registry(self):
        self.write("proj/.claude/tl-memory/data-sources.json", "{oops")
        self.assertIn("data-sources.json is not valid JSON", self.texts("WARN"))

    def test_limits(self):
        os.remove(os.path.join(self.root, ".claude", "settings.local.json"))
        self.assertIn("no time limit for MCP calls", self.texts("WARN"))
        self.write("proj/.claude/settings.local.json", json.dumps({"env": {"MCP_TOOL_TIMEOUT": "60000"},
                                                                    "permissions": {"allow": ["Bash(git:*)"]}}))
        self.assertNotIn("no time limit", self.texts("WARN"))
        added = tl_doctor.apply_limits(self.root)
        self.assertNotIn("MCP_TOOL_TIMEOUT", added)          # the user's own value is kept
        self.assertIn("CLAUDE_CODE_MCP_TOOL_IDLE_TIMEOUT", added)
        with open(os.path.join(self.root, ".claude", "settings.local.json"), encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data["env"]["MCP_TOOL_TIMEOUT"], "60000")
        self.assertEqual(data["permissions"]["allow"], ["Bash(git:*)"])
        self.assertEqual(data["permissions"]["deny"], ["Agent(Explore)", "Agent(Plan)", "Agent(general-purpose)"])
        self.assertEqual(tl_doctor.apply_limits(self.root), {})
        self.write("proj/.claude/settings.local.json", json.dumps({"env": {"MCP_TOOL_TIMEOUT": "100000000"}}))
        self.assertIn("no time limit for MCP calls", self.texts("WARN"))

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
