---
description: SQL at DBA level against the real schema — build SQL / a procedure from a requirement, check existing SQL for correctness and validity, or tune a slow query with options; never hangs on a query
argument-hint: "build <requirement or SPEC-nnn> | check <file, procedure or query> | tune <slow query or report> | <SQL task>"
---

SQL task: $ARGUMENTS

Use the `tl-sql-engineering` skill and follow its steps strictly. Mode by the first word (no mode
word → choose from the task and say which). Data sources and safety: CORE "Data sources".

**Common start (every mode):**
1. Step 0: source, engine, version/compat level, environment — from the registry
   (`.claude/tl-memory/data-sources.json` / `PROJECT_CONTEXT.md`) or the detection probe.
   Unknown environment = PROD.
2. Step 1: the real schema of every table involved — columns and types, keys, **all indexes**,
   row counts, statistics freshness, the current definition of procedures/views. Size first: a
   table of millions of rows is never scanned to "have a look". Summarize in a few lines.

**`build`** — write SQL / a procedure / a view from a requirement:
3. Read the requirement (`SPEC-nnn` → its REQ / DT / AC; words → restate it in 2 lines; ask only
   what changes the SQL, buttons).
4. Design the access path (which index serves which predicate/join) for today's volume and in 3
   years; then write the SQL by the engine reference (`sqlserver.md` / `db2-zos.md`,
   `stored-procedures.md`, `performance-indexing.md`). Hebrew comments for the "why".
5. Prove it on TEST: the AC values (or 3–5 cases you derive) return what the requirement says,
   plus NULLs, empty input, duplicates, boundaries; the plan where allowed.

**`check`** — is existing SQL correct and valid?
3. What it should do: the requirement (spec, ticket, comments, the calling code) — restate it.
4. Read the SQL against the real schema: logic vs requirement (filters, join types and
   cardinality → duplicates, NULL handling, boundaries `>` vs `>=`, time zones, rounding),
   validity (types and implicit conversions, SARGability, transactions and errors, security:
   dynamic SQL, permissions), performance (indexes, plan, volume).
5. Prove the key findings on TEST with small bounded queries (counts before/after a join, a
   boundary row). Report findings by severity with the exact fix; do not change the code unless asked.

**`tune`** — a slow query, procedure or report:
3. Measure cheaply first: row counts, statistics dates, the plan (Query Store / plan cache on PROD
   read-only; estimated plan on TEST; DB2 EXPLAIN on TEST only), waits and blocking if visible.
4. Follow `references/problem-solving.md`: the cause, then at least 3 options (rewrite, index,
   statistics, pre-aggregation, batching / window, archiving, an application change) with gain,
   cost and risk at the real volume; recommend one.

**Then (every mode):**
6. Schema change / data fix → LARGE: scripts per `schema-changes.md` (forward + rollback + impact
   list), present them and **do not execute** without approval; never on PROD.
7. Changed SQL → `tl-sql-reviewer` once (`mvp`: BLOCKER only).
8. Report in Russian: what you checked in the catalog, the access path / findings / options, the
   SQL, risks (locking, volume, plan stability), what to verify on PROD. End with the step card.
