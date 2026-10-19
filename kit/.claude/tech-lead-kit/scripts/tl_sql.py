#!/usr/bin/env python3
"""Gateway to the project's databases for Tech Lead Kit: check a query before it is sent, run it
through a command-line client with a hard time limit, and keep a schema cache. Standard library
only (Python 3.8+). Sources come from .claude/tl-memory/data-sources.json (written by /tl-init).

  check FILE [--source ALIAS | --engine sqlserver|db2-zos --env PROD|TEST]
              static check before any query is sent (MCP or CLI): writes on a read-only source,
              unbounded results, SELECT *, functions on filtered columns, leading-% LIKE, cartesian
              joins, missing guard, tables unknown to / large in the schema cache. Exit 1 on ERROR.
  guard FILE --source ALIAS | --engine …
              print the query with the engine guard (lock timeout, cost limit, isolation / WITH UR)
              — paste this into an MCP call
  run FILE --source ALIAS [--timeout SEC] [--max-rows N] [--out CSV]
              run through the source's command-line client (access=cli): check first (ERROR →
              refused), add the guard, kill the client at the timeout, save the result as CSV
              under .claude/tl-memory/results/, print the first rows, log to sql-journal.csv
  schema find ALIAS WORD | schema table ALIAS TABLE | schema joins ALIAS TABLE_A TABLE_B
              search the schema cache .claude/tl-memory/db/<alias>.json (format: SCHEMA_FORMAT)

A source (data-sources.json "sources" item): alias, access (mcp|cli), engine (sqlserver|db2-zos),
env (PROD|TEST), read_only, server, database, timeout_s, max_rows, and for cli either the default
sqlcmd (Windows authentication; password_env names an environment variable for SQL logins) or
"command": a list with {file} {timeout} {server} {database} placeholders (e.g. a DB2 CLP script).
Never write passwords into the registry.
"""
import argparse
import csv
import datetime
import json
import os
import re
import subprocess
import sys
import time
from collections import deque

SCHEMA_FORMAT = """{"tables": {"dbo.Orders": {"rows": 1200000, "stats_date": "2026-10-01",
  "columns": [{"name": "order_id", "type": "int", "nullable": false}, ...],
  "indexes": [{"name": "IX_Orders_date", "columns": ["created_at", "branch_id"], "unique": false}]}},
 "fks": [{"from": "dbo.OrderLines.order_id", "to": "dbo.Orders.order_id"}]}"""
LARGE_TABLE_ROWS = 1_000_000
WRITE_RE = re.compile(r"\b(INSERT|UPDATE|DELETE|MERGE|DROP|ALTER|CREATE|TRUNCATE|EXEC|EXECUTE|CALL|GRANT|"
                      r"REVOKE|DENY|BACKUP|RESTORE|DBCC|KILL|SHUTDOWN|RENAME|LOCK\s+TABLE|REORG|RUNSTATS)\b", re.I)
SELECT_INTO_RE = re.compile(r"\bSELECT\b(?:(?!\bFROM\b).)*?\bINTO\b", re.I | re.S)
ALLOWED_SET_RE = re.compile(r"^SET\s+(LOCK_TIMEOUT|QUERY_GOVERNOR_COST_LIMIT|TRANSACTION\s+ISOLATION\s+LEVEL|"
                            r"NOCOUNT|ARITHABORT|ANSI_WARNINGS|DEADLOCK_PRIORITY|SHOWPLAN_XML|STATISTICS)\b", re.I)
BOUND_RE = re.compile(r"\bTOP\s*\(?\s*\d+|\bFETCH\s+(FIRST|NEXT)\s+\d+|\bLIMIT\s+\d+", re.I)
AGG_RE = re.compile(r"\b(COUNT|SUM|AVG|MIN|MAX|COUNT_BIG|STDEV|VAR)\s*\(", re.I)
FUNC_ON_COL_RE = re.compile(r"\b(YEAR|MONTH|DAY|DATEPART|DATEDIFF|CONVERT|CAST|UPPER|LOWER|LTRIM|RTRIM|TRIM|"
                            r"ISNULL|COALESCE|SUBSTRING|SUBSTR|LEFT|RIGHT|DATE|CHAR|DIGITS)\s*\(\s*"
                            r"(?:[A-Za-z_][\w]*\.)?[A-Za-z_][\w]*\s*[,)]", re.I)
TABLE_RE = re.compile(r"\b(?:FROM|JOIN)\s+((?:\[?[A-Za-z_][\w$#]*\]?\.){0,2}\[?[A-Za-z_][\w$#]*\]?)", re.I)


def configure_stdout():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass


def find_root(start):
    path = os.path.abspath(start)
    while True:
        if any(os.path.isdir(os.path.join(path, ".claude", d)) for d in ("tech-lead-kit", "tl-memory")):
            return path
        parent = os.path.dirname(path)
        if parent == path:
            return os.path.abspath(start)
        path = parent


def memory(root, *parts):
    return os.path.join(root, ".claude", "tl-memory", *parts)


def load_source(root, alias):
    path = memory(root, "data-sources.json")
    if not os.path.exists(path):
        raise SystemExit(f"ERROR: {path} not found — run /tl-init to register the data sources")
    with open(path, encoding="utf-8-sig") as f:
        sources = json.load(f).get("sources") or []
    for src in sources:
        if src.get("alias") == alias:
            return src
    known = ", ".join(s.get("alias", "?") for s in sources) or "none"
    raise SystemExit(f"ERROR: data source '{alias}' is not registered (known: {known})")


def load_schema(root, alias):
    path = memory(root, "db", f"{alias}.json")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8-sig") as f:
        return json.load(f)


# ------------------------------------------------------------------ check
def strip_sql(sql):
    """SQL without comments and with string literals replaced by '' (keeps the structure)."""
    sql = re.sub(r"/\*.*?\*/", " ", sql, flags=re.S)
    sql = re.sub(r"--[^\n]*", " ", sql)
    return re.sub(r"N?'(?:[^']|'')*'", "''", sql)


def statements(sql):
    return [s.strip() for s in re.split(r";|^\s*GO\s*$", sql, flags=re.M | re.I) if s.strip()]


def norm_table(name):
    return name.replace("[", "").replace("]", "").lower()


def table_in_cache(schema, name):
    want = norm_table(name)
    for full in (schema.get("tables") or {}):
        low = full.lower()
        if low == want or low.split(".")[-1] == want.split(".")[-1] and "." not in want:
            return full
    return None


def check(sql, engine, env, read_only=True, schema=None):
    """[(level, message)] for one query file. Levels: ERROR (refused), WARN, INFO."""
    out = []
    raw = sql
    sql = strip_sql(sql)
    protect = read_only or env != "TEST"
    for st in statements(sql):
        head = st.split(None, 1)[0].upper() if st.split() else ""
        if head == "SET" and ALLOWED_SET_RE.match(st):
            continue
        if protect:
            m = WRITE_RE.search(st)
            if m:
                out.append(("ERROR", f"'{m.group(1).upper()}' on a read-only source ({env}) — only SELECT is allowed"))
            elif SELECT_INTO_RE.search(st) and not re.search(r"\bINSERT\s+INTO\b", st, re.I):
                out.append(("ERROR", f"SELECT … INTO creates a table — not allowed on a read-only source ({env})"))
            elif head not in ("SELECT", "WITH", "SET", "DECLARE", "(", ""):
                out.append(("ERROR", f"statement starts with '{head}' — only SELECT / WITH on a read-only source"))
            elif head == "SET":
                out.append(("ERROR", "SET option not in the allowed guard list"))
        if head not in ("SELECT", "WITH", "("):
            continue
        is_catalog = re.search(r"\b(sys\.|INFORMATION_SCHEMA\.|SYSIBM\.|SYSCAT\.)", st, re.I)
        if not BOUND_RE.search(st) and not AGG_RE.search(st) and not is_catalog:
            out.append(("WARN", "no TOP / FETCH FIRST and no aggregate — the result may be unbounded"))
        if re.search(r"\bSELECT\s+(DISTINCT\s+)?(TOP\s*\(?\s*\d+\s*\)?\s*)?\*", st, re.I):
            out.append(("WARN", "SELECT * — name the columns you need"))
        where = " ".join(re.findall(r"\b(?:WHERE|ON|HAVING)\b(.*?)(?=\bGROUP\s+BY\b|\bORDER\s+BY\b|\bJOIN\b|$)",
                                    st, re.I | re.S))
        for m in FUNC_ON_COL_RE.finditer(where):
            out.append(("WARN", f"{m.group(1).upper()}(column) in a filter — the index on that column cannot be "
                        "used; compare the bare column with a range"))
        if re.search(r"\bCROSS\s+JOIN\b", st, re.I) or (
                re.search(r"\bFROM\s+[\w.\[\]]+(\s+\w+)?\s*,\s*[\w.\[\]]+", st, re.I) and not re.search(r"\bWHERE\b", st, re.I)):
            out.append(("WARN", "cartesian product (CROSS JOIN or comma join without WHERE)"))
        if schema is not None:
            for name in TABLE_RE.findall(st):
                if name.lower().startswith(("sys.", "information_schema.", "sysibm.", "syscat.")):
                    continue
                full = table_in_cache(schema, name)
                if full is None:
                    out.append(("WARN", f"table {name} is not in the schema cache — check the name in the catalog"))
                    continue
                info = schema["tables"][full]
                rows = info.get("rows") or 0
                if rows >= LARGE_TABLE_ROWS:
                    leading = {ix["columns"][0].lower() for ix in info.get("indexes") or [] if ix.get("columns")}
                    words = {w.lower() for w in re.findall(r"[A-Za-z_]\w*", where)}
                    if not leading & words:
                        out.append(("WARN", f"{full} has {rows:,} rows and no leading index column "
                                    f"({', '.join(sorted(leading)) or 'no indexes'}) in the filter — full scan"))
    for m in re.finditer(r"\bLIKE\s+N?'%", strip_comments_only(raw), re.I):
        out.append(("WARN", "LIKE '%…' (leading wildcard) — scans the whole index or table"))
        break
    if engine == "db2-zos" and not re.search(r"\bWITH\s+UR\b", sql, re.I):
        out.append(("INFO", "no WITH UR — `guard` adds it; reads without it can wait on locks"))
    if engine == "sqlserver" and not re.search(r"\bLOCK_TIMEOUT\b", sql, re.I):
        out.append(("INFO", "no SET LOCK_TIMEOUT — `guard` / `run` add the guard; without it a lock wait is endless"))
    seen, unique = set(), []
    for item in out:
        if item not in seen:
            seen.add(item)
            unique.append(item)
    return unique


def strip_comments_only(sql):
    sql = re.sub(r"/\*.*?\*/", " ", sql, flags=re.S)
    return re.sub(r"--[^\n]*", " ", sql)


def guard(sql, engine, max_rows=None, analytics=True):
    """The query with the engine guard in front (SQL Server) or appended (DB2)."""
    body = sql.strip().rstrip(";")
    if engine == "sqlserver":
        lines = ["SET LOCK_TIMEOUT 5000;", "SET QUERY_GOVERNOR_COST_LIMIT 300;"]
        if analytics:
            lines.append("SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;")
        return "\n".join(lines) + "\n" + body + ";\n"
    if engine == "db2-zos":
        if max_rows and not re.search(r"\bFETCH\s+FIRST\b", body, re.I):
            body += f"\nFETCH FIRST {int(max_rows)} ROWS ONLY"
        if not re.search(r"\bWITH\s+UR\b", body, re.I):
            body += "\nWITH UR"
        return body + ";\n"
    return body + ";\n"


def engine_env(args, root):
    if args.source:
        src = load_source(root, args.source)
        return src, src.get("engine", ""), (src.get("env") or "PROD").upper()
    if not args.engine:
        raise SystemExit("ERROR: give --source ALIAS or --engine")
    return {"read_only": (args.env or "PROD").upper() != "TEST"}, args.engine, (args.env or "PROD").upper()


def read_sql(path):
    with open(path, encoding="utf-8-sig") as f:
        return f.read()


def cmd_check(args):
    src, engine, env = engine_env(args, args.root)
    schema = load_schema(args.root, args.source) if args.source else None
    findings = check(read_sql(args.file), engine, env, src.get("read_only", True) or env != "TEST", schema)
    print(f"{args.file}: {engine or '?'} · {env}" + ("" if schema is not None else " · no schema cache"))
    for level, msg in findings:
        print(f"{level:5} {msg}")
    errors = sum(1 for level, _ in findings if level == "ERROR")
    print(f"{errors} error(s), {sum(1 for level, _ in findings if level == 'WARN')} warning(s)")
    return 1 if errors else 0


def cmd_guard(args):
    src, engine, env = engine_env(args, args.root)
    print(guard(read_sql(args.file), engine, args.max_rows or src.get("max_rows")), end="")
    return 0


# ------------------------------------------------------------------ run
def client_command(src, file, timeout):
    template = src.get("command")
    if template:
        return [str(part).format(file=file, timeout=timeout, server=src.get("server", ""),
                                 database=src.get("database", "")) for part in template]
    cmd = ["sqlcmd", "-S", src.get("server", "."), "-b", "-W", "-s", ",", "-w", "65535",
           "-t", str(timeout), "-l", "15", "-i", file]
    if src.get("database"):
        cmd += ["-d", src["database"]]
    if src.get("user_env"):
        cmd += ["-U", os.environ.get(src["user_env"], "")]
    else:
        cmd += ["-E"]
    return cmd


def journal(root, row):
    path = memory(root, "sql-journal.csv")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    new = not os.path.exists(path)
    with open(path, "a", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["time", "source", "env", "file", "seconds", "rows", "status"])
        w.writerow(row)


def cmd_run(args):
    root = args.root
    src = load_source(root, args.source)
    engine, env = src.get("engine", ""), (src.get("env") or "PROD").upper()
    if src.get("access") != "cli":
        print(f"ERROR: source '{args.source}' is reached through {src.get('access', '?')} — run `check` and "
              "`guard`, then send the guarded query through the MCP server", file=sys.stderr)
        return 2
    sql = read_sql(args.file)
    findings = check(sql, engine, env, src.get("read_only", True) or env != "TEST", load_schema(root, args.source))
    for level, msg in findings:
        if level != "INFO":
            print(f"{level:5} {msg}")
    if any(level == "ERROR" for level, _ in findings):
        print("Refused: fix the ERRORs above.")
        return 1
    timeout = int(args.timeout or src.get("timeout_s") or 60)
    max_rows = int(args.max_rows or src.get("max_rows") or 200)
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    stem = os.path.splitext(os.path.basename(args.file))[0]
    out = args.out or memory(root, "results", f"{stem}-{stamp}.csv")
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    guarded = out[:-4] + ".sql" if out.endswith(".csv") else out + ".sql"
    with open(guarded, "w", encoding="utf-8") as f:
        f.write(guard(sql, engine, max_rows))
    env_vars = dict(os.environ)
    if src.get("password_env"):
        env_vars["SQLCMDPASSWORD"] = os.environ.get(src["password_env"], "")
    started = time.time()
    try:
        proc = subprocess.run(client_command(src, guarded, timeout), capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=timeout + max(2, min(15, timeout // 4)), env=env_vars)
    except subprocess.TimeoutExpired:
        secs = round(time.time() - started, 1)
        journal(root, [stamp, args.source, env, args.file, secs, "", "timeout"])
        print(f"TIMEOUT after {secs} s — the client was stopped. Do not repeat the same query: narrow the period, "
              "filter on an indexed column or aggregate by month (tl-sql-engineering problem-solving).")
        return 3
    except FileNotFoundError as e:
        print(f"ERROR: client not found ({e.filename}) — check the source's command in data-sources.json")
        return 2
    secs = round(time.time() - started, 1)
    if proc.returncode != 0:
        journal(root, [stamp, args.source, env, args.file, secs, "", f"error {proc.returncode}"])
        print(f"ERROR (exit {proc.returncode}, {secs} s):\n{(proc.stderr or proc.stdout).strip()[:2000]}")
        if re.search(r"\b(1222|8649|-911|-913|-905)\b", proc.stdout + proc.stderr):
            print("Lock wait or cost limit hit — the query is too heavy as written; redesign it, do not raise limits.")
        return 1
    lines = [l for l in proc.stdout.splitlines() if l.strip() and not re.match(r"^-[-,]*$", l.strip())
             and not re.match(r"^\(\d+ rows? affected\)$", l.strip())]
    with open(out, "w", encoding="utf-8", newline="") as f:
        f.write("\n".join(lines) + ("\n" if lines else ""))
    rows = max(len(lines) - 1, 0)
    journal(root, [stamp, args.source, env, args.file, secs, rows, "ok"])
    print(f"OK · {rows} row(s) · {secs} s · {out}")
    for line in lines[:args.show + 1]:
        print("  " + line)
    if rows > args.show:
        print(f"  … {rows - args.show} more in the CSV")
    return 0


# ------------------------------------------------------------------ schema
def cmd_schema(args):
    schema = load_schema(args.root, args.alias)
    if schema is None:
        print(f"No schema cache for '{args.alias}'. Save the catalog query results as "
              f".claude/tl-memory/db/{args.alias}.json in this format:\n{SCHEMA_FORMAT}")
        return 2
    tables = schema.get("tables") or {}
    if args.action == "find":
        word = args.names[0].lower()
        for name, info in sorted(tables.items()):
            cols = [c["name"] for c in info.get("columns") or [] if word in c["name"].lower()]
            if word in name.lower() or cols:
                print(f"{name} ({info.get('rows', '?')} rows)" + (f": {', '.join(cols)}" if cols else ""))
        return 0
    if args.action == "table":
        full = table_in_cache(schema, args.names[0])
        if not full:
            print(f"{args.names[0]}: not in the cache")
            return 1
        info = tables[full]
        print(f"{full} · {info.get('rows', '?')} rows · statistics {info.get('stats_date', '?')}")
        for c in info.get("columns") or []:
            print(f"  {c['name']:<32} {c.get('type', ''):<18} {'NULL' if c.get('nullable') else 'NOT NULL'}")
        for ix in info.get("indexes") or []:
            print(f"  index {ix['name']}: ({', '.join(ix.get('columns') or [])}){' UNIQUE' if ix.get('unique') else ''}")
        return 0
    a, b = (table_in_cache(schema, n) for n in args.names[:2])
    if not a or not b:
        print("both tables must be in the cache")
        return 1
    graph = {}
    for fk in schema.get("fks") or []:
        ta, ca = fk["from"].rsplit(".", 1)
        tb, cb = fk["to"].rsplit(".", 1)
        graph.setdefault(ta, []).append((tb, f"{fk['from']} = {fk['to']}"))
        graph.setdefault(tb, []).append((ta, f"{fk['to']} = {fk['from']}"))
    prev, queue = {a: None}, deque([a])
    while queue:
        cur = queue.popleft()
        for nxt, cond in graph.get(cur, []):
            if nxt not in prev:
                prev[nxt] = (cur, cond)
                queue.append(nxt)
    if b not in prev:
        print(f"no foreign-key path between {a} and {b} in the cache")
        return 1
    path, cur = [], b
    while prev[cur]:
        cur, cond = prev[cur][0], prev[cur][1]
        path.append(cond)
    for cond in reversed(path):
        print(f"JOIN ON {cond}")
    return 0


def main(argv=None):
    configure_stdout()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("check", "guard"):
        p = sub.add_parser(name)
        p.add_argument("file")
        p.add_argument("--source")
        p.add_argument("--engine", choices=("sqlserver", "db2-zos"))
        p.add_argument("--env", choices=("PROD", "TEST", "prod", "test"))
        p.add_argument("--max-rows", type=int)
        p.add_argument("--root")
    p = sub.add_parser("run")
    p.add_argument("file")
    p.add_argument("--source", required=True)
    p.add_argument("--timeout", type=int)
    p.add_argument("--max-rows", type=int)
    p.add_argument("--out")
    p.add_argument("--show", type=int, default=20)
    p.add_argument("--root")
    p = sub.add_parser("schema")
    p.add_argument("action", choices=("find", "table", "joins"))
    p.add_argument("alias")
    p.add_argument("names", nargs="+")
    p.add_argument("--root")
    args = ap.parse_args(argv)
    args.root = os.path.abspath(args.root) if args.root else find_root(os.getcwd())
    return {"check": cmd_check, "guard": cmd_guard, "run": cmd_run, "schema": cmd_schema}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
