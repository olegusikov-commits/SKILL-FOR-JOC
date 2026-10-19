# Validate before you report

Run this check on every number you are about to present (quick answers too). It takes minutes and
catches the errors a skeptic would otherwise find later — or nobody would.

## 1. Data quality of the inputs
- **Grain:** what is one row (object, event, version of an object)? Is the key unique at that grain?
  `COUNT(*)` vs `COUNT(DISTINCT key)`.
- **NULLs:** share per field used; > 5 % → say it, > 20 % → the field cannot carry a conclusion alone.
- **Placeholders:** -1, 0, 999999, '1900-01-01', 'N/A', empty strings counted as values.
- **Coverage:** every month of the period present; the last month complete (partial periods
  look like drops).

## 2. Calculations
- **Joins:** row count before and after every join — growth means a one-to-many join multiplied
  the rows; loss means an inner join dropped objects without a match.
- **Denominators:** the same population in numerator and denominator; the denominator did not
  shift between the compared periods or segments.
- **Averages:** no average of averages / of percentages — recompute from the counts.
- **Time:** dates compared in the same time zone and at the same moment (decision time vs
  update time); ranges `>= from AND < to`.
- **Small numbers:** a share from fewer than ~30 events gets its bound (`an_stats.py`), not a point.

## 3. Reasonableness
- Reproduces a number the business knows (calibration) — or the difference is explained.
- Red flags to re-check before showing: a change of more than 50 %, exactly 0 % or 100 %,
  suspiciously round totals, a segment that is better on every metric at once.
- Sum of the parts equals the whole (segments add up to the total).

## 4. Confidence of the answer
| Level | Meaning | Say it as |
|---|---|---|
| Ready | all checks pass, calibrated, bound computed | the verdict |
| With caveats | a check could not be done (data, access, time) | the verdict + what was not checked |
| Needs work | a check failed and is not explained | no verdict; what must be fixed first |

Write the level in the reply and in the report.
