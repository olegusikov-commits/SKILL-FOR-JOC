#!/usr/bin/env python3
"""Specification tool for the tl-requirements skill. Standard library only (Python 3.8+).

Commands:
  new SLUG [--title T] [--root DIR]      create .claude/tl-memory/spec/SPEC-nnn-SLUG/REQUEST.md
                                         from references/intake-form.md (next free SPEC number)
  lint FILE [--json]                     ids, traceability REQ <-> AC, decision tables, open
                                         questions, placeholders, vague words; exit 1 on errors
  render FILE [--out HTML] [--lang L]    self-contained HTML: RTL for Hebrew, light/dark, print,
                                         no external resources; Word can open and save it

Conventions (see references/spec-template.md): line 1 `<!-- tl-meta: k=v; ... -->`; requirements
are table rows whose first cell is REQ-nnn, acceptance criteria rows start with AC-nnn and name
their REQ, questions start with Q-n; a decision table follows a heading containing DT-n and has
an "else" (אחרת) row.
"""
import argparse
import datetime
import html
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
INTAKE = os.path.join(HERE, "..", "references", "intake-form.md")

META_RE = re.compile(r"<!--\s*tl-meta:\s*(.*?)\s*-->", re.S)
ID_RE = re.compile(r"(?<![\w-])(REQ-\d{3}|AC-\d{3}|DT-\d+|Q-\d+|ADR-\d{3}|SPEC-\d{3})(?![\w-])")
ELSE_RE = re.compile(r"(?<!\w)(אחרת|כל מקרה אחר|כל השאר|else|otherwise)(?!\w)", re.I)
VAGUE_WORDS = ["מהיר", "בערך", "סביר", "וכו'", "וכד'", "לפי הצורך", "במידת הצורך", "במידת האפשר",
               "בדרך כלל", "גמיש", "ידידותי", "fast", "reasonable", "appropriate",
               "as needed", "etc.", "user-friendly"]
VAGUE_RE = re.compile(r"(?<!\w)[והבלמשכ]{0,2}(" + "|".join(re.escape(w) for w in VAGUE_WORDS) + r")(?!\w)",
                      re.I)
PLACEHOLDER_RE = re.compile(r"<(?![=<>\s!/-]|(?:br|b|i|em|strong|sub|sup|code)\b)[^<>\n]{1,60}>|"
                            r"\bYYYY-MM-DD\b|\b(?:SPEC|REQ|AC|ADR)-N+\b|\bTBD\b|\bTODO\b|\?\?\?")
REQUIRED_SECTIONS = ["מטרה", "היקף", "דרישות", "כללים", "תרחישי קבלה", "השפעה", "שאלות"]
ID_HEADERS = {"מזהה", "id", "מס' זיהוי"}  # a table whose first column is the id defines those ids


def configure_stdout():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass


def read_text(path):
    with open(path, encoding="utf-8-sig") as f:
        return f.read()


def write_text(path, text):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
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


# ------------------------------------------------------------------ markdown structure
def split_cells(line):
    """Split a table row on unescaped pipes outside code spans."""
    cells, cur, in_code, i = [], "", False, 0
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|") and not s.endswith("\\|"):
        s = s[:-1]
    while i < len(s):
        ch = s[i]
        if ch == "\\" and i + 1 < len(s) and s[i + 1] == "|":
            cur += "|"
            i += 2
            continue
        if ch == "`":
            in_code = not in_code
        if ch == "|" and not in_code:
            cells.append(cur.strip())
            cur = ""
        else:
            cur += ch
        i += 1
    cells.append(cur.strip())
    return cells


def is_separator(line):
    return bool(re.match(r"^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$", line))


def scan(text):
    """Line-level scan outside fenced code: headings and tables with their line numbers."""
    lines = text.splitlines()
    headings, tables, prose = [], [], []
    in_fence, in_comment, i = False, False, 0
    while i < len(lines):
        line = lines[i]
        if line.strip().startswith("```"):
            in_fence = not in_fence
            i += 1
            continue
        if in_fence:
            i += 1
            continue
        if in_comment or line.strip().startswith("<!--"):
            in_comment = "-->" not in line
            i += 1
            continue
        m = re.match(r"^(#{1,6})\s+(.*?)\s*#*\s*$", line)
        if m:
            headings.append((i + 1, len(m.group(1)), m.group(2)))
            i += 1
            continue
        if line.strip().startswith("|") and i + 1 < len(lines) and is_separator(lines[i + 1]):
            start = i
            header = split_cells(line)
            rows = []
            i += 2
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append((i + 1, split_cells(lines[i])))
                i += 1
            tables.append({"line": start + 1, "header": header, "rows": rows,
                           "heading": headings[-1] if headings else None})
            continue
        prose.append((i + 1, line))
        i += 1
    return headings, tables, prose


def strip_md(cell):
    return re.sub(r"[*`_]", "", cell).strip()


def defines_ids(header):
    return bool(header) and strip_md(header[0]).lower() in ID_HEADERS


# ------------------------------------------------------------------ new
def published_dir(root, doc_type, default):
    cfg_path = os.path.join(root, ".claude", "tl-memory", "publish.json")
    cfg = {}
    if os.path.exists(cfg_path):
        try:
            cfg = json.loads(read_text(cfg_path))
        except ValueError:
            cfg = {}
    folder = cfg.get("folders", {}).get(doc_type, default)
    return os.path.join(root, cfg.get("docs_root", "docs"), folder)


def next_spec_number(root):
    numbers = [0]
    for folder in (os.path.join(root, ".claude", "tl-memory", "spec"), published_dir(root, "spec", "specs")):
        if os.path.isdir(folder):
            for name in os.listdir(folder):
                m = re.match(r"SPEC-(\d+)", name)
                if m:
                    numbers.append(int(m.group(1)))
    return max(numbers) + 1


def cmd_new(args):
    root = os.path.abspath(args.root)
    slug = re.sub(r"[^a-z0-9]+", "-", args.slug.lower()).strip("-")
    if not slug:
        print("ERROR: slug must contain latin letters or digits", file=sys.stderr)
        return 2
    template = read_text(INTAKE)
    m = re.search(r"<!-- template:begin -->\n(.*?)<!-- template:end -->", template, re.S)
    if not m:
        print(f"ERROR: template markers not found in {INTAKE}", file=sys.stderr)
        return 2
    spec_id = f"SPEC-{next_spec_number(root):03d}"
    folder = os.path.join(root, ".claude", "tl-memory", "spec", f"{spec_id}-{slug}")
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, "REQUEST.md")
    if os.path.exists(path):
        print(f"ERROR: {path} already exists", file=sys.stderr)
        return 2
    text = (m.group(1).replace("SPEC-NNN", spec_id)
            .replace("YYYY-MM-DD", datetime.date.today().isoformat())
            .replace("TITLE", (args.title or slug).replace(";", ",")))
    write_text(path, text)
    print(path)
    return 0


# ------------------------------------------------------------------ lint
def lint(text):
    findings = []

    def add(level, line, msg):
        findings.append({"level": level, "line": line, "message": msg})

    meta = parse_meta(text)
    if meta is None:
        add("ERROR", 1, "no tl-meta comment in the first lines")
        meta = {}
    else:
        for key in ("type", "id", "status", "date", "area", "title"):
            if not meta.get(key):
                add("ERROR", 1, f"tl-meta: '{key}' is empty")
        if meta.get("type") and meta["type"] != "spec":
            add("WARN", 1, f"tl-meta type is '{meta['type']}', expected 'spec'")

    headings, tables, prose = scan(text)
    h1 = next((h for h in headings if h[1] == 1), None)
    if h1 and meta.get("id") and meta["id"] not in h1[2]:
        add("WARN", h1[0], f"title does not contain the id {meta['id']}")

    reqs, acs, dts, questions = {}, {}, {}, {}
    ac_reqs, req_acs = {}, {}
    for t in tables:
        if not defines_ids(t["header"]):
            continue
        for line_no, cells in t["rows"]:
            first = strip_md(cells[0]) if cells else ""
            for kind, store in (("REQ", reqs), ("AC", acs), ("Q", questions)):
                if re.fullmatch(kind + (r"-\d+" if kind == "Q" else r"-\d{3}"), first):
                    if first in store:
                        add("ERROR", line_no, f"{first} is defined twice (also line {store[first]})")
                    store[first] = line_no
                    rest = " ".join(cells[1:])
                    if kind == "AC":
                        ac_reqs[first] = set(re.findall(r"REQ-\d{3}", rest))
                    if kind == "REQ":
                        req_acs[first] = set(re.findall(r"AC-\d{3}", rest))
                    if kind == "Q" and (len(cells) < 3 or not strip_md(cells[2])):
                        add("WARN", line_no, f"{first} has no proposed answer")
    for line_no, line in prose:
        m = re.match(r"^\s*[-*]\s+\**(REQ-\d{3})\**[\s:—-]", line)
        if m:
            reqs.setdefault(m.group(1), line_no)

    for line_no, level, title in headings:
        m = re.search(r"DT-\d+", title)
        if not m:
            continue
        if m.group(0) in dts:
            add("ERROR", line_no, f"{m.group(0)} is defined twice")
        table = next((t for t in tables if t["heading"] and t["heading"][0] == line_no), None)
        dts[m.group(0)] = line_no
        if table is None:
            add("ERROR", line_no, f"{m.group(0)} has no table under its heading")
            continue
        if not any(ELSE_RE.search(" ".join(cells)) for _, cells in table["rows"]):
            add("ERROR", table["line"], f"{m.group(0)} has no 'אחרת' (else) row")
        numbers = [strip_md(cells[0]) for _, cells in table["rows"] if cells]
        if numbers and all(n.isdigit() for n in numbers) and numbers != [str(k) for k in range(1, len(numbers) + 1)]:
            add("WARN", table["line"], f"{m.group(0)} rows are not numbered 1..n in order")

    for ac, refs in ac_reqs.items():
        if not refs:
            add("ERROR", acs[ac], f"{ac} does not name the requirement it verifies")
        for ref in sorted(refs - set(reqs)):
            add("ERROR", acs[ac], f"{ac} refers to {ref}, which is not defined")
    covered = set().union(*ac_reqs.values()) if ac_reqs else set()
    for req in sorted(set(reqs) - covered):
        add("ERROR", reqs[req], f"{req} has no acceptance criterion (no AC row names it)")
    for req, listed in req_acs.items():
        for ac in sorted(listed & set(acs)):
            if req not in ac_reqs.get(ac, set()):
                add("WARN", reqs[req], f"{req} lists {ac}, but {ac} does not name {req}")

    lines = text.splitlines()
    in_fence = False
    for no, line in enumerate(lines, 1):
        if line.strip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence or line.strip().startswith("<!--"):
            continue
        for ref in set(re.findall(r"(?<![\w-])((?:REQ|AC)-\d{3})(?![\w-])", line)):
            if ref.startswith("REQ") and ref not in reqs or ref.startswith("AC") and ref not in acs:
                add("ERROR", no, f"reference to {ref}, which is not defined")
        prose_only = re.sub(r"`[^`]*`", "", line)
        for m in PLACEHOLDER_RE.finditer(prose_only):
            add("WARN", no, f"placeholder left: {m.group(0)}")
        for m in VAGUE_RE.finditer(prose_only):
            add("WARN", no, f"vague word without a number: '{m.group(1)}'")

    sources = len(re.findall(r"\[מקור:", text))
    pending = len(re.findall(r"ממתין לאישור", text))
    if reqs and sources == 0:
        add("WARN", 1, "no [מקור: …] tags — where do the facts come from?")
    if len(questions) > 5:
        add("WARN", 1, f"{len(questions)} open questions — keep at most 5 per round")
    if meta.get("status") == "approved" and pending:
        add("WARN", 1, f"status is approved but {pending} assumption(s) still wait for approval")
    titles = " ".join(h[2] for h in headings)
    for section in REQUIRED_SECTIONS:
        if section not in titles:
            add("WARN", 1, f"no section about '{section}'")

    findings.sort(key=lambda f: (f["level"] != "ERROR", f["line"]))
    summary = {"req": len(reqs), "ac": len(acs), "dt": len(dts), "questions": len(questions),
               "sources": sources, "pending_assumptions": pending,
               "errors": sum(f["level"] == "ERROR" for f in findings),
               "warnings": sum(f["level"] == "WARN" for f in findings)}
    return findings, summary


def cmd_lint(args):
    findings, summary = lint(read_text(args.file))
    if args.json:
        print(json.dumps({"findings": findings, "summary": summary}, ensure_ascii=False, indent=2))
    else:
        for f in findings:
            print(f"{f['level']:5}  line {f['line']:>4}  {f['message']}")
        print("REQ {req} · AC {ac} · DT {dt} · questions {questions} · sources {sources} · "
              "errors {errors} · warnings {warnings}".format(**summary))
    return 1 if summary["errors"] else 0


# ------------------------------------------------------------------ render
LABELS = {
    "he": {"dir": "rtl", "toc": "תוכן", "generated": "נוצר מתוך", "area": "תחום",
           "types": {"spec": "אפיון", "request": "טופס דרישה", "spec-check": "בדיקת אפיון"},
           "status": {"draft": "טיוטה", "review": "לבדיקה", "approved": "מאושר", "accepted": "התקבל",
                      "superseded": "הוחלף", "deprecated": "בוטל", "final": "סופי"}},
    "ru": {"dir": "ltr", "toc": "Содержание", "generated": "Создано из", "area": "Область",
           "types": {"spec": "Спецификация", "request": "Запрос", "spec-check": "Проверка спецификации"},
           "status": {"draft": "черновик", "review": "на проверке", "approved": "утверждено",
                      "accepted": "принято", "superseded": "заменено", "deprecated": "отменено",
                      "final": "финальный"}},
    "en": {"dir": "ltr", "toc": "Contents", "generated": "Generated from", "area": "Area",
           "types": {"spec": "Specification", "request": "Request", "spec-check": "Spec check"},
           "status": {}},
}
STATUS_CLASS = {"draft": "s-draft", "review": "s-review", "approved": "s-ok", "accepted": "s-ok",
                "final": "s-ok", "superseded": "s-old", "deprecated": "s-old"}

CSS = """
:root{--paper:#f5f6f8;--card:#fff;--ink:#1c2733;--muted:#5a6776;--line:#c8d0da;--accent:#1d5ea8;
--accent-soft:#e4edf8;--stop:#b9450f;--stop-soft:#fbe8dc;--ok:#2b7a4b;--ok-soft:#e1f1e7;--warn:#8a6100;
--warn-soft:#fbf0d2;--code-bg:#eceff3;--font-body:"Segoe UI",Arial,"Noto Sans Hebrew","Noto Sans",system-ui,sans-serif;
--font-mono:Consolas,"Cascadia Mono","Courier New",monospace;color-scheme:light}
@media (prefers-color-scheme:dark){:root{--paper:#0f151c;--card:#16202a;--ink:#e2e8ef;--muted:#9ba7b5;
--line:#2d3b4a;--accent:#6ea8ea;--accent-soft:#19304a;--stop:#f08c52;--stop-soft:#3a2316;--ok:#6cc590;
--ok-soft:#16321f;--warn:#e8c06a;--warn-soft:#332a12;--code-bg:#1d2935;color-scheme:dark}}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);font-family:var(--font-body);font-size:16px;line-height:1.6}
.page{max-width:1080px;margin:0 auto;padding:40px 16px 80px}
header.intro{display:grid;gap:12px;margin-bottom:28px}
.eyebrow{font-family:var(--font-mono);font-size:.78rem;letter-spacing:.06em;color:var(--accent);display:flex;gap:10px;flex-wrap:wrap;align-items:center}
h1{font-size:clamp(1.7rem,4.5vw,2.4rem);line-height:1.2;margin:0}
h2{font-size:1.45rem;margin:44px 0 14px;padding-top:12px;border-top:2px solid var(--ink)}
h3{font-size:1.12rem;margin:26px 0 10px}
h4{font-size:1rem;margin:18px 0 8px}
p{margin:0 0 12px;max-width:78ch}
ul,ol{margin:0 0 12px;padding-inline-start:24px}
li{margin:3px 0}
a{color:var(--accent)}
code{font-family:var(--font-mono);font-size:.86em;background:var(--code-bg);padding:1px 5px;border-radius:4px;direction:ltr;unicode-bidi:isolate;overflow-wrap:anywhere}
pre{background:var(--code-bg);border-radius:6px;padding:12px 14px;overflow-x:auto;direction:ltr;text-align:left;font-size:.85rem}
pre code{background:none;padding:0}
hr{border:none;border-top:1px solid var(--line);margin:24px 0}
.chip{font-family:var(--font-body);font-size:.75rem;letter-spacing:0;border-radius:999px;padding:2px 10px;border:1px solid var(--line);background:var(--card);color:var(--muted)}
.s-ok{background:var(--ok-soft);border-color:var(--ok);color:var(--ok)}
.s-review{background:var(--warn-soft);border-color:var(--warn);color:var(--warn)}
.s-old{background:var(--stop-soft);border-color:var(--stop);color:var(--stop)}
.meta-line{color:var(--muted);font-size:.92rem}
nav.toc{display:flex;flex-wrap:wrap;gap:6px 16px;font-size:.92rem;padding:12px 0;border-top:1px solid var(--line);border-bottom:1px solid var(--line)}
nav.toc a{text-decoration:none}
.table-wrap{overflow-x:auto;border:1px solid var(--line);border-radius:6px;background:var(--card);margin:0 0 16px}
table{border-collapse:collapse;width:100%;font-size:.93rem}
th,td{text-align:start;padding:8px 12px;border-bottom:1px solid var(--line);vertical-align:top}
th{font-size:.78rem;letter-spacing:.03em;color:var(--muted);font-weight:600;background:var(--paper)}
tr:last-child td{border-bottom:none}
table.dt tr.else td{background:var(--accent-soft)}
table tr.new td{background:var(--ok-soft)}
table tr.changed td{background:var(--warn-soft)}
table.facts th{display:none}
table.facts td:first-child{width:180px;color:var(--muted)}
.id{font-family:var(--font-mono);font-size:.8rem;font-weight:600;border-radius:4px;padding:1px 6px;white-space:nowrap;direction:ltr;unicode-bidi:isolate;text-decoration:none;background:var(--accent-soft);color:var(--accent)}
.id-ac{background:var(--ok-soft);color:var(--ok)}
.id-dt{background:var(--warn-soft);color:var(--warn)}
.id-q{background:var(--stop-soft);color:var(--stop)}
.src{font-size:.78rem;color:var(--muted);border:1px solid var(--line);border-radius:4px;padding:0 5px;white-space:normal}
.assume{font-size:.78rem;color:var(--warn);background:var(--warn-soft);border-radius:4px;padding:0 5px}
.filled{font-size:.78rem;color:var(--accent);border:1px dashed var(--accent);border-radius:4px;padding:0 5px}
blockquote{margin:0 0 16px;border-inline-start:4px solid var(--accent);background:var(--accent-soft);padding:10px 16px;border-radius:4px}
blockquote p:last-child{margin-bottom:0}
.cb{font-family:var(--font-mono)}
figure.plate{margin:0 0 16px;background:var(--card);border:1px solid var(--line);border-radius:6px;overflow-x:auto}
figure.plate svg{display:block;width:100%;height:auto;min-width:640px}
svg text{font-family:var(--font-body);fill:var(--ink)}[dir="rtl"] svg text{direction:rtl}[dir="rtl"] svg text.ltr{direction:ltr}
svg .t-title{font-weight:600;font-size:15px}svg .t-sub{font-size:12px;fill:var(--muted)}
svg .t-mono{font-family:var(--font-mono);font-size:11px}svg .t-label{font-family:var(--font-mono);font-size:11px;fill:var(--accent)}
svg .t-stop{fill:var(--stop)}svg .t-ok{fill:var(--ok)}
svg .box{fill:var(--card);stroke:var(--line);stroke-width:1.2}svg .box-accent{fill:var(--accent-soft);stroke:var(--accent);stroke-width:1.2}
svg .box-stop{fill:var(--stop-soft);stroke:var(--stop);stroke-width:1.5}svg .box-ok{fill:var(--ok-soft);stroke:var(--ok);stroke-width:1.2}
svg .wire{fill:none;stroke:var(--muted);stroke-width:1.4}svg .wire-dash{fill:none;stroke:var(--muted);stroke-width:1.2;stroke-dasharray:4 4}
svg .wire-stop{fill:none;stroke:var(--stop);stroke-width:1.4}svg .head{fill:var(--muted)}svg .head-stop{fill:var(--stop)}
footer{margin-top:48px;color:var(--muted);font-size:.8rem;border-top:1px solid var(--line);padding-top:10px}
@media print{:root{--paper:#fff;--card:#fff;--ink:#000;--muted:#444;--line:#999;color-scheme:light}
body{font-size:11pt}.page{max-width:none;padding:0}nav.toc{display:none}h2{break-after:avoid}tr{break-inside:avoid}}
"""


class Inline:
    """Inline markdown -> HTML with a stash, so generated markup is never re-processed."""

    def __init__(self, defined):
        self.defined = defined
        self.stash = []

    def keep(self, markup):
        self.stash.append(markup)
        return f"\x00{len(self.stash) - 1}\x00"

    def id_html(self, ident, define=False):
        kind = ident.split("-")[0].lower()
        cls = f"id id-{kind}"
        if define:
            return f'<span class="{cls}" id="{ident}">{ident}</span>'
        if ident in self.defined:
            return f'<a class="{cls}" href="#{ident}">{ident}</a>'
        return f'<span class="{cls}">{ident}</span>'

    def render(self, text, define_first_id=False):
        out = []
        pos = 0
        for m in re.finditer(r"(`+)(.+?)\1", text):
            out.append(self._plain(text[pos:m.start()], define_first_id and pos == 0))
            out.append(self.keep(f"<code>{html.escape(m.group(2).strip(), quote=False)}</code>"))
            pos = m.end()
            define_first_id = False
        out.append(self._plain(text[pos:], define_first_id))
        result = "".join(out)
        while "\x00" in result:
            result = re.sub(r"\x00(\d+)\x00", lambda m: self.stash[int(m.group(1))], result)
        return result

    def _plain(self, text, define_first_id):
        t = html.escape(text, quote=False)
        t = re.sub(r"&lt;br\s*/?&gt;", lambda m: self.keep("<br>"), t)
        t = re.sub(r"!\[([^\]]*)\]\(([^)\s]+)\)",
                   lambda m: self.keep(f'<img alt="{m.group(1)}" src="{html.escape(m.group(2))}">'), t)
        t = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)",
                   lambda m: self.keep(f'<a href="{html.escape(m.group(2))}">{self._emph(m.group(1))}</a>'), t)
        t = re.sub(r"\[(מקור:[^\]]+)\]", lambda m: self.keep(f'<span class="src">{m.group(1)}</span>'), t)
        t = re.sub(r"\[(הנחה[^\]]*)\]", lambda m: self.keep(f'<span class="assume">{m.group(1)}</span>'), t)
        t = re.sub(r"\[(הושלם ע\"י המנתח)\]", lambda m: self.keep(f'<span class="filled">{m.group(1)}</span>'), t)
        t = re.sub(r"^\[ \]\s", lambda m: self.keep('<span class="cb">☐</span> '), t)
        t = re.sub(r"^\[[xX]\]\s", lambda m: self.keep('<span class="cb">☑</span> '), t)
        first = [define_first_id]

        def ident(m):
            define = first[0] and m.start() == len(t) - len(t.lstrip(" *"))
            first[0] = False
            return self.keep(self.id_html(m.group(1), define))
        t = ID_RE.sub(ident, t)
        return self._emph(t)

    @staticmethod
    def _emph(t):
        t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
        return re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", t)


def slugify(text, used):
    base = re.sub(r"[^\w֐-׿Ѐ-ӿ]+", "-", strip_md(text)).strip("-").lower() or "s"
    slug, n = base, 2
    while slug in used:
        slug, n = f"{base}-{n}", n + 1
    used.add(slug)
    return slug


LIST_RE = re.compile(r"^(\s*)([-*+]|\d+[.)])\s+(.*)$")


def render_list(lines, i, inline):
    first = LIST_RE.match(lines[i])
    indent = len(first.group(1))
    ordered = first.group(2)[0].isdigit()
    items = []
    while i < len(lines):
        line = lines[i]
        m = LIST_RE.match(line)
        if not line.strip():
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            nxt = LIST_RE.match(lines[j]) if j < len(lines) else None
            if nxt and len(nxt.group(1)) >= indent:
                i = j
                continue
            break
        if m and len(m.group(1)) > indent and items:
            sub, i = render_list(lines, i, inline)
            items[-1][1].append(sub)
            continue
        if m and len(m.group(1)) == indent and m.group(2)[0].isdigit() == ordered:
            items.append([m.group(3), []])
            i += 1
            continue
        if not m and items and (len(line) - len(line.lstrip())) > indent:
            items[-1][0] += " " + line.strip()
            i += 1
            continue
        break
    tag = "ol" if ordered else "ul"
    body = "".join(f"<li>{inline.render(text)}{''.join(subs)}</li>" for text, subs in items)
    return f"<{tag}>{body}</{tag}>", i


def render_table(header, rows, inline, classes):
    define = defines_ids(header)
    kinds = {re.sub(r"-\d+$", "", strip_md(c[0])) for c in rows if c and ID_RE.fullmatch(strip_md(c[0]))}
    cls = list(classes) + [f"t-{k.lower()}" for k in sorted(kinds)]
    head = "".join(f"<th>{inline.render(c)}</th>" for c in header)
    body = []
    for cells in rows:
        joined = " ".join(cells)
        row_cls = []
        if "dt" in classes and ELSE_RE.search(joined):
            row_cls.append("else")
        if "(חדש)" in joined:
            row_cls.append("new")
        if "(שונה)" in joined:
            row_cls.append("changed")
        tds = "".join(f"<td>{inline.render(c, define_first_id=(k == 0 and define))}</td>"
                      for k, c in enumerate(cells))
        attr = f' class="{" ".join(row_cls)}"' if row_cls else ""
        body.append(f"<tr{attr}>{tds}</tr>")
    attr = f' class="{" ".join(cls)}"' if cls else ""
    return (f'<div class="table-wrap"><table{attr} border="1" cellpadding="6">'
            f"<thead><tr>{head}</tr></thead><tbody>{''.join(body)}</tbody></table></div>")


def render_blocks(lines, inline, toc, used, state):
    out, i = [], 0
    while i < len(lines):
        line = lines[i]
        s = line.strip()
        if s.startswith("```"):
            lang = s[3:].strip().lower()
            j = i + 1
            while j < len(lines) and not lines[j].strip().startswith("```"):
                j += 1
            code = "\n".join(lines[i + 1:j])
            if lang == "svg":
                out.append(f'<figure class="plate">{code}</figure>')
            else:
                out.append(f"<pre><code>{html.escape(code, quote=False)}</code></pre>")
            i = j + 1
            continue
        if not s:
            i += 1
            continue
        if s.startswith("<!--"):
            while i < len(lines) and "-->" not in lines[i]:
                i += 1
            i += 1
            continue
        m = re.match(r"^(#{1,6})\s+(.*?)\s*#*\s*$", line)
        if m:
            level, text = len(m.group(1)), m.group(2)
            if level == 1 and not state.get("title"):
                state["title"] = text
                state["after_h1"] = True
                i += 1
                continue
            dt = re.search(r"DT-\d+", text)
            slug = dt.group(0) if dt and dt.group(0) not in used else slugify(text, used)
            used.add(slug)
            if level == 2:
                toc.append((slug, text))
            state["dt"] = bool(re.search(r"DT-\d+", text))
            out.append(f'<h{level} id="{slug}">{inline.render(text)}</h{level}>')
            state["after_h1"] = False
            i += 1
            continue
        if s.startswith("|") and i + 1 < len(lines) and is_separator(lines[i + 1]):
            header = split_cells(line)
            rows = []
            i += 2
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(split_cells(lines[i]))
                i += 1
            classes = []
            if state.get("after_h1") and not any(strip_md(h) for h in header):
                classes.append("facts")
            if state.get("dt"):
                classes.append("dt")
                state["dt"] = False
            out.append(render_table(header, rows, inline, classes))
            state["after_h1"] = False
            continue
        if s.startswith(">"):
            quoted = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                quoted.append(re.sub(r"^\s*>\s?", "", lines[i]))
                i += 1
            out.append(f"<blockquote>{render_blocks(quoted, inline, [], used, {})}</blockquote>")
            continue
        if LIST_RE.match(line):
            block, i = render_list(lines, i, inline)
            out.append(block)
            continue
        if re.fullmatch(r"(-{3,}|\*{3,}|_{3,})", s):
            out.append("<hr>")
            i += 1
            continue
        para = []
        while i < len(lines):
            cur = lines[i]
            if (not cur.strip() or cur.strip().startswith(("```", "#", ">", "<!--")) or LIST_RE.match(cur)
                    or (cur.strip().startswith("|") and i + 1 < len(lines) and is_separator(lines[i + 1]))):
                break
            para.append(cur.strip())
            i += 1
        out.append(f"<p>{inline.render(' '.join(para))}</p>")
    return "".join(out)


def render(text, source_name, lang=None):
    meta = parse_meta(text) or {}
    lang = lang or meta.get("lang") or ("he" if re.search(r"[֐-׿]", text) else "en")
    labels = LABELS.get(lang, LABELS["en"])
    _, tables, _ = scan(text)
    defined = set()
    for t in tables:
        if defines_ids(t["header"]):
            defined.update(strip_md(c[0]) for _, c in t["rows"] if c and ID_RE.fullmatch(strip_md(c[0])))
    for heading in re.findall(r"(?m)^#{2,6}\s.*?(DT-\d+)", text):
        defined.add(heading)
    inline = Inline(defined)
    toc, used, state = [], set(), {}
    body = render_blocks(text.splitlines(), inline, toc, used, state)
    title = state.get("title") or meta.get("title") or source_name
    doc_type = meta.get("type", "")
    status = meta.get("status", "")
    eyebrow = [labels["types"].get(doc_type, doc_type)]
    if meta.get("version"):
        eyebrow.append(f"v{meta['version']}")
    if meta.get("date"):
        eyebrow.append(meta["date"])
    chip = ""
    if status:
        chip = (f'<span class="chip {STATUS_CLASS.get(status, "s-draft")}">'
                f'{html.escape(labels["status"].get(status, status))}</span>')
    eyebrow_html = " · ".join(html.escape(e) for e in eyebrow if e) + chip
    area = (f'<div class="meta-line">{labels["area"]}: {inline.render(meta["area"])}</div>'
            if meta.get("area") else "")
    toc_html = ""
    if toc:
        links = "".join(f'<a href="#{slug}">{inline.render(text)}</a>' for slug, text in toc)
        toc_html = f'<nav class="toc" aria-label="{labels["toc"]}">{links}</nav>'
    return (f'<!doctype html>\n<html lang="{lang}" dir="{labels["dir"]}">\n<head>\n<meta charset="utf-8">\n'
            f'<meta name="viewport" content="width=device-width, initial-scale=1">\n'
            f'<meta name="generator" content="tl-requirements spec_tool.py">\n'
            f"<title>{html.escape(strip_md(title))}</title>\n<style>{CSS}</style>\n</head>\n<body>\n"
            f'<div class="page">\n<header class="intro"><div class="eyebrow">{eyebrow_html}</div>'
            f"<h1>{inline.render(title)}</h1>{area}{toc_html}</header>\n<main>{body}</main>\n"
            f'<footer>{labels["generated"]} {html.escape(source_name)}</footer>\n</div>\n</body>\n</html>\n')


def cmd_render(args):
    text = read_text(args.file)
    out = args.out or os.path.splitext(args.file)[0] + ".html"
    write_text(out, render(text, os.path.basename(args.file), args.lang))
    print(out)
    return 0


def main(argv=None):
    configure_stdout()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("new")
    p.add_argument("slug")
    p.add_argument("--title")
    p.add_argument("--root", default=".")
    p = sub.add_parser("lint")
    p.add_argument("file")
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("render")
    p.add_argument("file")
    p.add_argument("--out")
    p.add_argument("--lang", choices=sorted(LABELS))
    args = ap.parse_args(argv)
    return {"new": cmd_new, "lint": cmd_lint, "render": cmd_render}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
