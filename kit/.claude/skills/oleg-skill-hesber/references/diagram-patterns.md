# Diagram patterns and geometry rules

All patterns are drawn **left-to-right** in a `viewBox` 1000 units wide. For Hebrew, mirror them
with `scripts/mirror_svg.py` (see SKILL.md). Use only the CSS classes from `template.html` —
never literal colors.

## Geometry rules (prevent overlaps)

**Text width estimate** (multiply by number of characters, use the longest line):

| Class | Size | Latin / Cyrillic | Hebrew |
|---|---|---|---|
| `t-title` | 15px semibold | 8.5 | 8.0 |
| `t-sub` | 12px | 6.6 | 6.2 |
| `t-mono` | 11px | 6.7 | 6.7 |
| `t-band`, `t-label` | 10.5–11px mono, spacing | 7.2 | 7.0 |

- Box width ≥ longest text width + 32. If it does not fit: shorten the text, or use two lines.
- Box heights: one line 44 · title + subtitle 60 · title + two lines 86–96.
- Baselines inside a box at `y`: title `y+25`, subtitle `y+45`; three lines: `y+28`, `y+52`, `y+72`.
- Text inside boxes: `text-anchor="middle"` at the box center whenever possible — it survives
  mirroring and RTL without surprises. Long left-aligned lines: `text-anchor="start"` at
  `box.x + 16`.
- Horizontal gap between boxes 20–30; vertical gap between rows ≥ 40 (more if a label sits there).
- Arrows: orthogonal only (`M`/`L`/`H`/`V`), never through a box, end 4 units before the target
  edge (the marker tip covers it). Labels: 8 units above a horizontal wire, in an empty corridor,
  never on top of a box.
- Keep 20 units free on all sides of the viewBox; outermost labels need room too.
- One question per diagram, ≤ 12 boxes. Split if bigger.
- Each SVG has `role="img"` and an `aria-label` describing it in one sentence, and a
  `<figcaption>` explaining how to read it (what solid/dashed/colored elements mean).
- Each SVG needs its own marker ids (`ah1`, `ah2`, …) — ids must be unique in the page.

**Semantic classes:** `box` = normal component · `box-accent` = entry point / focus ·
`box-ok` = result / safe zone · `box-stop` = stop, approval, danger, PROD ·
`frame` = boundary (process, server, system) · `wire` = main flow · `wire-dash` = secondary,
read-only, optional · `wire-stop` = loop back / error path.

## Arrow marker (put in each SVG's `<defs>`, unique id)
```html
<defs>
  <marker id="ah1" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="head" d="M0,0 L10,5 L0,10 z"/></marker>
  <marker id="ah1s" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="head-stop" d="M0,0 L10,5 L0,10 z"/></marker>
</defs>
```

---

## A · Layers / components — "What is it made of?"
A dashed frame for the system boundary, horizontal bands from "always / outer" to "rare /
inner", external systems in a column outside the frame, shared storage as a band below.
```html
<svg viewBox="0 0 1000 420" role="img" aria-label="…">
  <defs>…marker ah1…</defs>
  <rect class="frame" x="20" y="20" width="690" height="300" rx="8"/>
  <text class="t-band" x="36" y="40">SYSTEM NAME</text>

  <text class="t-band" x="40" y="66">1 · ENTRY POINTS</text>
  <rect class="box" x="40" y="74" width="650" height="50" rx="6"/>
  <text class="t-title" x="365" y="104" text-anchor="middle">API · Batch · UI</text>

  <text class="t-band" x="40" y="152">2 · BUSINESS LOGIC</text>
  <rect class="box-accent" x="40" y="160" width="320" height="60" rx="6"/>
  <text class="t-title" x="200" y="186" text-anchor="middle">Orders</text>
  <text class="t-mono ltr" x="200" y="206" text-anchor="middle">OrderService</text>
  <rect class="box-accent" x="370" y="160" width="320" height="60" rx="6"/>
  <text class="t-title" x="530" y="186" text-anchor="middle">Billing</text>
  <text class="t-mono ltr" x="530" y="206" text-anchor="middle">InvoiceService</text>
  <path class="wire" d="M365,124 L365,156" marker-end="url(#ah1)"/>

  <text class="t-band" x="40" y="248">3 · DATA ACCESS</text>
  <rect class="box" x="40" y="256" width="650" height="46" rx="6"/>
  <text class="t-sub" x="365" y="284" text-anchor="middle">repositories · stored procedures</text>

  <!-- external system, outside the frame -->
  <rect class="box" x="745" y="256" width="235" height="46" rx="6"/>
  <text class="t-title" x="862" y="284" text-anchor="middle">SQL Server</text>
  <path class="wire" d="M690,279 L741,279" marker-end="url(#ah1)"/>

  <!-- shared band below -->
  <rect class="box" x="20" y="350" width="960" height="50" rx="6"/>
  <text class="t-sub" x="500" y="380" text-anchor="middle">logs · monitoring · configuration</text>
</svg>
```

## B · Pipeline — "What happens step by step?"
Equal boxes in one row, numbered only if the order is real. Up to 5 per row (width 175–180,
gap 15–20). Details of one step: a dashed connector down to a wide detail box.
```html
<rect class="box-accent" x="20"  y="30" width="180" height="74" rx="6"/>
<text class="t-title" x="110" y="60" text-anchor="middle">1 · Read</text>
<text class="t-sub"   x="110" y="82" text-anchor="middle">input file</text>
<path class="wire" d="M200,67 L216,67" marker-end="url(#ah2)"/>
<rect class="box" x="220" y="30" width="180" height="74" rx="6"/>
…
<!-- detail of step 2 -->
<path class="wire-dash" d="M310,104 L310,140"/>
<rect class="box" x="220" y="140" width="560" height="110" rx="6"/>
<text class="t-band" x="236" y="162">WHAT HAPPENS IN STEP 2</text>
<text class="t-sub"  x="236" y="186">1. …</text>
```

## C · Decision flow — "Where are the decisions and loops?"
Start at the left middle, a diamond (`polygon`, half-width 80, half-height 55), branches as
lanes: upper lane = simple path, lower lanes = complex path. Loops back use `wire-stop`
above or below the lane, with a label in the corridor.
```html
<rect class="box-accent" x="20" y="185" width="110" height="50" rx="6"/>
<text class="t-title" x="75" y="215" text-anchor="middle">Start</text>
<path class="wire" d="M130,210 L146,210" marker-end="url(#ah3)"/>
<polygon class="box" points="230,155 310,210 230,265 150,210"/>
<text class="t-title" x="230" y="206" text-anchor="middle">Question</text>
<text class="t-title" x="230" y="224" text-anchor="middle">line 2?</text>
<!-- yes: up -->
<path class="wire" d="M230,155 L230,70 L356,70" marker-end="url(#ah3)"/>
<text class="t-label" x="240" y="62">YES</text>
<!-- no: right -->
<path class="wire" d="M310,210 L356,210" marker-end="url(#ah3)"/>
<text class="t-label" x="314" y="202">NO</text>
<!-- loop back from box at x=560..730 to box at x=360..530 -->
<path class="wire-stop" d="M645,180 L645,150 L445,150 L445,176" marker-end="url(#ah3s)"/>
<text class="t-label t-stop" x="470" y="143">needs changes</text>
```

## D · Sequence — "Who calls whom, in what order?"
Participants as boxes on top, dashed lifelines down, messages as horizontal arrows top to
bottom; return messages `wire-dash`. Participant spacing 200–230; message rows every 44.
```html
<rect class="box-accent" x="40" y="20" width="160" height="44" rx="6"/>
<text class="t-title" x="120" y="47" text-anchor="middle">Client</text>
<rect class="box" x="300" y="20" width="160" height="44" rx="6"/>
<text class="t-title" x="380" y="47" text-anchor="middle">Web service</text>
<rect class="box" x="560" y="20" width="160" height="44" rx="6"/>
<text class="t-title" x="640" y="47" text-anchor="middle">DB2</text>
<line class="lifeline" x1="120" y1="64" x2="120" y2="300"/>
<line class="lifeline" x1="380" y1="64" x2="380" y2="300"/>
<line class="lifeline" x1="640" y1="64" x2="640" y2="300"/>

<path class="wire" d="M120,100 L376,100" marker-end="url(#ah4)"/>
<text class="t-label ltr" x="130" y="92">GET /cheques/{id}</text>
<path class="wire" d="M380,144 L636,144" marker-end="url(#ah4)"/>
<text class="t-label ltr" x="390" y="136">CALL APP.GET_CHEQUE</text>
<path class="wire-dash" d="M640,188 L384,188" marker-end="url(#ah4)"/>
<text class="t-label" x="400" y="180">result set</text>
```
Message labels start 10 units after the sender's lifeline, so they stay readable after mirroring
(Hebrew labels anchor at their right edge, `ltr` labels flip to `end`).

## E · Comparison panels — "What is allowed / different?"
Two (max three) equal panels side by side, colored by meaning (`box-stop` vs `box-ok`),
title + 2–4 short lines each, left-aligned at `x + 18`.
```html
<rect class="box-stop" x="20" y="20" width="470" height="118" rx="6"/>
<text class="t-title t-stop" x="38" y="46">PROD: read only</text>
<text class="t-sub" x="38" y="70">line 1</text>
<text class="t-sub" x="38" y="92">line 2</text>
<rect class="box-ok" x="510" y="20" width="470" height="118" rx="6"/>
<text class="t-title t-ok" x="528" y="46">TEST: changes announced</text>
<text class="t-sub" x="528" y="70">line 1</text>
```

## Steps strip (HTML, not SVG)
For short sequences inside a card use the `.steps` strip instead of a diagram.
Arrow character: `→` in LTR documents, `←` in RTL documents.
