# Index design and query performance

## The order of work
1. Read existing indexes on the table (catalog query) — **always first**.
2. Write the query so an existing index can serve it.
3. Only if none can: propose a new index or an extension of an existing one, with justification.

## Designing a composite index
- Key column order: **equality predicates first** (most selective first when equal otherwise),
  then **one range** predicate or the `ORDER BY` / join column. Columns after the first range
  column cannot be used for seeking.
- SQL Server: add `INCLUDE` columns to make the index **covering** for hot queries and remove
  key lookups — but only for columns the query actually returns.
- DB2 z/OS: `INCLUDE` columns are allowed on **unique** indexes only; otherwise add as trailing
  key columns if index-only access is worth it.
- Prefer **extending** an existing index (same leading keys) over creating a near-duplicate.
- Filtered index (SQL Server) for queries on a small, stable subset (`WHERE Status = 'OPEN'`)
  — parameters with different values cannot use it; check the predicate is literal-compatible.
- FK columns on the child side usually need an index (deletes on parent, joins).

## Cost of an index
Every index slows `INSERT`/`UPDATE`/`DELETE` of its columns, uses storage, and needs
maintenance. On write-heavy tables, justify each new index with the query it serves, how often
that query runs, and the expected improvement. Look for **unused** and **duplicate/overlapping**
indexes (usage stats / leading-key comparison) and list them as tech debt rather than adding more.

## Missing-index suggestions (SQL Server DMVs / plan hints)
They are **hints, not designs**: they ignore existing indexes, overlap with each other,
over-include columns and know nothing about write cost. Use them as input only.

## SARGable rewrites
| Instead of | Write |
|---|---|
| `WHERE YEAR(OrderDate) = 2024` | `WHERE OrderDate >= '2024-01-01' AND OrderDate < '2025-01-01'` |
| `WHERE ISNULL(Col, 0) = 5` / `COALESCE(...)` | `WHERE Col = 5` (NULLs already excluded) |
| `WHERE UPPER(Name) = UPPER(@n)` | rely on case-insensitive collation, or a persisted computed column + index |
| `WHERE Amount * 1.17 > @x` | `WHERE Amount > @x / 1.17` |
| `WHERE LEFT(Code, 3) = 'ABC'` | `WHERE Code LIKE 'ABC%'` |
| `WHERE CAST(Col AS varchar) = @s` | correct parameter type |
| `WHERE a = @x OR b = @y` (different indexes) | `UNION ALL` of two seeks (dedupe if needed) — verify with plan |

## Joins and subqueries
- Join on columns with the same type and collation.
- Check join cardinality — a missing join condition or a 1:N join where 1:1 was assumed
  duplicates rows; `DISTINCT` hiding that is a bug, not a fix.
- Correlated subqueries in the `SELECT` list executed per row → rewrite as a join/`APPLY`
  when the outer set is large.

## Large data operations
- Batch DML by key ranges, commit per batch, make it restartable.
- Avoid huge `IN (...)` lists from the application — use a table-valued parameter (SQL Server)
  or a temp/global temporary table (DB2) and join.
- Reports over large history: consider summary tables, indexed views (SQL Server, with care),
  or running on a read replica — an architecture decision (ADR).

## Statistics
Bad plans often come from stale statistics, not missing indexes. Check `STATS_DATE` /
`modification_counter` (SQL Server) or `STATSTIME` / `CARDF` (DB2) before tuning SQL.

## Plan smells
Table/clustered index scan on a large table · key lookup inside a nested loop with many rows ·
sort or hash spilling to tempdb · estimate vs actual off by 10x+ · implicit conversion warning
· several plans for the same query (sniffing) · DB2: `ACCESSTYPE = R` on a large table,
`MATCHCOLS = 0`, unexpected sorts (`SORTN_JOIN`, `SORTC_ORDERBY`).
