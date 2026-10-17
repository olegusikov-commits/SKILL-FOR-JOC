# Document types and writing rules

## Document types and their sections

| Type | When | Sections (in order) |
|---|---|---|
| **Module / program explanation** | "Explain how X works" | Purpose · Overview diagram (A) · Main flow (B or D) · Components (cards) · Data (tables, key columns, indexes) · Errors and edge cases · Where to look in the code |
| **Process / runbook** | Installation, deployment, batch run, operational procedure | Goal · Prerequisites · Steps diagram (B) · Detailed steps · Decision points (C) · Verification checklist · What to do when it fails |
| **Architecture overview** | System/integration, several services | Context (who uses it) · Components (A) · Interactions (D) · Data ownership · Key decisions (link ADRs) · Risks and limits |
| **Onboarding** | New team member | What the system does · Map (A) · Typical day/task flow (C) · Cheat sheet table "situation → what to do" · Glossary · Where to ask |
| **Code walkthrough** | Explain a change, a PR, a complex function | Why the change · Before/after (E) · Call sequence (D) · Changed files (table) · Tests · Risks |
| **Tool / kit guide** | How to install and use a tool | What's inside (A) · Install & update (B) · Workflow (C) · Cheat sheet · Per-part cards · Verification checklist |

Delete sections that do not apply; never leave empty placeholders.

## Writing rules (all languages)
- Lead with the answer: the first paragraph of each section says what the reader will learn.
- Short sentences, active voice, one idea per paragraph (2–4 sentences).
- Name things as the reader sees them in their work (screens, commands, files), not by internal
  jargon. Exact technical names in `<code>`: files, commands, tables, procedures, copybooks.
- Numbers with units (rows, seconds, MB); dates as `YYYY-MM-DD`.
- No filler words, no marketing tone, no emojis.
- Every diagram is introduced by one sentence before it and explained by its caption after it.
- Tables for comparisons and cheat sheets; cards for components; lists only for real sequences.
- End with something actionable: checklist, cheat sheet, or "where to look next".

## Hebrew (default)
- `<html lang="he" dir="rtl">`. The page, tables and cards flip automatically (the template uses
  logical properties like `border-inline-start`, `text-align: start`).
- Technical terms stay in English inside `<code>` (they are isolated left-to-right): לדוגמה
  `OrderService`, `/tl-init`, `dbo.Orders`.
- Use common Israeli developer terms: שרת, שירות, טבלה, אינדקס, פרוצדורה (stored procedure),
  תהליך batch, ממשק (interface/API), פריסה (deployment), סביבת בדיקות (TEST), ייצור (PROD).
- Diagrams flow right to left (mirror the LTR draft). Steps strip arrows: `←`.
- Labels in SVG: Hebrew text normally; Latin-only text gets class `ltr`.

## Russian
- `<html lang="ru" dir="ltr">`. Technical terms in English inside `<code>`.
- Steps strip arrows: `→`. No mirroring.

## Accessibility
- Every SVG: `role="img"` + `aria-label`. Contrast through the tokens only.
- Headings in order (h1 → h2 → h3); table headers in `<th>`.
