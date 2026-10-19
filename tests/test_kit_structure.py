"""Structure checks for the kit: frontmatter, names under the install masks, links, installer."""
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KIT = os.path.join(ROOT, "kit", ".claude")
# skills that install.cmd / uninstall.cmd handle explicitly besides the tl-* mask
EXPLICIT_SKILLS = {"oleg-skill-hesber"}


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def frontmatter(path):
    text = read(path)
    m = re.match(r"---\n(.*?)\n---\n", text, re.S)
    if not m:
        return None
    fields = {}
    for line in m.group(1).splitlines():
        if re.match(r"^[A-Za-z-]+:", line):
            key, _, value = line.partition(":")
            fields[key.strip()] = value.strip()
    return fields


def kit_files(sub, pattern):
    folder = os.path.join(KIT, sub)
    return sorted(os.path.join(folder, n) for n in os.listdir(folder) if re.fullmatch(pattern, n))


class FrontmatterTests(unittest.TestCase):
    def test_commands(self):
        for path in kit_files("commands", r".+\.md"):
            with self.subTest(path=path):
                fm = frontmatter(path)
                self.assertIsNotNone(fm, "missing frontmatter")
                self.assertTrue(fm.get("description"), "missing description")
                self.assertTrue(os.path.basename(path).startswith("tl-"), "not under the tl-* mask")
                self.assertIn("$ARGUMENTS", read(path), "command ignores its arguments")

    def test_agents(self):
        skills = set(os.listdir(os.path.join(KIT, "skills")))
        for path in kit_files("agents", r".+\.md"):
            with self.subTest(path=path):
                fm = frontmatter(path)
                self.assertIsNotNone(fm)
                self.assertEqual(fm.get("name"), os.path.basename(path)[:-3])
                self.assertTrue(fm.get("description"))
                self.assertTrue(fm["name"].startswith("tl-"), "not under the tl-* mask")
                block = re.search(r"^skills:\n((?:  - .+\n)+)", read(path), re.M)
                for skill in re.findall(r"  - (.+)", block.group(1)) if block else []:
                    self.assertIn(skill.strip(), skills, f"unknown skill {skill}")

    def test_skills(self):
        for name in sorted(os.listdir(os.path.join(KIT, "skills"))):
            with self.subTest(skill=name):
                fm = frontmatter(os.path.join(KIT, "skills", name, "SKILL.md"))
                self.assertIsNotNone(fm)
                self.assertEqual(fm.get("name"), name)
                self.assertTrue(fm.get("description"))
                self.assertTrue(name.startswith("tl-") or name in EXPLICIT_SKILLS,
                                "not covered by install/uninstall")


class LinkTests(unittest.TestCase):
    """Every `.claude/...` path and `references/*.md` / `scripts/*.py` mentioned in kit files exists."""

    def test_paths_exist(self):
        missing = []
        for dirpath, _, files in os.walk(KIT):
            for name in files:
                if not name.endswith(".md"):
                    continue
                path = os.path.join(dirpath, name)
                text = read(path)
                for ref in re.findall(r"\.claude/((?:skills|commands|agents|tech-lead-kit)/[\w./-]+\.(?:md|py|html))",
                                      text):
                    if not os.path.exists(os.path.join(KIT, ref)):
                        missing.append(f"{path}: .claude/{ref}")
                skill_dir = None
                parts = os.path.relpath(path, KIT).split(os.sep)
                if parts[0] == "skills":
                    skill_dir = os.path.join(KIT, "skills", parts[1])
                for ref in re.findall(r"`((?:references|scripts)/[\w.-]+\.(?:md|py|html))`", text):
                    candidates = [os.path.join(skill_dir, ref)] if skill_dir else []
                    candidates += [os.path.join(KIT, "skills", s, ref)
                                   for s in os.listdir(os.path.join(KIT, "skills"))]
                    if not any(os.path.exists(c) for c in candidates):
                        missing.append(f"{path}: {ref}")
        self.assertEqual(missing, [])


class NameTests(unittest.TestCase):
    """Every `tl-…` name in backticks is a real skill, agent or command (catches renamed agents)."""
    NON_ENTITIES = {"tl-memory", "tl-meta", "tl-agents"}

    def test_names_exist(self):
        skills = set(os.listdir(os.path.join(KIT, "skills")))
        agents = {n[:-3] for n in os.listdir(os.path.join(KIT, "agents"))}
        commands = {n[:-3] for n in os.listdir(os.path.join(KIT, "commands"))}
        unknown = []
        for dirpath, _, files in os.walk(KIT):
            for name in files:
                if not name.endswith(".md"):
                    continue
                path = os.path.join(dirpath, name)
                for slash, ident in re.findall(r"`(/?)(tl-[a-z0-9]+(?:-[a-z0-9]+)*)", read(path)):
                    if slash and ident not in commands:
                        unknown.append(f"{path}: /{ident}")
                    elif not slash and ident not in skills | agents | commands | self.NON_ENTITIES:
                        unknown.append(f"{path}: {ident}")
        self.assertEqual(unknown, [])


class TemplateMetaTests(unittest.TestCase):
    """Documents written from these templates must be findable through KNOWLEDGE.md."""
    TEMPLATES = ["skills/tl-architecture/references/design-doc-template.md",
                 "skills/tl-architecture/references/adr-template.md",
                 "skills/tl-architecture/references/project-doc-template.md",
                 "skills/tl-analytics/references/report-template.md",
                 "skills/tl-analytics/references/topic-memory.md",
                 "skills/tl-tech-debt/SKILL.md",
                 "skills/oleg-skill-hesber/references/template.html",
                 "skills/tl-requirements/references/spec-template.md",
                 "skills/tl-requirements/references/intake-form.md",
                 "skills/tl-requirements/references/flow-template.md"]

    def test_templates_carry_tl_meta(self):
        for rel in self.TEMPLATES:
            with self.subTest(template=rel):
                self.assertRegex(read(os.path.join(KIT, rel)), r"<!-- tl-meta: type=[a-z-]+; ")


class CoreAndDocsTests(unittest.TestCase):
    def test_core_stays_short(self):
        lines = read(os.path.join(KIT, "tech-lead-kit", "CORE.md")).splitlines()
        self.assertLessEqual(len(lines), 120, "CORE.md is loaded always — keep it short")

    def test_kit_guide_is_imported_and_complete(self):
        core = read(os.path.join(KIT, "tech-lead-kit", "CORE.md"))
        self.assertIn("\n@KIT_GUIDE.md\n", core, "KIT_GUIDE.md must be imported on its own line")
        guide = read(os.path.join(KIT, "tech-lead-kit", "KIT_GUIDE.md"))
        for path in kit_files("commands", r".+\.md"):
            with self.subTest(cmd=path):
                self.assertIn("/" + os.path.basename(path)[:-3], guide)

    def test_version_is_semver(self):
        self.assertRegex(read(os.path.join(KIT, "tech-lead-kit", "VERSION")).strip(), r"^\d+\.\d+\.\d+$")

    def test_core_and_readme_mention_every_command(self):
        core = read(os.path.join(KIT, "tech-lead-kit", "CORE.md"))
        readme = read(os.path.join(ROOT, "README.md"))
        for path in kit_files("commands", r".+\.md"):
            cmd = "/" + os.path.basename(path)[:-3]
            with self.subTest(cmd=cmd):
                self.assertIn(f"`{cmd}`", core)
                self.assertIn(cmd, readme)


class GeneralityAndLimitsTests(unittest.TestCase):
    """The kit fits any project and never waits forever."""

    def kit_texts(self):
        for dirpath, _, files in os.walk(KIT):
            for name in files:
                if name.endswith((".md", ".py")):
                    yield os.path.join(dirpath, name), read(os.path.join(dirpath, name))

    def test_no_hardcoded_database_servers(self):
        for path, text in self.kit_texts():
            with self.subTest(path=path):
                self.assertNotRegex(text, r"meet-check|meet-chequ", "data sources come from the registry")

    def test_agents_have_turn_limits(self):
        for path in kit_files("agents", r".+\.md"):
            with self.subTest(path=path):
                self.assertRegex(frontmatter(path).get("maxTurns", ""), r"^\d+$")

    def test_knowledge_skills_are_hidden_from_the_menu(self):
        for name in os.listdir(os.path.join(KIT, "skills")):
            fm = frontmatter(os.path.join(KIT, "skills", name, "SKILL.md"))
            with self.subTest(skill=name):
                expected = None if name in EXPLICIT_SKILLS else "false"
                self.assertEqual(fm.get("user-invocable"), expected)

    def test_changelog_covers_version(self):
        version = read(os.path.join(KIT, "tech-lead-kit", "VERSION")).strip()
        self.assertIn(f"## {version} ", read(os.path.join(KIT, "tech-lead-kit", "CHANGELOG.md")))

    def test_guide_defines_shared_protocols(self):
        guide = read(os.path.join(KIT, "tech-lead-kit", "KIT_GUIDE.md"))
        for section in ("## Routes", "## Depth levels", "## FLOW of a new task", "## Questions",
                        "## Loop limits", "## Step card"):
            self.assertIn(section, guide)
        for path in kit_files("commands", r".+\.md"):
            with self.subTest(cmd=path):
                self.assertIn("step card", read(path))


class InstallerTests(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(ROOT, "install.cmd"), "rb") as f:
            self.raw = f.read()
        self.text = self.raw.decode("utf-8")

    def test_crlf(self):
        self.assertNotIn(b"\n", self.raw.replace(b"\r\n", b""), "install.cmd must use CRLF only")

    def test_no_label_inside_claude_md_block(self):
        block = self.text.split('if not exist "%CLAUDE_MD%" (', 1)[1].split("rem ---- 4.", 1)[0]
        self.assertNotRegex(block, r"(?m)^\s*:\w", "a label inside ( ... ) breaks cmd.exe")
        self.assertNotIn("goto :eof", block)

    def test_excludes_cover_kit(self):
        for pattern in (".claude/tech-lead-kit/", ".claude/skills/tl-*/", ".claude/commands/tl-*.md",
                        ".claude/agents/tl-*.md", ".claude/tl-memory/"):
            self.assertIn(pattern, self.text)
        for skill in EXPLICIT_SKILLS:
            self.assertIn(f".claude/skills/{skill}/", self.text)

    def test_gui_installer(self):
        with open(os.path.join(ROOT, "installer", "install-gui.ps1"), "rb") as f:
            raw = f.read()
        self.assertTrue(raw.startswith(b"\xef\xbb\xbf"), "PowerShell 5.1 needs a BOM for Russian text")
        self.assertNotIn(b"\n", raw.replace(b"\r\n", b""), "install-gui.ps1 must use CRLF only")
        ps1 = raw.decode("utf-8-sig")
        for needle in ("install.cmd", "publish.json", "auto_publish", "docs_root", "TechLeadKit",
                       "FolderBrowserDialog", "TLK_FROM_GUI", "Find-GitProjects", "Get-VsCodeRecent",
                       "DragDrop", "uninstall.cmd", "settings.json", "CHANGELOG.md", "ProgressBar"):
            self.assertIn(needle, ps1)
        self.assertIn("installer\\install-gui.ps1", self.text)
        self.assertIn("TLK_FROM_GUI", self.text)
        self.assertIn("TechLeadKit\\projects.txt", self.text)
        self.assertIn('"auto_publish": true', self.text)

    def test_update_removes_old_kit_files_first(self):
        clean, copy = self.text.index('del /q "%C%\\commands\\tl-*.md"'), self.text.index("robocopy")
        self.assertLess(clean, copy)
        self.assertNotIn("tl-memory", self.text[clean - 400:copy].replace("never touches tl-memory", ""))

    def test_memory_folders(self):
        for sub in ("adr", "design", "analysis", "spec"):
            self.assertIn(f"tl-memory\\{sub}", self.text)

    def test_uninstall_covers_explicit_skills(self):
        un = read(os.path.join(ROOT, "uninstall.cmd"))
        for skill in EXPLICIT_SKILLS:
            self.assertIn(f"skills\\{skill}", un)


if __name__ == "__main__":
    unittest.main()
