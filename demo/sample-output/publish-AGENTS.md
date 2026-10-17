# AGENTS.md

<!-- tech-lead-kit:begin -->
<!-- generated from the documents in docs/ — edits inside this block are overwritten -->
## ידע על הפרויקט

לפני שינוי בקוד או בנתונים — פתח את המסמך שה"תחום" שלו נוגע בשינוי.
אפיון מאושר ו-ADR שהתקבל מחייבים: אם המשימה סותרת אותם — עצור ואמור זאת.
אם ההתנהגות שמתוארת במסמך משתנה — עדכן גם את המסמך באותו שינוי.

| מסמך | סוג | סטטוס | תאריך | תחום |
|---|---|---|---|---|
| [SPEC-001: אישור אוטומטי לשיקים של מושכים קבועים](docs/specs/SPEC-001-auto-approve-regular-drawer-cheques.md) · [html](docs/specs/SPEC-001-auto-approve-regular-drawer-cheques.html) | אפיון | approved | 2026-10-17 | src/chequeflow/rules.py, src/chequeflow/config.py, tests/test_rules.py, auto_decisions.re… |

### עובדות על הפרויקט
**ChequeFlow** — שירות Python (ספריית תקן) להחלטה אוטומטית על שיקים: אישור אוטומטי או העברה לפקיד.
- קוד ראשי: `src/chequeflow/` (`rules.py` — לוגיקה עסקית, `config.py` — ספים, `repository.py` — נתונים).
- בדיקות: `PYTHONPATH=src python -m unittest discover -s tests`.
- מסדי נתונים רק דרך שרתי MCP: `meet-chequemis` (שיקים, החלטות, ביקורות פקיד), `meet-checkov` (פקידים, יומן ביקורת).
- שני השרתים הם **TEST** (עותקי SQLite להדגמה); שינויים מותרים רק עם הצגת ההצהרה מראש, ופעולות הרסניות — באישור מפורש. **PROD הוא לקריאה בלבד** תמיד.
- שינויי סכמה נמסרים כקבצי סקריפט ב-`sql/`, לא מורצים על PROD.
- ספים עסקיים רק ב-`config.py`; שאילתות תמיד parameterized (`?`).
- הערות בקוד ובמסמכים בעברית, מזהים באנגלית.

<!-- tech-lead-kit:end -->
