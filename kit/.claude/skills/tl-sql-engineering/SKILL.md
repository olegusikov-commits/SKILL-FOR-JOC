---
name: tl-sql-engineering
description: Senior/DBA-level SQL engineering for SQL Server 2019/2022 and DB2 for z/OS. Use for ANY work that writes, changes, reviews or optimizes SQL — queries, stored procedures, views, functions, indexes, DDL, migrations, data fixes, embedded SQL in COBOL/Natural/C#/Python/Node — and whenever the SQL MCP servers (meet-checkov, meet-chequemis) are involved. Enforces schema-first work against the real catalog via MCP, set-based and index-aware SQL, safe PROD/TEST handling.
---

# SQL Engineering (Tech Lead + DBA level)

The typical junior failure: SQL written from guesses about the schema, row-by-row logic,
functions on indexed columns, implicit conversions, `SELECT *`, no error handling, no thought
about volume or locking. This skill exists to prevent exactly that.

## Step 0 — Know where you are (once per session)
1. Read `.claude/tl-memory/PROJECT_CONTEXT.md` → "Databases" section, if it exists. It maps
   MCP servers to engines, environments and databases.
2. If not known, discover with a trivial, safe query through the MCP server and record it
   (see `references/mcp-catalog-queries.md`, section "Engine & environment detection").
3. Determine: **engine** (SQL Server / DB2 z/OS), **version** (SQL Server 2019 = 15.x,
   2022 = 16.x, and the database **compatibility level**), **environment** (PROD / TEST).
   Unknown environment = **PROD**.

## Step 1 — Schema first (mandatory, before writing any SQL)
Through the SQL MCP (`meet-checkov` / `meet-chequemis`), look up for every table you touch:
- Columns: exact data types, lengths, nullability, defaults, identity/sequence.
- Primary key, unique constraints, foreign keys (both directions), check constraints.
- **All existing indexes**: key columns in order, included columns, uniqueness, filter,
  clustering. (DB2: clustering index, cluster ratio.)
- Approximate row count / cardinality (SQL Server partition stats, DB2 `CARDF`) and
  statistics freshness.
- For procedures/views you change or call: the current definition and its dependents.

Use the ready-made queries in `references/mcp-catalog-queries.md`. Summarize what you found
in a few lines before writing SQL. **Never invent a column, type, or index.** If MCP is not
available, say so explicitly and list the assumptions the user must verify.

## Step 2 — Design the access path, then write the SQL
- Decide **which index should serve each predicate and join** and write the query so it can
  use it (SARGable; leading key columns; equality before range). If no suitable index
  exists, say so and decide: acceptable scan (small table) / rewrite / propose an index.
- Volume: what is the row count today and in 3 years? Batch large DML.
- Concurrency: what locks does this take, for how long, and what else runs at the same time?
- Correctness: NULL semantics, duplicates from joins, time zones, rounding/precision,
  empty input, concurrent updates (lost update / race).

## Step 3 — Non-negotiable rules
1. **Parameterized always.** No string-concatenated values. Dynamic SQL only via
   `sp_executesql` with parameters (SQL Server) or prepared statements with parameter markers
   (DB2); identifiers only from a whitelist / `QUOTENAME`.
2. **Set-based.** No cursors/loops for what a single statement or a few set operations can do.
   Row-by-row is allowed only with a written reason (e.g., per-row external call, controlled
   batch commit in z/OS batch).
3. **SARGable predicates.** No functions/arithmetic/`CAST` on the indexed column side of
   WHERE/JOIN; no leading-wildcard `LIKE` on large tables; ranges instead of `YEAR(col) = …`.
4. **Types match.** Parameter / host-variable types equal the column types (length,
   precision, `varchar` vs `nvarchar`, `DECIMAL(p,s)`). Implicit conversion silently turns
   seeks into scans.
5. **Explicit column lists.** No `SELECT *` in application code, views, procedures, or
   `INSERT` without a column list.
6. **Schema-qualified names** (`dbo.Table`, `SCHEMA.TABLE`).
7. **Transactions are short and explicit.** Know the isolation level. No user interaction or
   remote calls inside a transaction. Handle deadlock/timeout (SQL Server 1205, DB2 -911/-913)
   with a bounded retry at the right layer.
8. **No `NOLOCK` / `WITH UR` as a performance fix.** Dirty reads can return missing or
   duplicated rows. Allowed only for explicitly approximate reporting, with a comment.
9. **Pagination:** keyset (seek) pagination for large sets; `OFFSET` only for small ones.
10. **Every schema change is a reviewed script** with rollback, idempotency and deployment
    order (see `references/schema-changes.md`). Never executed on PROD by you.

## Step 4 — Engine-specific standards
- SQL Server 2019/2022 → `references/sqlserver.md`
- DB2 for z/OS → `references/db2-zos.md`
- Stored procedures (both engines) → `references/stored-procedures.md`
- Index and performance design → `references/performance-indexing.md`
- DDL, migrations, data fixes → `references/schema-changes.md`

Load only the files relevant to the current task.

## Step 5 — Verify
- Check the plan where the environment allows it:
  - SQL Server: on TEST use the estimated plan; on PROD read Query Store / plan cache views
    with `SELECT` only.
  - DB2 z/OS: `EXPLAIN` writes into `PLAN_TABLE`, so **TEST only**; remember TEST statistics
    may differ from PROD — compare `CARDF`/`STATSTIME` in both catalogs.
- Look for: scans on large tables, key lookups in loops, sorts/spools on big inputs, implicit
  conversion warnings, estimate vs actual row mismatches.
- Test with edge data: NULLs, empty sets, duplicates, max lengths, boundary dates.

## Output to the user
In Russian: what you checked in the catalog, the chosen access path and why, the SQL, the
risks (locking, volume, plan stability), and what to verify on PROD. SQL comments in Hebrew.

## Red flags — stop and rethink if you see yourself writing
`SELECT *` · cursor over a table to update it · `WHERE UPPER(col) =` · `WHERE col + 0 =` ·
`LIKE '%x'` on a big table · `NOT IN (subquery)` with nullable column · `NOLOCK` ·
string-built SQL · `BEGIN TRAN` without error handling · a new index without checking
existing ones · a DELETE/UPDATE without a tested WHERE · `ORDER BY` missing where order matters.
