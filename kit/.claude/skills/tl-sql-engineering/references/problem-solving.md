# DBA problem solving — understand, measure, options, choose

The junior answer to "the report is slow" is one index or one rewrite. The DBA answer starts from
the size and the cause and compares real options. Use this for `/tl-sql tune`, a design that
touches large tables, and any analysis that runs into volume.

## 1. Understand the problem in numbers
| Ask | How (read-only, cheap) |
|---|---|
| How big? rows, pages, growth per month | catalog row counts (`mcp-catalog-queries.md`), monthly `COUNT` on an indexed date over 2–3 months |
| How is it distributed? skew, hot values, NULLs | `GROUP BY` the filter column `TOP 20`; DB2 `SYSCOLDIST` |
| What does the query really do? | plan: Query Store / plan cache (SQL Server, read-only), estimated plan or EXPLAIN on TEST |
| Is it the query or the environment? | waits / blocking (`sys.dm_exec_requests`, `sys.dm_os_waiting_tasks` if permitted), time of day, concurrent batch |
| Are statistics fresh? | `STATS_DATE` / `modification_counter`; DB2 `STATSTIME`, `CARDF = -1` |
| When is it needed and how fresh? | the user / the calling code: online in 1 s, nightly batch, a report once a month |

Write the facts in 3–6 lines before proposing anything.

## 2. Symptom → usual causes
| Symptom | Look for |
|---|---|
| Slow report over history | scan of a large table, function on the date column, no covering index, aggregation over raw rows every run |
| Fast sometimes, slow sometimes | parameter sniffing (several plans in Query Store), stale statistics, blocking |
| Timeouts / deadlocks | long transactions, lock escalation, missing index on a FK used in updates, order of access |
| Grows slower every month | no archiving / partitioning, index fragmentation on a hot insert key, unbounded "all history" queries |
| Big DELETE / UPDATE hurts | one huge transaction → batch by key with commits; log size; replication |
| Batch window exceeded | row-by-row processing, no restart point, sorts on big inputs |

## 3. At least three options — including ones that are not "an index"
| Option family | Examples | Good when |
|---|---|---|
| Rewrite the query | SARGable range, `EXISTS` instead of `IN`, window functions instead of self-joins, remove a row multiplier join | the plan shows avoidable work |
| Index | composite in the right order, covering (`INCLUDE`), filtered index (SQL Server) | a frequent, selective predicate; check existing indexes and write cost |
| Statistics / plan | update statistics, `OPTIMIZE FOR`, `OPTION (RECOMPILE)` for rare skewed calls, Query Store plan forcing | estimates are wrong, data is skewed |
| Pre-aggregate | summary table filled incrementally (watermark), indexed view (SQL Server), MQT (DB2) | the same aggregates are read many times |
| Analytics storage | columnstore index for large scans and aggregates (SQL Server) | reporting over millions of rows |
| Change the time | move to the batch window, incremental load instead of full recompute | freshness of minutes/hours is enough |
| Reduce the data | archive / partition by date (SQL Server partitioning, DB2 range-partitioned tablespace) | most queries touch recent data |
| Change the application | cache a reference result, page (keyset) instead of returning everything, ask for less | the caller does not need all rows / every time |

For each option: expected gain (with the number you measured), cost (build, write overhead,
storage, operations), risk (locking during build, plan changes for other queries), who must do it
(you / DBA / DevOps). The minimal change is always one of the options.

## 4. Choose and prove
Recommend one with the reason in numbers. Prove it on TEST where possible (plan, logical reads,
time on a comparable volume — and say how TEST differs from PROD). Anything that changes schema
or PROD configuration is a reviewed script (`schema-changes.md`) and a LARGE task.
