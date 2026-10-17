# מסמך תכנון: העברת שיקים שנדחו ע"י פקיד לאנטי-פרוד דרך IBM MQ

**תאריך:** 2026-10-17   **סטטוס:** טיוטה (ממתין לאישור ותשובות)   **ADR קשורים:** ADR-001

## 1. רקע ומטרה
כשפקיד דוחה שיק, יש סיכוי שמדובר בנוכל שהגיש גם שיקים נוספים. שירות האנטי-פרוד צריך לקבל את אירוע הדחייה כדי לחסום שיקים קשורים.
המסירה נעשית באופן אסינכרוני דרך תור IBM MQ, כך שהאירוע לא יאבד גם כשה-MQ או האנטי-פרוד אינם זמינים.

## 2. דרישות
### דרישות פונקציונליות
- כל דחיית פקיד (`REJECTED`) שעונה על מסנן הסיבות (ראה שאלות) מייצרת הודעה אחת לתור האנטי-פרוד.
- ההודעה מכילה מספיק מפתחות לקישור: `cheque_id`, `account_id`, `payer_id`, `branch_id`, `channel`, סכום, מועדים, סיבת דחייה.
- האנטי-פרוד הוא שמחליט מהם "שיקים קשורים" ומבצע חסימה; ChequeFlow רק מדווח.
### דרישות לא פונקציונליות
- נפח (נמדד ב-DB בבדיקה, TEST): ~300–360 דחיות בחודש (~11 ביום); `FRAUD` ~673 מתוך 2,952 דחיות (כ-23%) בתקופה. כלומר אין צורך באופטימיזציית תפוקה.
- אמינות: אין אובדן אירוע (at-least-once); כפילות אפשרית ומטופלת ע"י הצרכן.
- השהיה: דקות בודדות מקובלות כברירת מחדל (לאשר — ראה שאלות).
- אבטחה: TLS/הרשאות MQ לפי תקן הארגון; ללא סודות בקוד/לוגים; מינימום PII בהודעה.
- ביקורת: כל אירוע נשמר עם סטטוס שליחה וזמנים.
### אילוצים
- המערכת כיום ללא תלויות חיצוניות (stdlib בלבד); ספריית MQ היא תלות חדשה.
- DDL נמסר כסקריפט לבדיקה (ל-PROD לא מריצים ישירות).
- אין CI/היררכיית חריגים/logging — יוגדרו במינימום הנדרש לרכיב החדש.
### שאלות פתוחות
ראה סעיף 10 למטה.

## 3. מצב קיים
- `service.process_cheque` מבצע load → decide → save_decision לשיק; **אין בריפו קוד שכותב ל-`clerk_reviews`** ולכן לא ידוע היכן ומתי נרשמת דחיית פקיד.
- `clerk_reviews` (chequemis): `review_id` PK, `cheque_id`, `reviewed_at`, `clerk_id`, `decision` APPROVED/REJECTED, `reject_reason` (FRAUD/FUNDS/OTHER/SIGNATURE/DATE), `corrected_amount`, `is_spot_check`; אינדקס `ix_clerk_reviews_cheque`.
- לשיק יכולות להיות כמה בדיקות; "ההחלטה האחרונה קובעת". נמצאו 115 שיקים עם החלטות סותרות (גם APPROVED וגם REJECTED) — דחייה עלולה להתהפך.
- מפתחות קישור זמינים בסכמה: `account_id` (חשבון מפקיד), `payer_id` (מושך), `branch_id`, `channel`. אין שם מוטב/מכשיר/IP — אילו מפתחות האנטי-פרוד באמת משתמש בהם? (שאלה).
- אין MQ בקוד; אין ADR קודם.

## 4. חלופות
### חלופה א': שליחה ישירה ל-MQ אחרי שמירה
פשוטה, אך dual write: קריסה בין commit לשליחה = אירוע אבוד בשקט. סיכון גבוה למטרה העסקית. מאמץ נמוך.
### חלופה ב': Transactional Outbox + relay (נבחרה)
טבלת `antifraud_outbox` נכתבת באותה טרנזקציה של הדחייה; relay קורא ושולח. אין אובדן, MQ למטה לא חוסם. מאמץ בינוני.
### חלופה ג': האנטי-פרוד קורא מה-DB
לא עומדת בדרישת MQ, יוצרת צימוד לסכמה. נדחתה.

## 5. ההחלטה והתכנון
חלופה ב'. הנימוק המלא ב-ADR-001.

### תרשים
```
 [פקיד דוחה שיק]
      |  (טרנזקציה אחת)
      v
 clerk_reviews (REJECTED) + antifraud_outbox (status=NEW)
      |
      v   poll קטן, לפי outbox_id
 [Outbox Relay] --put persistent, syncpoint--> IBM MQ: ANTIFRAUD.CHEQUE.REJECTED
      |  הצלחה: status=SENT                              |
      |  כשל זמני: attempts+1, retry עם backoff          v
      |  חריגה מ-N ניסיונות: status=FAILED + התראה  [שירות אנטי-פרוד]
                                                   dedup לפי message_id
```

### גבולות ואחריות
- **domain/event builder** (פונקציה טהורה): בונה payload מ-review+cheque; ללא I/O.
- **repository** (`AntifraudOutboxRepository`): כתיבה לטבלה, שליפת NEW, סימון SENT/FAILED. SQL פרמטרי.
- **publisher** (`MqPublisher`, ממשק + מימוש IBM MQ): ה-put בלבד, ללא לוגיקה עסקית. ממשק מאפשר fake בבדיקות.
- **relay** (`outbox_relay.run_once`): מתזמר שליפה → שליחה → עדכון סטטוס.
- הלוגיקה "מי קשור ומה לחסום" נמצאת באנטי-פרוד, לא כאן.

### חוזים (הודעה — טיוטה לאישור צוות האנטי-פרוד)
- תור: `ANTIFRAUD.CHEQUE.REJECTED` (שם סופי ומנהל תורים — לברר). הודעה persistent, JSON UTF-8 (CCSID 1208), תור ייעודי + DLQ.
- MQMD: `MsgId`/`CorrelationId` לפי `message_id`; property `event_type`.
```json
{
  "schema_version": 1,
  "message_id": "chq-review-<review_id>",     // דטרמיניסטי → dedup
  "event_type": "CHEQUE_REJECTED_BY_CLERK",
  "occurred_at": "2026-10-17T09:30:00+00:00", // ISO-8601 עם אזור זמן
  "review_id": 123, "cheque_id": 456,
  "account_id": 789, "payer_id": 1011, "branch_id": "B01", "channel": "MOBILE",
  "amount": "1250.00",                          // מחרוזת עשרונית
  "received_at": "...", "reject_reason": "FRAUD",
  "clerk_id": 17                                // לאשר אם מותר/נדרש
}
```
שינויים עתידיים: תוספת שדות אופציונליים בלבד; שבירה = `schema_version` חדש. הצרכן מתעלם משדות לא מוכרים.

### שינויי נתונים (טיוטה; מאומת מול סכמת chequemis, SQLite בהדגמה / SQL Server בייצור)
```sql
CREATE TABLE antifraud_outbox (
    outbox_id   INTEGER PRIMARY KEY,                        -- IDENTITY ב-SQL Server
    review_id   INTEGER NOT NULL UNIQUE REFERENCES clerk_reviews(review_id),
    payload     TEXT    NOT NULL,
    status      TEXT    NOT NULL DEFAULT 'NEW',             -- NEW / SENT / FAILED
    attempts    INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT    NOT NULL,
    sent_at     TEXT,
    last_error  TEXT
);
CREATE INDEX ix_antifraud_outbox_status ON antifraud_outbox(status, outbox_id);
```
- ה-UNIQUE על `review_id` מונע כפילות ברישום.
- נפח זניח (~11 שורות ביום); מדיניות ניקוי של SENT ישנות (למשל 90 יום) — להחליט.
- שינוי הוא expand בלבד (טבלה חדשה, ללא שינוי בטבלאות קיימות). ל-PROD — סקריפט לבדיקת DBA.
- אם הכותב ל-`clerk_reviews` אינו בקוד שלנו: אפשר `AFTER INSERT` trigger ל-`REJECTED`, או relay שסורק `clerk_reviews` לפי watermark. נקבע לאחר התשובה לשאלה 2.

### טיפול בשגיאות, טרנזקציות ועקביות
- רישום outbox באותה טרנזקציה כמו הדחייה; כשל ברישום = כשל הדחייה (לא מדלגים בשקט).
- Relay: שליחה → commit ב-MQ → עדכון `SENT`. קריסה בין השניים = שליחה חוזרת (כפילות) ← האנטי-פרוד מבצע dedup לפי `message_id`.
- כשל זמני של MQ (חיבור/תור מלא): retry עם exponential backoff + jitter, ללא חסימת הפקידים.
- Poison: payload שאינו תקין/שגיאה קבועה → `FAILED` + `last_error` (בלי PII) + התראה; לא מנסים לנצח.
- סדר: לא מובטח ולא נדרש (כל הודעה עצמאית). דחייה שהתהפכה (ראה שאלה 5) תיוצג בהודעה מפצה נפרדת, לא בעדכון הודעה.
- שגיאות מוגדרות במפורש (`OutboxPublishError` transient/permanent), בלי `except Exception: pass`.

### אבטחה ולוגים
- פרטי חיבור MQ (מנהל תורים, ערוץ, משתמש, מפתחות TLS) מ-environment/secret store, לא מקוד או `config.py`.
- חשבון שירות עם הרשאת put בלבד לתור היעד.
- לוג עם `message_id`/`review_id`/`cheque_id` ותוצאה; ללא תוכן payload מלא וללא סודות. correlation id מועבר ב-MQMD.

## 6. תוכנית מימוש (צעדים קטנים)
1. לקבל תשובות לשאלות 1–5 ולסגור חוזה הודעה עם צוות האנטי-פרוד (חוסם).
2. סקריפט DDL לטבלת `antifraud_outbox` (בהדגמה — ב-TEST לאחר הכרזה; ל-PROD — סקריפט בלבד).
3. `event builder` (פונקציה טהורה) + בדיקות יחידה על ה-payload (סכום כמחרוזת, תאריכים ISO, `message_id`).
4. `AntifraudOutboxRepository` (insert/fetch NEW/mark SENT/mark FAILED) + בדיקות על SQLite; כולל אידמפוטנטיות ברישום.
5. חיבור הרישום לנקודת כתיבת הדחייה (או trigger/watermark לפי תשובה 2), באותה טרנזקציה.
6. ממשק `MessagePublisher` + `FakePublisher` ובדיקות ל-`outbox_relay.run_once` (הצלחה, כשל זמני, כשל קבוע, קריסה אחרי שליחה).
7. מימוש IBM MQ (`MqPublisher`) מאחורי הממשק + קונפיגורציה מ-env; בדיקת אינטגרציה מול queue manager של TEST.
8. ניטור: מדד גיל ההודעה הישנה ב-`NEW`, ספירת `FAILED`; runbook לשליחה חוזרת.
9. rollout: relay ב-dry-run (לוג בלבד) → תור TEST → PROD לפי feature flag. `/tl-review` לפני מיזוג.

## 7. בדיקות
- יחידה: בניית payload, מסנן סיבות, חישוב backoff.
- repository על SQLite זמני: רישום, כפילות `review_id`, מעברי סטטוס.
- relay עם `FakePublisher`: ארבעת תרחישי הכשל. בדיקת חוזה מול JSON-schema משותף עם האנטי-פרוד.
- אינטגרציה (ידנית/סביבת TEST): שליחה אמיתית לתור, אימות dedup אצל הצרכן.

## 8. פריסה וחזרה לאחור
Expand-only: טבלה חדשה + relay כבוי כברירת מחדל. Rollback = כיבוי ה-relay; האירועים נשארים ב-`NEW` ולא אובדים, ואפשר לשחזר שליחה. אין שינוי בטבלאות קיימות.

## 9. סיכונים ומה נבחן מחדש בהמשך
- הכותב ל-`clerk_reviews` לא ידוע — עלול לדרוש trigger או שינוי במערכת אחרת.
- חוזה לא סגור עם האנטי-פרוד; הגדרת "קשור" אינה אצלנו.
- שיקים עם החלטות סותרות (115) — חסימות שכבר בוצעו עלולות להיות שגויות אם הדחייה בוטלה.
- תלות חדשה (MQ client) בסביבה שמוגבלת ל-stdlib; בעיית התקנה/רישוי.
- שליחת PII (`clerk_id`, מזהי חשבון) — דורש אישור אבטחה.
- נבחן מחדש: נפח גדול בסדר גודל, צרכנים נוספים → CDC / topic.

## 10. שאלות פתוחות
1. אילו סיבות דחייה נשלחות: רק `FRAUD`, או גם `SIGNATURE`/`OTHER`? (`FUNDS`/`DATE` כנראה לא קשורות לנוכל.)
2. איפה (איזה קוד/מערכת) נכתבת שורה ל-`clerk_reviews`? האם אפשר להוסיף שם כתיבה ל-outbox?
3. מהו חוזה האנטי-פרוד בפועל: שם תור/מנהל תורים, פורמט (JSON/XML/COBOL copybook), קידוד, שדות חובה? האם יש מזהה "נוכל" משלהם?
4. אילו מפתחות קישור קיימים אצלם: חשבון מפקיד, מושך, מכשיר, IP, מוטב? האם הנתונים בסכמה מספיקים?
5. מה קורה כשדחייה מתהפכת ע"י מפקח (115 מקרים כאלה)? צריך הודעה מפצה / ביטול חסימה?
6. האם האנטי-פרוד צריך להחזיר תשובה (חסם/לא חסם, reply queue), ומה ChequeFlow עושה עם חסימה שהתקבלה?
7. SLA השהיה (שניות או דקות) והאם הכמות מאשרת relay בודד?
8. איפה רץ השירות/ה-relay בייצור (Windows service, scheduler), ואיזו ספריית MQ מותרת (pymqi / IBM MQ client)?
9. מותר לכלול `clerk_id` ו-`account_id` בהודעה (PII/הרשאות)?
