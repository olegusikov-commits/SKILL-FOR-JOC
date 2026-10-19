---
description: Requirement (אפיון) — start a new one and write it together with you, complete an existing one with you, build it alone from a request, or check someone's spec; Hebrew document + HTML; stops for approval
argument-hint: "new <name or request> | complete SPEC-nnn | SPEC-nnn | <request text or form path> | check <path>"
---

Specification task: $ARGUMENTS

Use the `tl-requirements` skill and follow its rules exactly; depth by the level in the task's
`FLOW.md` (KIT_GUIDE "Depth levels"; no `FLOW.md` → `standard`). Do not modify production code.
Read `.claude/tl-memory/PROJECT_CONTEXT.md` and `.claude/tl-memory/KNOWLEDGE.md` first.

**Mode by the first word of the arguments:**

- `new <name or request>` — a new requirement, **written together with the user**:
  1. `python .claude/skills/tl-requirements/scripts/spec_tool.py new <latin-slug> --title "<name>"
     --level <level>` (`py -3` if `python` is missing; level from `/tl-go`, else ask once with
     buttons, `standard` recommended for a change in existing code, `mvp` for something new).
     A folder for this request already exists → use it, do not create a second one.
  2. Put what the user already said into `REQUEST.md` section 1; tell them in one line they may
     add documents or paths, but nothing else is required.
  3. Follow the skill's "Write it together with the user": learn, then section by section —
     draft → 1–4 questions with buttons → apply. "дальше сам" → finish alone.
  4. Then the build steps 5–8 (lint, skeptic by level, render, stop for approval).

- `complete SPEC-nnn` — the skill's "Complete a specification together": gap map, close what the
  evidence closes, ask the rest with buttons, report closed / still open.

- `check <path>` — review a specification someone else wrote: the skill's "Check a
  specification" section. Output `CHECK-<date>.md` (Hebrew) with a verdict and findings with
  exact fixes; do not rewrite the spec. Reply in Russian: verdict, top findings, the report
  path, and an offer to produce a corrected version in kit format (`complete`).

- anything else (`SPEC-nnn`, a request in words, a path to a filled form `.md` / `.docx`) —
  build or update the specification alone: the skill's "Build a specification", all steps, in
  order; questions only at the end (≤ 5, buttons). A spec already published (`KNOWLEDGE.md` ·
  פורסם) is edited at its published path; lint and render it there.

**Reply in Russian:** the requirement in 3 lines, the decision table in short (if any), the
effect with its bound and verdict (if measured), what was filled from evidence vs assumed, what
the skeptic changed (if it ran), the open questions, the paths of `SPEC.md` and `SPEC.html`.

**STOP** for approval ("утверждаю" / "approved"). On approval: status `approved`, version 1.0,
history row, render again, tick stage 4 in `FLOW.md`, refresh the index, publish (automatic when
`auto_publish` is on, otherwise offer `/tl-publish`). Next: at `mvp` `/tl-implement SPEC-nnn`
(section 19 is the plan); otherwise `/tl-design SPEC-nnn` for LARGE, `/tl-implement SPEC-nnn` for
SMALL. End with the step card.
