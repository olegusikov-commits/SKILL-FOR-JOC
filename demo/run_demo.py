#!/usr/bin/env python3
"""Run the Tech Lead Kit end-to-end on the ChequeFlow demo with headless Claude Code.

Not part of the kit. Needs: `claude` CLI, git, and the SQLite MCP server:
  uv tool install mcp-server-sqlite --with "mcp<2"
Each scenario runs in its own copy of the project, so scenarios do not influence each other.

  python run_demo.py setup WORK            # project copy + data + kit install + git → WORK/base
  python run_demo.py run WORK SCENARIO     # copy the scenario's start state, run, save transcript
  python run_demo.py run-all WORK [JOBS]   # every scenario, in dependency order, JOBS in parallel
  python run_demo.py list

A scenario step is a prompt (str) or a file operation done by the "user" between prompts:
("put", file in demo/inputs, destination in the project — may contain one *), ("rm", path).

Results: WORK/<scenario>/ (project state after the run) and WORK/_logs/<scenario>.*.jsonl
"""
import concurrent.futures
import glob
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.join(HERE, "..", "kit", ".claude")

INIT_ANSWER = ("Ответ на вопрос о средах: в этой демо-среде meet-chequemis и meet-checkov — "
               "это TEST (копии в SQLite). Запиши это и закончи инициализацию.")
LEARN_PROMPT = ("/tl-an learn чеки — Тема: автоматическое разрешение чеков. Сейчас около 8% чеков "
                "разрешаются автоматически, остальные проверяет פקיד. Хочу поднять автоматизацию, "
                "допустимая ошибка до 2%. Процесс описан в docs/process.docx. Данные в meet-chequemis.")
LEARN_ANSWER = ("План запросов одобряю (это TEST). На твои вопросы: принимаю предложенные тобой ответы. "
                "Продолжай и доведи изучение темы до конца.")
SPEC_ANSWER = ("На вопросы: принимаю твои предложенные ответы. Утверждаю אפיון — переведи его в статус "
               "approved и закончи по своей процедуре.")
PLAIN_CODE = ("Чеки с датой поступления received_at в будущем (позже текущего момента) должны уходить "
              "к פקיד с причиной FUTURE_DATE. Сделай это.")
CHANGE_LIMIT = "Подними лимит суммы для постоянных плательщиков-организаций до 8 000 ₪."

SCENARIOS = {
    # name: (start state, patch or None, [prompts...])
    "init": ("base", None, ["/tl-init", INIT_ANSWER]),
    "design": ("init", None, [
        "/tl-design Передавать чеки, отклонённые פקיד, в сервис антифрода через очередь IBM MQ, "
        "чтобы антифрод мог заблокировать связанные чеки того же мошенника.",
        "Если остались вопросы — принимаю твои варианты по умолчанию и допущения. Продолжай по процедуре."]),
    "implement": ("init", None, [
        "/tl-implement Чеки с ocr_amount <= 0 должны уходить к פקיד с причиной INVALID_AMOUNT "
        "(проверка сразу после hard stops). Добавь тест."]),
    "review": ("init", "review-branch-reprocess.patch", ["/tl-review"]),
    "sql": ("init", None, [
        "/tl-sql Запрос для отчёта: по каждому отделению за последние 30 дней (от последней даты в "
        "данных) — число чеков, число авто-разрешённых и их доля. Проверь схему и индексы."]),
    "debt": ("init", None, ["/tl-debt src/"]),
    "hesber": ("init", None, [
        "/tl-explain Объясни на русском, как обрабатывается чек: от сканирования до решения "
        "(авто-разрешение или פקיד), со схемой."]),
    "projdoc": ("init", None, ["/tl-explain project"]),
    "an-learn": ("init", None, [LEARN_PROMPT, LEARN_ANSWER]),
    "an-improve": ("an-learn", None, [
        "/tl-an Как поднять автоматизацию чеков выше 8% при ошибке до 2%? Найди возможности, "
        "проверь их на истории и дай рекомендацию."]),
    "an-verify": ("an-learn", "chq-512.patch", [
        "/tl-an Разработчик реализовал задачу docs/tasks/CHQ-512.md — изменения в рабочей копии "
        "(git diff). Проверь, отвечает ли код задаче, и оцени, как он повлияет на автоматизацию и "
        "ошибку."]),
    # systems analyst: the request form is filled by the "user" between the two commands;
    # CHQ-512.md is removed so the analyst cannot copy a ready, precise task text
    "spec-build": ("an-learn", None, [
        ("rm", "docs/tasks/CHQ-512.md"),
        "/tl-spec new אישור אוטומטי לשיקים של מושכים קבועים",
        ("put", "request-recurring-payers.md", ".claude/tl-memory/spec/SPEC-001-*/REQUEST.md"),
        "/tl-spec SPEC-001 — я заполнил טופס דרישה.",
        SPEC_ANSWER]),
    "spec-check": ("init", None, [
        ("put", "spec-mobile-small.md", "docs/specs/mobile-small-cheques.md"),
        "/tl-spec check docs/specs/mobile-small-cheques.md"]),
    "publish": ("spec-build", None, ["/tl-publish", "Настройки по умолчанию подходят. Публикуй."]),
    # /tl-implement may classify the change as LARGE and stop after a design — then it is approved
    "spec-implement": ("publish", None, [
        "/tl-implement SPEC-001",
        "Если ты остановился на дизайне — утверждаю; имя кода причины бери из утверждённой אפיון. "
        "Доведи реализацию до конца."]),
    "spec-verify": ("spec-implement", None, [
        "/tl-an Проверь реализацию SPEC-001 (изменения в рабочей копии, git diff): отвечает ли код "
        "אפיון и как он повлияет на автоматизацию и ошибку."]),
    # a plain request (no command) that contradicts the approved, published spec
    "own-session": ("spec-implement", None, [CHANGE_LIMIT]),
    # a teammate without the kit: only what was published into the project is left
    "teammate": ("spec-implement", None, [("rm", ".claude"), CHANGE_LIMIT]),
    # code requested in plain words, no command: the kit standards must still be loaded first
    "plain-code": ("init", None, [PLAIN_CODE]),
    # 2.0: the navigator — a new task from one line (MVP level), stops only at the approval
    "go-new": ("init", None, [
        "/tl-go new Построить REST-сервис, который выдаёт чеки по номеру счёта и периоду дат, "
        "с постраничной выдачей.",
        "Уровень MVP. На вопросы — принимаю твои рекомендации. Продолжай.",
        "Утверждаю. Доведи до кода с тестами и проверки кода."]),
    # 2.0: where am I — after an approved spec the navigator names the next step
    "go-where": ("spec-build", None, ["/tl-go"]),
    # 2.0: SQL correctness check of existing code (the report query in reports.py / schema)
    "sql-check": ("init", None, [
        "/tl-sql check src/chequeflow/reports.py — запрос отчёта по отделениям: правильный ли он "
        "и корректный (логика, границы, NULL, производительность)?"]),
    # a competing skill and team rules that contradict the kit: /tl-init must find them, and a
    # plain code request must still go through the kit (standards, Hebrew comments, no commit)
    "rival": ("init", None, [
        ("put", "rival-skill.md", ".claude/skills/quick-coder/SKILL.md"),
        ("put", "rival-claude.md", "CLAUDE.md"),
        "/tl-init",
        "На твои вопросы: принимаю твои рекомендации. Закончи по процедуре.",
        PLAIN_CODE]),
}


def sh(cmd, cwd=None, check=True):
    return subprocess.run(cmd, cwd=cwd, check=check, text=True, capture_output=True)


def install_kit(project):
    """Linux equivalent of install.cmd."""
    shutil.copytree(KIT, os.path.join(project, ".claude"), dirs_exist_ok=True)
    for sub in ("adr", "design", "analysis", "spec"):
        os.makedirs(os.path.join(project, ".claude", "tl-memory", sub), exist_ok=True)
    claude_md = os.path.join(project, ".claude", "CLAUDE.md")
    if not os.path.exists(claude_md):
        with open(claude_md, "w", encoding="utf-8") as f:
            f.write("# Project instructions\n\n@tech-lead-kit/CORE.md\n")
    exclude = os.path.join(project, ".git", "info", "exclude")
    with open(exclude, "a", encoding="utf-8") as f:
        f.write("\n# tech-lead-kit (local only, not committed)\n.claude/\n*.db\n.mcp-demo.json\n")


def setup(work):
    base = os.path.join(work, "base")
    if os.path.exists(base):
        shutil.rmtree(base)
    shutil.copytree(os.path.join(HERE, "project"), base,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    sh([sys.executable, os.path.join(HERE, "make_demo.py"), base])
    sh(["git", "init", "-q"], cwd=base)
    with open(os.path.join(base, ".gitignore"), "w", encoding="utf-8") as f:
        f.write("__pycache__/\n*.pyc\n*.db\n")
    sh(["git", "-c", "user.email=demo@example.com", "-c", "user.name=demo", "add", "-A"], cwd=base)
    sh(["git", "-c", "user.email=demo@example.com", "-c", "user.name=demo",
        "commit", "-q", "-m", "ChequeFlow demo"], cwd=base)
    install_kit(base)
    print(f"base ready: {base}")


def mcp_config(project):
    path = os.path.join(project, ".mcp-demo.json")
    servers = {name: {"command": "mcp-server-sqlite", "args": ["--db-path", os.path.join(project, db)]}
               for name, db in (("meet-chequemis", "chequemis.db"), ("meet-checkov", "checkov.db"))}
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"mcpServers": servers}, f, indent=2)
    return path


def run(work, name):
    start, patch, prompts = SCENARIOS[name]
    src = os.path.join(work, start)
    dst = os.path.join(work, name)
    if not os.path.isdir(src):
        sys.exit(f"start state {src} does not exist — run that scenario first")
    if os.path.exists(dst):
        shutil.rmtree(dst)
    shutil.copytree(src, dst, symlinks=True)
    if patch:
        sh(["git", "apply", os.path.join(HERE, "patches", patch)], cwd=dst)
    logs = os.path.join(work, "_logs")
    os.makedirs(logs, exist_ok=True)
    cfg = mcp_config(dst)
    session = None
    total_cost = 0.0
    turn = 0
    for step in prompts:
        if isinstance(step, tuple):
            file_op(dst, step)
            continue
        turn += 1
        i, prompt = turn, step
        cmd = ["claude", "-p", prompt, "--output-format", "stream-json", "--verbose",
               "--mcp-config", cfg, "--strict-mcp-config",
               "--setting-sources", "project,local",
               "--permission-mode", "bypassPermissions"]
        if session:
            cmd += ["--resume", session]
        log_path = os.path.join(logs, f"{name}.{i}.jsonl")
        with open(log_path, "w", encoding="utf-8") as log:
            proc = subprocess.run(cmd, cwd=dst, stdout=log, stderr=subprocess.STDOUT, text=True,
                                  timeout=5400)
        result = None
        with open(log_path, encoding="utf-8") as f:
            for line in f:
                try:
                    msg = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if msg.get("type") == "result":
                    result = msg
        if result is None:
            sys.exit(f"{name} turn {i}: no result (exit {proc.returncode}), see {log_path}")
        session = result.get("session_id")
        total_cost += result.get("total_cost_usd") or 0
        with open(os.path.join(logs, f"{name}.{i}.result.md"), "w", encoding="utf-8") as f:
            f.write(result.get("result") or "")
        print(f"{name} turn {i}: {result.get('subtype')} turns={result.get('num_turns')} "
              f"cost=${result.get('total_cost_usd', 0):.2f}")
    print(f"{name}: total cost ${total_cost:.2f}")


def file_op(project, step):
    """What the user does between prompts: put a prepared file, or remove one."""
    if step[0] == "rm":
        path = os.path.join(project, step[1])
        if os.path.isdir(path):
            shutil.rmtree(path)
        elif os.path.exists(path):
            os.remove(path)
        print(f"  (user) removed {step[1]}")
        return
    _, src, pattern = step
    matches = sorted(glob.glob(os.path.join(project, pattern)))
    dst = matches[0] if matches else os.path.join(project, pattern.replace("*", "request"))
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copyfile(os.path.join(HERE, "inputs", src), dst)
    print(f"  (user) put {src} -> {os.path.relpath(dst, project)}")


def run_all(work, jobs):
    done, failed, running = {"base"}, set(), {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as pool:
        while True:
            for name, (start, _, _) in SCENARIOS.items():
                if name in done | failed or name in running.values():
                    continue
                if start in failed:
                    failed.add(name)
                    print(f"{name}: skipped, {start} failed")
                elif start in done:
                    running[pool.submit(run, work, name)] = name
            if not running:
                break
            finished, _ = concurrent.futures.wait(running, return_when=concurrent.futures.FIRST_COMPLETED)
            for future in finished:
                name = running.pop(future)
                try:
                    future.result()
                    done.add(name)
                except BaseException as exc:  # run() exits via SystemExit on a failed turn
                    failed.add(name)
                    print(f"{name}: FAILED {exc}")
    print(f"done: {len(done) - 1}, failed: {sorted(failed) or '-'}")
    return 1 if failed else 0


def main(argv):
    if len(argv) >= 2 and argv[1] == "list":
        for k, (start, patch, prompts) in SCENARIOS.items():
            first = next(p for p in prompts if isinstance(p, str))
            print(f"{k:14} from {start:14} patch={patch or '-'}  {first[:60]}")
        return 0
    if len(argv) in (3, 4) and argv[1] == "run-all":
        return run_all(os.path.abspath(argv[2]), int(argv[3]) if len(argv) == 4 else 3)
    if len(argv) == 3 and argv[1] == "setup":
        setup(os.path.abspath(argv[2]))
        return 0
    if len(argv) == 4 and argv[1] == "run":
        run(os.path.abspath(argv[2]), argv[3])
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
