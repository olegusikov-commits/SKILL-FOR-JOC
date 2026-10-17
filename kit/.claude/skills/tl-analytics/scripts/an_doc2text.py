#!/usr/bin/env python3
"""Convert Office documents to plain text so they can be read in analysis.
Standard library only (Python 3.8+). Supports .docx, .xlsx, .pptx; .txt/.md/.csv are copied.
Old binary formats (.doc, .xls, .ppt) are not supported: save them as the new format first.

Usage: an_doc2text.py FILE [FILE ...] [--out OUT.txt] [--max-rows 200]
"""
import argparse
import posixpath
import re
import sys
import zipfile
import xml.etree.ElementTree as ET

NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
}
W = "{%s}" % NS["w"]


def _xml(z, name):
    return ET.fromstring(z.read(name))


def _paragraph_text(p):
    parts = []
    for node in p.iter():
        if node.tag == W + "t" and node.text:
            parts.append(node.text)
        elif node.tag == W + "tab":
            parts.append("\t")
        elif node.tag in (W + "br", W + "cr"):
            parts.append("\n")
    return "".join(parts)


def docx_to_text(path):
    with zipfile.ZipFile(path) as z:
        body = _xml(z, "word/document.xml").find("w:body", NS)
        lines = []
        for block in body:
            if block.tag == W + "p":
                style = block.find("w:pPr/w:pStyle", NS)
                text = _paragraph_text(block)
                if style is not None and style.get(W + "val", "").lower().startswith("heading") and text:
                    level = re.sub(r"\D", "", style.get(W + "val")) or "1"
                    text = "#" * min(int(level), 6) + " " + text
                lines.append(text)
            elif block.tag == W + "tbl":
                for row in block.iter(W + "tr"):
                    cells = [" ".join(_paragraph_text(p) for p in tc.iter(W + "p")).strip()
                             for tc in row.iter(W + "tc")]
                    lines.append("| " + " | ".join(cells) + " |")
                lines.append("")
        return "\n".join(lines)


def _col_index(ref):
    letters = re.match(r"[A-Z]+", ref).group(0)
    n = 0
    for ch in letters:
        n = n * 26 + ord(ch) - 64
    return n - 1


def xlsx_to_text(path, max_rows=200):
    with zipfile.ZipFile(path) as z:
        shared = []
        if "xl/sharedStrings.xml" in z.namelist():
            for si in _xml(z, "xl/sharedStrings.xml").findall("s:si", NS):
                shared.append("".join(t.text or "" for t in si.iter("{%s}t" % NS["s"])))
        rels = {r.get("Id"): r.get("Target")
                for r in _xml(z, "xl/_rels/workbook.xml.rels").findall("rel:Relationship", NS)}
        out = []
        for sheet in _xml(z, "xl/workbook.xml").find("s:sheets", NS):
            name = sheet.get("name")
            target = rels[sheet.get("{%s}id" % NS["r"])]
            target = target.lstrip("/") if target.startswith("/") else posixpath.normpath("xl/" + target)
            out.append(f"## Sheet: {name}")
            rows = _xml(z, target).iter("{%s}row" % NS["s"])
            for i, row in enumerate(rows):
                if i >= max_rows:
                    out.append(f"... (more rows not shown, use --max-rows)")
                    break
                values = {}
                for c in row.findall("s:c", NS):
                    t = c.get("t")
                    v = c.find("s:v", NS)
                    if t == "s" and v is not None:
                        val = shared[int(v.text)]
                    elif t == "inlineStr":
                        val = "".join(x.text or "" for x in c.iter("{%s}t" % NS["s"]))
                    else:
                        val = v.text if v is not None else ""
                    values[_col_index(c.get("r"))] = val
                if values:
                    width = max(values) + 1
                    out.append("| " + " | ".join(values.get(j, "") for j in range(width)) + " |")
            out.append("")
        return "\n".join(out)


def pptx_to_text(path):
    with zipfile.ZipFile(path) as z:
        slides = [n for n in z.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)]
        slides.sort(key=lambda n: int(re.search(r"(\d+)\.xml$", n).group(1)))
        out = []
        for i, name in enumerate(slides, 1):
            out.append(f"## Slide {i}")
            for p in _xml(z, name).iter("{%s}p" % NS["a"]):
                text = "".join(t.text or "" for t in p.iter("{%s}t" % NS["a"]))
                if text.strip():
                    out.append(text)
            out.append("")
        return "\n".join(out)


def convert(path, max_rows=200):
    low = path.lower()
    if low.endswith(".docx"):
        return docx_to_text(path)
    if low.endswith(".xlsx"):
        return xlsx_to_text(path, max_rows)
    if low.endswith(".pptx"):
        return pptx_to_text(path)
    if low.endswith((".txt", ".md", ".csv")):
        with open(path, encoding="utf-8-sig", errors="replace") as f:
            return f.read()
    raise ValueError(f"unsupported format: {path} (supported: .docx .xlsx .pptx .txt .md .csv)")


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="+")
    ap.add_argument("--out", help="write UTF-8 text to this file instead of stdout")
    ap.add_argument("--max-rows", type=int, default=200, help="max rows per Excel sheet")
    args = ap.parse_args(argv)
    chunks, status = [], 0
    for path in args.files:
        try:
            chunks.append(f"# File: {path}\n\n{convert(path, args.max_rows)}\n")
        except (ValueError, OSError, KeyError, zipfile.BadZipFile, ET.ParseError) as e:
            print(f"ERROR: {path}: {e}", file=sys.stderr)
            status = 1
    text = "\n".join(chunks)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text)
    else:
        print(text)
    return status


if __name__ == "__main__":
    sys.exit(main())
