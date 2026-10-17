# DB2 for z/OS standards

Applies to embedded SQL in COBOL / Natural / PL/I, native SQL procedures, external (COBOL)
procedures, and dynamic SQL from distributed clients (C#, Python, Node via DRDA/ODBC/JDBC).

## Mental model the junior misses
- Most z/OS application SQL is **static**: bound into a **package** with an access path chosen
  at BIND time. Changing SQL, indexes or statistics affects packages → **REBIND** is part of the
  change. Find affected packages via `SYSIBM.SYSPACKDEP` (see catalog queries).
- Distributed/dynamic SQL is prepared at runtime → use parameter markers (`?`) so statements
  are reused from the dynamic statement cache; literals defeat the cache.
- CPU on the mainframe costs money. "Works" is not enough — the access path matters.

## Predicates: indexable / stage 1 / stage 2
- **Indexable stage 1** predicates (`col = :hv`, `col > :hv`, `col BETWEEN`, `col IN (list)`,
  `col LIKE 'abc%'`) can use matching index access — design queries around them.
- Predicates with **expressions or functions on the column** (`SUBSTR(col,1,3) = ...`,
  `col + 1 = ...`, `YEAR(col) = ...`), `col <> ...`, `NOT ...`, leading `%` are not matching
  index predicates; many are **stage 2** (evaluated late, expensive). Rewrite them.
  (Index on expression exists in DB2 z/OS — use only with DBA agreement.)
- `OR` across different columns usually prevents a single matching index; consider `UNION ALL`
  or multiple index access, check EXPLAIN.
- **Host variable type and length must match the column** (`CHAR(10)` ↔ `PIC X(10)`,
  `DECIMAL(9,2)` ↔ `PIC S9(7)V99 COMP-3`, `INTEGER` ↔ `PIC S9(9) COMP`). Mismatches can make
  predicates non-indexable or cause conversion errors.
- Use indicator variables for nullable columns; missing indicator on NULL → SQLCODE -305.

## Writing SQL
- Explicit column lists; `SELECT *` in a program breaks when a column is added.
- Singleton `SELECT ... INTO` only when uniqueness is guaranteed by a unique index;
  otherwise SQLCODE -811. If "any one row" is acceptable, add `FETCH FIRST 1 ROW ONLY`.
- Cursors: declare `FOR READ ONLY` or `FOR UPDATE OF col1, col2` explicitly.
  Add `OPTIMIZE FOR n ROWS` when only the first rows are consumed (online screens).
- Use **multi-row FETCH / INSERT** (rowsets) in batch programs for large volumes.
- `MERGE` is available for upsert logic.
- Pagination (online): keyset — `WHERE (key1, key2) > (:last1, :last2)` style with
  `ORDER BY key1, key2 FETCH FIRST n ROWS ONLY`, matching an index.
- `WITH UR` only for catalog reads or explicitly approximate reporting (with a Hebrew comment);
  default isolation follows the package BIND (`ISOLATION(CS)` typical).

## Batch programs (COBOL)
- **Commit frequency**: commit every N rows/units (configurable, not hard-coded) to release locks
  and allow restart. Long units of work cause lock escalation, timeouts for online users and
  long rollback.
- **Restartability**: store a checkpoint (last key processed) in a restart table/file so a
  failed job resumes, not reprocesses. Cursors used across commits: `WITH HOLD`.
- Process in clustering-key order when possible (sequential prefetch, fewer random I/Os).
- Lock escalation is controlled by `LOCKMAX` of the tablespace — know it for heavy updates.

## Error handling (SQLCODE / SQLSTATE)
Check after **every** SQL statement. Typical handling:

| SQLCODE | Meaning | Handling |
|---|---|---|
| 0 | OK | — |
| +100 | Not found / end of cursor | Normal flow, not an error |
| -803 | Duplicate key | Business decision (exists → update / reject) |
| -811 | More than one row for SELECT INTO | Bug in assumptions — fix query/index |
| -305 | NULL without indicator | Add indicator variable |
| -911 | Deadlock/timeout, **rolled back** | Unit of work is gone — restart from checkpoint/retry the unit |
| -913 | Deadlock/timeout, **not rolled back** | Program must ROLLBACK, then retry/restart |
| -904 | Resource unavailable | Abort with clear message; operational issue |
| other negative | Unexpected | Log SQLCODE, SQLSTATE, SQLERRMC, program, key data; abort the unit cleanly |

Centralize this in one error paragraph / copybook per program — not copy-pasted checks.

## Native SQL procedures
- Use `DECLARE ... HANDLER` for expected conditions (`NOT FOUND`, specific SQLSTATEs) and
  `SIGNAL SQLSTATE '7xxxx' SET MESSAGE_TEXT = ...` for business errors (documented range).
- Keep them focused (data access + data rules). Heavy business logic belongs in the application.
- Version them (`VERSION` clause / `ALTER PROCEDURE ... ACTIVATE VERSION`) for safe deployment.

## Schema changes on z/OS
- Some `ALTER`s put the tablespace/index in **advisory REORG pending (AREO\*)** or
  **REORG pending (REORP)** or **rebuild pending** — plan REORG/REBUILD in the change.
- After structural changes: **RUNSTATS** then **REBIND** of affected packages; compare access
  paths before/after (APCOMPARE / EXPLAIN) for critical packages.
- Coordinate with the DBA: DDL on z/OS is a DBA-owned deliverable. Your output is a reviewed
  script + impact list (packages, programs, jobs) + rollback.

## Avoid
`SELECT *` in programs · functions on indexed columns in predicates · host-variable type
mismatches · cursor without `FOR READ ONLY / FOR UPDATE OF` · no commit in long batch ·
ignoring SQLCODE after a statement · literals in dynamic SQL · `WITH UR` on business data ·
singleton SELECT without a unique key.
