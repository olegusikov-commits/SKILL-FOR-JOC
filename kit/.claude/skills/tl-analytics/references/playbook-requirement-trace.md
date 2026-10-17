# Playbook: does the code meet the task?

Input: a task (the user's explanation in the conversation, a document, a ticket text) and code
(files, folder, or the uncommitted changes / a git diff). Output: a verdict with a traceability
matrix and, when the code changes decision logic, the expected effect measured on history.

## 1. Extract criteria from the task
If an approved spec covers the task (`.claude/tl-memory/KNOWLEDGE.md`), its REQ, decision-table
rows and AC **are** the criteria — use their ids in the matrix and add only implicit and boundary
criteria the spec missed (report those as gaps of the spec). Otherwise, write a numbered list
before reading the code, so the code does not bias you:
- **Explicit** requirements — what the task literally says (each one testable).
- **Implicit** requirements — what any senior would expect even if unsaid: existing hard stops
  still apply, logging/reason codes like the rest of the module, no change in behaviour for
  cases outside the scope, configuration instead of magic numbers if the module does so.
  Mark them as implicit — they are findings of lower weight.
- **Boundary cases** — values exactly at thresholds, empty/NULL data, units (agorot vs shekels),
  dates, duplicates.
- **Measurable goal** if any ("raise automation", "reduce errors") → it will be measured.
If the task is ambiguous, write your interpretation and continue (question protocol).

## 2. Read the code as it really is
Delegate to `tl-researcher` (focus `code`): the real decision table of the changed code and
of the code before the change (git diff / previous version if available), with file:line, the
order of conditions and the default branch.

## 3. Traceability matrix
| # | Criterion | Type | Where in code (file:line) | Status | Comment |
|---|---|---|---|---|---|
| 1 | ... | explicit | src/rules.py:44 | ✔ выполнено | |
| 2 | ... | explicit | — | ✖ не выполнено | evidence |
| 3 | ... | implicit | src/rules.py:51 | ◐ частично | threshold is `>` instead of `>=` |
| 4 | ... | boundary | — | ? нельзя проверить | why |

Also list **extra behaviour**: what the code does that the task did not ask for (scope creep or
a bug).

## 4. Measure the effect (if the code changes decision logic or a measurable goal exists)
Use `playbook-decision-automation.md` step 8: translate code → SQL (mapping table), calibrate,
backtest, verdict against the threshold. If some criterion is not met (e.g. a hard stop is
missing), measure **both**: the code as written and the code as the task requires — the
difference shows the cost of the gap (e.g. "без проверки блокировки ошибка 2,6% → FAIL;
с проверкой 1,1% → PASS").

## 5. Verdict
- **Отвечает задаче: да / частично / нет** — "да" only if all explicit criteria are ✔ and no
  hard stop is broken.
- **Ожидаемый эффект:** KPI before → after, guardrail metric with bound, verdict.
- What must be fixed (blocking) vs. recommended.
- Run `tl-an-skeptic` on the verdict before giving it.
