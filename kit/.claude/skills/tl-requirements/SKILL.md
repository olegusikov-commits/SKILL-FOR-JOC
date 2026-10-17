---
name: tl-requirements
description: Systems analyst (מנתח מערכות) — turns a business request into a precise, evidence-based requirement and specification (אפיון) that developers can code from and QA can test, or checks an existing specification. Use for "write a spec / requirement / אפיון / דרישה / טופס דרישה", "analyze this request before development", "check this spec", decision tables, acceptance criteria, and whenever /tl-spec is run. Verifies every rule and term against the real code and data, measures the expected effect on history, and gets an independent skeptic review before presenting.
---

# Requirements & specification (systems analyst)

The typical failure: a spec that restates the request in nicer words — vague terms, thresholds
without boundaries, no order of rules, nothing about what must NOT change, numbers nobody
checked. The developer guesses, and the guesses become defects. (In the cheque demo every defect
of the implemented task — rule placed before the hard stops, missing channel check, `>` instead
of `>=`, no boundary tests — was a gap in the requirement.) This skill closes those gaps before
the first line of code.

## Non-negotiable rules
1. **Learn before you write or ask.** Sources, in this order: the request (intake form +
   conversation), `.claude/tl-memory/KNOWLEDGE.md` (specs, ADRs, analysis topics of the area),
   code, data (SQL MCP), documents.
2. **Every business term maps to a real source** — `table.column`, code `file:line`, or a
   document section — or is marked "לא נמצא" with a question. "Regular payer", "veteran
   customer", "small amount" are not definitions.
3. **Every rule is a decision table** (`DT-n`, `references/decision-tables.md`): evaluation
   order, hard stops first, exact boundaries (`>=` vs `>`), units, NULL / missing data, an
   explicit "אחרת" (else) row, and the measured volume of each row.
4. **Every requirement is testable:** `REQ-nnn` with acceptance criteria `AC-nnn` (given / when /
   then with concrete values, including values exactly at and just beyond every boundary).
   No "fast", "reasonable", "etc." without a number.
5. **Fill the gaps yourself** where evidence exists — from knowledge, code, data, documents — and
   label the source of every filled item: `[מקור: קוד src/x.py:21]`, `[מקור: נתונים Q-3]`,
   `[מקור: מסמך process.docx §2]`, `[מקור: ADR-002]`, `[מקור: טופס הדרישה]`, or `[הנחה]`.
   Ask the user only what you could not find **and** what changes the spec (question protocol).
6. **What does not change is part of the spec:** hard stops, other rules, reports and interfaces
   that keep their behaviour — listed explicitly.
7. **Impact on others is part of the spec:** who else reads or writes the data, the codes or the
   config (reports, other modules, batch jobs, mainframe, documents such as reason-code tables).
8. **A measurable goal is checked on history before code:** replay the to-be decision table on
   past data with the `tl-analytics` method (`backtest-sql.md`, `an_stats.py verdict`, verdict
   by the upper bound). A spec that cannot meet its own goal says so and offers alternatives.
9. **Every number comes from a saved query** (`queries/Q-n-<name>.sql` in the spec folder; the
   key queries also go to the spec's appendix) — never from your head.
10. **No production code changes.** Write only in the spec folder, or in the published spec
    file when you update a published spec. Data: `SELECT` only, per
    `.claude/skills/tl-analytics/references/analytical-read-safety.md` (TEST first; PROD by the
    plan approved once per topic).
11. **Before presenting:** `scripts/spec_tool.py lint`, then the `tl-spec-skeptic` subagent.
    Fix what they find or answer it in the spec.

## Where things are
- Spec folder: `.claude/tl-memory/spec/SPEC-nnn-<slug>/` — `REQUEST.md` (intake form),
  `SPEC.md` (the specification), `SPEC.html` (rendered), `queries/`, `CHECK-<date>.md` (check
  reports), `NOTES.md` (working notes, optional).
- After `/tl-publish`, `SPEC.md` / `SPEC.html` move to the project's docs (default
  `docs/specs/SPEC-nnn-<slug>.md`); `KNOWLEDGE.md` shows where each spec lives. Update a
  published spec in place.
- Templates: `references/intake-form.md` (the form the user fills before starting),
  `references/spec-template.md`. Rules and data checks: `references/decision-tables.md`.
  Quality gates and severities: `references/spec-quality-checklist.md`.
- Tool (stdlib Python; if `python` is not found use `py -3`):
  `python .claude/skills/tl-requirements/scripts/spec_tool.py new <slug> --title "<name>"` ·
  `… lint <SPEC.md>` · `… render <SPEC.md>`.
- Every document carries a first-line `tl-meta` comment (type, id, status, date, area, title);
  after writing run `python .claude/tech-lead-kit/scripts/tl_knowledge.py index`.

## Build a specification
1. **Folder and id.** A spec folder for this request exists (the user ran `/tl-spec new`) → use
   it. Otherwise `spec_tool.py new <slug> --title "<name>"`. A filled form elsewhere (a path, a
   `.docx`) → copy its content into the folder's `REQUEST.md`. No form → fill `REQUEST.md`
   yourself from the conversation: it is the record of what was asked.
2. **Learn.** Read `KNOWLEDGE.md` and the documents of the area: an approved spec or an accepted
   ADR you must respect; an analysis topic (`DATA_MAP.md`, `LOGIC_AS_IS.md`, `BASELINE.md`) saves
   you re-research. Then `tl-researcher` subagents in parallel (focus `code`, `data`, `docs`)
   with the request text, the business terms and what each should find. Documents
   `.docx/.xlsx/.pptx`: `python .claude/skills/tl-analytics/scripts/an_doc2text.py <file>`.
3. **Draft `SPEC.md`** from `references/spec-template.md`. Scale it: a small change gets short
   sections and one line "לא רלוונטי" for the rest, but never drop goal and metric, scope
   (including what does not change), REQ, DT, glossary, edge cases, AC, effect, assumptions and
   questions.
4. **Verify against data** (`references/decision-tables.md`): the as-is table reproduces actual
   decisions; volume per to-be row; values the table does not mention; mass exactly at each
   boundary; NULLs; every input known at decision time; the effect and the guardrail with its
   bound.
5. **Self-check:** `spec_tool.py lint` → fix every ERROR and every WARN you can.
6. **Skeptic:** `tl-spec-skeptic` with the paths of `REQUEST.md`, `SPEC.md`, `queries/` and the
   documents used. Apply its findings; record in section 18 what changed.
7. **Render:** `spec_tool.py render SPEC.md` → `SPEC.html` (offline, RTL, light/dark, prints;
   Word opens it and can save it as `.docx`).
8. **Questions and stop.** At most 5 open questions, each with your proposed answer and its basis
   (section 16 and the reply). Set status `לבדיקה` (`tl-meta status=review`), refresh the index,
   and **STOP** for the user's approval.
9. **On approval:** status `מאושר` (`status=approved`), version 1.0, history row, render again,
   refresh the index, offer `/tl-publish` (so the team and every agent see it) and the next step:
   `/tl-design` for a LARGE change, `/tl-implement` for a SMALL one.

## Check a specification (written by someone else)
1. Read it: Markdown directly; `.docx/.xlsx/.pptx` through `an_doc2text.py`; PDF directly.
   Review it — do not rewrite it.
2. Kit-format Markdown → `spec_tool.py lint`. Any other format → apply the checklist by hand.
3. Verify the 5–10 facts the spec depends on, against code and data yourself: every term → field
   mapping, every threshold and boundary, every data claim (shares, volumes), the order relative
   to hard stops, fields known at decision time, the goal (backtest when decision logic changes).
4. `tl-spec-skeptic` on your findings.
5. Write `CHECK-<YYYY-MM-DD>.md` (Hebrew, for the author; `tl-meta type=spec-check`) in the spec
   folder — a new folder `SPEC-nnn-<slug>` if the spec has none: verdict (מוכן לפיתוח / מוכן אחרי
   תיקונים / לא מוכן), findings by severity with the location in the spec, evidence and the
   exact replacement text. Reply in Russian with the summary; offer a corrected version in kit
   format.

## Update a specification
New information or a changed request → edit in place, bump the version, add a history row. An
approved spec that changes goes back to `לבדיקה` until approved again. Code already implemented
from it → list what must change in code and tests.

## Question protocol
As in `tl-analytics`: ask only after learning; at most 5 at a time; each with your proposed
answer and what it is based on. Do not block: continue with the proposed answer, mark it
`[הנחה — ממתין לאישור]` and list which REQ / DT rows depend on it.

## Output language
The request form, the spec and check reports are project documents — **Hebrew**; identifiers,
table and column names stay in English. Talk to the user in Russian.
