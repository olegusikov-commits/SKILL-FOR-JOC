# Decision tables and data checks

A business rule written as prose ("approve regular customers up to 5,000") hides the decisions the
developer must make: in which order, `>` or `>=`, which field means "regular", what happens when a
value is missing, what about everything else. A decision table makes each of those explicit and
lets you measure each row on real data.

## Format
```markdown
### טבלת החלטה DT-1: אישור אוטומטי לתביעה (דוגמה)
סדר הבדיקה: מלמעלה למטה, השורה הראשונה שמתקיימת קובעת.

| # | תנאים | תוצאה | קוד סיבה | מקרים בחודש | מקור |
|---|---|---|---|---|---|
| 1 | פוליסה לא פעילה: `policies.status <> 'ACTIVE'` | לפקיד | POLICY_INACTIVE | 118 | [מקור: קוד rules.py:14] |
| 2 | חשד לכפילות: `claims.is_duplicate_suspect = 1` | לפקיד | DUPLICATE_SUSPECT | 60 | [מקור: קוד rules.py:16] |
| 3 | (חדש) לקוח מוסדי ותיק: `customers.customer_type IN ('COMPANY','GOVERNMENT')` ו-`claims.prev_claims >= 6` ו-`claim_amount <= 5000` ו-בדיקות המסמכים עוברות | אישור אוטומטי | AUTO_REGULAR_CUSTOMER | 280 | [מקור: נתונים D-4] |
| … | … | … | … | … | … |
| 9 | אחרת | אישור אוטומטי | OK | 312 | [מקור: קוד rules.py:32] |
```

## Rules for every table
1. **Order.** Say "first matching row wins" (or that rows are independent, if so). Hard stops
   come first; a new rule states its position relative to them.
2. **Conditions in data terms:** `table.column`, operator, value — with the business words next to
   them. Operators explicit: `>=`, `<=`, `<>`, `IN (…)`, `IS NULL`.
3. **Boundaries:** for every threshold — inclusive or not, the unit (₪ / agorot, %, 0–1
   confidence, days), the precision (2 decimals). Check the unit in data (look at real values).
4. **Missing data:** what happens when an input is NULL, empty, or not yet known.
5. **"אחרת" row always present:** what happens to everything that matches no row.
6. **Delta visible:** mark new and changed rows `(חדש)` / `(שונה)`; keep the unchanged rows so the
   reader sees the whole decision, not only the patch.
7. **Configuration:** thresholds that belong in config get the key name (follow the module's
   existing pattern).
8. **Volume per row** measured on a recent, representative period (monthly average) — a row with
   zero volume is a dead rule or a wrong condition; a huge "אחרת" row is a gap.
9. **Every input known at decision time.** A field filled later (by a clerk, by a batch, after
   review) must not be a condition — that is leakage: it looks perfect on history and fails in
   production. Evidence: who writes the field and when (code), NULL pattern, timestamps, or the
   analysis topic's `DATA_MAP.md` table "known at decision time".

## Checks against data
All checks: `SELECT` only, bounded period on an indexed date column, `WITH (NOLOCK)` (SQL Server)
/ `WITH UR` (DB2), aggregates only — `tl-analytics/references/analytical-read-safety.md`.
Save each query as `queries/D-n-<name>.sql`. SQL Server shown; DB2 differences are in
`tl-analytics/references/backtest-sql.md`.

**(a) Calibrate the as-is table** — write today's logic as a `CASE` in the same order and compare
with the decision actually stored. Agreement must be ~100%; otherwise your as-is table is wrong
(missing condition, wrong order, wrong field) — fix it before designing the to-be table.
```sql
WITH x AS (
  SELECT d.reason_code AS actual,
         CASE WHEN p.status <> 'ACTIVE'          THEN 'POLICY_INACTIVE'
              WHEN c.is_duplicate_suspect = 1    THEN 'DUPLICATE_SUSPECT'
              /* … every row of the as-is table, same order … */
              ELSE 'OK' END AS as_is
  FROM dbo.claims c WITH (NOLOCK)
  JOIN dbo.policies p WITH (NOLOCK) ON p.policy_id = c.policy_id
  JOIN dbo.auto_decisions d WITH (NOLOCK) ON d.claim_id = c.claim_id
  WHERE c.submitted_at >= @from AND c.submitted_at < @to
)
SELECT SUM(CASE WHEN actual = as_is THEN 1 ELSE 0 END) AS agree, COUNT(*) AS n FROM x;
```

**(b) Volume per row of the to-be table** — the same `CASE` returning the row number, grouped by
month and row.

**(c) Values the table does not mention** — for every categorical input:
`SELECT channel, COUNT(*) … GROUP BY channel`. A value in data that no row names (e.g. a third
channel) falls into "אחרת" — say whether that is intended.

**(d) Mass at the boundary** — how many objects sit exactly on each threshold and one unit around
it (`claim_amount = 5000`, `prev_claims IN (5, 6, 7)`). A large mass at the boundary makes
`>` vs `>=` a business decision with a number attached — write the number.

**(e) NULLs** per input field.

**(f) Effect and guardrail** — objects whose outcome changes from as-is to to-be, by row and by
month, with their known historical outcome. Measure the KPI change and the guardrail (e.g. the
error rate of the newly automated objects) and decide by the bound, not the point value:
`python .claude/skills/tl-analytics/scripts/an_stats.py verdict --k <errors> --n <objects> --threshold 0.02`;
by month: `an_stats.py stability --threshold 0.02 --rows "2026-07:n:k,2026-08:n:k,…"`. Use the outcome definitions of the analysis topic if
one exists (e.g. the last review is final; a corrected amount counts as an error). Large or
contested effect → hand the measurement to `/tl-an` and reference its report.

## From the table to acceptance criteria
- Each row → at least one AC that lands exactly on that row.
- Each threshold → an AC exactly on the boundary and one just beyond it (5,000.00 / 5,000.01;
  6 / 5 previous claims).
- Each hard stop → an AC where the new rule's conditions hold **and** the hard stop fires — the
  hard stop must win.
- The "אחרת" row → one AC.
- Missing data → one AC per input that can be NULL.
