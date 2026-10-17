# Data reads for analysis — TEST and PROD

Analysis needs aggregates over months of history. It is always **read-only** work, on every
environment. These rules extend the SQL MCP safety protocol in `CORE.md`; they never relax
"PROD is read-only".

## Where
- **TEST first** if it has fresh and complete enough data for the question (check the latest
  date and monthly volumes). Say so in the report.
- **PROD is allowed** for analysis, read-only, under the rules below and the once-per-topic
  query plan approval.
- **Unknown environment = PROD.** State the environment and data freshness in every report
  ("PROD/TEST, данные по <дата>").

## Allowed (everywhere)
- `SELECT` only. Analysis never writes, even on TEST where changes are allowed: no DML/DDL,
  no `EXEC`/`CALL`, no temporary tables, no `SELECT INTO`, no MCP "write" tools. Use CTEs and
  subqueries.
- Results returned to you: **aggregates** (`GROUP BY`) or samples of **≤ 20 rows**. Never pull raw
  history into the conversation.

## Required for every heavy query (scan of more than one month of a large table)
1. **Bounded period** on a date column, written as a range (`>= @from AND < @to`), not as a
   function on the column. Check in the catalog that this column is indexed (or is the
   clustering key). If it is not — say so and plan smaller periods.
2. **No locks:** SQL Server `WITH (NOLOCK)` on each table; DB2 `WITH UR`. Aggregates do not need
   row-exact consistency; blocking production (or colleagues on TEST) does real damage.
3. **Volume known in advance:** estimate rows first (catalog row counts or pattern 1 in
   `backtest-sql.md` on one month).

## PROD: once per topic — the query plan approval
Before the first heavy query of a topic on PROD, show the user in one short message:
server / database, tables, period and estimated rows; the kinds of queries (baseline by month,
funnel, segment scans, backtests); that all are SELECT, bounded, aggregated, `NOLOCK` / `WITH UR`.
After the user agrees, record "План запросов PROD одобрен <дата>" in `TOPIC.md` and work within it
without asking again. A new table, a longer period or a new kind of query → ask again.

## While running
- A query is slow or times out → do **not** retry the same or a bigger one. Split by month or
  narrow the columns.
- Prefer one query that returns monthly rows over twelve separate queries.
- Record each query in `queries/` with the server, environment and the date it was run.
