---
description: Write, optimize or fix SQL / stored procedures / DDL at DBA level against the real schema via SQL MCP
argument-hint: "<SQL task, query to optimize, or procedure name>"
---

SQL task: $ARGUMENTS

Use the `tl-sql-engineering` skill and follow its steps strictly:

1. Step 0: identify engine, version/compat level and environment of the target (from
   `.claude/tl-memory/PROJECT_CONTEXT.md` or the detection probe). Unknown environment = PROD.
2. Step 1: inspect the real schema through the SQL MCP (`meet-checkov` / `meet-chequemis`):
   columns and types, keys, **all existing indexes**, row counts, statistics freshness, and the
   current definition of any procedure/view involved. Summarize findings in a few lines.
3. Step 2: design the access path (which index serves which predicate/join), considering volume
   and concurrency.
4. Write the SQL following the engine reference (`sqlserver.md` / `db2-zos.md`,
   `stored-procedures.md`, `performance-indexing.md`). Hebrew comments for the "why".
5. Verify: plan check where allowed (TEST only for actions that write, e.g. DB2 EXPLAIN), edge
   cases (NULLs, empty, duplicates, boundaries).
6. Schema change / data fix → this is a LARGE task: produce scripts per `schema-changes.md`
   (forward + rollback + impact list), present them, and **do not execute** without approval;
   never on PROD.
7. Report in Russian: what you checked in the catalog, the chosen access path, the SQL, risks,
   and what to verify on PROD.
