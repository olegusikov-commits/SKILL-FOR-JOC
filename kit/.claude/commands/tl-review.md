---
description: Code check before git or colleagues — independent architect (+ DBA when SQL changed) review of the current changes or given files; prioritized findings with fixes and coverage of the requirement by tests
argument-hint: "[files/folders to review — default: uncommitted changes]"
---

Review target: $ARGUMENTS

1. Determine the scope:
   - If arguments are given → those files/folders.
   - Otherwise → the uncommitted changes (`git status` / `git diff` and `git diff --staged`).
     If git is not available or there are no changes, ask the user what to review.
2. Find in `.claude/tl-memory/KNOWLEDGE.md` the approved specs, accepted ADRs and designs whose
   `area` touches the changed files. Delegate the review to the **`tl-architect-reviewer`**
   subagent with the list of files, a one-paragraph description of the intent of the change, and
   the paths of those documents (the change is reviewed against them).
3. If the scope contains SQL, stored procedures, DDL, migrations, or embedded SQL (C#, Python,
   Node, COBOL, Natural), also delegate to the **`tl-sql-reviewer`** subagent in parallel.
4. Merge the results into one report in Russian, grouped by severity:
   - **BLOCKER** — must be fixed before merge (bugs, data loss/corruption risk, security, broken
     contracts, PROD-safety, severe performance).
   - **MAJOR** — should be fixed in this change (design/boundary violations, missing tests for
     key logic, error handling gaps).
   - **MINOR** — improvements; may go to TECH_DEBT.md.
   Each finding: file:line, problem, why it matters, concrete fix. An approved spec covers the
   change → add the coverage table `REQ / AC → task → test` and name every AC without a test.
5. Ask with buttons (KIT_GUIDE "Questions"): "исправить BLOCKER+MAJOR сейчас (рекомендуется) /
   только BLOCKER / MINOR и остальное — в TECH_DEBT.md / оставить как есть" (unless this review was
   invoked from `/tl-implement`, where BLOCKERs are fixed automatically). Tick stage 7 in the task's
   `FLOW.md` when no BLOCKER is left; end with the step card.
