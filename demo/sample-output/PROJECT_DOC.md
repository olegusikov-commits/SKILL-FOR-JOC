# ChequeFlow — מסמך פרויקט
גרסה 1 · 2026-10-17 · מקורות: קוד (commit `814f489`, branch נוכחי), מסדי נתונים `chequemis.db` / `checkov.db` (SQLite, סביבת TEST, קריאה בלבד), מסמכים (`README.md`, `docs/process.docx`, `docs/tasks/CHQ-512.md`)

> גרסה ראשונה — אין מסמך קודם לעדכון. הנתונים המספריים נמדדו על עותקי ההדגמה (36,000 שיקים, 2026-01-01..2026-09-30).

## 1. מטרה והקשר עסקי
ChequeFlow הוא שירות עיבוד שיקים: שיק מופקד בסניף (`BRANCH_SCAN`), באפליקציה (`MOBILE`) או בכספומט (`ATM`), מנוע OCR מזהה סכום, תאריך וחתימה ומחזיר רמת ביטחון לכל שדה, וכללי ההחלטה מאשרים אוטומטית (`AUTO_APPROVED`) או מעבירים לפקיד (`TO_CLERK`) (`docs/process.docx`; `src/chequeflow/rules.py:8-9`).
כיום רק כ-8% מהשיקים מאושרים אוטומטית (process.docx; במסד: 2,995 מתוך 36,000 = 8.3%), והשאר מעמיס על הפקידים.
יעד העסק: להגדיל את האישור האוטומטי כך ששיעור הטעויות באישורים האוטומטיים החדשים לא יעלה על 2% (process.docx; `docs/tasks/CHQ-512.md`).
משימה פתוחה: CHQ-512 — כלל חדש `AUTO_RECURRING_PAYER` למושכים מוסדיים קבועים (ראה סעיף 11).
קהל היעד של המסמך: מפתח חדש בצוות.

## 2. תמונה כללית (ארכיטקטורה)
```
 OCR (חיצוני, אין קוד בריפו)         פקיד / מפקח (חיצוני, אין קוד בריפו)
        │ כותב cheques.ocr_*                  │ כותב clerk_reviews, cheques.risk_flag
        ▼                                     ▼
 ┌────────────────────── chequemis.db (SQLite בהדגמה) ───────────────────┐
 │ branches · accounts · payers · cheques · auto_decisions · clerk_reviews│
 └───────▲───────────────────────────────▲───────────────────────────────┘
         │ load / save_decision          │ SELECT ישיר (עוקף repository)
 ┌───────┴────────────── src/chequeflow ─┴────────────┐
 │ service.process_cheque ─► rules.decide (טהור)       │
 │        │                    └─► config (ספים)       │
 │        └─► repository.ChequeRepository              │
 │ reports.daily_report / weekly_report                │
 └─────────────────────────────────────────────────────┘
 checkov.db: clerks, audit_log — לא בשימוש בקוד; קשר ל-chequemis רק לוגי (clerk_id, ללא FK)
```
שכבות בפועל: `service` → (`repository`, `rules`) → `models`/`config`. `reports.py` חריג: ניגש ישירות ל-sqlite (`reports.py:1,5`).
סגנון: מודול אחד (monolith קטן), ספרייה בלבד — אין שרת, CLI או scheduler בריפו.

## 3. מודולים ואחריות
| מודול | אחריות | שכבה | נקודות כניסה | נתיב |
|---|---|---|---|---|
| `config` | ספי החלטה וערוצים מותרים, `DB_PATH` | תצורה | — | `src/chequeflow/config.py` |
| `models` | dataclasses קפואים: `Cheque`, `Account`, `Payer`, `Decision` | דומיין | — | `src/chequeflow/models.py` |
| `rules` | `decide(cheque, account, payer) -> Decision` — פונקציה טהורה; הבדיקה הראשונה שנכשלת קובעת את קוד הסיבה | דומיין | `decide` | `src/chequeflow/rules.py` |
| `repository` | `ChequeRepository.load` / `save_decision` (SQL עם `?`, חיבור לכל פעולה) | גישה לנתונים | `load`, `save_decision` | `src/chequeflow/repository.py` |
| `service` | `process_cheque`: load → decide → save | יישום | `process_cheque` | `src/chequeflow/service.py` |
| `reports` | דוחות יומי/שבועי כטקסט | דיווח (עוקף שכבות) | `daily_report`, `weekly_report` | `src/chequeflow/reports.py` |
| tests | 5 בדיקות ל-`decide` בלבד | — | — | `tests/test_rules.py` |

## 4. תהליכים עיקריים
**4.1 עיבוד שיק** (`service.py:9-13`)
1. `process_cheque(repo, cheque_id)` → `repo.load` מבצע JOIN של `cheques`+`accounts`+`payers`; אם אין שיק — `KeyError` (`repository.py:30-31`).
2. `rules.decide` מריץ את הבדיקות לפי הסדר: חשבון לא `ACTIVE` → `ACCOUNT_BLOCKED`; חשד כפילות → `DUPLICATE_SUSPECT`; ערוץ → `CHANNEL_NOT_ALLOWED`; סכום > 1,000 → `AMOUNT_LIMIT`; ביטחון סכום < 0.95 → `LOW_OCR_AMOUNT`; ביטחון תאריך < 0.90 → `LOW_OCR_DATE`; חתימה < 0.85 → `LOW_SIGNATURE`; פחות מ-3 שיקים קודמים → `NEW_PAYER`; אחרת `OK` (`rules.py:14-32`).
3. `repo.save_decision` כותב שורה ל-`auto_decisions` עם `decided_at` ב-UTC.

**4.2 בדיקת פקיד ובדיקה חוזרת** (process.docx, נתונים): שיק שהועבר לפקיד נכנס ל-`clerk_reviews` (APPROVED/REJECTED, `corrected_amount`), הפקיד קובע `cheques.risk_flag`; בדיקה חוזרת של מפקח מוסיפה שורה נוספת — "ההחלטה האחרונה קובעת". במסד: 32,593 שיקים עם בדיקה אחת, 491 עם שתיים. **אין קוד בריפו לשלב הזה** — הוא קורה במערכת אחרת.

**4.3 דגימת ביקורת (spot check)**: כ-3% מהאישורים האוטומטיים נבדקים בדיעבד (`is_spot_check=1`). במסד: 79 מתוך 2,995 (2.6%); אין קוד בריפו שמבצע את הדגימה.

**4.4 דוחות** (`reports.py`): `daily_report(db_path, day)` שולף שיקים+החלטות ליום, סופר סה"כ, אושרו אוטומטית, מעל 1,000 ₪, ביטחון סכום < 0.9, ופירוק לפי סניף; `weekly_report` מצרף דוחות יומיים.

## 5. מודל נתונים
מקור: `sql/schema.sql` ו-`sqlite_master` של המסד (זהים). נפחים נמדדו ב-2026-10-17.

**chequemis**
| טבלה | מטרה | מפתח / קשרים | שורות |
|---|---|---|---|
| `branches` | סניפים (`name`, `region`) | PK `branch_id` | 20 |
| `accounts` | חשבונות (`segment`, `status` ACTIVE/BLOCKED/CLOSED) | PK `account_id`; FK→branches | 8,000 |
| `payers` | מושכים (`payer_type`: PRIVATE 1,851 / COMPANY 846 / GOVERNMENT 303; `bank_code`) | PK `payer_id` | 3,000 |
| `cheques` | שיק שהתקבל: שדות `ocr_*`, `ocr_engine_version` (v2.4: 12,000 עד 31.3; v3.1: 24,000 מ-1.4), `payer_prev_cheques` (מחושב בעת קבלה), `is_duplicate_suspect`, `risk_flag` | PK `cheque_id`; FK→branches/accounts/payers | 36,000 |
| `auto_decisions` | החלטת הכללים | PK=FK `cheque_id` (1:1) | 36,000 |
| `clerk_reviews` | בדיקות פקיד/מפקח/דגימה | PK `review_id`; `cheque_id` (FK, N:1); `clerk_id` ללא FK | 33,575 |

אינדקסים: `ix_cheques_received_at`, `ix_cheques_account`, `ix_clerk_reviews_cheque` (+ PK). אין אינדקס על `cheques.payer_id`, `cheques.branch_id`, `auto_decisions.decided_at/result`.

**checkov**: `clerks` (40; `team`, `is_supervisor`), `audit_log` (2,000; `logged_at`, `clerk_id`, `action`, `cheque_id`; אינדקס `ix_audit_log_logged_at`). הקוד אינו ניגש ל-checkov.

התפלגות החלטות (36,000): AMOUNT_LIMIT 12,120 · CHANNEL_NOT_ALLOWED 10,212 · LOW_OCR_AMOUNT 3,476 · NEW_PAYER 3,237 · OK 2,995 · ACCOUNT_BLOCKED 1,352 · LOW_SIGNATURE 1,100 · LOW_OCR_DATE 1,024 · DUPLICATE_SUSPECT 484.
`risk_flag`: NULL ב-2,916 שיקים — בדיוק האישורים האוטומטיים ללא ביקורת (2,995 − 79 דגימות). כלומר `risk_flag` מתמלא רק ע"י פקיד.

**מי קורא/כותב מה (מהקוד):**
| מודול | קורא | כותב |
|---|---|---|
| `repository.load` | cheques, accounts, payers | — |
| `repository.save_decision` | — | auto_decisions |
| `reports.daily_report` | cheques, auto_decisions | — |
| (מחוץ לריפו) OCR / פקיד | — | cheques, clerk_reviews, risk_flag |

## 6. אינטגרציות
- **OCR** — אין קוד אינטגרציה; הנתונים מגיעים מוכנים בעמודות `cheques.ocr_*`. מנוע הוחלף ל-v3.1 ב-2026-04-01 (process.docx; תואם לנתונים).
- **מערכת הפקידים** — אין קוד; כותבת ל-`clerk_reviews`/`risk_flag`.
- **MQ / web service / mainframe** — אין בקוד. בעלים ותדירות: לא ידוע (שאלה פתוחה).

## 7. תצורה וסביבות
- כל התצורה בקובץ `src/chequeflow/config.py` כקבועי מודול (לא env, לא קובץ חיצוני): `AUTO_APPROVE_MAX_AMOUNT=1000.0`, `OCR_AMOUNT_MIN_CONF=0.95`, `OCR_DATE_MIN_CONF=0.90`, `SIGNATURE_MIN_SCORE=0.85`, `MIN_PAYER_HISTORY=3`, `AUTO_APPROVE_CHANNELS={BRANCH_SCAN, ATM}`, `DB_PATH="chequemis.db"`.
- `.mcp-demo.json` מגדיר שני שרתי MCP (`meet-chequemis`, `meet-checkov`) ככלי SQLite מקומיים; בהדגמה שניהם TEST (לפי PROJECT_CONTEXT, אישור משתמש). אם יחוברו ל-PROD אמיתי — לטפל כ-PROD.
- סביבות DEV/TEST/PROD, feature flags: לא קיימים בקוד.
- מנוע ייצור: SQL Server לפי docstring ב-`repository.py:1`; גרסה לא ידועה.

## 8. בנייה, בדיקות ופריסה
- בדיקות (משורש הפרויקט): `PYTHONPATH=src python -m unittest discover -s tests` — הורצו: 5 בדיקות, OK.
- Python 3.13 (לפי `__pycache__`), stdlib בלבד. אין `pyproject`/`requirements`, CI, lint, type-checker או סקריפט פריסה.

## 9. תפעול
אין logging, ניטור, jobs או תזמון בריפו. כשל צפוי היחיד שמטופל: `KeyError` על שיק לא קיים. עיבוד חוזר של אותו שיק יזרוק `sqlite3.IntegrityError` (PK על `auto_decisions.cheque_id`, `repository.py:48`). איפה השירות רץ בפועל — לא ידוע.

## 10. אבטחה
אין אימות/הרשאות בקוד (ספרייה). אין סודות בקוד; חיבור ל-DB מוגדר לפי נתיב קובץ. נקודת תורפה: `daily_report` משרשר את `day` ישירות ל-SQL (`reports.py:10`) — SQL injection (TD-001). קבצי `*.db` ב-git עשויים להכיל נתוני לקוחות (TD-006).

## 11. סיכונים, חוב טכני ותצפיות
| ID | נושא | הערה |
|---|---|---|
| TD-001 | SQL injection ב-`daily_report` | עדיפות 45; להחליף ב-`?` |
| TD-002 | `substr(received_at,1,10)=` לא SARGable | `ix_cheques_received_at` לא בשימוש |
| TD-003 | `except Exception: pass`, לוגיקה+שליפה מעורבבות, חיבור לא נסגר בחריגה | `reports.py:40-43` |
| TD-004 | `save_decision` לא אידמפוטנטי | retry → `IntegrityError` |
| TD-005 | אין בדיקות ל-service/repository/reports ולספי גבול | |
| TD-006 | `__pycache__` ו-`*.db` (9MB) ב-git, אין `.gitignore` | |
| TD-007 | אין אריזה/CI/lint; קודי סיבה כמחרוזות ללא enum | יקשה על CHQ-512 |

תצפיות נוספות (חדשות, לא ברישום החוב):
1. **ספים משוכפלים בדוח:** `reports.py:21,23` מקודד קשיח 1000 ו-0.9 במקום `config` (0.9 ≠ `OCR_AMOUNT_MIN_CONF=0.95`) — "low OCR" בדוח אינו תואם לכלל ההחלטה.
2. **פורמט זמן לא אחיד:** `service` כותב `decided_at` כ-`datetime.now(timezone.utc).isoformat()` (עם `+00:00`), בעוד שבנתונים הקיימים הערכים נאיביים (`2026-01-01T00:09:41`) וגם `received_at` נאיבי — השוואות/מיון טקסטואליים עלולים להתנהג בצורה שונה.
3. **CHQ-512 — ההיקף העסקי:** בנתונים 13,168 שיקים מעל 1,000 ₪ הם של מושכים COMPANY/GOVERNMENT (37% מכלל השיקים) — זה הפוטנציאל, לא ההערכה; הערכת שיעור שגיאה דורשת ניתוח (`/tl-an`) והגדרת "שגיאה".
4. **סתירה במסמכים:** CHQ-512 אומר "6 שיקים קודמים **לאותו חשבון**", process.docx מגדיר `payer_prev_cheques` כ-"מאותו מושך לאותו חשבון" — כנראה אותו שדה, לא אושר.

## 12. מילון מונחים
| מונח | משמעות | היכן |
|---|---|---|
| שיק / `cheque` | שיק שהופקד | טבלה `cheques`, `models.Cheque` |
| מושך / `payer` | מי שחתם על השיק (PRIVATE/COMPANY/GOVERNMENT) | `payers`, `models.Payer` |
| `AUTO_APPROVED` / `TO_CLERK` | תוצאת ההחלטה האוטומטית | `rules.py:8-9`, `auto_decisions.result` |
| `reason_code` | סיבת ההחלטה (`OK` או אחד מקודי הסירוב) | `auto_decisions.reason_code` |
| `payer_prev_cheques` | מספר שיקים קודמים מהמושך לחשבון, מחושב בעת קבלה | `cheques` |
| `risk_flag` | דגל OK/SUSPICIOUS שהפקיד קובע | `cheques.risk_flag` |
| `is_spot_check` | בדיקת דגימה בדיעבד (~3%) של אישור אוטומטי | `clerk_reviews` |
| בדיקה חוזרת | מפקח בודק שוב; האחרונה קובעת | `clerk_reviews` (כמה שורות לשיק) |
| `ocr_engine_version` | גרסת OCR (v2.4 → v3.1 ב-1.4.2026) | `cheques` |

## 13. שאלות פתוחות
1. ייצור: האם SQL Server (איזו גרסה)? האם ה-SQLite הוא רק הדגמה? — את מי לשאול: בעלי המערכת/DBA.
2. איפה השירות רץ בפועל (נקודת כניסה, תזמון, לוגים)? מי קורא ל-`process_cheque`?
3. CHQ-512: האם `payer_prev_cheques` הוא אותו שדה כמו "6 שיקים לאותו חשבון"? מהי "שגיאה" ב-2% (נדחה / תוקן סכום / `SUSPICIOUS`)? האם סף ה-6 נפרד מ-`MIN_PAYER_HISTORY=3`?
4. מי כותב ל-`cheques` (OCR/קליטה) ומי מחשב את `payer_prev_cheques` ובעת קבלה — באיזה קוד?
5. איך מבוצעת דגימת ה-3% ומי בוחר אותה?
6. האם הנתונים ב-`*.db` אמיתיים או סינתטיים (TD-006)?
7. מה הקשר הרצוי בין `clerks`/`audit_log` (checkov) לבין השירות — האם מתוכנן שימוש?
