---
description: Analyst learns a topic (from your explanation, documents, code and the database), builds the topic memory, then asks only the questions that remain — each with a proposed answer
argument-hint: "<topic name> [your explanation, documents/paths to read]"
---

Learn the topic for analysis. User input: $ARGUMENTS

Use the `tl-analytics` skill (rules, topic memory layout in `references/topic-memory.md`).
Do NOT change production code. Write only under `.claude/tl-memory/analysis/`.

1. **Topic.** Derive a short latin slug from the topic name. Read
   `.claude/tl-memory/analysis/INDEX.md` — if the topic exists, you are updating it: read its
   files first and show at the end what changed. Read `.claude/tl-memory/PROJECT_CONTEXT.md` if
   it exists (stack, databases, PROD/TEST mapping).
2. **Collect sources.** The user's explanation in this conversation is the primary source of
   intent. Documents: the paths the user gave plus relevant docs found in the project (search
   by the topic's business terms). Convert `.docx/.xlsx/.pptx` with
   `scripts/an_doc2text.py`.
3. **Research in parallel** — launch `tl-researcher` subagents (one message, several calls):
   - focus `docs`: business process, terms, rules, thresholds, who decides what and when;
   - focus `code`: the decision logic as it really is (decision table with file:line, order of
     conditions, hard stops, reason codes), where the outcome is written;
   - focus `data` (SQL MCP, read-only, catalog + small samples + monthly counts): tables,
     keys, joins, the outcome field, volumes by month, indexed date column, data quality, and
     for each candidate field **when it becomes known** (at decision time or later).
   Give each the topic description, the business terms and what the others are looking for.
4. **Synthesize** into `TOPIC.md` (profile), `DATA_MAP.md` (incl. glossary and the
   "known at decision time" table), `LOGIC_AS_IS.md`. Resolve contradictions between docs,
   code and data — code and data describe what really happens; docs describe intent. Record
   every contradiction.
5. **Calibrate early** (if a known business number exists, e.g. "8% automatic"): one bounded,
   aggregated query by month (follow `references/analytical-read-safety.md`: TEST first if fresh
   enough; on PROD first ask for the once-per-topic query plan approval). Save it to `queries/`, write
   `BASELINE.md`. Mismatch → investigate and record why.
6. **Questions — only now, after learning.** Up to 5, each with your proposed answer and its
   basis (question protocol in the skill). Typical: exact definition of the error/outcome,
   threshold scope, period, which conditions are hard stops, whether spot-checks exist for
   automatic decisions. Record them in `TOPIC.md`.
7. Update `INDEX.md` and `JOURNAL.md`.
8. **Reply in Russian:** what the topic is in 3–4 lines (your understanding), the calibrated
   baseline, the main findings and contradictions, the questions with proposed answers, and
   what you suggest analysing next. Do not wait for answers to continue other work the user asks
   for — unanswered questions are used as stated assumptions.
