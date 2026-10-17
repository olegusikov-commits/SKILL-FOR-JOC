---
description: Implement a task (or an approved design) at Tech Lead level — small steps, tests, self-review, independent review for LARGE tasks
argument-hint: "<task description or path to approved design doc>"
---

Implement: $ARGUMENTS

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
   - LARGE with an approved design → implement exactly that design; if reality forces a
     deviation, stop and explain before continuing.
3. Load the `tl-engineering-standards` skill and the reference file for the language(s) involved.
   For any SQL, load `tl-sql-engineering` and verify the real schema/indexes via the SQL MCP
   (read-only on PROD) before writing SQL.
4. State the plan as small steps. Implement step by step; each step compiles and keeps tests green.
   Do not mix refactoring with behavior change in the same step.
5. Add/update tests (bug fix → failing test first). Run the project's build/tests if possible.
6. Self-review with the checklist in `tl-engineering-standards`.
7. For LARGE tasks: run the independent review — use the `tl-architect-reviewer` subagent on the
   changed files, and `tl-sql-reviewer` if SQL/procedures/DDL changed. Fix all BLOCKER findings,
   then re-check them.
8. Record any knowingly created or discovered debt in the `TECH_DEBT.md` that `.claude/tl-memory/KNOWLEDGE.md` lists (its published path if it was published, else `.claude/tl-memory/TECH_DEBT.md`).
9. If you implemented a spec, fill its traceability section (code `file:line`, tests) — that is
   not a change of the spec: version and status stay; then `spec_tool.py render` it and run
   `python .claude/tech-lead-kit/scripts/tl_knowledge.py index`. If behaviour differs from the spec in any way, say so instead.
10. Report in Russian: what changed (files), why, tests added and their results (AC coverage when
   a spec exists), review results, risks, and what the user must verify manually (e.g. on TEST /
   mainframe compile / BIND).
