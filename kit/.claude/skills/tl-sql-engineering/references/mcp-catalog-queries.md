# Catalog queries for the SQL MCP (meet-checkov / meet-chequemis)

All queries in this file are **read-only `SELECT`s against the system catalog** and are safe
on PROD. Replace `dbo.TableName` / `'SCHEMA'` / `'TABLE'` with real names.
Run only what you need; do not dump whole catalogs.

---

## Engine & environment detection

Try the SQL Server probe first; if it fails with a syntax error, try the DB2 probe.

**SQL Server**
```sql
SELECT @@SERVERNAME                          AS server_name,
       DB_NAME()                             AS current_db,
       SERVERPROPERTY('ProductMajorVersion') AS major_version,  -- 15 = 2019, 16 = 2022
       SERVERPROPERTY('Edition')             AS edition;

SELECT name, compatibility_level,            -- 150 = 2019 features, 160 = 2022 features
       is_read_committed_snapshot_on,
       snapshot_isolation_state_desc,
       is_query_store_on
FROM sys.databases
WHERE name = DB_NAME();
```

**DB2 for z/OS**
```sql
SELECT CURRENT SERVER, CURRENT SQLID, CURRENT SCHEMA
FROM SYSIBM.SYSDUMMY1;

SELECT GETVARIABLE('SYSIBM.VERSION') AS DB2_VERSION   -- e.g. DSN12015 = Db2 12
FROM SYSIBM.SYSDUMMY1;
```

**Environment (PROD/TEST)** cannot be proven by SQL. Use, in this order: the mapping in
`.claude/tl-memory/PROJECT_CONTEXT.md`; the server / location name; ask the user.
Until confirmed → treat as **PROD**. Record the answer in `PROJECT_CONTEXT.md`.

---

## SQL Server 2019 / 2022

### Columns
```sql
SELECT c.column_id, c.name AS column_name, t.name AS data_type,
       c.max_length,            -- bytes; nvarchar = 2 bytes/char; -1 = MAX
       c.precision, c.scale, c.is_nullable, c.is_identity,
       dc.definition AS default_value, c.collation_name
FROM sys.columns c
JOIN sys.types t               ON t.user_type_id = c.user_type_id
LEFT JOIN sys.default_constraints dc ON dc.object_id = c.default_object_id
WHERE c.object_id = OBJECT_ID(N'dbo.TableName')
ORDER BY c.column_id;
```

### Indexes (key order, included columns, filters)
```sql
SELECT i.name AS index_name, i.type_desc, i.is_primary_key, i.is_unique,
       i.filter_definition,
       STRING_AGG(CASE WHEN ic.is_included_column = 0
                       THEN c.name + CASE WHEN ic.is_descending_key = 1 THEN ' DESC' ELSE '' END
                  END, ', ') WITHIN GROUP (ORDER BY ic.key_ordinal) AS key_columns,
       STRING_AGG(CASE WHEN ic.is_included_column = 1 THEN c.name END, ', ') AS included_columns
FROM sys.indexes i
JOIN sys.index_columns ic ON ic.object_id = i.object_id AND ic.index_id = i.index_id
JOIN sys.columns c        ON c.object_id = ic.object_id AND c.column_id = ic.column_id
WHERE i.object_id = OBJECT_ID(N'dbo.TableName')
  AND i.type > 0                                   -- skip heap entry
GROUP BY i.name, i.type_desc, i.is_primary_key, i.is_unique, i.filter_definition
ORDER BY i.is_primary_key DESC, i.name;
```

### Row count
```sql
SELECT SUM(p.rows) AS row_count
FROM sys.partitions p
WHERE p.object_id = OBJECT_ID(N'dbo.TableName')
  AND p.index_id IN (0, 1);                        -- heap or clustered index only
```

### Foreign keys (both directions)
```sql
SELECT fk.name AS fk_name,
       OBJECT_SCHEMA_NAME(fk.parent_object_id) + '.' + OBJECT_NAME(fk.parent_object_id)         AS child_table,
       COL_NAME(fkc.parent_object_id, fkc.parent_column_id)                                     AS child_column,
       OBJECT_SCHEMA_NAME(fk.referenced_object_id) + '.' + OBJECT_NAME(fk.referenced_object_id) AS parent_table,
       COL_NAME(fkc.referenced_object_id, fkc.referenced_column_id)                             AS parent_column,
       fk.delete_referential_action_desc, fk.is_disabled, fk.is_not_trusted
FROM sys.foreign_keys fk
JOIN sys.foreign_key_columns fkc ON fkc.constraint_object_id = fk.object_id
WHERE fk.parent_object_id     = OBJECT_ID(N'dbo.TableName')
   OR fk.referenced_object_id = OBJECT_ID(N'dbo.TableName')
ORDER BY fk.name, fkc.constraint_column_id;
```
Note: an FK child column **without an index** is a common source of slow deletes and
blocking — check it against the index list.

### Check constraints and unique constraints
```sql
SELECT name, definition, is_disabled, is_not_trusted
FROM sys.check_constraints
WHERE parent_object_id = OBJECT_ID(N'dbo.TableName');
```

### Statistics freshness (may need extra permissions)
```sql
SELECT s.name AS stats_name, sp.last_updated, sp.rows, sp.rows_sampled, sp.modification_counter
FROM sys.stats s
CROSS APPLY sys.dm_db_stats_properties(s.object_id, s.stats_id) sp
WHERE s.object_id = OBJECT_ID(N'dbo.TableName');
```

### Index usage (resets on instance restart — interpret with care)
```sql
SELECT i.name AS index_name, us.user_seeks, us.user_scans, us.user_lookups, us.user_updates,
       us.last_user_seek, us.last_user_scan
FROM sys.indexes i
LEFT JOIN sys.dm_db_index_usage_stats us
       ON us.object_id = i.object_id AND us.index_id = i.index_id AND us.database_id = DB_ID()
WHERE i.object_id = OBJECT_ID(N'dbo.TableName') AND i.type > 0;
```

### Procedure / view / function: definition and parameters
```sql
SELECT o.type_desc, o.create_date, o.modify_date, m.definition
FROM sys.sql_modules m
JOIN sys.objects o ON o.object_id = m.object_id
WHERE m.object_id = OBJECT_ID(N'dbo.ProcName');

SELECT p.parameter_id, p.name, TYPE_NAME(p.user_type_id) AS data_type,
       p.max_length, p.precision, p.scale, p.is_output
FROM sys.parameters p
WHERE p.object_id = OBJECT_ID(N'dbo.ProcName')
ORDER BY p.parameter_id;
```

### Impact analysis: who uses this table / procedure
```sql
SELECT DISTINCT OBJECT_SCHEMA_NAME(d.referencing_id) + '.' + OBJECT_NAME(d.referencing_id) AS referencing_object,
       o.type_desc
FROM sys.sql_expression_dependencies d
JOIN sys.objects o ON o.object_id = d.referencing_id
WHERE d.referenced_id = OBJECT_ID(N'dbo.TableName');
```
Dynamic SQL and application code are **not** in this list — also search the source code.

### Real workload on PROD via Query Store (read-only)
```sql
SELECT TOP (20)
       q.query_id,
       SUM(rs.count_executions)                                                          AS executions,
       SUM(rs.avg_duration * rs.count_executions)
         / NULLIF(SUM(rs.count_executions), 0) / 1000.0                                  AS avg_duration_ms,
       SUM(rs.avg_logical_io_reads * rs.count_executions)
         / NULLIF(SUM(rs.count_executions), 0)                                           AS avg_logical_reads,
       MAX(qt.query_sql_text)                                                            AS query_text
FROM sys.query_store_query_text qt
JOIN sys.query_store_query q           ON q.query_text_id = qt.query_text_id
JOIN sys.query_store_plan p            ON p.query_id = q.query_id
JOIN sys.query_store_runtime_stats rs  ON rs.plan_id = p.plan_id
WHERE qt.query_sql_text LIKE N'%TableName%'
GROUP BY q.query_id
ORDER BY avg_logical_reads DESC;
```
Plan XML for a query: `SELECT plan_id, query_plan FROM sys.query_store_plan WHERE query_id = @id;`
Several plans for one query = plan instability / parameter sniffing candidate.

### Estimated plan — TEST only
`SET SHOWPLAN_XML ON` must be alone in its batch; use it only if the MCP server supports
separate batches. Otherwise ask the user to show the estimated plan in SSMS.

---

## DB2 for z/OS (catalog `SYSIBM.*`)

Catalog reads use `WITH UR` to avoid taking locks on the catalog — this is the accepted
exception to the "no UR" rule.

### Table, size and statistics date
```sql
SELECT CREATOR, NAME, TYPE, DBNAME, TSNAME, CARDF, NPAGESF, STATSTIME
FROM SYSIBM.SYSTABLES
WHERE CREATOR = 'SCHEMA' AND NAME = 'TABLE'
WITH UR;
```
`CARDF = -1` or an old `STATSTIME` → statistics missing/stale; the optimizer is guessing.

### Columns
```sql
SELECT COLNO, NAME, COLTYPE, LENGTH, SCALE, NULLS, DEFAULT, COLCARDF
FROM SYSIBM.SYSCOLUMNS
WHERE TBCREATOR = 'SCHEMA' AND TBNAME = 'TABLE'
ORDER BY COLNO
WITH UR;
```
For `DECIMAL`, `LENGTH` = precision and `SCALE` = scale. COBOL host variables must match
(e.g. `DECIMAL(11,2)` ↔ `PIC S9(9)V99 COMP-3`).

### Indexes with key columns
```sql
SELECT I.NAME AS INDEX_NAME, I.UNIQUERULE, I.CLUSTERING, I.CLUSTERRATIOF,
       I.FIRSTKEYCARDF, I.FULLKEYCARDF, I.NLEVELS, I.NLEAF, I.STATSTIME,
       K.COLSEQ, K.COLNAME, K.ORDERING             -- ORDERING: A/D; blank = INCLUDE column
FROM SYSIBM.SYSINDEXES I
JOIN SYSIBM.SYSKEYS K
  ON K.IXCREATOR = I.CREATOR AND K.IXNAME = I.NAME
WHERE I.TBCREATOR = 'SCHEMA' AND I.TBNAME = 'TABLE'
ORDER BY I.NAME, K.COLSEQ
WITH UR;
```
`UNIQUERULE`: D = duplicates allowed, U = unique, P = primary key, C = unique constraint.
Low `CLUSTERRATIOF` on the clustering index → range scans become random I/O; REORG candidate.

### Foreign keys (both directions)
```sql
SELECT R.RELNAME, R.CREATOR AS CHILD_SCHEMA, R.TBNAME AS CHILD_TABLE,
       R.REFTBCREATOR AS PARENT_SCHEMA, R.REFTBNAME AS PARENT_TABLE, R.DELETERULE,
       F.COLSEQ, F.COLNAME
FROM SYSIBM.SYSRELS R
JOIN SYSIBM.SYSFOREIGNKEYS F
  ON F.CREATOR = R.CREATOR AND F.TBNAME = R.TBNAME AND F.RELNAME = R.RELNAME
WHERE (R.CREATOR = 'SCHEMA' AND R.TBNAME = 'TABLE')
   OR (R.REFTBCREATOR = 'SCHEMA' AND R.REFTBNAME = 'TABLE')
ORDER BY R.RELNAME, F.COLSEQ
WITH UR;
```

### Stored procedures and parameters
```sql
SELECT SCHEMA, NAME, ORIGIN, LANGUAGE, EXTERNAL_NAME, COLLID, RESULT_SETS, CREATEDTS, ALTEREDTS
FROM SYSIBM.SYSROUTINES
WHERE SCHEMA = 'SCHEMA' AND NAME = 'PROCNAME' AND ROUTINETYPE = 'P'
WITH UR;

SELECT ORDINAL, PARMNAME, ROWTYPE, TYPENAME, LENGTH, SCALE     -- ROWTYPE: P=in, O=out, B=inout
FROM SYSIBM.SYSPARMS
WHERE SCHEMA = 'SCHEMA' AND NAME = 'PROCNAME'
ORDER BY ORDINAL
WITH UR;
```
The source of external (COBOL) procedures lives in the source library, not in the catalog.

### Impact analysis: which packages (programs) use this table
```sql
SELECT DISTINCT DCOLLID AS COLLECTION, DNAME AS PACKAGE
FROM SYSIBM.SYSPACKDEP
WHERE BQUALIFIER = 'SCHEMA' AND BNAME = 'TABLE' AND BTYPE = 'T'
WITH UR;
```
Every package listed here may need a REBIND / retest after a schema change.

### Access path with EXPLAIN — TEST only (it INSERTs into PLAN_TABLE)
```sql
EXPLAIN PLAN SET QUERYNO = 9001 FOR
  <the statement>;

SELECT QBLOCKNO, PLANNO, METHOD, TNAME, ACCESSTYPE, MATCHCOLS, ACCESSNAME,
       INDEXONLY, PREFETCH, SORTN_JOIN, SORTC_ORDERBY, SORTC_GROUPBY
FROM PLAN_TABLE
WHERE QUERYNO = 9001
ORDER BY QBLOCKNO, PLANNO;
-- cleanup of your own rows (TEST): DELETE FROM PLAN_TABLE WHERE QUERYNO = 9001;
```
Read it as: `ACCESSTYPE` R = tablespace scan (bad on large tables), I = index,
N = IN-list index, M/MX/MI/MU = multiple index; `MATCHCOLS` = how many leading index columns
are matched (0 with ACCESSTYPE I = non-matching index scan); `INDEXONLY = Y` = no data page
access; `SORT*` = Y → sorts. Compare TEST vs PROD statistics (`CARDF`, `STATSTIME`) before
trusting a TEST access path.
