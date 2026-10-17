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
        if re.match(r"^[a-z-]+:", line):
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
                for ref in re.findall(r"\.claude/((?:skills|commands|agents)/[\w./-]+\.(?:md|py))", text):
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


class CoreAndDocsTests(unittest.TestCase):
    def test_core_stays_short(self):
        lines = read(os.path.join(KIT, "tech-lead-kit", "CORE.md")).splitlines()
        self.assertLessEqual(len(lines), 120, "CORE.md is loaded always — keep it short")

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

    def test_uninstall_covers_explicit_skills(self):
        un = read(os.path.join(ROOT, "uninstall.cmd"))
        for skill in EXPLICIT_SKILLS:
            self.assertIn(f"skills\\{skill}", un)


if __name__ == "__main__":
    unittest.main()
