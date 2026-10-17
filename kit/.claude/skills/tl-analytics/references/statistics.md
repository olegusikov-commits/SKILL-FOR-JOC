# Statistics for decisions

Use `scripts/an_stats.py` for every calculation below (stdlib Python 3.8+, no packages).
Call it as `python .claude/skills/tl-analytics/scripts/an_stats.py <command> ...`
(if `python` is not found: `py -3`). Add `--json` for machine-readable output.

## Error rate with a confidence bound
An observed rate on a sample is not the true rate. Use the **one-sided 95% Wilson upper bound**
— the error rate we can be 95% sure is not exceeded.

```
an_stats.py wilson  --k 10 --n 1000            → point 1.00%, upper 1.67%
an_stats.py verdict --k 10 --n 1000 --threshold 0.02
```

**Verdict rule** (threshold t):
| Condition | Verdict |
|---|---|
| n = 0 | INSUFFICIENT (МАЛО ДАННЫХ) |
| observed k/n > t | FAIL |
| upper bound ≤ t | PASS |
| otherwise | INSUFFICIENT — observed is fine but not proven; needs more history |

Reference values (t = 2%):
| k / n | observed | upper | verdict |
|---|---|---|---|
| 0 / 100 | 0% | 2.63% | INSUFFICIENT |
| 0 / 133 | 0% | 1.99% | PASS |
| 5 / 500 | 1.0% | 2.04% | INSUFFICIENT |
| 10 / 1000 | 1.0% | 1.67% | PASS |
| 15 / 1000 | 1.5% | 2.28% | INSUFFICIENT |
| 40 / 1000 | 4.0% | 5.15% | FAIL |

## How much data is needed
```
an_stats.py min-n --threshold 0.02 --expected-rate 0.01   → n needed if the true rate is ~1%
```
Use it before searching: segments smaller than this cannot be proven, do not spend time on them.

## Stability over time
A rule that is good on average can be bad in one month (fraud wave, seasonality, a process
change). Check every period:
```
an_stats.py stability --threshold 0.02 --rows "2026-04:520:3,2026-05:498:2,2026-06:510:14"
```
Flags: **UNSTABLE** — even the period's lower bound is above the threshold (the period is bad
with confidence); **watch** — only the observed rate is above it (may be noise of a small period).
An UNSTABLE period → find the cause (a segment, a bank, a channel, an event) before any PASS;
usually the verdict becomes "PASS С УСЛОВИЯМИ" (with an exclusion) or FAIL. A watch period →
look at it and mention it; do not conclude from it alone.

## Comparing two rates (before/after, version A vs B)
```
an_stats.py compare --k1 30 --n1 1000 --k2 18 --n2 1000
```
Two-proportion z-test: difference, its 95% interval, p-value. A difference is "real" only if
the interval does not include 0. Also state if the difference is practically meaningful.

## Pitfalls checklist (the skeptic checks these)
1. **Leakage from the future** — a field filled after the decision (by the human, by later
   processes), or a value corrected by the human instead of the original one, or a counter
   computed over the whole history including the future.
2. **Overfitting** — many segments tried, the best one looks perfect by chance. Confirm
   out-of-time (search on A, verdict on B).
3. **Small sample** — decide by the bound, not the point.
4. **Instability** — check each month; seasonality.
5. **Overlap** — combined effect of rules is computed on their union, never summed.
6. **Selection bias** — ground truth exists only for objects that went to the human.
7. **Label noise** — humans make mistakes too; inspect a sample of disputed cases.
8. **Cost** — errors by amount, not only by count; large amounts separately.
9. **Gaming** — bunching of objects just below a threshold; how easy is it to adapt to the rule.
10. **Process changes** — new OCR version, new rules, new form → analysis period after it.
11. **Definitions** — numerator and denominator of every rate written explicitly; duplicates
    (one object, several rows) removed; time zone and period boundaries correct.
