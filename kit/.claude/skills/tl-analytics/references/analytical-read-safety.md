# Analytical reads on PROD — safety rules

Analysis needs aggregates over months of history. This is still **read-only** work, but a
careless analytical query can load a production server. These rules extend the SQL MCP safety
protocol in `CORE.md`; they never relax "PROD is read-only".

## Allowed
- `SELECT` only. No DML/DDL, no `EXEC`/`CALL`, no temporary tables, no `SELECT INTO`,
  no table variables filled from large scans, no MCP "write" tools of any kind.
  Use CTEs and subqueries.
- Result sets returned to you: **aggregates** (`GROUP BY`) or samples of **≤ 20 rows**.
  Never pull raw history into the conversation.

## Required for every heavy query (scan of more than one month of a large table)
1. **Bounded period** on a date column, written as a range (`>= @from AND < @to`), not as a
   function on the column. Check in the catalog that this column is indexed (or is the
   clustering key). If it is not indexed — say so and plan smaller periods.
2. **No locks:** SQL Server `WITH (NOLOCK)` on each table; DB2 `WITH UR`. Aggregates for
   analysis do not need row-exact consistency; blocking production does real damage.
3. **Volume known in advance:** estimate rows first (catalog row counts or pattern 1 in
   `backtest-sql.md` on one month).

## Once per topic: the query plan approval
Before the first heavy query of a topic, show the user in one short message:
- server / database / environment, tables, period and estimated rows;
- the kinds of queries you will run (baseline by month, funnel, segment scans, backtests);
- that all are SELECT, bounded, aggregated, `NOLOCK` / `WITH UR`.
After the user agrees, record "План запросов одобрен <дата>" in `TOPIC.md` and work within it
without asking again. A new table, a longer period or a new kind of query → ask again.
If TEST has a fresh enough copy of the data, prefer TEST and say so.

## While running
- A query is slow or times out → do **not** retry the same or a bigger one. Split by month or
  narrow the columns.
- Prefer one query that returns monthly rows over twelve separate queries.
- Record each query in `queries/` with the date it was run.
