#!/usr/bin/env python3
"""Offline SVG charts for analysis reports, from the CSV result of a saved query.
Standard library only (Python 3.8+). Light and dark theme, readable when printed.

  python an_chart.py bar  data.csv --x month --y share [--title T] [--unit %] [--out chart.svg]
  python an_chart.py line data.csv --x month --y before,after [--lo lo --hi hi] [--title T] [--out chart.svg]

bar   one series, one bar per row (a value label on each bar)
line  one or more series over x; --lo/--hi draw the confidence band of the first series
--target V draws a horizontal reference line (a goal or a guardrail, e.g. 2 for "error ≤ 2%").
The SVG goes to --out (default: next to the CSV, same name) and can be pasted into an HTML report.
"""
import argparse
import csv
import html
import os
import sys

W, H = 760, 360
LEFT, RIGHT, TOP, BOTTOM = 64, 24, 44, 56
PALETTE = ["#2563eb", "#d97706", "#059669", "#7c3aed", "#dc2626"]
STYLE = """<style>
  .bg { fill: #ffffff; } .axis { stroke: #94a3b8; stroke-width: 1; } .grid { stroke: #e2e8f0; stroke-width: 1; }
  .lbl { fill: #334155; font: 12px system-ui, sans-serif; } .ttl { fill: #0f172a; font: 600 14px system-ui, sans-serif; }
  .val { fill: #0f172a; font: 11px system-ui, sans-serif; } .band { opacity: 0.18; } .tgt { stroke: #dc2626; stroke-dasharray: 6 4; }
  @media (prefers-color-scheme: dark) {
    .bg { fill: #0f172a; } .grid { stroke: #1e293b; } .lbl { fill: #cbd5e1; } .ttl, .val { fill: #f1f5f9; }
  }
</style>"""


def configure_stdout():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass


def read_rows(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def num(value):
    text = str(value).strip().replace("%", "").replace(" ", "").replace(" ", "")
    if text.count(",") == 1 and "." not in text:
        text = text.replace(",", ".")
    return float(text.replace(",", "")) if text else None


def nice_max(value):
    if value <= 0:
        return 1.0
    step = 10 ** (len(str(int(value))) - 1) if value >= 1 else 0.1
    top = step
    while top < value * 1.05:
        top += step / 2 if step >= 1 else step
    return top


def fmt(value, unit=""):
    text = f"{value:,.2f}".rstrip("0").rstrip(".") if abs(value) < 1000 else f"{value:,.0f}"
    return text.replace(",", " ") + unit


def frame(title, ymax, unit, xs, target=None):
    pw, ph = W - LEFT - RIGHT, H - TOP - BOTTOM
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" role="img" aria-label="{html.escape(title)}">',
           STYLE, f'<rect class="bg" width="{W}" height="{H}"/>',
           f'<text class="ttl" x="{LEFT}" y="24">{html.escape(title)}</text>']
    for i in range(5):
        v = ymax * i / 4
        y = TOP + ph - ph * i / 4
        out.append(f'<line class="grid" x1="{LEFT}" y1="{y:.1f}" x2="{W - RIGHT}" y2="{y:.1f}"/>')
        out.append(f'<text class="lbl" x="{LEFT - 8}" y="{y + 4:.1f}" text-anchor="end">{fmt(v, unit)}</text>')
    out.append(f'<line class="axis" x1="{LEFT}" y1="{TOP + ph}" x2="{W - RIGHT}" y2="{TOP + ph}"/>')
    step = max(1, len(xs) // 12)
    for i, x in enumerate(xs):
        if i % step == 0:
            cx = LEFT + pw * (i + 0.5) / len(xs)
            out.append(f'<text class="lbl" x="{cx:.1f}" y="{TOP + ph + 18}" text-anchor="middle">{html.escape(x)}</text>')
    if target is not None:
        y = TOP + ph - ph * target / ymax
        out.append(f'<line class="tgt" x1="{LEFT}" y1="{y:.1f}" x2="{W - RIGHT}" y2="{y:.1f}"/>')
        out.append(f'<text class="lbl" x="{W - RIGHT}" y="{y - 6:.1f}" text-anchor="end">{fmt(target, unit)}</text>')
    return out, pw, ph


def bar_chart(rows, x, y, title, unit="", target=None):
    xs = [r[x] for r in rows]
    vals = [num(r[y]) or 0.0 for r in rows]
    ymax = nice_max(max(vals + [target or 0]))
    out, pw, ph = frame(title, ymax, unit, xs, target)
    slot = pw / max(len(xs), 1)
    for i, v in enumerate(vals):
        h = ph * v / ymax
        bx = LEFT + slot * i + slot * 0.15
        out.append(f'<rect x="{bx:.1f}" y="{TOP + ph - h:.1f}" width="{slot * 0.7:.1f}" height="{h:.1f}" '
                   f'fill="{PALETTE[0]}" rx="2"><title>{html.escape(xs[i])}: {fmt(v, unit)}</title></rect>')
        if len(xs) <= 24:
            out.append(f'<text class="val" x="{bx + slot * 0.35:.1f}" y="{TOP + ph - h - 5:.1f}" '
                       f'text-anchor="middle">{fmt(v, unit)}</text>')
    out.append("</svg>")
    return "\n".join(out) + "\n"


def line_chart(rows, x, ys, title, unit="", lo=None, hi=None, target=None):
    xs = [r[x] for r in rows]
    series = {y: [num(r[y]) for r in rows] for y in ys}
    values = [v for s in series.values() for v in s if v is not None]
    if hi:
        values += [num(r[hi]) for r in rows if num(r[hi]) is not None]
    ymax = nice_max(max(values + [target or 0]))
    out, pw, ph = frame(title, ymax, unit, xs, target)

    def pt(i, v):
        return LEFT + pw * (i + 0.5) / len(xs), TOP + ph - ph * v / ymax

    if lo and hi:
        upper = [pt(i, num(r[hi])) for i, r in enumerate(rows) if num(r[hi]) is not None]
        lower = [pt(i, num(r[lo])) for i, r in enumerate(rows) if num(r[lo]) is not None]
        poly = " ".join(f"{a:.1f},{b:.1f}" for a, b in upper + lower[::-1])
        out.append(f'<polygon class="band" fill="{PALETTE[0]}" points="{poly}"/>')
    for k, (name, vals) in enumerate(series.items()):
        color = PALETTE[k % len(PALETTE)]
        pts = [pt(i, v) for i, v in enumerate(vals) if v is not None]
        out.append(f'<polyline fill="none" stroke="{color}" stroke-width="2.5" '
                   f'points="{" ".join(f"{a:.1f},{b:.1f}" for a, b in pts)}"/>')
        for (a, b), v in zip(pts, [v for v in vals if v is not None]):
            out.append(f'<circle cx="{a:.1f}" cy="{b:.1f}" r="3" fill="{color}"><title>{html.escape(name)}: '
                       f'{fmt(v, unit)}</title></circle>')
        lx = LEFT + 140 * k
        out.append(f'<rect x="{lx}" y="{H - 18}" width="12" height="4" fill="{color}"/>')
        out.append(f'<text class="lbl" x="{lx + 18}" y="{H - 13}">{html.escape(name)}</text>')
    out.append("</svg>")
    return "\n".join(out) + "\n"


def main(argv=None):
    configure_stdout()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("kind", choices=("bar", "line"))
    ap.add_argument("csv")
    ap.add_argument("--x", required=True)
    ap.add_argument("--y", required=True, help="column (bar) or comma-separated columns (line)")
    ap.add_argument("--lo")
    ap.add_argument("--hi")
    ap.add_argument("--target", type=float)
    ap.add_argument("--title", default="")
    ap.add_argument("--unit", default="")
    ap.add_argument("--out")
    args = ap.parse_args(argv)
    rows = read_rows(args.csv)
    if not rows:
        print("ERROR: the CSV has no rows", file=sys.stderr)
        return 2
    missing = [c for c in [args.x] + args.y.split(",") + [c for c in (args.lo, args.hi) if c] if c not in rows[0]]
    if missing:
        print(f"ERROR: columns not in the CSV: {', '.join(missing)} (have: {', '.join(rows[0])})", file=sys.stderr)
        return 2
    title = args.title or args.y
    if args.kind == "bar":
        svg = bar_chart(rows, args.x, args.y, title, args.unit, args.target)
    else:
        svg = line_chart(rows, args.x, args.y.split(","), title, args.unit, args.lo, args.hi, args.target)
    out = args.out or os.path.splitext(args.csv)[0] + ".svg"
    with open(out, "w", encoding="utf-8") as f:
        f.write(svg)
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
