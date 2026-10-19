---
description: Technical design for a LARGE change — how to build it: options with cost and risk, the choice, contracts, ADR and a task plan with checkboxes — then STOP for approval before any code
argument-hint: "SPEC-nnn | <what needs to be built or changed>"
---

Task to design: $ARGUMENTS

Use the `tl-architecture` skill and follow its process exactly. If the task involves the
database, also use the `tl-sql-engineering` skill and inspect the real schema through the SQL MCP
(read-only).

1. Read `.claude/tl-memory/PROJECT_CONTEXT.md` and `.claude/tl-memory/KNOWLEDGE.md`; open the
   ADRs, specs and analyses of the area. If an approved spec covers the task, its REQ / DT / AC
   are the requirements — reference their ids, do not re-elicit; if the design must change the
   spec, say so.
2. Ask clarifying questions first if the business rules or constraints are unclear — do not
   invent them (buttons, KIT_GUIDE "Questions"; ≤ 5, one round). If only minor details are open,
   continue and list them as open questions. A new service → `references/new-service.md`.
3. Write the design doc to `.claude/tl-memory/design/` (Hebrew) and, for significant decisions,
   an ADR with status `Proposed` to `.claude/tl-memory/adr/` (number from
   `tl_knowledge.py next-id ADR`, which counts published ADRs too). Both start with a `tl-meta` line; then
   run `python .claude/tech-lead-kit/scripts/tl_knowledge.py index`.
   Section 6 is the task plan with checkboxes (`- [ ] T<n> … · בדיקה: … · (REQ-…, AC-…)`); every
   REQ / AC of the approved spec is covered by some task — list any that is not and why.
4. Reply in Russian with: the problem in 2 sentences, options compared (short table),
   the recommendation and why, main risks, the task plan (count + phases),
   open questions, and the paths of the files you wrote. In the task's `FLOW.md` set
   `Дальше: «утверждаю» → /tl-implement <design path>` and end with the step card.
5. **STOP. Do not modify production code.** Wait for the user's explicit approval
   (e.g. "утверждаю" / "approved" / "go"). When approved, set the ADR status to `Accepted`
   (`tl-meta status=accepted`, design `status=approved`), rebuild the index, publish (automatic
   when `auto_publish` is on, otherwise offer `/tl-publish`),
   tick stage 5 in `FLOW.md`, and continue with `/tl-implement <design path>`.
