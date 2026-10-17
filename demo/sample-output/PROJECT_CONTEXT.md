# PROJECT_CONTEXT — ChequeFlow

> נוצר ע"י /tl-init בתאריך 2026-10-17. מקורות: קוד, README, docs/process.docx, docs/tasks/CHQ-512.md, קטלוג ה-DB דרך MCP (קריאה בלבד).

## Overview
שירות עיבוד שיקים. שיק נסרק (BRANCH_SCAN / MOBILE / ATM), ה-OCR מחזיר סכום, תאריך וחתימה עם רמות ביטחון,
וכללי ההחלטה (`rules.py`) מאשרים אוטומטית (`AUTO_APPROVED`) או מעבירים לפקיד (`TO_CLERK`).
כיום ~8% מאושרים אוטומטית (לפי process.docx). יעד העסק: להגדיל אישור אוטומטי כשהשגיאה באישורים החדשים ≤ 2%.
משימה פתוחה: `docs/tasks/CHQ-512.md` (כלל חדש `AUTO_RECURRING_PAYER`).

## Stack & versions
- Python 3.13 (לפי `__pycache__` cpython-313; אין pyproject / requirements — אין תלויות חיצוניות)
- stdlib בלבד: `sqlite3`, `dataclasses`, `unittest`
- DB בהדגמה: SQLite 3.45.1 (בייצור — SQL Server לפי docstring ב-`repository.py`; גרסה לא ידועה)
- אין CI, אין lint, אין type-checker, אין `.gitignore`

## Structure & modules (`src/chequeflow/`)
| קובץ | אחריות |
|---|---|
| `config.py` | ספי החלטה (סכום, ביטחון OCR, חתימה, היסטוריית מושך, ערוצים מותרים), `DB_PATH` |
| `models.py` | dataclasses קפואים: `Cheque`, `Account`, `Payer`, `Decision` |
| `rules.py` | `decide(cheque, account, payer) -> Decision` — פונקציה טהורה, סדר הבדיקות קובע את קוד הסיבה |
| `repository.py` | `ChequeRepository`: `load`, `save_decision` (SQL מפורמט, `?`) |
| `service.py` | `process_cheque(repo, id)` — load → decide → save |
| `reports.py` | `daily_report` / `weekly_report` — מחרוזות טקסט (ראה סיכונים) |
Layering בפועל: service → (repository, rules) → models/config. `reports.py` עוקף את ה-repository וניגש ישירות ל-sqlite.

## Entry points
- `service.process_cheque(repo, cheque_id)` — הנקודה היחידה לעיבוד שיק. אין CLI / API / batch runner בריפו.
- `reports.daily_report(db_path, day)` / `weekly_report(db_path, days)`.

## Build/Test commands
- בדיקות (מתיקיית השורש): `PYTHONPATH=src python -m unittest discover -s tests` — 5 בדיקות, עוברות.
- build / lint: לא מוגדרים.

## Conventions
- שמות: snake_case; קודי סיבה/תוצאות — קבועי מחרוזת UPPER_SNAKE (אין enum).
- הערות ו-docstrings בעברית (נשמר), זיהויים באנגלית.
- ספים — ב-`config.py` ולא בקוד (דרישה גם ב-CHQ-512).
- DB: SQL ב-parameterized (`?`) ב-repository; חיבור לכל פעולה, `closing(...)`.
- שגיאות: `KeyError` כשהשיק לא נמצא. אין היררכיית חריגים, אין logging.
- בדיקות: unittest, `make_cheque(**overrides)` כ-factory.
- DDL: `sql/schema.sql` יחיד (אין תיקיית migrations / גרסאות).

## Databases
> סביבה: לפי אישור המשתמש (2026-10-17), בסביבת ההדגמה הזו **שני השרתים הם TEST** (עותקי SQLite).
> שני השרתים מוגדרים ב-`.mcp-demo.json` כקבצי SQLite מקומיים (`chequemis.db`, `checkov.db`).
> TEST: שינויים מותרים בהכרזה מראש; פעולות הרסניות (DROP/TRUNCATE/DELETE-UPDATE רחב/ALTER) — רק באישור מפורש.
> אם אותם שמות שרתים יחוברו ל-PROD אמיתי (SQL Server) — להתייחס כ-PROD עד אישור מחדש.

| שרת MCP | מנוע / גרסה | compat level | סביבה | טבלאות עיקריות |
|---|---|---|---|---|
| `meet-chequemis` | SQLite 3.45.1 (לא SQL Server/DB2; probe של שרת לא רלוונטי) | n/a | **TEST** | `branches`(20), `accounts`(8,000), `payers`(3,000), `cheques`(36,000; 2026-01-01..2026-09-30), `auto_decisions`(36,000), `clerk_reviews`(33,575) |
| `meet-checkov` | SQLite | n/a | **TEST** | `clerks`, `audit_log` |

אינדקסים (chequemis): `ix_cheques_received_at`, `ix_cheques_account`, `ix_clerk_reviews_cheque` (+ PK). אין אינדקס על `auto_decisions.decided_at/result`, `cheques.payer_id`.
אינדקסים (checkov): `ix_audit_log_logged_at`.
קשרים: cheques→branches/accounts/payers; auto_decisions 1:1 ל-cheques; clerk_reviews N:1 ל-cheques (בדיקות חוזרות — "ההחלטה האחרונה קובעת").
מונחי תחום מ-process.docx: `risk_flag` נקבע ע"י הפקיד בזמן הבדיקה; `is_spot_check=1` — דגימה של ~3% מהאישורים האוטומטיים;
OCR engine הוחלף ל-v3.1 ב-2026-04-01 (v2.4 היה "בטוח מדי" ברמות ביטחון).
`clerk_id` ב-chequemis מפנה ל-`clerks` ב-checkov — **אין FK** בין מסדי הנתונים.

## Integrations
- OCR (מקור הנתונים: ocr_* בעמודות cheques) — אין קוד אינטגרציה בריפו; מגיע מוכן ל-DB.
- ערוצי קלט: סניף, אפליקציה (MOBILE), כספומט — רק כערך בעמודה `channel`.
- אין MQ / web service / mainframe בקוד.

## Known risks & observations
1. `reports.daily_report` — SQL נבנה בשרשור מחרוזות (`day`) ← SQL injection (TD-001).
2. אותה שאילתה: `substr(received_at,1,10) = ...` — לא SARGable, אינדקס `ix_cheques_received_at` לא בשימוש (TD-002).
3. `reports.py`: `except Exception: pass`, פונקציה ארוכה עם לוגיקה ושליפה מעורבבים, חיבור שלא נסגר בחריגה (TD-003).
4. `save_decision` לא אידמפוטנטי: `auto_decisions.cheque_id` הוא PK → עיבוד חוזר זורק `IntegrityError` (TD-004).
5. אין בדיקות ל-service / repository / reports; אין בדיקות גבול לספים (TD-005).
6. `__pycache__` ו-`*.db` (9MB) ב-git, אין `.gitignore` (TD-006).
7. `payer_prev_cheques` — שדה מחושב-מראש בעת הקבלה (denormalized), "מושך→חשבון" לפי docx; אין דרך לאמת אותו מהנתונים בלי חישוב מחדש.

## Open questions
- ייצור: SQL Server (איזו גרסה / compat level)? ה-SQLite הוא רק הדגמה?
- CHQ-512: "לפחות 6 שיקים קודמים **לאותו חשבון**" מול `payer_prev_cheques` (מושך→חשבון לפי docx) — האם זה אותו שדה? ומה ההגדרה המדויקת של "שגיאה" ב-2% (נדחה / תוקן סכום / risk_flag=SUSPICIOUS)?
- `MIN_PAYER_HISTORY=3` ב-config מול 6 ב-CHQ-512: אותו סף או סף נפרד לכלל החדש?
- איך מתנהגים עם בדיקה חוזרת של מפקח (כמה שורות ב-clerk_reviews לשיק)?
- איפה רץ השירות בפועל (נקודת כניסה אמיתית, תזמון, לוגים)?
