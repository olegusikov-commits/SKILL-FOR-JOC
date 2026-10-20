import io
import json
import os
import re
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "kit", ".claude", "tech-lead-kit", "scripts"))
import tl_knowledge  # noqa: E402
import tl_learn  # noqa: E402

LESSON = ("\n## L-001 · active · route:/tl-sql\n- Когда: отчёт по клиентам\n"
          "- Правило: «активный клиент» — `status IN (1,4)`, не `status = 1`\n- Почему: поправка, видели 2×\n")


class LearnTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.root = os.path.join(self.tmp, "proj")
        self.home = os.path.join(self.tmp, "home")
        os.makedirs(os.path.join(self.root, ".claude", "tl-memory"))
        os.makedirs(self.home)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def path(self, rel):
        return os.path.join(self.root, *rel.split("/"))

    def write(self, rel, text, base=None):
        path = os.path.join(base or self.root, *rel.split("/"))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(text)
        return path

    def append(self, rel, text):
        with open(self.path(rel), "a", encoding="utf-8", newline="") as f:
            f.write(text)

    def read(self, rel):
        with open(self.path(rel), encoding="utf-8") as f:
            return f.read()

    def run_tool(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = tl_learn.main(list(argv) + ["--root", self.root])
        return code, out.getvalue() + err.getvalue()

    def lint_messages(self):
        return "\n".join(f"{level} {msg}" for level, _, _, msg in tl_learn.lint(self.root))

    # ---------------------------------------------------------------- note
    def test_note_creates_inbox_and_counts(self):
        code, out = self.run_tool("note", "correction", "route:/tl-sql", "взял status=1 вместо 1,4")
        self.assertEqual(code, 0)
        self.assertIn("1 новых", out)
        inbox = self.read(".claude/tl-memory/learn/INBOX.md")
        self.assertTrue(inbox.startswith("<!-- tl-meta: type=learn-inbox"))
        self.assertRegex(inbox, r"- \[ \] \d{4}-\d\d-\d\d · correction · route:/tl-sql · взял status=1 вместо 1,4 · model")
        code, out = self.run_tool("note", "correction", "route:/tl-sql", "взял status=1 вместо 1,4")
        self.assertIn("already noted", out)
        for i in range(4):
            self.run_tool("note", "style", "project", f"ответ слишком длинный {i}")
        self.assertIn("/tl-retro", self.run_tool("note", "habit", "project", "всегда mvp")[1])

    def test_note_refuses_bad_input_and_secrets(self):
        self.assertEqual(self.run_tool("note", "feeling", "project", "x")[0], 2)
        self.assertEqual(self.run_tool("note", "term", "everywhere", "x")[0], 2)
        for text in ("password=Secret1", "Server=db01;Database=x;", "пиши на oleg@example.com",
                     "клиент 123456789 жаловался", "звонить 052-1234567"):
            with self.subTest(text=text):
                code, out = self.run_tool("note", "term", "project", text)
                self.assertEqual(code, 2)
                self.assertIn("not written", out)
        self.assertFalse(os.path.exists(self.path(".claude/tl-memory/learn/INBOX.md")))

    # ---------------------------------------------------------------- render
    def test_render_creates_files_and_active(self):
        code, out = self.run_tool("render")
        self.assertEqual(code, 0)
        for name in ("INBOX.md", "LESSONS.md", "PROFILE.md", "GLOSSARY.md", "ACTIVE.md"):
            self.assertTrue(os.path.exists(self.path(f".claude/tl-memory/learn/{name}")), name)
        for name in ("INBOX.md", "LESSONS.md", "PROFILE.md", "GLOSSARY.md"):
            meta = tl_knowledge.parse_meta(self.read(f".claude/tl-memory/learn/{name}"))
            self.assertTrue(meta and meta["type"] and meta["date"], name)
        active = self.read(".claude/tl-memory/learn/ACTIVE.md")
        self.assertIn("CORE wins", active)
        self.assertIn("Nothing learned yet", active)
        self.assertEqual(tl_learn.lint(self.root), [])

    def test_render_lists_what_was_learned(self):
        self.run_tool("render")
        self.append(".claude/tl-memory/learn/LESSONS.md", LESSON +
                    "\n## L-002 · rejected · project\n- Когда: всегда\n- Правило: писать по-английски\n")
        profile = self.read(".claude/tl-memory/learn/PROFILE.md").replace(
            "## Общение\n", "## Общение\n- Ответы короткие, сначала вывод\n")
        self.write(".claude/tl-memory/learn/PROFILE.md", profile)
        self.append(".claude/tl-memory/learn/GLOSSARY.md", "| לקוח פעיל | status IN (1,4) | dbo.Customers.status |\n")
        self.write(".claude/skills/tlp-monthly-report/SKILL.md",
                   "---\nname: tlp-monthly-report\ndescription: Monthly cheques report — when the user asks for it\n---\n"
                   "<!-- tl-meta: type=project-skill; id=tlp-monthly-report; status=living; date=2026-10-20; "
                   "area=reports; title=x -->\n")
        self.run_tool("render")
        active = self.read(".claude/tl-memory/learn/ACTIVE.md")
        self.assertIn("L-001 [route:/tl-sql] отчёт по клиентам → «активный клиент»", active)
        self.assertNotIn("L-002", active, "rejected lessons are not loaded")
        self.assertIn("Общение: Ответы короткие", active)
        self.assertIn("לקוח פעיל = status IN (1,4) · dbo.Customers.status", active)
        self.assertIn("tlp-monthly-report — Monthly cheques report", active)
        self.assertEqual(tl_learn.lint(self.root), [])

    def test_active_stays_in_budget(self):
        self.run_tool("render")
        rows = "".join(f"| מונח {i} | משמעות {i} | טבלה{i} |\n" for i in range(200))
        self.append(".claude/tl-memory/learn/GLOSSARY.md", rows)
        self.run_tool("render")
        active = self.read(".claude/tl-memory/learn/ACTIVE.md")
        self.assertLessEqual(len(active.splitlines()), tl_learn.MAX_ACTIVE_LINES)
        self.assertRegex(active, r"… \d+ more: \.claude/tl-memory/learn/GLOSSARY\.md")

    def test_published_glossary_is_the_master(self):
        self.run_tool("render")
        self.append(".claude/tl-memory/learn/GLOSSARY.md", "| ריבית | ריבית שנתית | loans.rate |\n")
        out = io.StringIO()
        with redirect_stdout(out):
            code = tl_knowledge.main(["publish", self.path(".claude/tl-memory/learn/GLOSSARY.md"), "--root", self.root])
        self.assertEqual(code, 0, out.getvalue())
        self.assertTrue(os.path.exists(self.path("docs/project/GLOSSARY.md")))
        self.assertEqual(tl_learn.glossary_path(self.root), self.path("docs/project/GLOSSARY.md"))
        self.run_tool("render")
        self.assertFalse(os.path.exists(self.path(".claude/tl-memory/learn/GLOSSARY.md")), "not recreated locally")
        self.assertIn("ריבית = ריבית שנתית", self.read(".claude/tl-memory/learn/ACTIVE.md"))
        with redirect_stdout(io.StringIO()):
            tl_knowledge.main(["index", "--root", self.root])
        knowledge = self.read(".claude/tl-memory/KNOWLEDGE.md")
        self.assertIn("מילון מונחים", knowledge)
        self.assertNotIn("LESSONS", knowledge, "working memory is not a project document")

    # ---------------------------------------------------------------- lint
    def test_lint_finds_bad_lessons(self):
        self.run_tool("render")
        self.append(".claude/tl-memory/learn/LESSONS.md", LESSON +
                    "\n## L-001 · active · everywhere\n- Когда: мелкая правка\n- Правило: можно без тестов\n"
                    "\n## L-003 · active · project\n- Когда: всё готово\n- Правило: делай commit сам\n"
                    "\n## L-004 · active · project\n- Когда: срочно\n- Правило: на PROD можно UPDATE одной строки\n"
                    "\n## L-005 · draft · project\n- Когда: x\n- Правило: y\n"
                    "\n## L-006 · active · project\n- Когда: модуль\n- Правило: смотри `src/gone/module.py`\n"
                    "\n## L-007 · active · project\n- Правило: без «Когда»\n"
                    "\n## L-008 · active · project\n- Когда: x\n- Правило: пароль password=abc\n")
        msgs = self.lint_messages()
        self.assertIn("L-001 is used twice", msgs)
        self.assertIn("bad scope 'everywhere'", msgs)
        self.assertRegex(msgs, r"ERROR L-001: the rule weakens CORE")
        self.assertRegex(msgs, r"ERROR L-003: the rule weakens CORE")
        self.assertRegex(msgs, r"ERROR L-004: the rule weakens CORE")
        self.assertIn("status 'draft'", msgs)
        self.assertIn("`src/gone/module.py` no longer exists", msgs)
        self.assertIn("L-007: an active lesson needs", msgs)
        self.assertIn("L-008: looks like a secret", msgs)
        self.assertIn("out of date", msgs)
        code, _ = self.run_tool("lint")
        self.assertEqual(code, 1)

    def test_lint_allows_lessons_that_narrow_core(self):
        self.run_tool("render")
        self.append(".claude/tl-memory/learn/LESSONS.md",
                    "\n## L-001 · active · route:/tl-sql\n- Когда: запрос к PROD\n"
                    "- Правило: никогда не запускать UPDATE даже на TEST без показа плана\n"
                    "\n## L-002 · active · project\n- Когда: тесты\n- Правило: всегда запускать тесты модуля billing\n"
                    "\n## L-003 · active · project\n- Когда: данные\n- Правило: на PROD никогда не делать UPDATE\n")
        self.run_tool("render")
        self.assertNotIn("ERROR", self.lint_messages())

    def test_lint_budgets_and_project_skills(self):
        self.run_tool("render")
        self.append(".claude/tl-memory/learn/LESSONS.md", "".join(
            f"\n## L-{i:03d} · active · project\n- Когда: случай {i}\n- Правило: правило номер {i}\n" for i in range(1, 33)))
        profile = self.read(".claude/tl-memory/learn/PROFILE.md").replace(
            "## Привычки\n", "## Привычки\n" + "".join(f"- привычка {i}\n" for i in range(13)))
        self.write(".claude/tl-memory/learn/PROFILE.md", profile)
        self.write(".claude/skills/tlp-x/SKILL.md", "---\nname: tlp-y\n---\n")
        msgs = self.lint_messages()
        self.assertIn("32 active lessons (budget 30)", msgs)
        self.assertIn("13 profile items (budget 12)", msgs)
        self.assertIn("name 'tlp-y' differs from the folder 'tlp-x'", msgs)
        self.assertIn("project skill without a description", msgs)

    # ---------------------------------------------------------------- harvest
    def transcript(self, lines):
        folder = os.path.join(self.home, "projects", re.sub(r"[^A-Za-z0-9]", "-", os.path.abspath(self.root)))
        self.write("s1.jsonl", "\n".join(json.dumps(l, ensure_ascii=False) for l in lines) + "\n", base=folder)

    def test_harvest_transcripts(self):
        human = {"type": "user", "origin": {"kind": "human"}}
        self.transcript([
            dict(human, message={"role": "user", "content": "יש לי משימה יותר חשובה"}),  # 'שוב' inside a word
            dict(human, message={"role": "user", "content": "תענה שוב ברוסית"}),
            dict(human, message={"role": "user", "content": "опять взял не ту таблицу, нужна dbo.Clients"}),
            dict(human, message={"role": "user", "content": "<command-name>/tl-go</command-name>"}),
            {"type": "user", "isMeta": True, "message": {"content": [{"type": "text", "text": "ты ошибся"}]}},
            {"type": "user", "origin": {"kind": "task-notification"}, "message": {"content": "опять ошибка"}},
            {"type": "user", "message": {"content": [{"type": "tool_result", "is_error": True, "content":
                "The user doesn't want to proceed with this tool use. To tell you how to proceed, the user said:\n"
                "сначала покажи план"}]}},
            {"type": "user", "message": {"content": [{"type": "tool_result", "content":
                "output that quotes the user said: something"}]}},
            {"type": "user", "message": {"content": [{"type": "text", "text": "[Request interrupted by user]"}]}},
            dict(human, message={"role": "user", "content": "сделай через view"}),
            dict(human, message={"role": "user", "content": "мой пароль password=abc, не так"}),
            "not json",
        ])
        code, out = self.run_tool("harvest", "--home", self.home)
        self.assertEqual(code, 0)
        self.assertIn("1 skipped", out)
        inbox = self.read(".claude/tl-memory/learn/INBOX.md")
        self.assertIn("· style · project · תענה שוב ברוסית · harvest:transcript", inbox)
        self.assertIn("· correction · project · опять взял не ту таблицу", inbox)
        self.assertIn("отклонил действие: сначала покажи план", inbox)
        self.assertIn("после прерывания: сделай через view", inbox)
        for absent in ("חשובה", "/tl-go", "ты ошибся", "опять ошибка", "something", "password"):
            self.assertNotIn(absent, inbox)
        self.assertEqual(len(re.findall(r"^- \[ \]", inbox, re.M)), 4)
        self.run_tool("harvest", "--home", self.home)
        self.assertEqual(len(re.findall(r"^- \[ \]", self.read(".claude/tl-memory/learn/INBOX.md"), re.M)), 4,
                         "a second harvest adds nothing")

    def test_harvest_sql_answers_and_auto_memory(self):
        self.write(".claude/tl-memory/sql-journal.csv",
                   "time,source,env,file,seconds,rows,status\n"
                   "29990101-100000,main,PROD,q/report.sql,60,,timeout\n"
                   "29990101-100500,main,PROD,q/report.sql,60,,timeout\n"
                   "29990101-101000,main,PROD,q/ok.sql,1,5,ok\n"
                   "20000101-101000,main,PROD,q/old.sql,1,,error 1\n")
        for n in (1, 2):
            self.write(f".claude/tl-memory/spec/SPEC-00{n}-x/SPEC.md",
                       "## הבהרות\n- ש: האם לכלול לקוחות עסקיים? → ת: לא (הוחל בסעיפים: 3)\n")
        folder = os.path.join(self.home, "projects", re.sub(r"[^A-Za-z0-9]", "-", os.path.abspath(self.root)))
        self.write("memory/MEMORY.md", "- [Стиль](style.md) — пользователь любит таблицы\n", base=folder)
        self.run_tool("harvest", "--home", self.home)
        inbox = self.read(".claude/tl-memory/learn/INBOX.md")
        self.assertIn("· mistake · route:/tl-sql · SQL timeout ×2: report.sql на main (PROD)", inbox)
        self.assertNotIn("old.sql", inbox)
        self.assertNotIn("ok.sql", inbox)
        self.assertIn("· habit · project · на вопрос «האם לכלול לקוחות עסקיים?» ответ всегда «לא» (2 задач)", inbox)
        self.assertIn("auto memory: Стиль — пользователь любит таблицы", inbox)

    def test_harvest_finds_transcripts_by_cwd(self):
        folder = os.path.join(self.home, "projects", "shortened-name")
        self.write("a.jsonl", json.dumps({"type": "user", "cwd": self.root, "origin": {"kind": "human"},
                                          "message": {"content": "не так, переделай"}}) + "\n", base=folder)
        self.assertEqual(tl_learn.transcript_dirs(self.home, self.root), [folder])
        self.run_tool("harvest", "--home", self.home)
        self.assertIn("не так, переделай", self.read(".claude/tl-memory/learn/INBOX.md"))

    def test_status_shows_waiting_observations(self):
        self.run_tool("note", "kit", "kit", "команда /tl-sql не предложила tune")
        out = io.StringIO()
        with redirect_stdout(out):
            tl_knowledge.main(["status", "--root", self.root])
        self.assertIn("Наблюдений для разбора: 1 → /tl-retro", out.getvalue())


if __name__ == "__main__":
    unittest.main()
