# Writing standard for every kit document

A kit document is read by a developer who must build from it, a tester who must test it, or a
manager who must decide. Every line either gives them a fact, a decision or an action — or it is
deleted. This applies to specs, designs, ADRs, reports, project documents and explanations, in
every language. (Diagrams and HTML: `oleg-skill-hesber/references/writing-guide.md`.)

## The rules
1. **Answer first.** The first line of a section is its conclusion; evidence follows.
2. **Every claim has a source** — `[מקור: קוד src/x.py:21]`, `[מקור: נתונים D-3]`,
   `[מקור: מסמך process.docx §2]`, `[מקור: ADR-002]` — or is marked `[הנחה]`. Reports in Russian
   use the same tags or "(источник: …)".
3. **Numbers, not adjectives.** A number has a unit, a period, a source and, for estimates, a
   bound. "Fast" → "≤ 300 ms p95"; "many" → "4 812 per month (2026-09, D-2)".
4. **Exact names.** Tables, columns, files, codes and endpoints exactly as in the code, in `code`.
5. **Tables over paragraphs** for rules, comparisons, mappings, options and scenarios.
6. **Nothing empty.** A section with nothing true to say is deleted, or one line "לא רלוונטי"
   where a reader would expect it. No "TBD", no placeholders, no "will be decided later" without
   a named question `Q-n`.
7. **Length follows the decision.** One page for a small change; the template's size budget is a
   maximum, not a target. No restating the request, no generic background, no summary that
   repeats the document.

## Words that mean nothing — replace with a fact or delete
| Instead of | Write |
|---|---|
| significant(ly), substantial, dramatically · משמעותי · значительно | the number and its bound |
| efficient, optimal, robust, scalable, seamless, best practice · יעיל, אופטימלי · эффективный, оптимальный | what exactly it does and the measured / required value |
| as needed, if necessary, appropriate, reasonable · לפי הצורך, בהתאם, סביר · по необходимости, при необходимости, разумный | the condition and the value |
| etc., and so on · וכו' · и т.д. | the full list, or "the list in table X" |
| "it is important to note", "in conclusion", "this document describes" | delete |
| should probably, might, could potentially | a decision, or an assumption `[הנחה]` with its question |

## Self-check before saying "done"
- Remove every sentence the reader would not miss.
- Each section: does its first line answer a question someone asked?
- Pick 3 claims at random: is the source there and does it say that?
- No word from the table above is left without a number next to it.
