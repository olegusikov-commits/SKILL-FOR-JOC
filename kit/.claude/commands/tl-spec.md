---
description: Systems analyst (מנתח מערכות) — creates the intake form, builds an evidence-based specification (אפיון) from a request, or checks an existing one; Hebrew document + HTML; stops for approval
argument-hint: "new <name> | <request text, path to a filled form, or SPEC id> | check <path to a spec>"
---

Specification task: $ARGUMENTS

Use the `tl-requirements` skill and follow its rules exactly. Do not modify production code.
Read `.claude/tl-memory/PROJECT_CONTEXT.md` and `.claude/tl-memory/KNOWLEDGE.md` first.

**Mode by the first word of the arguments:**

- `new <name>` — create the intake form and stop:
  `python .claude/skills/tl-requirements/scripts/spec_tool.py new <latin-slug> --title "<name>"`
  (if `python` is not found use `py -3`). Reply in Russian: the path of `REQUEST.md`, that the
  user fills what they know (every field except section 1 may stay empty — you will fill the
  rest from code, data and documents), and the next command: `/tl-spec <SPEC id>`.

- `check <path>` — review a specification someone else wrote: the skill's "Check a
  specification" section. Output `CHECK-<date>.md` (Hebrew) with a verdict and findings with
  exact fixes; do not rewrite the spec. Reply in Russian: verdict, top findings, the report
  path, and an offer to produce a corrected version in kit format.

- anything else — build or update a specification: the skill's "Build a specification" section,
  all steps, in order. The argument may be the request in words, a path to a filled form
  (`.md` / `.docx`), or the id of an existing spec (`SPEC-003`) to continue or update it.
  1. Find or create the spec folder; make sure `REQUEST.md` holds the request. A spec already
     published (`KNOWLEDGE.md` · פורסם) is edited at its published path; lint and render it there.
  2. Learn: `KNOWLEDGE.md` documents of the area, the analysis topic if any, then `tl-researcher`
     subagents in parallel (code / data / docs).
  3. Write `SPEC.md` from the template; verify against data with saved queries; fill gaps from
     evidence with source tags.
  4. `spec_tool.py lint SPEC.md` → fix; `tl-spec-skeptic` → fix; `spec_tool.py render SPEC.md`.
  5. Status `review`, `python .claude/tech-lead-kit/scripts/tl_knowledge.py index`.
  6. Reply in Russian: the requirement in 3 lines, the decision table in short, the expected
     effect with its bound and verdict, what was filled from evidence vs assumed, what the
     skeptic changed, at most 5 questions with proposed answers, the paths of `SPEC.md` and
     `SPEC.html`.
  7. **STOP.** Wait for approval ("утверждаю" / "approved"). On approval: status `approved`,
     version 1.0, history row, render again, refresh the index, and offer `/tl-publish` and the
     next step (`/tl-design` for a LARGE change, `/tl-implement` for a SMALL one).
