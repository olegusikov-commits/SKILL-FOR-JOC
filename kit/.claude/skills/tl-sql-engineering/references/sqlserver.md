# SQL Server 2019 / 2022 standards

The project runs **both 2019 and 2022**. Before using a version-specific feature, check
`SERVERPROPERTY('ProductMajorVersion')` (15 / 16) **and** the database
`compatibility_level` (150 / 160) of the target database. Code that must run on both uses the
2019 subset only.

## Version features worth knowing

| Feature | Needs | Note |
|---|---|---|
| `CREATE OR ALTER` | 2016 SP1+ | Use for procs/views/functions — idempotent deploy |
| `STRING_AGG`, `TRIM`, `CONCAT_WS` | 2017+ | Prefer over `FOR XML PATH` tricks |
| Scalar UDF inlining | 2019, compat 150 | Has many restrictions; check `sys.sql_modules.is_inlineable` |
| Table variable deferred compilation | 2019, compat 150 | Table variables get real row estimates |
| Batch mode on rowstore | 2019, compat 150, Enterprise | Analytics-style queries |
| `OPTIMIZE_FOR_SEQUENTIAL_KEY` | 2019 | Index option for last-page insert contention (identity/date keys) |
| Accelerated Database Recovery | 2019 | Fast rollback of long transactions — DBA setting |
| Parameter Sensitive Plan optimization | 2022, compat 160 | Multiple plans per parameterized query |
| `IS [NOT] DISTINCT FROM` | 2022 | NULL-safe comparison |
| `GREATEST` / `LEAST`, `DATETRUNC`, `DATE_BUCKET`, `GENERATE_SERIES` | 2022 | Do not use in code that must run on 2019 |
| `WINDOW` clause, `STRING_SPLIT(..., 1)` ordinal | 2022 | Same |

## Style
- Keywords UPPERCASE, objects in project convention, always schema-qualified (`dbo.Orders`).
- One clause per line for non-trivial queries; meaningful table aliases (`o` for Orders, not `a`, `b`).
- Explicit `JOIN ... ON` — never comma joins.
- Terminate statements with `;` (required before CTEs, `THROW`, `MERGE`).
- Hebrew comments explain **why** (business rule, chosen access path), not what.

## Data types
- Match parameters to column types exactly. `nvarchar` parameter vs `varchar` column →
  `CONVERT_IMPLICIT` on the column → index scan. In C# (`SqlParameter`) set `SqlDbType` and
  `Size` explicitly; do not use `AddWithValue` for strings.
- Money: `decimal(p,s)`, never `float`/`real`. Dates: `date`, `datetime2(n)`; time zone aware
  data → `datetimeoffset` or store UTC and say so.
- `varchar(MAX)` / `nvarchar(MAX)` only when really unbounded.

## Query patterns
- Existence: `EXISTS (SELECT 1 ...)`, not `COUNT(*) > 0`.
- `NOT EXISTS` instead of `NOT IN (subquery)` (NULL in the subquery makes `NOT IN` return no rows).
- Date ranges: `col >= @From AND col < @ToExclusive` — never `CONVERT(date, col) = ...`
  on large tables, never `BETWEEN` with `datetime` end-of-day hacks.
- Optional filters ("catch-all" `(@p IS NULL OR col = @p)`): causes bad plans. Use
  `OPTION (RECOMPILE)` for low-frequency queries, or build parameterized dynamic SQL with
  `sp_executesql` for high-frequency ones.
- Upsert: `MERGE` has known concurrency pitfalls; prefer `UPDATE ... ; IF @@ROWCOUNT = 0 INSERT ...`
  inside a transaction with `UPDLOCK, HOLDLOCK` (or `SERIALIZABLE`) on the key, or `MERGE`
  with `HOLDLOCK` if the team standard uses it.
- `TOP` without `ORDER BY` = arbitrary rows. Always order when it matters.
- `OUTPUT` clause to get generated keys/changed rows; `SCOPE_IDENTITY()` — never `@@IDENTITY`.

## Transactions and errors
```sql
SET NOCOUNT ON;
SET XACT_ABORT ON;   -- any runtime error dooms and rolls back the transaction
BEGIN TRY
    BEGIN TRANSACTION;
    -- ... work ...
    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;            -- rethrow original error; do not swallow
END CATCH;
```
- New code: `THROW`, not `RAISERROR` (except when `WITH NOWAIT` progress messages are needed).
- Business errors: `THROW 50001, N'<message>', 1;` with a documented error number range.
- Deadlock victim = error 1205 → retry belongs in the application layer (bounded, with backoff),
  or in the procedure only if the whole unit is safe to repeat.

## Concurrency
- Check `is_read_committed_snapshot_on`. With RCSI readers don't block writers; without it,
  long reads block updates.
- `NOLOCK` / `READ UNCOMMITTED` is not a fix — see the main skill rule.
- Large DML in batches (e.g. 1,000–5,000 rows per transaction, keyed loop) to avoid lock
  escalation (~5,000 locks per statement triggers escalation to table lock) and log growth.

## Temp objects
- `#temp` tables for intermediate sets that are large or need indexes/statistics.
- Table variables for small sets (on 2019+ estimates are better, but still no statistics).
- CTEs are not materialized — a CTE referenced twice is executed twice.

## Things to avoid
`SELECT *` · `sp_` prefix for user procedures · cursors for set logic · scalar UDFs in
large-row queries (unless inlined) · triggers containing business logic · `GOTO` ·
`WITH (NOLOCK)` · implicit conversions · non-deterministic `TOP` · `ORDER BY` ordinal numbers ·
hints (`FORCESEEK`, `INDEX(...)`, `MAXDOP`) without a documented reason and DBA agreement.
