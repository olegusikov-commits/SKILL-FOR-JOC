# SQL patterns for analysis and backtests

Templates are written for **SQL Server** (T-SQL). DB2 for z/OS differences are listed at the
end. Replace `<…>` placeholders with real names from `DATA_MAP.md`. Follow
`analytical-read-safety.md` for every query (TEST or PROD). Save each query that produces a reported
number to `queries/NNN-name.sql` with a header comment.

All patterns share one **base CTE**: one row per object, only decision-time fields + the
outcome. Write it once per topic, save it as `queries/000-base.sql`, and reuse it — this keeps
definitions identical across all numbers.

```sql
-- 000-base: one row per object (cheque); decision-time fields + outcome
WITH base AS (
    SELECT o.<id>                               AS obj_id,
           o.<received_at>                      AS received_at,
           DATEFROMPARTS(YEAR(o.<received_at>), MONTH(o.<received_at>), 1) AS month_start,
           o.<amount_seen_by_automation>        AS amount,
           o.<feature_1>, o.<feature_2>,        -- decision-time fields only
           a.<auto_result>                      AS auto_result,    -- e.g. AUTO_APPROVED / TO_HUMAN
           a.<reason_code>                      AS reason_code,
           h.<human_decision>                   AS human_decision, -- NULL if no human review
           CASE WHEN h.<human_decision> = '<REJECTED>'
                  OR (h.<human_decision> = '<APPROVED>' AND h.<corrected_field> IS NOT NULL)
                THEN 1 ELSE 0 END               AS is_error_if_auto
    FROM <schema>.<objects>        o WITH (NOLOCK)
    JOIN <schema>.<auto_decisions> a WITH (NOLOCK) ON a.<obj_id> = o.<id>
    LEFT JOIN <schema>.<human_reviews> h WITH (NOLOCK) ON h.<obj_id> = o.<id>
                                                    -- AND h.<is_spot_check> = 0  (if relevant)
    WHERE o.<received_at> >= @from AND o.<received_at> < @to   -- indexed date column, bounded
)
```
Check **one row per object** (`COUNT(*)` vs `COUNT(DISTINCT obj_id)`) — joins to review tables
often duplicate objects (re-reviews, history rows).

## 1. Volume estimate (before any heavy query)
```sql
SELECT DATEFROMPARTS(YEAR(<received_at>), MONTH(<received_at>), 1) AS month_start, COUNT(*) AS n
FROM <schema>.<objects> WITH (NOLOCK)
WHERE <received_at> >= @from AND <received_at> < @to
GROUP BY DATEFROMPARTS(YEAR(<received_at>), MONTH(<received_at>), 1)
ORDER BY month_start;
```

## 2. Baseline KPI by month (calibration)
```sql
SELECT month_start,
       COUNT(*)                                                  AS n_all,
       SUM(CASE WHEN auto_result = '<AUTO_APPROVED>' THEN 1 ELSE 0 END) AS n_auto
FROM base GROUP BY month_start ORDER BY month_start;
```
Compute the rate with `an_stats.py wilson --k n_auto --n n_all` (two-sided if you report an
interval for the KPI itself) — not in your head.

## 3. Funnel: why objects were not automated + human outcome per reason
```sql
SELECT reason_code,
       COUNT(*)                                                    AS n,
       SUM(CASE WHEN human_decision IS NOT NULL THEN 1 ELSE 0 END) AS n_reviewed,
       SUM(is_error_if_auto)                                       AS k_err
FROM base
WHERE auto_result <> '<AUTO_APPROVED>'
GROUP BY reason_code ORDER BY n DESC;
```

## 4. Ceiling
```sql
SELECT COUNT(*) AS n_all,
       SUM(CASE WHEN auto_result <> '<AUTO_APPROVED>' AND human_decision IS NOT NULL
                 AND is_error_if_auto = 0 THEN 1 ELSE 0 END) AS n_could_be_auto
FROM base;
```

## 5. Segment scan (period A) — one field, numeric field in bins
```sql
SELECT <feature_bin_expression>      AS segment,      -- e.g. FLOOR(ocr_conf * 20) / 20.0
       COUNT(*)                      AS n,
       SUM(is_error_if_auto)         AS k_err
FROM base
WHERE auto_result <> '<AUTO_APPROVED>' AND human_decision IS NOT NULL
  AND received_at < @split_date                       -- period A only
GROUP BY <feature_bin_expression>
HAVING COUNT(*) >= @min_n
ORDER BY 1.0 * SUM(is_error_if_auto) / COUNT(*), n DESC;
```
For pairs, group by two expressions. Keep the result small (`HAVING`, `TOP (50)`).

## 6. Rule backtest by month (period B)
```sql
SELECT month_start,
       COUNT(*)                                                       AS n_all,
       SUM(CASE WHEN new_auto = 1 THEN 1 ELSE 0 END)                  AS n_new,
       SUM(CASE WHEN new_auto = 1 THEN is_error_if_auto ELSE 0 END)   AS k_err,
       SUM(CASE WHEN new_auto = 1 AND is_error_if_auto = 1 THEN amount ELSE 0 END) AS err_amount,
       SUM(CASE WHEN new_auto = 1 THEN amount ELSE 0 END)             AS new_amount
FROM (
    SELECT b.*,
           CASE WHEN b.auto_result <> '<AUTO_APPROVED>'
                 AND b.human_decision IS NOT NULL
                 AND (<hard stops pass>)
                 AND (<rule predicate>)
                THEN 1 ELSE 0 END AS new_auto
    FROM base b
    WHERE b.received_at >= @split_date                 -- period B
) x
GROUP BY month_start ORDER BY month_start;
```
Gain (p.p.) = Σn_new / Σn_all. Then `an_stats.py verdict` on Σk_err / Σn_new and
`an_stats.py stability` on the monthly rows.

## 7. Union of rules
Same as 6 with `(<rule 1>) OR (<rule 2>) OR …` as the predicate. Add a column per rule
(`CASE WHEN <rule i> THEN 1 ELSE 0 END`) to show overlaps.

## 8. Calibrating the logic translation
```sql
SELECT SUM(CASE WHEN (<current logic as SQL>) THEN 1 ELSE 0 END)                    AS pred_auto,
       SUM(CASE WHEN auto_result = '<AUTO_APPROVED>' THEN 1 ELSE 0 END)              AS real_auto,
       SUM(CASE WHEN (CASE WHEN (<current logic as SQL>) THEN 1 ELSE 0 END)
                   = (CASE WHEN auto_result = '<AUTO_APPROVED>' THEN 1 ELSE 0 END)
                THEN 1 ELSE 0 END)                                                   AS agree,
       COUNT(*)                                                                      AS n
FROM base;
```
Agreement ≥ 99% → translation trusted. Otherwise list a sample of disagreements (`TOP (20)`).

## 9. Monitoring after launch (deliver in the report)
Weekly automation rate of the new rule, error among its decisions found by spot checks /
complaints / later reversals, with the rollback trigger. Adapt to what the process records after
launch (spot-check sample of automatic decisions is required to measure error at all — say so).

## DB2 for z/OS differences
| SQL Server | DB2 z/OS |
|---|---|
| `WITH (NOLOCK)` per table | `WITH UR` once at the end of the statement |
| `DATEFROMPARTS(YEAR(d), MONTH(d), 1)` | `DATE(VARCHAR_FORMAT(d, 'YYYY-MM') || '-01')` or `VARCHAR_FORMAT(d, 'YYYY-MM')` |
| `TOP (n)` | `FETCH FIRST n ROWS ONLY` |
| `@param` | literal dates in the analysis query, or parameter markers `?` |
| `1.0 * a / b` | `DECIMAL(a, 15, 4) / b` |
| `FLOOR(x * 20) / 20.0` | `FLOOR(x * 20) / 20.0` (same) |

Other engines: keep the logic, adapt the functions; note the engine in the query header.
