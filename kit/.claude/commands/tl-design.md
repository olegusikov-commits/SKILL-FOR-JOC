---
description: Architect-level design for a task — requirements, options, trade-offs, ADR — then STOP for approval before any code
argument-hint: "<what needs to be built or changed>"
---

Task to design: $ARGUMENTS

Use the `tl-architecture` skill and follow its process exactly. If the task involves the
database, also use the `tl-sql-engineering` skill and inspect the real schema through the SQL MCP
(read-only).

1. Read `.claude/tl-memory/PROJECT_CONTEXT.md` and existing ADRs in `.claude/tl-memory/adr/`.
2. Ask clarifying questions first if the business rules or constraints are unclear — do not
   invent them. If only minor details are open, continue and list them as open questions.
3. Write the design doc to `.claude/tl-memory/design/` (Hebrew) and, for significant decisions,
   an ADR with status `Proposed` to `.claude/tl-memory/adr/`.
4. Reply in Russian with: the problem in 2 sentences, options compared (short table),
   the recommendation and why, main risks, the implementation plan as numbered small steps,
   open questions, and the paths of the files you wrote.
5. **STOP. Do not modify production code.** Wait for the user's explicit approval
   (e.g. "утверждаю" / "approved" / "go"). When approved, set the ADR status to `Accepted` and
   continue with `/tl-implement`.
