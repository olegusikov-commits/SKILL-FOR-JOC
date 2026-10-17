# Playbook: decision automation

For processes where an object (cheque, request, claim, document…) is either decided
**automatically** or sent to a **human**, and the goal is to decide automatically more often
without exceeding an error threshold. The human's decision is the ground truth.

Also used to evaluate **an idea or a code change** of the decision logic: "how much will it
raise automation and what error will it bring?"

## 0. Prerequisites (from learning)
- `LOGIC_AS_IS.md`: every condition of the current automatic decision, its threshold and
  reason code, with file:line. Mark **hard stops** — conditions that must never be relaxed by
  a new rule (blocked/closed account, duplicates, legal holds, fraud lists, missing mandatory
  data). A new rule relaxes "soft" conditions only, unless the user explicitly says otherwise.
- `DATA_MAP.md`: the outcome field (human decision), and for every candidate field — **is it
  known at the moment of the automatic decision?** Fields filled by the human or later
  processes are forbidden in rules (leakage). Values must be the ones the automation saw
  (e.g. OCR value, not the value corrected by the human).
- Who has ground truth: usually only objects that went to the human. Objects decided
  automatically today often have none (or only a spot-check sample). Say so explicitly.

## 1. Define the error precisely
Default definition (propose it to the user, do not block on it):
- **Error of an automatic approval** = the human **rejected** the object, **or** approved it
  only **after correcting decision-relevant data** (amount, date, account…) — because the
  automation would have approved wrong data.
- Show both numbers if they differ a lot: "rejected only" and "rejected or corrected".
- Count errors **by number** and **by amount** (money). Report large amounts separately.

## 2. Population and periods
- Use the period after the last change of the process (new OCR version, new rules) — find it
  in code history, documents or in the data (sudden shift in shares by month).
- Split by time: **period A** (earlier, ~2/3) for searching, **period B** (later, ~1/3) for
  confirmation. Report final numbers on period B (and on A+B for stability).
- Evaluation population for a new rule: objects that today go to the human (that is where the
  gain comes from), with known human decision.

## 3. Calibrate
1. Reproduce today's automation rate (known to the business) by month. Must match.
2. **Calibrate the logic translation:** translate the CURRENT logic from `LOGIC_AS_IS.md` into a
   SQL predicate and compare with the actual automatic decisions stored in the data
   (agreement %). ≥ 99% agreement → your understanding of the logic and data is trustworthy.
   Lower → find and explain the mismatch before evaluating any new rule.

## 4. Baseline and ceiling
- Funnel: share of objects stopped by each condition (first failing condition, in the order the
  code checks them) and the human approval rate inside each group.
- **Ceiling** = share of all objects that went to the human and were approved without
  correction. No rule can gain more than this.
- Groups where the human approves almost everything are the first candidates.

## 5. Search for opportunities (period A)
Work only with decision-time fields. In order:
1. **Over-strict conditions:** for each soft condition, the human error rate among objects
   stopped *only* by it.
2. **Threshold relaxation:** for numeric thresholds (confidence, amount, age…), compute the
   error in the **marginal band** that a relaxed threshold would add (e.g. OCR 0.90–0.95), not
   in the whole population.
3. **Segments:** error rate and n by single fields (categorical values, numeric bins), then by
   pairs of the best fields.
4. **User / document / code ideas:** every idea becomes a hypothesis too.
Candidate if: observed error on A ≤ half the threshold and n large enough
(`an_stats.py min-n`). Avoid IDs and fields that a customer can easily game (check for
bunching just below a threshold).
Register each candidate in `HYPOTHESES.md` with its **mechanism** (why it should work).

## 6. Backtest (period B)
For each hypothesis, one SQL query (`references/backtest-sql.md`) gives, by month:
- `n_all` — all objects in the period; `n_new` — objects the rule would newly automate
  (rule true, hard stops pass, not automated today); `k_err` — errors among them; error amount.
- Gain in percentage points = `n_new / n_all`.
Then:
- `an_stats.py verdict --k <k_err> --n <n_new> --threshold <t>` → PASS / FAIL / INSUFFICIENT.
- `an_stats.py stability --rows "<month>:<n>:<k>,..." --threshold <t>` → no month above threshold.
- Error by amount and for large amounts.

## 7. Combine
Accepted rules overlap. Compute the **union** with one query (rule1 OR rule2 OR …): total gain
and total error, then the verdict on the union. Never add up gains of separate rules.

## 8. Evaluate a given code change
1. `tl-an-researcher` (focus `code`) builds the decision table of the **new** code and of the
   current code, with file:line for each condition.
2. Translate each condition into SQL, row by row; keep the mapping table
   (code condition → SQL expression) in the report.
3. Calibrate the translation method on the current code (step 3.2). If the code is Python and
   can be run safely on a sample of rows, run it and compare decisions with the SQL predicate.
4. Backtest as in step 6; compare with the current logic: gain, error, verdict.
5. Note conditions that cannot be expressed on historical data (e.g. external service calls)
   and what that means for the confidence of the estimate.

## 9. Challenge, conclude, hand off
- `tl-an-skeptic` reviews every PASS and the union.
- Report: recommended rule set (exact conditions), gain and error with bounds, by month,
  by amount; what is excluded and why; rollout (shadow mode 2–4 weeks → limited launch →
  full); **monitoring SQL** (weekly automation rate and error, rollback trigger: error above
  threshold in a week); ready task text for `/tl-design`.
