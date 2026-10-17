---
description: Give the analyst any analysis task — improve a metric, evaluate an idea or a code change, check that code meets a task, answer a data question, write a report
argument-hint: "<task in your words, with paths to documents/code if relevant>"
---

Analysis task: $ARGUMENTS

Use the `tl-analytics` skill and follow its rules exactly. This is an **ANALYSIS** task: do not
modify production code; write only under `.claude/tl-memory/analysis/`.

1. **Topic.** Read `.claude/tl-memory/analysis/INDEX.md` and find the topic of this task. Read
   `.claude/tl-memory/KNOWLEDGE.md`: an approved spec for the task gives the criteria (REQ / DT /
   AC) — check the code against them, not against your own reading of the task.
   - Not found or not learned → do the `/tl-an-learn` steps first (read
     `.claude/commands/tl-an-learn.md`), then continue with the task without waiting for
     answers (use your proposed answers as assumptions).
   - Found → read `TOPIC.md` and the end of `JOURNAL.md`; continue from there.
2. **Frame** the task in 2–3 lines: question, KPI, guardrail and threshold, period, scenario.
   Choose the playbook:
   - improve / find opportunities / evaluate an idea or a decision-logic change →
     `references/playbook-decision-automation.md` (if the topic is a decision process),
     otherwise the generic cycle;
   - "does this code meet the task", "check this implementation" →
     `references/playbook-requirement-trace.md`;
   - data question, "why is X", before/after → generic cycle + `references/statistics.md`.
3. **Work the cycle** (calibrate → baseline → hypotheses → test → challenge). Every number from a
   saved query or `an_stats.py`. Heavy reading → `tl-researcher` subagents. Respect
   `references/analytical-read-safety.md` (TEST first; PROD within the approved plan).
4. **Challenge:** before the final answer, delegate to `tl-an-skeptic` with the conclusions,
   numbers, query files and the topic folder path. Apply its findings: fix, recompute, or
   downgrade verdicts. Mention what the skeptic changed.
5. **Report** to `analysis/<topic>/reports/` using `references/report-template.md` (with its
   `tl-meta` line); update `HYPOTHESES.md`, `BASELINE.md`, `INDEX.md`, `JOURNAL.md`; run
   `python .claude/tech-lead-kit/scripts/tl_knowledge.py index`.
6. **Reply in Russian:** the answer first (numbers with bounds and verdict), then the key
   evidence, what was rejected and why, risks/assumptions, next steps, the report path.
   If implementation is recommended, offer the ready task for `/tl-design`.
