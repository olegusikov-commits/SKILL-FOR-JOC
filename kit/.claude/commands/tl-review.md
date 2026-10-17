---
description: Independent architect + DBA review of the current changes (or given files) with prioritized findings
argument-hint: "[files/folders to review — default: uncommitted changes]"
---

Review target: $ARGUMENTS

1. Determine the scope:
   - If arguments are given → those files/folders.
   - Otherwise → the uncommitted changes (`git status` / `git diff` and `git diff --staged`).
     If git is not available or there are no changes, ask the user what to review.
2. Delegate the review to the **`tl-architect-reviewer`** subagent with the list of files and a
   one-paragraph description of the intent of the change (from the conversation or design doc).
3. If the scope contains SQL, stored procedures, DDL, migrations, or embedded SQL (C#, Python,
   Node, COBOL, Natural), also delegate to the **`tl-sql-reviewer`** subagent in parallel.
4. Merge the results into one report in Russian, grouped by severity:
   - **BLOCKER** — must be fixed before merge (bugs, data loss/corruption risk, security, broken
     contracts, PROD-safety, severe performance).
   - **MAJOR** — should be fixed in this change (design/boundary violations, missing tests for
     key logic, error handling gaps).
   - **MINOR** — improvements; may go to TECH_DEBT.md.
   Each finding: file:line, problem, why it matters, concrete fix.
5. Ask the user whether to fix BLOCKER/MAJOR findings now (unless this review was invoked from
   `/tl-implement`, where BLOCKERs are fixed automatically).
