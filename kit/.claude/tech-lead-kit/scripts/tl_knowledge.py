#!/usr/bin/env python3
"""Project knowledge for Tech Lead Kit: the map every agent reads, and publishing to the project.
Standard library only (Python 3.8+). Run from the project root (or pass --root).

  index                   rebuild .claude/tl-memory/KNOWLEDGE.md from the tl-meta lines of all
                          kit documents (local memory + published docs)
  check FILE...           what would be wrong if FILE were shared with the team: missing metadata,
                          not approved, links to local-only files, kit commands, secrets
  publish FILE... [--dry-run] [--force]
                          move approved documents from .claude/tl-memory/ to the project's docs,
                          then rebuild the index and the agents block. Never runs git.
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
}
TYPE_LABELS = {"spec": "אפיון", "request": "טופס דרישה", "spec-check": "בדיקת אפיון", "adr": "ADR",
               "design": "תכנון", "project-doc": "מסמך פרויקט", "explain": "הסבר",
               "analysis-topic": "נושא ניתוח", "analysis-report": "דוח ניתוח", "tech-debt": "חוב טכני"}
TYPE_ORDER = list(TYPE_LABELS)
FINAL_STATUSES = {"approved", "accepted", "final", "superseded", "deprecated", "living"}
BLOCK_BEGIN = "<!-- tech-lead-kit:begin -->"
BLOCK_END = "<!-- tech-lead-kit:end -->"
META_RE = re.compile(r"<!--\s*tl-meta:\s*(.*?)\s*-->", re.S)
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


def write_text(path, text, like=None):
    """Write UTF-8; keep the newline style of `like` (the previous content) if given."""
    if like is not None and "\r\n" in like:
        text = re.sub(r"(?<!\r)\n", "\r\n", text)
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)


def parse_meta(text):
    m = META_RE.search("\n".join(text.splitlines()[:40]))
    if not m:
        return None
    meta = {}
    for part in m.group(1).split(";"):
        key, sep, value = part.partition("=")
        if sep:
            meta[key.strip().lower()] = value.strip()
    return meta


def rel(root, path):
    return os.path.relpath(path, root).replace(os.sep, "/")


def memory_dir(root):
    return os.path.join(root, ".claude", "tl-memory")


def load_config(root):
    cfg = json.loads(json.dumps(DEFAULTS))
    path = os.path.join(memory_dir(root), "publish.json")
    if os.path.exists(path):
        user = json.loads(read_text(path))
        cfg.update({k: v for k, v in user.items() if k != "folders"})
        cfg["folders"].update(user.get("folders", {}))
    return cfg


def published_dirs(root, cfg):
    dirs = {}
    for doc_type, folder in cfg["folders"].items():
        dirs[doc_type] = os.path.normpath(os.path.join(root, cfg["docs_root"], folder))
    return dirs


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


def cell(text, limit=90):
    text = text.replace("|", "/").replace("\n", " ")
    return text if len(text) <= limit else text[:limit - 1] + "…"


def cmd_index(args):
    root = os.path.abspath(args.root)
    cfg = load_config(root)
    entries, missing = collect(root, cfg)
    lines = ["# מפת ידע של הפרויקט",
             "<!-- generated by .claude/tech-lead-kit/scripts/tl_knowledge.py index — do not edit by hand -->",
             "",
             "לפני כל משימה: פתח את המסמכים שה\"תחום\" שלהם נוגע במשימה (קבצים, טבלאות, מונחים).",
             "אפיון מאושר (approved) ו-ADR שהתקבל (accepted) מחייבים: פעל לפיהם, או אמור במפורש שהמשימה סותרת אותם.",
             "", "| סוג | מזהה | כותרת | סטטוס | תאריך | תחום | מיקום |", "|---|---|---|---|---|---|---|"]
    for e in entries:
        where = e["path"] + (" (+html)" if e["html"] else "")
        where += " · פורסם" if e["location"] == "published" else " · מקומי"
        lines.append(f"| {TYPE_LABELS.get(e['type'], e['type'])} | {e['id']} | {cell(e['title'], 70)} | "
                     f"{e['status']} | {e['date']} | {cell(e['area'])} | {where} |")
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
    return 0


# ------------------------------------------------------------------ check
def check_file(root, path):
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
    base = os.path.dirname(os.path.abspath(path))
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
            if not os.path.exists(os.path.normpath(os.path.join(base, target))):
                issues.append((no, f"link to a file that does not exist here: {target}"))
    return issues


def cmd_check(args):
    root = os.path.abspath(args.root)
    total = 0
    for path in args.files:
        issues = check_file(root, path)
        total += len(issues)
        print(f"{path}: {'OK' if not issues else str(len(issues)) + ' issue(s)'}")
        for no, msg in issues:
            print(f"  line {no:>4}  {msg}")
    return 1 if total else 0


# ------------------------------------------------------------------ publish
def destination(root, cfg, path, meta):
    folder = published_dirs(root, cfg).get(meta.get("type", ""))
    if folder is None:
        return None
    name = os.path.basename(path)
    doc_id = meta.get("id", "")
    if doc_id and not name.startswith(doc_id):
        parent = os.path.basename(os.path.dirname(os.path.abspath(path)))
        ext = os.path.splitext(name)[1]
        name = parent + ext if parent.startswith(doc_id) else f"{doc_id}-{name}"
    return os.path.join(folder, name)


def cmd_publish(args):
    root = os.path.abspath(args.root)
    cfg = load_config(root)
    mem = os.path.normcase(os.path.abspath(memory_dir(root)))
    moved, failed = [], 0
    for path in args.files:
        src = os.path.abspath(path)
        if not os.path.normcase(src).startswith(mem):
            print(f"SKIP {path}: not in .claude/tl-memory (already in the project?)")
            continue
        meta = parse_meta(read_text(src)) or {}
        dest = destination(root, cfg, src, meta)
        if dest is None:
            print(f"ERROR {path}: type '{meta.get('type')}' cannot be published "
                  f"(publishable: {', '.join(sorted(cfg['folders']))})")
            failed += 1
            continue
        pairs = [(src, dest)]
        twin = os.path.splitext(src)[0] + ".html"
        if src.endswith(".md") and os.path.exists(twin):
            pairs.append((twin, os.path.splitext(dest)[0] + ".html"))
        for s, d in pairs:
            if os.path.exists(d) and read_text(d) != read_text(s) and not args.force:
                print(f"ERROR {rel(root, d)} exists and differs (someone edited it?) — merge by hand "
                      "or use --force")
                failed += 1
                break
        else:
            for s, d in pairs:
                print(f"{'would move' if args.dry_run else 'moved'} {rel(root, s)} -> {rel(root, d)}")
                if not args.dry_run:
                    os.makedirs(os.path.dirname(d), exist_ok=True)
                    shutil.move(s, d)
                    moved.append(d)
    if args.dry_run:
        return 1 if failed else 0
    for d in moved:
        if d.endswith(".md"):
            for no, msg in check_file(root, d):
                print(f"  CHECK {rel(root, d)} line {no}: {msg}")
    cmd_index(args)
    cmd_block(args)
    if moved:
        print("Review and commit (the kit never commits): git add " + " ".join(rel(root, d) for d in moved))
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
                "אם ההתנהגות שמתוארת במסמך משתנה — עדכן גם את המסמך באותו שינוי.", "",
                "| מסמך | סוג | סטטוס | תאריך | תחום |", "|---|---|---|---|---|"]
        for e in published:
            title = cell((e["id"] + ": " if e["id"] else "") + e["title"], 80)
            link = f"[{title}]({e['path']})" + (f" · [html]({e['html']})" if e["html"] else "")
            out.append(f"| {link} | {TYPE_LABELS.get(e['type'], e['type'])} | {e['status']} | {e['date']} | "
                       f"{cell(e['area'])} |")
        out.append("")
    if facts:
        out += ["### עובדות על הפרויקט", facts, ""]
    out.append(BLOCK_END)
    return "\n".join(out)


def upsert_block(path, block):
    old = read_text(path) if os.path.exists(path) else None
    if old is None:
        new = f"# {os.path.basename(path)}\n\n{block}\n"
    elif BLOCK_BEGIN in old and BLOCK_END in old:
        start = old.index(BLOCK_BEGIN)
        end = old.index(BLOCK_END) + len(BLOCK_END)
        new = old[:start] + block + old[end:]
    else:
        new = old.rstrip("\r\n") + "\n\n" + block + "\n"
    if old is not None and new.replace("\r\n", "\n") == old.replace("\r\n", "\n"):
        return False
    write_text(path, new, like=old)
    return True


def ensure_import(path, target):
    line = "@" + target
    old = read_text(path) if os.path.exists(path) else None
    if old is not None and any(l.strip() == line for l in old.splitlines()):
        return False
    new = f"# {os.path.basename(path)}\n\n{line}\n" if old is None else old.rstrip("\r\n") + f"\n\n{line}\n"
    write_text(path, new, like=old)
    return True


def cmd_block(args):
    root = os.path.abspath(args.root)
    cfg = load_config(root)
    block = build_block(root, cfg)
    if block is None:
        print("block: nothing published and no tl-agents facts in PROJECT_CONTEXT.md — skipped")
        return 0
    agents = os.path.join(root, cfg["agents_file"])
    print(f"{cfg['agents_file']}: {'updated' if upsert_block(agents, block) else 'unchanged'}")
    if cfg.get("claude_md_import") and os.path.basename(agents).upper() != "CLAUDE.MD":
        claude_md = os.path.join(root, "CLAUDE.md")
        if ensure_import(claude_md, cfg["agents_file"]):
            print(f"CLAUDE.md: added @{cfg['agents_file']}")
    return 0


def main(argv=None):
    configure_stdout()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("index", "block"):
        sub.add_parser(name).add_argument("--root", default=".")
    p = sub.add_parser("check")
    p.add_argument("files", nargs="+")
    p.add_argument("--root", default=".")
    p = sub.add_parser("publish")
    p.add_argument("files", nargs="+")
    p.add_argument("--root", default=".")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--force", action="store_true")
    args = ap.parse_args(argv)
    return {"index": cmd_index, "check": cmd_check, "publish": cmd_publish, "block": cmd_block}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
