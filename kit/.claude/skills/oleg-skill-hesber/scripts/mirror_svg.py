"""Mirror inline SVG diagrams horizontally for right-to-left (Hebrew) documents.

Author diagrams once with left-to-right coordinates, then run:

    python mirror_svg.py input.html output.html

Every <svg viewBox="0 0 W H"> in the file is mirrored (x -> W - x), except SVGs with the
attribute data-no-mirror. Supported geometry: rect, text, line, circle, ellipse, polygon,
polyline and path with absolute M/L/H/V/Z commands. Paths inside <defs> (arrow markers) are
left as they are, because markers with orient="auto-start-reverse" turn by themselves.

Text anchoring: the document's CSS sets `direction: rtl` on SVG text, so `text-anchor="start"`
already means "right edge" for Hebrew text and needs no change. Text with class "ltr"
(code, paths, Latin-only names) keeps left-to-right direction, so its start/end anchors are
swapped.
"""
import re
import sys

SVG_RE = re.compile(r"<svg\b[^>]*>.*?</svg>", re.S)
DEFS_RE = re.compile(r"<defs\b.*?</defs>", re.S)
TAG_RE = re.compile(r"<(rect|text|line|circle|ellipse|polygon|polyline|path)\b[^>]*>", re.S)
NUM = r"-?\d+(?:\.\d+)?"


def fmt(value):
    return str(int(value)) if float(value).is_integer() else f"{value:.2f}".rstrip("0").rstrip(".")


def get_attr(tag, name):
    m = re.search(rf'\s{name}="([^"]*)"', tag)
    return m.group(1) if m else None


def set_attr(tag, name, value):
    if get_attr(tag, name) is None:
        return re.sub(r"(/?>)$", f' {name}="{value}"\\1', tag, count=1)
    return re.sub(rf'(\s{name}=")[^"]*(")', rf"\g<1>{value}\g<2>", tag, count=1)


def mirror_path(d, width):
    tokens = re.findall(rf"[A-Za-z]|{NUM}", d)
    out, cmd, i = [], None, 0
    while i < len(tokens):
        tok = tokens[i]
        if re.fullmatch("[A-Za-z]", tok):
            cmd = tok
            if cmd not in "MLHVZz":
                raise ValueError(f"unsupported path command '{cmd}' in: {d}")
            out.append(cmd)
            i += 1
            continue
        if cmd in ("M", "L"):
            x, y = float(tokens[i]), float(tokens[i + 1])
            out.append(f"{fmt(width - x)},{fmt(y)}")
            i += 2
        elif cmd == "H":
            out.append(fmt(width - float(tok)))
            i += 1
        else:  # V or anything numeric after V
            out.append(tok)
            i += 1
    return " ".join(out)


def mirror_points(points, width):
    pairs = re.findall(rf"({NUM})\s*,\s*({NUM})", points)
    return " ".join(f"{fmt(width - float(x))},{y}" for x, y in pairs)


def mirror_tag(tag, name, width):
    if name == "rect":
        x = float(get_attr(tag, "x") or 0)
        w = float(get_attr(tag, "width") or 0)
        return set_attr(tag, "x", fmt(width - x - w))
    if name == "text":
        x = get_attr(tag, "x")
        if x is not None:
            tag = set_attr(tag, "x", fmt(width - float(x)))
        classes = (get_attr(tag, "class") or "").split()
        if "ltr" in classes:
            anchor = get_attr(tag, "text-anchor") or "start"
            swapped = {"start": "end", "end": "start"}.get(anchor, anchor)
            tag = set_attr(tag, "text-anchor", swapped)
        return tag
    if name == "line":
        for a in ("x1", "x2"):
            v = get_attr(tag, a)
            if v is not None:
                tag = set_attr(tag, a, fmt(width - float(v)))
        return tag
    if name in ("circle", "ellipse"):
        v = get_attr(tag, "cx")
        return set_attr(tag, "cx", fmt(width - float(v))) if v is not None else tag
    if name in ("polygon", "polyline"):
        return set_attr(tag, "points", mirror_points(get_attr(tag, "points"), width))
    if name == "path":
        return set_attr(tag, "d", mirror_path(get_attr(tag, "d"), width))
    return tag


def mirror_svg(svg):
    open_tag = svg[: svg.index(">") + 1]
    if "data-no-mirror" in open_tag:
        return svg
    view_box = get_attr(open_tag, "viewBox")
    if not view_box:
        raise ValueError("SVG without viewBox cannot be mirrored")
    width = float(view_box.split()[2])

    # protect <defs> (markers) from mirroring
    defs = DEFS_RE.findall(svg)
    body = DEFS_RE.sub("\0DEFS\0", svg)
    body = TAG_RE.sub(lambda m: mirror_tag(m.group(0), m.group(1), width), body)
    for block in defs:
        body = body.replace("\0DEFS\0", block, 1)
    return body


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(2)
    src, dst = sys.argv[1], sys.argv[2]
    with open(src, encoding="utf-8") as f:
        html = f.read()
    result, count = SVG_RE.subn(lambda m: mirror_svg(m.group(0)), html)
    with open(dst, "w", encoding="utf-8") as f:
        f.write(result)
    print(f"mirrored {count} svg block(s): {src} -> {dst}")


if __name__ == "__main__":
    main()
