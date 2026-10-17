# Schema changes, migrations and data fixes

Schema changes are always a **LARGE** task: design + user approval first.

## Deliverable
For every change produce, as files in the project (not executed on PROD):
1. `NNN_<description>.sql` — forward script, **idempotent** (safe to run twice).
2. `NNN_<description>_rollback.sql` — rollback script, or an explicit statement why rollback is
   impossible (e.g. data dropped) and what the recovery plan is.
3. Impact list: tables, procedures, views, application code, COBOL/Natural programs, packages
   (DB2 `SYSPACKDEP`), jobs, reports, interfaces.
4. Deployment notes: order relative to application deploy, expected duration and locking,
   whether it is online, post-steps (RUNSTATS/REBIND on DB2, statistics update on SQL Server).

Follow the project's existing migration folder and naming if one exists.

## Expand → migrate → contract (zero-downtime pattern)
Never rename or drop in one step while old code is still running:
1. **Expand**: add the new column/table (nullable or with default); old code unaffected.
2. **Migrate**: deploy code that writes both / reads new; backfill data in batches.
3. **Contract**: after all consumers moved, drop the old column/object in a later release.

## SQL Server specifics
- Idempotency guards: `IF COL_LENGTH('dbo.T', 'NewCol') IS NULL ALTER TABLE ...`,
  `IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = ... AND object_id = OBJECT_ID(...))`,
  `CREATE OR ALTER` for modules.
- Adding a `NOT NULL` column with a constant default is metadata-only on Enterprise edition;
  on Standard it may rewrite the table — check edition.
- Index creation on large tables: `ONLINE = ON` (Enterprise), `RESUMABLE = ON` (2019+ for
  index create/rebuild), and an explicit `MAXDOP` agreed with DBA; schedule off-peak.
- Changing a column type/length on a large table rewrites data and takes a schema lock — plan
  as expand/contract instead.
- Name every constraint and index explicitly (no system-generated names), following project convention.

## DB2 z/OS specifics
- DDL is DBA-owned; deliver scripts + impact analysis for the DBA.
- Know the pending states an `ALTER` can cause (AREO\*, REORP, rebuild pending) and include the
  required REORG/REBUILD.
- After change: RUNSTATS, then REBIND affected packages; compare access paths of critical packages.
- COBOL copybooks / DCLGEN for changed tables must be regenerated and programs recompiled where
  the layout is used.

## Data fixes
- First a `SELECT` that shows exactly the rows that will change (count + sample) — run it on
  TEST, and on PROD only as read-only verification.
- Back up affected rows (to a backup table or file) in the script before changing them.
- Batch by key, commit per batch, print progress.
- Guard with an expected-count check: abort if affected rows differ from the expected number.
- Never `UPDATE`/`DELETE` without a `WHERE` that you tested.
