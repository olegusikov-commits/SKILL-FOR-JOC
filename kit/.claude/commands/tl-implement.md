---
description: Write or fix code at Tech Lead level — a small fix, an approved spec or design; works through the task plan with checkboxes and resumes where it stopped; tests for every acceptance scenario
argument-hint: "<task> | SPEC-nnn | <path to approved design>"
---

Implement: $ARGUMENTS

0. **First action, before reading code or editing anything:** load the `tl-engineering-standards`
   skill with the Skill tool (if the tool is not available, Read
   `.claude/skills/tl-engineering-standards/SKILL.md`), then Read its references for the
   language(s) involved plus `references/testing.md` and `references/error-handling.md`. SMALL
   tasks are no exception — a one-line fix follows the same standard. For any SQL also load
   `tl-sql-engineering`.
1. Read `.claude/tl-memory/PROJECT_CONTEXT.md` and `.claude/tl-memory/KNOWLEDGE.md`. Read the
   design doc / spec the argument points to, and every approved spec and accepted ADR whose
   `area` touches the files you will change.
   - An approved spec covers the task → implement exactly its decision tables (order, boundaries,
     units, the "אחרת" row) and turn **every AC into at least one test** named or commented with
     its AC id.
   - The task contradicts an approved spec or accepted ADR → stop and say so; the document is
     changed first (`/tl-spec` / `/tl-design`), then the code.
2. **Classify** the task as SMALL or LARGE (core rules) and state it in one line.
   - LARGE without an approved design → do not code. Run the `/tl-design` process instead and stop.
     At level `mvp` an approved spec with section 19 (solution + plan) is the approved design.
   - LARGE with an approved design → implement exactly that design; if reality forces a
     deviation, stop and explain before continuing.
3. Check that step 0 was done (standards and language reference are in your context). For any
   SQL verify the real schema/indexes via the SQL MCP (read-only on PROD) before writing SQL.
4. **The plan.** A design (section 6) or an `mvp` spec (section 19) has a task plan with
   checkboxes → start at the first `- [ ]`; before the first task check that every REQ / AC of the
   approved spec is in some task (missing → stop and ask). No plan (SMALL) → state 2–6 small steps.
   Implement task by task; each compiles and keeps tests green; after each green task set its
   `[x]` in the document at once (that is how the next session resumes). A red test: ≤ 3 tries,
   then stop with the test, the error and your hypothesis. Do not mix refactoring with behavior
   change in the same step.
5. Add/update tests (bug fix → failing test first). Run the project's build/tests if possible.
6. Self-review with the checklist in `tl-engineering-standards`.
7. For LARGE tasks: run the independent review — use the `tl-architect-reviewer` subagent on the
   changed files, and `tl-sql-reviewer` only if SQL/procedures/DDL changed (`mvp`: BLOCKER only).
   Fix all BLOCKER findings, then re-check them (≤ 2 rounds, KIT_GUIDE "Loop limits").
8. Record any knowingly created or discovered debt in the `TECH_DEBT.md` that `.claude/tl-memory/KNOWLEDGE.md` lists (its published path if it was published, else `.claude/tl-memory/TECH_DEBT.md`).
9. If you implemented a spec, fill its traceability section (code `file:line`, tests) — that is
   not a change of the spec: version and status stay; then `spec_tool.py render` it and run
   `python .claude/tech-lead-kit/scripts/tl_knowledge.py index`. If behaviour differs from the spec in any way, say so instead.
10. Report in Russian. Start with one line: `Стандарты kit: <skills and references loaded>; агенты:
   <kit agents used or "—">`. Then: what changed (files), why, tests added and their results (AC coverage when
   a spec exists), tasks done / left, review results, risks, and what the user must verify manually
   (e.g. on TEST / mainframe compile / BIND). Tick stages 6–7 in the task's `FLOW.md` when all tasks
   are `[x]` and BLOCKERs are fixed. End with the step card.
