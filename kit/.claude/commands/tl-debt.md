---
description: Technical debt audit for the project or a given path, merged into the tech debt register with a phased plan
argument-hint: "[path or module — default: ask]"
---

Tech debt audit scope: $ARGUMENTS

Use the `tl-tech-debt` skill and follow its "Audit process":
1. If no scope is given and the project is large, ask which module/path to audit first.
2. Scan the scope for debt in all categories (code, architecture, data/SQL, tests, integration,
   dependencies, security, operability, documentation). For SQL, use read-only MCP catalog queries
   only for tables used in the scope.
3. Score each finding (impact, risk, effort → priority) with concrete evidence (file:line, table,
   index name).
4. Merge into the `TECH_DEBT.md` that `.claude/tl-memory/KNOWLEDGE.md` lists (its published path if it was published, else `.claude/tl-memory/TECH_DEBT.md`) (create from the template only if neither exists), no duplicates;
   refresh the `date` in its `tl-meta` line and run `python .claude/tech-lead-kit/scripts/tl_knowledge.py index`.
5. Report in Russian: top 10 by priority, quick wins, and a phased plan that can run alongside
   feature work. Large refactors are listed as future LARGE tasks (need `/tl-design`).
