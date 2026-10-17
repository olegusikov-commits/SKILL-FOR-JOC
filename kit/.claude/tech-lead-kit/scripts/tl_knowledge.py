#!/usr/bin/env python3
"""Project knowledge for Tech Lead Kit: the map every agent reads, and publishing to the project.
Standard library only (Python 3.8+). The project root is found from the current folder (the
nearest parent with .claude/tech-lead-kit or .claude/tl-memory); --root overrides it.

  index                   rebuild .claude/tl-memory/KNOWLEDGE.md from the tl-meta lines of all
                          kit documents (local memory + published docs); refreshes the AGENTS.md
                          block too if it exists
  next-id PREFIX          next free number for ADR / SPEC, counting local and published files
  check FILE...           what would be wrong if FILE were shared with the team (judged at its
                          publish destination): metadata, not approved, links to local-only
                          files, kit commands, secrets
  publish FILE... [--dry-run] [--force]
                          move approved documents from .claude/tl-memory/ to the project's docs
                          (refused if check finds issues, unless --force), then rebuild the index
                          and the agents block. Never runs git.
  block                   rewrite the managed knowledge block in AGENTS.md (and make CLAUDE.md
                          import it) from the published documents + PROJECT_CONTEXT.md facts

Every kit document starts with:  <!-- tl-meta: type=…; id=…; status=…; date=…; area=…; title=… -->
Settings (optional): .claude/tl-memory/publish.json — see DEFAULTS below.
"""
import argparse
import json
import os
import re
import shutil
import sys

DEFAULTS = {
    "docs_root": "docs",
    "folders": {"spec": "specs", "adr": "adr", "design": "design", "project-doc": "project",
                "explain": "explain", "analysis-report": "analysis", "spec-check": "specs/checks",
                "tech-debt": "."},
    "agents_file": "AGENTS.md",
    "claude_md_import": True,
    "auto_publish": False,  # true: documents are published right after approval (CORE "Publishing")
}
TYPE_LABELS = {"spec": "אפיון", "request": "טופס דרישה", "spec-check": "בדיקת אפיון", "adr": "ADR",
               "design": "תכנון", "project-doc": "מסמך פרויקט", "explain": "הסבר",
               "analysis-topic": "נושא ניתוח", "analysis-report": "דוח ניתוח", "tech-debt": "חוב טכני",
               "project-context": "הקשר הפרויקט"}
TYPE_ORDER = list(TYPE_LABELS)
ID_TYPES = {"ADR": "adr", "SPEC": "spec"}
FINAL_STATUSES = {"approved", "accepted", "final", "superseded", "deprecated", "living"}
BLOCK_BEGIN = "<!-- tech-lead-kit:begin -->"
BLOCK_END = "<!-- tech-lead-kit:end -->"
META_RE = re.compile(r"<!--\s*tl-meta:\s*(.*?)\s*-->", re.S)
META_FIELD_RE = re.compile(r"([\w-]+)\s*=\s*(.*?)\s*(?=;\s*[\w-]+\s*=|$)", re.S)
SECRET_RE = re.compile(r"\b(password|passwd|pwd|secret|api[_-]?key|token)\s*[=:]\s*\S+|"
                       r"\b(server|data source)\s*=\s*[^;\s]+;", re.I)
KIT_CMD_RE = re.compile(r"(?<![\w/.-])/tl-[a-z][a-z-]*")
LINK_RE = re.compile(r"\]\(([^)\s]+)\)")
# files in tl-memory that are documents and must carry tl-meta
EXPECTED_DOCS = [r"spec/[^/]+/SPEC\.md", r"design/[^/]+\.md", r"adr/[^/]+\.md", r"project-doc/[^/]+\.(md|html)",
                 r"hesber/[^/]+\.html", r"analysis/[^/]+/TOPIC\.md", r"analysis/[^/]+/reports/[^/]+\.md",
                 r"TECH_DEBT\.md"]


def configure_stdout():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass


def read_text(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        return f.read()


def has_bom(path):
    with open(path, "rb") as f:
        return f.read(3) == b"\xef\xbb\xbf"


def write_text(path, text, like=None, bom=False):
    """Write UTF-8; keep the newline style of `like` (the previous content) and a BOM if asked."""
    if like is not None and "\r\n" in like:
        text = re.sub(r"(?<!\r)\n", "\r\n", text)
    with open(path, "w", encoding="utf-8-sig" if bom else "utf-8", newline="") as f:
        f.write(text)


def parse_meta(text):
    m = META_RE.search("\n".join(text.splitlines()[:40]))
    if not m:
        return None
    return {k.lower(): v.strip() for k, v in META_FIELD_RE.findall(m.group(1))}


def rel(root, path):
    return os.path.relpath(path, root).replace(os.sep, "/")


def memory_dir(root):
    return os.path.join(root, ".claude", "tl-memory")


def find_root(start):
    path = os.path.abspath(start)
    while True:
        if any(os.path.isdir(os.path.join(path, ".claude", d)) for d in ("tech-lead-kit", "tl-memory")):
            return path
        parent = os.path.dirname(path)
        if parent == path:
            return os.path.abspath(start)
        path = parent


def load_config(root):
    cfg = json.loads(json.dumps(DEFAULTS))
    path = os.path.join(memory_dir(root), "publish.json")
    if os.path.exists(path):
        user = json.loads(read_text(path))
        cfg.update({k: v for k, v in user.items() if k != "folders"})
        cfg["folders"].update(user.get("folders", {}))
    return cfg


def published_dirs(root, cfg):
    return {t: os.path.normpath(os.path.join(root, cfg["docs_root"], f)) for t, f in cfg["folders"].items()}


def inside(path, folder):
    path, folder = os.path.normcase(os.path.abspath(path)), os.path.normcase(os.path.abspath(folder))
    return path == folder or path.startswith(folder.rstrip(os.sep) + os.sep)


# ------------------------------------------------------------------ scanning
def doc_entry(root, path, location):
    try:
        text = read_text(path)
    except (OSError, UnicodeDecodeError):
        return None
    meta = parse_meta(text)
    if meta is None:
        return None
    stem, ext = os.path.splitext(path)
    return {"type": meta.get("type", "?"), "id": meta.get("id", ""), "title": meta.get("title", ""),
            "status": meta.get("status", ""), "date": meta.get("date", ""), "area": meta.get("area", ""),
            "path": rel(root, path), "location": location,
            "html": rel(root, stem + ".html") if ext == ".md" and os.path.exists(stem + ".html") else ""}


def walk_docs(folder, recursive=True):
    if not os.path.isdir(folder):
        return
    if not recursive:
        for name in sorted(os.listdir(folder)):
            path = os.path.join(folder, name)
            if os.path.isfile(path) and name.endswith((".md", ".html")):
                yield path
        return
    for dirpath, dirnames, files in os.walk(folder):
        dirnames[:] = sorted(d for d in dirnames if d not in ("queries", ".git"))
        for name in sorted(files):
            if name.endswith((".md", ".html")):
                yield os.path.join(dirpath, name)


def collect(root, cfg):
    entries, missing, seen = [], [], set()
    mem = memory_dir(root)
    for path in walk_docs(mem):
        if os.path.basename(path) == "KNOWLEDGE.md":
            continue
        entry = doc_entry(root, path, "local")
        if entry:
            entries.append(entry)
            seen.add(os.path.normcase(os.path.abspath(path)))
        elif any(re.fullmatch(p, rel(mem, path)) for p in EXPECTED_DOCS):
            missing.append(rel(root, path))
    for doc_type, folder in published_dirs(root, cfg).items():
        for path in walk_docs(folder, recursive=cfg["folders"][doc_type] not in (".", "")):
            key = os.path.normcase(os.path.abspath(path))
            if key in seen:
                continue
            entry = doc_entry(root, path, "published")
            if entry:
                entries.append(entry)
                seen.add(key)
    by_path = {e["path"] for e in entries}
    entries = [e for e in entries  # rendered HTML twins of a Markdown document are not separate entries
               if not (e["path"].endswith(".html") and e["path"][:-5] + ".md" in by_path)]
    specs = {e["id"] for e in entries if e["type"] == "spec"}
    entries = [e for e in entries if not (e["type"] == "request" and e["id"] in specs)]
    entries.sort(key=lambda e: (TYPE_ORDER.index(e["type"]) if e["type"] in TYPE_ORDER else 99,
                                e["id"] or "~", e["date"]))
    return entries, missing


def cell(text, limit=None):
    text = text.replace("|", "/").replace("\n", " ")
    return text if limit is None or len(text) <= limit else text[:limit - 1] + "…"


def cmd_index(args, quiet_block=False):
    root = args.root
    cfg = load_config(root)
    entries, missing = collect(root, cfg)
    lines = ["# מפת ידע של הפרויקט",
             "<!-- generated by .claude/tech-lead-kit/scripts/tl_knowledge.py index — do not edit by hand -->",
             "",
             "לפני כל משימה: פתח את המסמכים שה\"תחום\" שלהם נוגע במשימה (קבצים, טבלאות, מונחים).",
             "אפיון מאושר (approved) ו-ADR שהתקבל (accepted) מחייבים: פעל לפיהם, או אמור במפורש שהמשימה סותרת אותם.",
             "מסמך שפורסם עורכים במקום שבו הוא פורסם — לא יוצרים עותק מקומי חדש.",
             "", "| סוג | מזהה | כותרת | סטטוס | תאריך | תחום | מיקום |", "|---|---|---|---|---|---|---|"]
    for e in entries:
        where = e["path"] + (" (+html)" if e["html"] else "")
        where += " · פורסם" if e["location"] == "published" else " · מקומי"
        lines.append(f"| {TYPE_LABELS.get(e['type'], e['type'])} | {e['id']} | {cell(e['title'], 80)} | "
                     f"{e['status']} | {e['date']} | {cell(e['area'], 400)} | {where} |")
    if not entries:
        lines.append("| — | | אין עדיין מסמכים | | | | |")
    if missing:
        lines += ["", "## מסמכים בלי tl-meta (להוסיף שורת tl-meta בראש הקובץ)"]
        lines += [f"- {m}" for m in missing]
    os.makedirs(memory_dir(root), exist_ok=True)
    path = os.path.join(memory_dir(root), "KNOWLEDGE.md")
    write_text(path, "\n".join(lines) + "\n")
    print(f"{rel(root, path)}: {len(entries)} documents"
          + (f", {len(missing)} without tl-meta" if missing else ""))
    agents = os.path.join(root, cfg["agents_file"])
    if not quiet_block and os.path.exists(agents) and BLOCK_BEGIN in read_text(agents):
        cmd_block(args)  # a published document changed status → the team's block must follow
    return 0


def cmd_next_id(args):
    prefix = args.prefix.upper()
    if prefix not in ID_TYPES:
        print(f"ERROR: unknown prefix {prefix} (known: {', '.join(ID_TYPES)})", file=sys.stderr)
        return 2
    cfg = load_config(args.root)
    folders = [os.path.join(memory_dir(args.root), ID_TYPES[prefix]),
               published_dirs(args.root, cfg)[ID_TYPES[prefix]]]
    numbers = [0]
    for folder in folders:
        if os.path.isdir(folder):
            for name in os.listdir(folder):
                m = re.match(prefix + r"-(\d+)", name)
                if m:
                    numbers.append(int(m.group(1)))
    print(f"{prefix}-{max(numbers) + 1:03d}")
    return 0


# ------------------------------------------------------------------ check
def check_file(root, path, link_base=None):
    """Issues that make `path` unfit for the team. Links are judged from `link_base` (the folder
    the file will live in after publishing)."""
    issues = []
    text = read_text(path)
    meta = parse_meta(text)
    if meta is None:
        issues.append((1, "no tl-meta line — add it so agents can find this document"))
    else:
        for key in ("type", "status", "date", "area", "title"):
            if not meta.get(key):
                issues.append((1, f"tl-meta: '{key}' is empty"))
        if meta.get("status") and meta["status"] not in FINAL_STATUSES:
            issues.append((1, f"status is '{meta['status']}' — publish approved documents only"))
    base = link_base or os.path.dirname(os.path.abspath(path))
    local = os.path.join(root, ".claude")
    in_fence = False
    for no, line in enumerate(text.splitlines(), 1):
        if line.strip().startswith("```"):
            in_fence = not in_fence
        if SECRET_RE.search(line):
            issues.append((no, "looks like a secret or a connection string"))
        if in_fence:
            continue
        for m in KIT_CMD_RE.finditer(line):
            issues.append((no, f"mentions the kit command {m.group(0)} — teammates may not have the kit"))
        if ".claude/" in line or ".claude\\" in line:
            issues.append((no, "refers to .claude/ — local, not in the repository"))
        for m in LINK_RE.finditer(line):
            target = m.group(1).split("#")[0]
            if not target or re.match(r"^[a-z]+:", target):
                continue
            resolved = os.path.normpath(os.path.join(base, target))
            if inside(resolved, local):
                issues.append((no, f"link into .claude/ (local only): {target}"))
            elif not os.path.exists(resolved):
                issues.append((no, f"link to a file that will not exist for the team: {target}"))
    return issues


def destination(root, cfg, path, meta):
    folder = published_dirs(root, cfg).get(meta.get("type", ""))
    if folder is None:
        return None
    name = os.path.basename(path)
    doc_id = meta.get("id", "")
    if doc_id and not name.startswith(doc_id):
        parent = os.path.basename(os.path.dirname(os.path.abspath(path)))
        ext = os.path.splitext(name)[1]
        if meta.get("type") != "spec-check" and parent.startswith(doc_id):
            name = parent + ext
        else:
            name = f"{doc_id}-{name}"
    return os.path.join(folder, name)


def cmd_check(args):
    root = args.root
    cfg = load_config(root)
    total = 0
    for path in args.files:
        base = None
        if inside(path, memory_dir(root)):
            dest = destination(root, cfg, path, parse_meta(read_text(path)) or {})
            base = os.path.dirname(dest) if dest else None
        issues = check_file(root, path, base)
        total += len(issues)
        print(f"{path}: {'OK' if not issues else str(len(issues)) + ' issue(s)'}")
        for no, msg in issues:
            print(f"  line {no:>4}  {msg}")
    return 1 if total else 0


# ------------------------------------------------------------------ publish
def quote(path):
    return f'"{path}"' if " " in path else path


def cmd_publish(args):
    root = args.root
    cfg = load_config(root)
    moved, failed = [], 0
    for path in args.files:
        src = os.path.abspath(path)
        if not os.path.exists(src):
            print(f"SKIP {path}: not found (already moved?)")
            continue
        if not inside(src, memory_dir(root)):
            print(f"SKIP {path}: not in .claude/tl-memory (already in the project?)")
            continue
        meta = parse_meta(read_text(src)) or {}
        dest = destination(root, cfg, src, meta)
        if dest is None:
            print(f"ERROR {path}: type '{meta.get('type')}' cannot be published "
                  f"(publishable: {', '.join(sorted(cfg['folders']))})")
            failed += 1
            continue
        issues = check_file(root, src, os.path.dirname(dest))
        if issues and not args.force:
            print(f"ERROR {path}: not fit for the team yet — fix and run again (or --force if the user insists):")
            for no, msg in issues:
                print(f"  line {no:>4}  {msg}")
            failed += 1
            continue
        pairs = [(src, dest)]
        twin = os.path.splitext(src)[0] + ".html"
        if src.endswith(".md") and os.path.exists(twin):
            pairs.append((twin, os.path.splitext(dest)[0] + ".html"))
        conflict = [d for s, d in pairs if os.path.exists(d) and read_text(d) != read_text(s)]
        if conflict and not args.force:
            print(f"ERROR {rel(root, conflict[0])} exists and differs (someone edited it?) — merge by hand")
            failed += 1
            continue
        for s, d in pairs:
            print(f"{'would move' if args.dry_run else 'moved'} {rel(root, s)} -> {rel(root, d)}")
            if not args.dry_run:
                os.makedirs(os.path.dirname(d), exist_ok=True)
                shutil.move(s, d)
                moved.append(d)
    if args.dry_run:
        return 1 if failed else 0
    cmd_index(args, quiet_block=True)
    if moved:
        changed = cmd_block(args)
        to_add = [rel(root, d) for d in moved] + changed
        print("Review and commit (the kit never commits): git add " + " ".join(quote(p) for p in to_add))
    return 1 if failed else 0


# ------------------------------------------------------------------ agents block
def agents_facts(root):
    path = os.path.join(memory_dir(root), "PROJECT_CONTEXT.md")
    if not os.path.exists(path):
        return ""
    m = re.search(r"<!--\s*tl-agents:begin\s*-->(.*?)<!--\s*tl-agents:end\s*-->", read_text(path), re.S)
    return m.group(1).strip().replace("\r\n", "\n") if m else ""


def build_block(root, cfg):
    entries, _ = collect(root, cfg)
    published = [e for e in entries if e["location"] == "published"]
    facts = agents_facts(root)
    if not published and not facts:
        return None
    out = [BLOCK_BEGIN,
           "<!-- generated from the documents in " + cfg["docs_root"] + "/ — edits inside this block are overwritten -->",
           "## ידע על הפרויקט", ""]
    if published:
        out += ["לפני שינוי בקוד או בנתונים — פתח את המסמך שה\"תחום\" שלו נוגע בשינוי.",
                "אפיון מאושר ו-ADR שהתקבל מחייבים: אם המשימה סותרת אותם — עצור ואמור זאת.",
                "התנהגות שמתוארת באפיון משתנה — עדכן את האפיון באותו שינוי (הוא חוזר לבדיקה); "
                "ADR שהתקבל לא משנים — מחליפים אותו ב-ADR חדש.",
                "קובץ html שליד מסמך נוצר ממנו אוטומטית; המקור הוא קובץ ה-md.", "",
                "| מסמך | סוג | סטטוס | תאריך | תחום |", "|---|---|---|---|---|"]
        for e in published:
            title = cell((e["id"] + ": " if e["id"] else "") + e["title"], 80)
            link = f"[{title}]({e['path']})" + (f" · [html]({e['html']})" if e["html"] else "")
            out.append(f"| {link} | {TYPE_LABELS.get(e['type'], e['type'])} | {e['status']} | {e['date']} | "
                       f"{cell(e['area'], 400)} |")
        out.append("")
    if facts:
        out += ["### עובדות על הפרויקט", facts, ""]
    out.append(BLOCK_END)
    return "\n".join(out)


def upsert_block(path, block):
    """Returns True if written, False if unchanged; raises ValueError on damaged markers."""
    old = read_text(path) if os.path.exists(path) else None
    bom = has_bom(path) if old is not None else False
    if old is None:
        new = f"# {os.path.basename(path)}\n\n{block}\n"
    else:
        begins, ends = old.count(BLOCK_BEGIN), old.count(BLOCK_END)
        if begins == ends == 0:
            new = old.rstrip("\r\n") + "\n\n" + block + "\n"
        elif begins == ends == 1 and old.index(BLOCK_BEGIN) < old.index(BLOCK_END):
            start = old.index(BLOCK_BEGIN)
            end = old.index(BLOCK_END) + len(BLOCK_END)
            new = old[:start] + block + old[end:]
        else:
            raise ValueError(f"{os.path.basename(path)}: the tech-lead-kit begin/end markers are damaged "
                             f"({begins} begin, {ends} end) — fix them by hand; nothing was written")
    if old is not None and new.replace("\r\n", "\n") == old.replace("\r\n", "\n"):
        return False
    write_text(path, new, like=old, bom=bom)
    return True


def ensure_import(path, target):
    old = read_text(path) if os.path.exists(path) else None
    wanted = {"@" + target, "@./" + target}
    if old is not None and any(l.strip() in wanted for l in old.splitlines()):
        return False
    line = "@" + target
    new = f"# {os.path.basename(path)}\n\n{line}\n" if old is None else old.rstrip("\r\n") + f"\n\n{line}\n"
    write_text(path, new, like=old, bom=has_bom(path) if old is not None else False)
    return True


def cmd_block(args):
    """Returns the list of files it changed (relative to the root)."""
    root = args.root
    cfg = load_config(root)
    block = build_block(root, cfg)
    if block is None:
        print("block: nothing published and no tl-agents facts in PROJECT_CONTEXT.md — skipped")
        return []
    changed = []
    agents = os.path.join(root, cfg["agents_file"])
    try:
        if upsert_block(agents, block):
            changed.append(cfg["agents_file"])
    except ValueError as exc:
        print(f"ERROR {exc}")
        return changed
    print(f"{cfg['agents_file']}: {'updated' if changed else 'unchanged'}")
    if cfg.get("claude_md_import") and os.path.basename(agents).upper() != "CLAUDE.MD":
        if ensure_import(os.path.join(root, "CLAUDE.md"), cfg["agents_file"]):
            print(f"CLAUDE.md: added @{cfg['agents_file']}")
            changed.append("CLAUDE.md")
    return changed


def main(argv=None):
    configure_stdout()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("index", "block"):
        sub.add_parser(name).add_argument("--root")
    p = sub.add_parser("next-id")
    p.add_argument("prefix")
    p.add_argument("--root")
    p = sub.add_parser("check")
    p.add_argument("files", nargs="+")
    p.add_argument("--root")
    p = sub.add_parser("publish")
    p.add_argument("files", nargs="+")
    p.add_argument("--root")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--force", action="store_true")
    args = ap.parse_args(argv)
    args.root = os.path.abspath(args.root) if args.root else find_root(os.getcwd())
    if args.cmd == "block":
        return 0 if cmd_block(args) is not None else 1
    return {"index": cmd_index, "next-id": cmd_next_id, "check": cmd_check,
            "publish": cmd_publish}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
