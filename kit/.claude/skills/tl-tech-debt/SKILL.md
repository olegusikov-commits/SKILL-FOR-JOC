---
name: tl-tech-debt
description: Identify, categorize, prioritize and track technical debt in a register (.claude/tl-memory/TECH_DEBT.md). Use for tech-debt audits, "what should we refactor", code-health questions, before planning a refactor, and whenever a task knowingly creates or discovers debt (shortcuts, TODOs, out-of-scope problems) that must be recorded instead of silently fixed or forgotten.
user-invocable: false
---

# Tech Debt Management

Based on Anthropic's `tech-debt` framework, extended with a persistent register and with
categories specific to this environment (SQL/DB2, mainframe, integration).

## Register
File: the `TECH_DEBT.md` that `.claude/tl-memory/KNOWLEDGE.md` lists (its published path if it was published, else `.claude/tl-memory/TECH_DEBT.md`) (Hebrew). Create it from the template below only if it exists in neither place.
Every item has a stable id `TD-NNN`. Never delete items — mark them `Resolved` with date and
how they were resolved.

```markdown
<!-- tl-meta: type=tech-debt; id=; status=living; date=<YYYY-MM-DD>; area=whole project; title=רישום חוב טכני -->
# רישום חוב טכני

| ID | כותרת | קטגוריה | מיקום | השפעה (1-5) | סיכון (1-5) | מאמץ (1-5) | עדיפות | סטטוס | נוצר | הערות |
|---|---|---|---|---|---|---|---|---|---|---|
| TD-001 | ... | Code | src/Orders/OrderService.cs | 4 | 3 | 2 | 28 | Open | 2026-01-01 | ... |
```

Priority = **(Impact + Risk) × (6 − Effort)** (range 2–50). Higher = do first.

## Categories
| Category | Examples here |
|---|---|
| Code | God classes/programs, duplicated business rules, magic values, dead code, giant COBOL paragraphs |
| Architecture | Logic in the wrong layer, modules sharing tables, synchronous chains, missing boundaries |
| Data / SQL | Missing or duplicate indexes, non-SARGable queries, cursors, implicit conversions, stale stats, no FK indexes, `NOLOCK` usage |
| Test | No tests around critical rules, flaky tests, no characterization tests for legacy |
| Integration | Undocumented contracts, non-idempotent consumers, no timeouts/retries, encoding hacks |
| Dependency | Unsupported framework/runtime versions, outdated libraries with vulnerabilities |
| Security | Secrets in code/config, string-built SQL, missing authorization checks |
| Operability | No structured logs, no correlation id, no restartability in batch, manual deploy steps |
| Documentation | Missing ADRs for key decisions, unknown ownership, outdated runbooks |

## Audit process (`/tl-debt`)
1. Scope: whole project or a given path/module (ask if unclear; prefer scoped audits).
2. Scan the code for the patterns above (search, read hot spots: largest files/classes,
   most-changed files via `git log` if available, modules with no tests).
3. For SQL: use the MCP read-only queries (`tl-sql-engineering` → `mcp-catalog-queries.md`) to find
   unused/duplicate indexes, FK columns without indexes, tables without PK, stale statistics —
   only for the tables in scope.
4. Each finding: concrete location, evidence, why it matters (business impact), scores.
5. Merge with the existing register (no duplicates; update scores if the situation changed).
6. Output in Russian: top 10 by priority with a **phased plan** that can run alongside feature
   work (quick wins first, then items that unblock upcoming features, then large refactors —
   each large one as a separate LARGE task with design).

## During normal work
- Debt you knowingly create (shortcut agreed with the user) → add an item with the reason.
- Problems noticed out of scope → add an item and mention it in the report; do not fix silently.
- When a task resolves an item → mark it `Resolved` with the date.
