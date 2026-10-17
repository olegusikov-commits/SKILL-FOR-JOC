---
name: oleg-skill-hesber
description: Creates illustrated explanation documents ("הסבר") — one self-contained offline HTML file with inline SVG diagrams (architecture/layers, flows, decisions, sequences, comparisons), light/dark theme, Hebrew right-to-left by default, or Russian/English on request. Use when the user asks to explain a system, module, codebase, program, process, data flow, integration, installation or workflow with a diagram/scheme ("הסבר", "תסביר עם דיאגרמה", "סכמה", "מדריך", "схема", "объясни со схемой", "guide", "overview", "onboarding doc"), or invokes /oleg-skill-hesber.
---

# OLEG-SKILL-HESBER — illustrated explanation documents

Produces documents like the Tech Lead Kit guide: a reader understands the subject from the
diagrams first and the text second. Output is **one HTML file** that opens by double-click in
any browser on the work PC — no internet, no extensions, no external requests.

## 1. Brief (keep it short)
Determine, from the request or by asking only what is truly unclear:
- **Subject and scope** — what exactly is explained (system, module, program, process, tool).
- **Audience** — developer on the team, new team member, manager, DBA/ops. This decides depth.
- **Language** — default **Hebrew (RTL)**. Russian or English only if asked.
- **Output path** — what the user named; otherwise
  `.claude/tl-memory/hesber/<YYYY-MM-DD>-<slug>.html` (local, not committed). Right after
  `<!doctype html>` put `<!-- tl-meta: type=explain; id=; status=final; date=<YYYY-MM-DD>;
  area=<what it explains: modules, tables, process>; title=<title> -->` and then run
  `python .claude/tech-lead-kit/scripts/tl_knowledge.py index`.

## 2. Facts first — never invent
Collect facts from real sources before drawing anything:
- Code, configs, build files, copybooks/PDAs, JCL, DDL, existing docs.
- `.claude/tl-memory/PROJECT_CONTEXT.md` and the documents listed in `.claude/tl-memory/KNOWLEDGE.md`
  (specs, ADRs, designs) if they exist.
- Database structure through the SQL MCP — **read-only catalog queries only** (see the
  `tl-sql-engineering` skill rules for PROD/TEST).
Every box and arrow in a diagram must correspond to something real. If something is assumed,
put it in an "הנחות" (assumptions) callout and say so to the user.

## 3. Plan the document
Pick the document type and its sections from `references/writing-guide.md`.
Pick **2–5 diagrams**, each answering one question:

| Question the reader has | Diagram pattern (`references/diagram-patterns.md`) |
|---|---|
| What is it made of? What depends on what? | A · Layers / components |
| What happens step by step? | B · Pipeline |
| Where are the decisions and loops? | C · Decision flow |
| Who calls whom, in what order? | D · Sequence |
| What is allowed / different between X and Y? | E · Comparison panels |

Write the outline (headings + which diagram goes where) before writing HTML.

## 4. Build
1. Copy `references/template.html` as the starting file. It contains the design tokens,
   light/dark themes, RTL/LTR switch, and all components: diagram plate, table, component
   card, steps strip, example block, callout, checklist.
2. Set `<html lang="…" dir="…">`: Hebrew `lang="he" dir="rtl"`; Russian `lang="ru" dir="ltr"`;
   English `lang="en" dir="ltr"`.
3. Fill sections with real content. Keep paragraphs short (≤ 70 characters per line is
   handled by CSS; keep each paragraph to 2–4 sentences).
4. Draw diagrams with the patterns and geometry rules in `references/diagram-patterns.md`.

### Right-to-left diagrams
In Hebrew, flows run **right to left**. Two ways:
- **Recommended:** draw with left-to-right coordinates (as in the patterns), then mirror:
  `python .claude/skills/oleg-skill-hesber/scripts/mirror_svg.py draft.html final.html`
  Mark Latin-only text (code, paths, names like `tl-sql-engineering`) with class `ltr`.
  Hebrew text keeps `text-anchor="start"`: after mirroring and with the template's CSS it
  anchors at the right edge. Delete the draft after mirroring.
- If Python is not available: author coordinates directly right-to-left following the same
  rules (first step at the right).

## 5. Self-check before handing over
- [ ] Every component in diagrams exists in the real code/system; assumptions marked.
- [ ] Each diagram answers one question and has a caption explaining how to read it.
- [ ] Text fits its box (use the width estimates in the patterns file); no line crosses a box or
      a label; labels sit in empty corridors.
- [ ] Colors come only from tokens (works in light and dark); no literal colors in SVG.
- [ ] No external resources: no CDN, no web fonts, no images from URLs.
- [ ] RTL document: `dir="rtl"`, diagrams mirrored, code/paths readable (class `ltr`).
- [ ] Technical names (files, commands, tables) exactly as in the source, in `<code>`.
- [ ] Ends with something actionable: checklist, cheat sheet, or "where to look next".

If a browser or screenshot tool is available, open the file once and fix overlaps you see.

## 6. Report
Tell the user (in Russian, per the core rules) the file path, what the document covers, the
diagrams included, and any assumptions that need their confirmation.
