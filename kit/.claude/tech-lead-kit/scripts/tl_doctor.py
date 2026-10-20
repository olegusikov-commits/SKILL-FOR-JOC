#!/usr/bin/env python3
"""Tech Lead Kit self-check: is the kit installed and loaded, and what else could Claude Code use
instead of it. Standard library only (Python 3.8+). Read-only, except --apply-settings.

  python .claude/tech-lead-kit/scripts/tl_doctor.py [--root DIR] [--home DIR] [--json]
  python .claude/tech-lead-kit/scripts/tl_doctor.py --apply-settings  # MCP limits + kit agents only

Kit:        VERSION, .claude/CLAUDE.md imports CORE, CORE imports KIT_GUIDE, every command / skill /
            agent named in CORE and KIT_GUIDE exists, the kit is hidden from git, Python version.
Competitors (things Claude may pick instead of the kit):
            skills / agents / commands outside the kit in the project and in the user folder
            (~/.claude), same names as kit ones, other instruction files (CLAUDE.md, CLAUDE.local.md,
            AGENTS.md, .claude/rules), MCP servers, plugins, hooks, permission rules that block
            what the kit needs.
Data:       database MCP servers and command-line clients (sqlcmd, db2) against the registry
            .claude/tl-memory/data-sources.json that /tl-init writes.
Limits:     Claude Code waits for an MCP call up to ~28 hours by default and never moves a subagent's
            MCP call to the background — a slow query looks like a hang.
Memory:     what the kit learned here (.claude/tl-memory/learn/, tl_learn.py lint), ACTIVE.md in place;
            Claude Code's own auto memory, which writes notes without the user's approval and competes with it.
Agents:     the built-in Explore and Plan agents start WITHOUT CLAUDE.md (no kit rules), general-purpose
            has no kit skills; agents of the user folder, of plugins or of the project that are not the
            kit's load CLAUDE.md but not the kit skills, and their own prompt may contradict the kit.
            Kit agents (tl-*) load CLAUDE.md and preload their skills.
--apply-settings (alias --apply-limits) [--keep-agent NAME ...] adds to .claude/settings.local.json
            (personal, hidden from git; other keys kept; this project only): time and output limits for
            MCP calls, and permission rules that deny the built-in agents and every agent that is not the
            kit's (except --keep-agent ones), so delegated work goes to kit agents; turns Claude Code's auto
            memory off (the kit's memory is approved by the user) and allows `tl_learn.py note` without a prompt.
Levels: ERROR — the kit does not work as designed; WARN — something may be used instead of the kit
or contradict it, Claude must look at it with the user; INFO — facts. Exit code 1 if any ERROR.
"""
import argparse
import json
import os
import re
import shutil
import sys

KIT_SKILLS_EXTRA = {"oleg-skill-hesber"}       # kit skills without the tl- prefix
PROJECT_SKILL_PREFIX = "tlp-"                  # skills /tl-retro made for this project — kit skills too
SQL_CLIENTS = ("sqlcmd", "db2", "db2cmd", "clpplus")
# env limits for Claude Code (ms / tokens); the defaults let one MCP call run for a day
LIMITS = {"MCP_TOOL_TIMEOUT": "180000", "CLAUDE_CODE_MCP_TOOL_IDLE_TIMEOUT": "120000",
          "MAX_MCP_OUTPUT_TOKENS": "20000"}
MAX_TOOL_TIMEOUT_MS = 600000
# built-in agents that work outside the kit: Explore / Plan skip CLAUDE.md, general-purpose has no kit skills
BUILTIN_AGENTS = ("Explore", "Plan", "general-purpose")
DB_HINT_RE = re.compile(r"sql|db2|database|postgres|mysql|oracle|sqlite|odbc|jdbc|mssql", re.I)
EXCLUDE_LINES = [".claude/tech-lead-kit/", ".claude/skills/tl-*/", ".claude/skills/tlp-*/",
                 ".claude/commands/tl-*.md", ".claude/agents/tl-*.md", ".claude/tl-memory/"]
# `tl_learn.py note` runs whenever the user corrects Claude — it must not ask for permission every time
NOTE_ALLOW = ["Bash(python .claude/tech-lead-kit/scripts/tl_learn.py note:*)",
              "Bash(py -3 .claude/tech-lead-kit/scripts/tl_learn.py note:*)"]
# permission rules that would stop kit tools (scripts, skills, subagents, SQL MCP reads)
BLOCKING_DENY_RE = re.compile(r"^((Skill|Task|Agent)(\(\*?\))?$|(Task|Agent)\(tl-|Bash\((python|py)\b)", re.I)


def configure_stdout():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass


def read_text(path):
    try:
        with open(path, encoding="utf-8-sig", errors="replace") as f:
            return f.read()
    except OSError:
        return None


def read_json(path):
    text = read_text(path)
    if text is None:
        return None
    try:
        return json.loads(text)
    except ValueError:
        return {"__invalid__": True}


def find_root(start):
    cur = os.path.abspath(start)
    while True:
        if os.path.isdir(os.path.join(cur, ".claude", "tech-lead-kit")):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            return os.path.abspath(start)
        cur = parent


def description(path):
    """First line of the `description:` field of a skill / agent / command front matter."""
    text = read_text(path) or ""
    m = re.search(r"^description:\s*[\"']?(.*?)[\"']?\s*$", text, re.M)
    return (m.group(1) if m else "").strip()[:160]


def entities(claude_dir):
    """{kind: {name: (path, description)}} for skills, agents and commands in one .claude folder."""
    found = {"skill": {}, "agent": {}, "command": {}}
    skills = os.path.join(claude_dir, "skills")
    if os.path.isdir(skills):
        for name in sorted(os.listdir(skills)):
            path = os.path.join(skills, name, "SKILL.md")
            if os.path.isfile(path):
                found["skill"][name] = (path, description(path))
    for kind, folder in (("agent", "agents"), ("command", "commands")):
        base = os.path.join(claude_dir, folder)
        if not os.path.isdir(base):
            continue
        for dirpath, _, files in os.walk(base):
            for f in sorted(files):
                if f.endswith(".md"):
                    path = os.path.join(dirpath, f)
                    name = os.path.relpath(path, base)[:-3].replace(os.sep, ":")
                    found[kind][name] = (path, description(path))
    return found


def is_kit_name(kind, name):
    return name.startswith("tl-") or (kind == "skill" and (name in KIT_SKILLS_EXTRA
                                                          or name.startswith(PROJECT_SKILL_PREFIX)))


class Report:
    def __init__(self):
        self.items = []

    def add(self, level, area, text):
        self.items.append({"level": level, "area": area, "text": text})

    def count(self, level):
        return sum(1 for i in self.items if i["level"] == level)


def check_kit(root, rep):
    kit = os.path.join(root, ".claude", "tech-lead-kit")
    version = (read_text(os.path.join(kit, "VERSION")) or "").strip()
    if not version:
        rep.add("ERROR", "kit", "no .claude/tech-lead-kit/VERSION — the kit is not installed here; run install.cmd")
        return
    rep.add("INFO", "kit", f"Tech Lead Kit {version}")
    claude_md = read_text(os.path.join(root, ".claude", "CLAUDE.md"))
    if claude_md is None or not re.search(r"(?m)^@tech-lead-kit/CORE\.md\s*$", claude_md):
        rep.add("ERROR", "kit", ".claude/CLAUDE.md does not import @tech-lead-kit/CORE.md on its own line — "
                "Claude does not see the kit rules; run install.cmd again")
    core = read_text(os.path.join(kit, "CORE.md")) or ""
    guide = read_text(os.path.join(kit, "KIT_GUIDE.md")) or ""
    if not core:
        rep.add("ERROR", "kit", "CORE.md is missing")
    elif not re.search(r"(?m)^@KIT_GUIDE\.md\s*$", core) or not guide:
        rep.add("ERROR", "kit", "CORE.md does not import KIT_GUIDE.md (or it is missing) — "
                "Claude does not know which command fits which request")
    own = entities(os.path.join(root, ".claude"))
    for cmd in sorted(set(re.findall(r"`/(tl-[a-z-]+)", core + guide))):
        if cmd not in own["command"]:
            rep.add("ERROR", "kit", f"command /{cmd} is named in CORE/KIT_GUIDE but .claude/commands/{cmd}.md is missing")
    for name in sorted(set(re.findall(r"`((?:tl-[a-z-]+)|oleg-skill-hesber)`", core))):
        if name in ("tl-memory", "tl-meta", "tl-agents") or name in own["command"]:
            continue
        if name not in own["skill"] and name not in own["agent"]:
            rep.add("ERROR", "kit", f"{name} is named in CORE but is not in .claude/skills or .claude/agents")
    if sys.version_info < (3, 8):
        rep.add("ERROR", "kit", f"Python {sys.version.split()[0]} — kit scripts need 3.8+")
    git = os.path.join(root, ".git")
    if os.path.isdir(git):
        exclude = {l.strip().lstrip("/") for l in (read_text(os.path.join(git, "info", "exclude")) or "").splitlines()}
        whole = exclude & {".claude", ".claude/", ".claude/*", ".claude/**"}
        missing = [] if whole else [p for p in EXCLUDE_LINES if p not in exclude]
        if missing:
            rep.add("WARN", "kit", "kit files are not hidden from git (.git/info/exclude lacks: "
                    + ", ".join(missing) + ") — run install.cmd again")
    elif not os.path.exists(git):
        rep.add("INFO", "kit", "no .git folder — the kit cannot hide its files from git")


def check_entities(root, home, rep):
    """Skills / agents / commands that are not the kit's, here and in the user folder."""
    project = entities(os.path.join(root, ".claude"))
    user = entities(home) if home else {"skill": {}, "agent": {}, "command": {}}
    for kind in ("skill", "agent", "command"):
        for name, (path, desc) in project[kind].items():
            if not is_kit_name(kind, name):
                rep.add("WARN", "project", f"{kind} '{name}' (not from the kit) — {desc or 'no description'} "
                        f"[{os.path.relpath(path, root)}]")
        for name, (path, desc) in user[kind].items():
            same = name in project[kind] and is_kit_name(kind, name)
            if same:
                rep.add("ERROR", "user", f"{kind} '{name}' exists both in the kit and in the user folder "
                        f"({path}) — Claude may run the wrong one; rename or remove the user copy")
            else:
                rep.add("WARN", "user", f"{kind} '{name}' (user folder, active in every project) — "
                        f"{desc or 'no description'} [{path}]")


def check_instructions(root, home, rep):
    """Other instruction files Claude loads next to CORE — they can contradict the kit."""
    for rel in ("CLAUDE.md", "CLAUDE.local.md", "AGENTS.md", os.path.join(".claude", "CLAUDE.local.md")):
        text = read_text(os.path.join(root, rel))
        if text is None:
            continue
        own = text.split("<!-- tech-lead-kit:begin -->")[0] + text.split("<!-- tech-lead-kit:end -->")[-1] \
            if "<!-- tech-lead-kit:begin -->" in text else text
        lines = [l for l in own.splitlines() if l.strip() and l.strip() not in ("@AGENTS.md", "@./AGENTS.md")]
        if lines:
            rep.add("WARN", "project", f"{rel.replace(os.sep, '/')}: {len(lines)} lines of other instructions — "
                    "read them and report anything that contradicts the kit rules")
    rules = os.path.join(root, ".claude", "rules")
    if os.path.isdir(rules):
        for dirpath, _, files in os.walk(rules):
            for f in sorted(files):
                if f.endswith(".md"):
                    rep.add("WARN", "project", f"rule file {os.path.relpath(os.path.join(dirpath, f), root)} — "
                            "read it and report contradictions with the kit")
    if home:
        text = read_text(os.path.join(home, "CLAUDE.md"))
        if text and text.strip():
            rep.add("WARN", "user", f"{os.path.join(home, 'CLAUDE.md')}: {len(text.splitlines())} lines of personal "
                    "instructions (every project) — read them and report contradictions with the kit")


def mcp_servers(root, home):
    """{name: (where, command text)} from .mcp.json and the user config (~/.claude.json)."""
    found = {}
    data = read_json(os.path.join(root, ".mcp.json")) or {}
    for name, cfg in (data.get("mcpServers") or {}).items():
        found[name] = (".mcp.json", json.dumps(cfg, ensure_ascii=False))
    if home:
        data = read_json(os.path.join(os.path.dirname(home), ".claude.json")) or {}
        for name, cfg in (data.get("mcpServers") or {}).items():
            found.setdefault(name, ("~/.claude.json (user)", json.dumps(cfg, ensure_ascii=False)))
        projects = data.get("projects") or {}
        norm = os.path.normcase(os.path.abspath(root)).replace("\\", "/").rstrip("/")
        for path, pcfg in projects.items():
            if os.path.normcase(path).replace("\\", "/").rstrip("/") == norm:
                for name, cfg in ((pcfg or {}).get("mcpServers") or {}).items():
                    found.setdefault(name, ("~/.claude.json (this project)", json.dumps(cfg, ensure_ascii=False)))
    return found


def registry(root):
    """{alias: source} from .claude/tl-memory/data-sources.json (written by /tl-init)."""
    data = read_json(os.path.join(root, ".claude", "tl-memory", "data-sources.json")) or {}
    if data.get("__invalid__"):
        return None
    return {s.get("alias") or s.get("server") or "?": s for s in data.get("sources") or [] if isinstance(s, dict)}


def check_mcp(root, home, rep):
    servers = mcp_servers(root, home)
    reg = registry(root)
    if reg is None:
        rep.add("WARN", "data", ".claude/tl-memory/data-sources.json is not valid JSON — run /tl-init again")
        reg = {}
    registered = {s.get("server") for s in reg.values() if s.get("access") == "mcp"}
    for alias, src in sorted(reg.items()):
        rep.add("INFO", "data", f"data source '{alias}': {src.get('access', '?')} {src.get('server') or src.get('client') or ''}"
                f" · {src.get('engine', '?')} · {src.get('env', 'PROD?')}")
    for name, (where, cmd) in sorted(servers.items()):
        if name in registered:
            rep.add("INFO", "mcp", f"'{name}' configured in {where} (registered data source)")
        elif DB_HINT_RE.search(name + " " + cmd):
            rep.add("WARN", "data", f"'{name}' ({where}) looks like a database server but is not in "
                    "data-sources.json — /tl-init registers it (engine, PROD/TEST); until then it is PROD, read-only")
        else:
            rep.add("WARN", "mcp", f"'{name}' ({where}) — another MCP server; kit work does not use it "
                    "unless the user says so")
    for client in SQL_CLIENTS:
        path = shutil.which(client)
        if path:
            rep.add("INFO", "data", f"command-line database client '{client}' found ({path})")


def settings_env(root, home):
    """Merged "env" of the settings files, later files win (user < project < local)."""
    env = {}
    paths = ([os.path.join(home, "settings.json")] if home else []) + [
        os.path.join(root, ".claude", "settings.json"), os.path.join(root, ".claude", "settings.local.json")]
    for path in paths:
        data = read_json(path)
        if data and not data.get("__invalid__") and isinstance(data.get("env"), dict):
            env.update({k: str(v) for k, v in data["env"].items()})
    return env


def check_limits(root, home, rep):
    env = settings_env(root, home)
    value = env.get("MCP_TOOL_TIMEOUT") or os.environ.get("MCP_TOOL_TIMEOUT")
    try:
        ok = value is not None and 0 < int(value) <= MAX_TOOL_TIMEOUT_MS
    except ValueError:
        ok = False
    if ok:
        rep.add("INFO", "limits", f"MCP_TOOL_TIMEOUT = {value} ms")
    else:
        rep.add("WARN", "limits", "no time limit for MCP calls (default ~28 hours) — a slow or blocked query "
                "looks like a hang; run tl_doctor.py --apply-settings")


def settings_deny(root, home):
    rules = []
    paths = ([os.path.join(home, "settings.json")] if home else []) + [
        os.path.join(root, ".claude", "settings.json"), os.path.join(root, ".claude", "settings.local.json")]
    for path in paths:
        data = read_json(path)
        if data and not data.get("__invalid__"):
            rules += [str(r) for r in (data.get("permissions") or {}).get("deny") or []]
    return rules


def agent_name(path, fallback):
    m = re.search(r"^name:\s*[\"']?([^\"'\n]+?)[\"']?\s*$", read_text(path) or "", re.M)
    return m.group(1).strip() if m else fallback


def enabled_plugins(root, home):
    names = set()
    paths = ([os.path.join(home, "settings.json")] if home else []) + [
        os.path.join(root, ".claude", "settings.json"), os.path.join(root, ".claude", "settings.local.json")]
    for path in paths:
        data = read_json(path)
        if data and not data.get("__invalid__"):
            names |= {k.split("@")[0] for k, on in (data.get("enabledPlugins") or {}).items() if on}
    return names


def foreign_agents(root, home):
    """[(name, where)] of agents that are not the kit's: project, user folder, enabled plugins."""
    found = {}
    for where, claude_dir in (("project", os.path.join(root, ".claude")), ("user", home)):
        if not claude_dir:
            continue
        for key, (path, _) in entities(claude_dir)["agent"].items():
            name = agent_name(path, key)
            if not is_kit_name("agent", name):
                found.setdefault(name, where)
    plugins = enabled_plugins(root, home)
    base = os.path.join(home, "plugins") if home else None
    if plugins and base and os.path.isdir(base):
        for dirpath, _, files in os.walk(base):
            if os.path.basename(dirpath) != "agents":
                continue
            parts = os.path.normpath(dirpath).split(os.sep)
            plugin = next((p for p in reversed(parts) if p in plugins), None)
            for f in sorted(files):
                if plugin and f.endswith(".md"):
                    found.setdefault(f"{plugin}:{agent_name(os.path.join(dirpath, f), f[:-3])}", "plugin")
    return sorted(found.items())


def agents_to_deny(root, home, keep=()):
    names = list(BUILTIN_AGENTS) + [n for n, _ in foreign_agents(root, home)]
    return [n for n in names if n not in set(keep)]


def check_agents(root, home, rep):
    deny = {r.replace("Task(", "Agent(") for r in settings_deny(root, home)}
    if "Agent" in deny:
        return
    open_builtin = [a for a in BUILTIN_AGENTS if f"Agent({a})" not in deny]
    open_foreign = [f"{n} ({w})" for n, w in foreign_agents(root, home) if f"Agent({n})" not in deny]
    if open_builtin:
        rep.add("WARN", "agents", f"built-in agents {', '.join(open_builtin)} are allowed — Explore and Plan start "
                "without CLAUDE.md (no kit rules) and none of them has the kit skills; run tl_doctor.py "
                "--apply-settings so delegated work goes to the kit agents (tl-researcher, tl-dba, reviewers)")
    if open_foreign:
        rep.add("WARN", "agents", f"agents outside the kit are allowed here: {', '.join(open_foreign)} — they have "
                "no kit skills and their own prompt may contradict the kit; run tl_doctor.py --apply-settings "
                "(this project only; add --keep-agent NAME for one you want to keep)")
    if not open_builtin and not open_foreign:
        rep.add("INFO", "agents", "agents outside the kit denied in this project — delegated work goes to kit agents")


def apply_limits(root, home=None, keep=()):
    """Add the missing LIMITS, deny rules for the built-in and foreign agents (except `keep`), auto memory
    off and the allow rule for `tl_learn.py note` to .claude/settings.local.json; keep every other key (a
    value the user set, e.g. autoMemoryEnabled: true, stays). Returns what was added: {name: value}."""
    path = os.path.join(root, ".claude", "settings.local.json")
    data = read_json(path)
    if data is None:
        data = {}
    elif data.get("__invalid__"):
        raise ValueError(f"{path} is not valid JSON — fix it first")
    env = data.setdefault("env", {})
    added = {k: v for k, v in LIMITS.items() if k not in env}
    env.update(added)
    if "autoMemoryEnabled" not in data:
        data["autoMemoryEnabled"] = False
        added["autoMemoryEnabled"] = "false"
    allow = data.setdefault("permissions", {}).setdefault("allow", [])
    for rule in NOTE_ALLOW:
        if rule not in allow:
            allow.append(rule)
            added[rule] = "allow"
    deny = data["permissions"].setdefault("deny", [])
    for agent in agents_to_deny(root, home, keep):
        rule = f"Agent({agent})"
        if rule not in deny and f"Task({agent})" not in deny:
            deny.append(rule)
            added[rule] = "deny"
    if not added:
        return {}
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return added


def check_settings(root, home, rep):
    files = [(".claude/settings.json", os.path.join(root, ".claude", "settings.json")),
             (".claude/settings.local.json", os.path.join(root, ".claude", "settings.local.json"))]
    if home:
        files.append((os.path.join(home, "settings.json"), os.path.join(home, "settings.json")))
    for label, path in files:
        data = read_json(path)
        if data is None:
            continue
        if data.get("__invalid__"):
            rep.add("WARN", "settings", f"{label} is not valid JSON — Claude Code may ignore it")
            continue
        if data.get("hooks"):
            rep.add("WARN", "settings", f"{label} has hooks ({', '.join(sorted(data['hooks']))}) — they run "
                    "on every tool call and can change what the kit does")
        plugins = [p for p, on in (data.get("enabledPlugins") or {}).items() if on]
        if plugins:
            rep.add("WARN", "settings", f"{label} enables plugins: {', '.join(sorted(plugins))} — their skills "
                    "and agents compete with the kit (and plugins are not allowed at work)")
        for rule in (data.get("permissions") or {}).get("deny") or []:
            if BLOCKING_DENY_RE.search(str(rule)):
                rep.add("WARN", "settings", f"{label} denies '{rule}' — a kit step that needs it will fail")
    if home and os.path.isdir(os.path.join(home, "plugins")):
        rep.add("INFO", "settings", f"{os.path.join(home, 'plugins')} exists — installed plugins may add skills")


def settings_value(root, home, key):
    """The value of a top-level settings key, later files win (user < project < local)."""
    value = None
    paths = ([os.path.join(home, "settings.json")] if home else []) + [
        os.path.join(root, ".claude", "settings.json"), os.path.join(root, ".claude", "settings.local.json")]
    for path in paths:
        data = read_json(path)
        if data and not data.get("__invalid__") and key in data:
            value = data[key]
    return value


def check_memory(root, home, rep):
    env = settings_env(root, home)
    off_env = (env.get("CLAUDE_CODE_DISABLE_AUTO_MEMORY") or os.environ.get("CLAUDE_CODE_DISABLE_AUTO_MEMORY", "")) \
        in ("1", "true", "yes")
    if settings_value(root, home, "autoMemoryEnabled") is False or off_env:
        rep.add("INFO", "memory", "Claude Code auto memory is off in this project — the kit's memory is the only one")
    else:
        rep.add("WARN", "memory", "Claude Code auto memory is on — Claude writes its own notes without your approval "
                "next to the kit's memory (/tl-retro); run tl_doctor.py --apply-settings to turn it off here")
    learn = os.path.join(root, ".claude", "tl-memory", "learn")
    if not os.path.isdir(learn):
        return
    if not os.path.exists(os.path.join(learn, "ACTIVE.md")):
        rep.add("WARN", "memory", "tl-memory/learn/ACTIVE.md is missing — run tl_learn.py render (CORE imports it)")
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import tl_learn
        issues = tl_learn.lint(root)
    except Exception as exc:  # the memory check must never stop the self-check
        rep.add("WARN", "memory", f"tl_learn.py lint failed: {exc}")
        return
    for level, path, line, msg in issues:
        rep.add("WARN", "memory", f"{path}:{line} {msg} ({level.lower()} in tl_learn.py lint)")
    if not issues:
        lessons = sum(1 for l in tl_learn.lessons(root) if l["status"] == "active")
        new = sum(1 for done, _ in tl_learn.inbox_items(root) if not done)
        rep.add("INFO", "memory", f"kit memory: {lessons} active lesson(s), {len(tl_learn.glossary_terms(root))} "
                f"term(s), {len(tl_learn.project_skills(root))} project skill(s), {new} observation(s) waiting")


def run(root, home):
    rep = Report()
    check_kit(root, rep)
    check_entities(root, home, rep)
    check_instructions(root, home, rep)
    check_mcp(root, home, rep)
    check_settings(root, home, rep)
    check_limits(root, home, rep)
    check_agents(root, home, rep)
    check_memory(root, home, rep)
    return rep


def default_home():
    env = os.environ.get("CLAUDE_CONFIG_DIR")
    return env if env else os.path.join(os.path.expanduser("~"), ".claude")


def main(argv=None):
    configure_stdout()
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", help="project folder (default: found from the current folder)")
    ap.add_argument("--home", help="user Claude folder (default: ~/.claude or CLAUDE_CONFIG_DIR)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--apply-settings", "--apply-limits", dest="apply_limits", action="store_true",
                    help="add MCP limits and deny agents outside the kit in .claude/settings.local.json, then check")
    ap.add_argument("--keep-agent", action="append", default=[], metavar="NAME",
                    help="with --apply-settings: do not deny this agent (repeatable)")
    args = ap.parse_args(argv)
    root = os.path.abspath(args.root) if args.root else find_root(os.getcwd())
    home = args.home or default_home()
    if os.path.normcase(os.path.abspath(home)) == os.path.normcase(os.path.join(root, ".claude")):
        home = None  # the project is the home folder itself; nothing extra to check
    home = home if home and os.path.isdir(home) else None
    if args.apply_limits:
        try:
            added = apply_limits(root, home, args.keep_agent)
        except ValueError as e:
            print(f"ERROR {e}")
            return 1
        print("Added to .claude/settings.local.json: " + (", ".join(f"{k}={v}" for k, v in added.items())
                                                           if added else "nothing (already set)"))
        print("Start a new Claude Code session so the settings take effect.\n")
    rep = run(root, home)
    if args.json:
        print(json.dumps(rep.items, ensure_ascii=False, indent=2))
    else:
        print(f"Tech Lead Kit doctor: {root}")
        for level in ("ERROR", "WARN", "INFO"):
            for item in (i for i in rep.items if i["level"] == level):
                print(f"{level:5} [{item['area']}] {item['text']}")
        print(f"\n{rep.count('ERROR')} error(s), {rep.count('WARN')} warning(s)")
    return 1 if rep.count("ERROR") else 0


if __name__ == "__main__":
    sys.exit(main())
