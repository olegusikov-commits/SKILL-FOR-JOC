---
description: Analyst — learn a topic, or answer any question with numbers: improve a metric, evaluate an idea or a code change, check that code meets the task, verify the effect of a spec, a data question, a report
argument-hint: "learn <topic> [explanation, documents] | verify SPEC-nnn | <task in your words, with paths to documents/code if relevant>"
---

Analysis: $ARGUMENTS

Use the `tl-analytics` skill and follow its rules exactly. Do not modify production code; write
only under `.claude/tl-memory/analysis/`. Data: CORE "Data sources" and
`references/analytical-read-safety.md` (TEST first; PROD within the approved plan; query guard,
probe → expand). Questions with buttons (KIT_GUIDE "Questions").

## Mode `learn <topic>` — build the topic memory (once per topic; also run by the other modes)
1. **Topic.** Derive a short latin slug. Read `.claude/tl-memory/analysis/INDEX.md` — if the topic
   exists, you are updating it: read its files first and show at the end what changed. Read
   `PROJECT_CONTEXT.md` (stack, data sources, PROD/TEST) and `KNOWLEDGE.md` (specs, ADRs and
   reports of the same area are sources too).
2. **Collect sources.** The user's explanation in this conversation is the primary source of
   intent. Documents: the paths the user gave plus relevant docs found in the project (search by
   the topic's business terms). Convert `.docx/.xlsx/.pptx` with `scripts/an_doc2text.py`.
3. **Research in parallel** — `tl-researcher` subagents (one message, several calls), only the
   focuses the topic needs, each with its budget:
   - `docs`: business process, terms, rules, thresholds, who decides what and when;
   - `code`: the decision logic as it really is (decision table with file:line, order of
     conditions, hard stops, reason codes), where the outcome is written;
   - `data` (read-only, catalog + small samples + monthly counts): tables, keys, joins, the
     outcome field, volumes by month, indexed date column, data quality, and for each candidate
     field **when it becomes known** (at decision time or later).
   Give each the topic description, the business terms and what the others are looking for.
   Several sources need data → the data researcher works through the main conversation's
   results if MCP calls are slow (CORE: queries run in the main conversation).
4. **Synthesize** into `TOPIC.md` (profile), `DATA_MAP.md` (incl. glossary and the "known at
   decision time" table), `LOGIC_AS_IS.md`. Resolve contradictions between docs, code and data —
   code and data describe what really happens; docs describe intent. Record every contradiction.
5. **Calibrate early** (if a known business number exists, e.g. "8% automatic"): one bounded,
   aggregated query by month (TEST first if fresh enough; on PROD first ask for the
   once-per-topic query plan approval). Save it to `queries/`, write `BASELINE.md`. Mismatch →
   investigate and record why.
6. **Questions — only now.** Up to 5, buttons, each with your proposed answer and its basis.
   Record them in `TOPIC.md`. Unanswered questions are used as stated assumptions.
7. Update `INDEX.md` and `JOURNAL.md`; `TOPIC.md` starts with its `tl-meta` line; run
   `python .claude/tech-lead-kit/scripts/tl_knowledge.py index`.
8. Reply (learn only): the topic in 3–4 lines, the calibrated baseline, main findings and
   contradictions, the questions with proposed answers, what to analyse next.

## Mode `verify SPEC-nnn` — did the change give what the spec promised?
Playbook `references/playbook-requirement-trace.md` with the spec's REQ / DT / AC as the
criteria, plus the effect of section 14 measured after the change. Verdict PASS / FAIL / МАЛО
ДАННЫХ; tick stage 8 in the task's `FLOW.md`.

## Any other task
1. **Topic.** Find it in `INDEX.md`. An approved spec in `KNOWLEDGE.md` gives the criteria (REQ /
   DT / AC) — check the code against them, not against your own reading of the task.
   - Not found, but an approved spec covers the area → it counts as learned: create the topic's
     `TOPIC.md` with a link to the spec, reuse its glossary, decision tables and `queries/`, and run
     only the missing `learn` steps (usually calibration).
   - Not found or not learned → run the `learn` steps above first, then continue without waiting
     for answers (proposed answers are assumptions).
   - Found → read `TOPIC.md` and the end of `JOURNAL.md`; continue from there.
2. **Frame** in 2–3 lines: question, KPI, guardrail and threshold, period, scenario. Size the
   work: a quick data question → one or two queries and a short answer, no report file; an
   evaluation or improvement → the full cycle and a report.
   Playbook: improve / evaluate a decision-logic change → `references/playbook-decision-automation.md`;
   "does this code meet the task" → `references/playbook-requirement-trace.md`; data question,
   "why is X", before/after → generic cycle + `references/statistics.md`.
3. **Work the cycle** (calibrate → baseline → hypotheses → test → challenge). Every number from a
   saved query or `an_stats.py`. Heavy reading → `tl-researcher` subagents with budgets.
4. **Check before concluding:** `references/validate-before-report.md` (row counts across joins,
   denominators, partial periods, red flags). Then `tl-an-skeptic`, one round, for conclusions
   that recommend a change or carry a verdict; apply its findings and say what changed.
5. **Report** (full cycle only) to `analysis/<topic>/reports/` with `references/report-template.md`
   (`tl-meta` line), with 1–3 charts of the key numbers:
   `python .claude/skills/tl-analytics/scripts/an_chart.py bar|line <result.csv> --x … --y … [--lo --hi]
   [--target …]` → SVG next to the report (inline it in the HTML version); update `HYPOTHESES.md`, `BASELINE.md`, `INDEX.md`, `JOURNAL.md`; run
   `tl_knowledge.py index`.

**Reply in Russian:** the answer first (numbers with bounds and verdict), then the key evidence,
what was rejected and why, risks/assumptions, next steps, the report path. Implementation
recommended → offer the ready task for `/tl-spec` or `/tl-design`. End with the step card.
