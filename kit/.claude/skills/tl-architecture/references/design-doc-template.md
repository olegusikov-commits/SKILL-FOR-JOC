# Design document template (write in Hebrew)

Save as `.claude/tl-memory/design/<YYYY-MM-DD>-<short-name>.md`. Keep each section short;
delete sections that genuinely do not apply (say "לא רלוונטי" if a reviewer would expect it).
Write by `.claude/tech-lead-kit/WRITING.md`. A new service: also `references/new-service.md`.

Section 6 is the **task plan** `/tl-implement` works from and resumes: one line per small task,
`- [ ] T<n> <what> — <files> · בדיקה: <test or command> · (REQ-…, AC-…)`; phases "הכנה" (skeleton,
config) → "עיקר" (one block per main scenario) → "סיום" (edge cases, docs). Each task compiles and
keeps tests green on its own. No "TBD". Every REQ / AC of the approved spec appears in at least
one task, and every task names the REQ / AC it serves (or "תשתית").

```markdown
<!-- tl-meta: type=design; id=; status=draft; date=<YYYY-MM-DD>; area=<קבצים, מודולים, טבלאות>; title=<שם> -->
# מסמך תכנון: <שם>

**תאריך:** <YYYY-MM-DD>   **סטטוס:** טיוטה | מאושר   **ADR קשורים:** ADR-NNN   **אפיון:** SPEC-NNN (אם יש)

## 1. רקע ומטרה
<מה הבעיה העסקית, למי, ולמה עכשיו — 2–3 משפטים>

## 2. דרישות
### דרישות פונקציונליות
- ...
### דרישות לא פונקציונליות
- נפח: <שורות / בקשות לשנייה / חלון batch>
- ביצועים: <זמני תגובה>
- זמינות, אבטחה, ביקורת (audit): ...
### אילוצים
- ...
### שאלות פתוחות
- ...

## 3. מצב קיים
<רכיבים, טבלאות, פרוצדורות, תוכניות רלוונטיות — כפי שנבדקו בקוד וב-MCP>

## 4. חלופות
### חלופה א': <שם>
<תיאור> | יתרונות | חסרונות | סיכון | מאמץ
### חלופה ב': <שם>
...

## 5. ההחלטה והתכנון
<החלופה הנבחרת ולמה>

### תרשים
(ASCII diagram of components and data flow)

### גבולות ואחריות
### חוזים (API / WSDL / הודעות / פרוצדורות / copybooks)
<לכל פעולה: קלט (שדות, טיפוסים, חובה), פלט, קודי שגיאה, idempotency, גרסה>
### שינויי נתונים (טבלאות, אינדקסים, מיגרציה)
### טיפול בשגיאות, טרנזקציות ועקביות
### אבטחה ולוגים

## 6. תוכנית מימוש — משימות
### הכנה
- [ ] T1 <מה> — <קבצים> · בדיקה: <טסט/פקודה> · (תשתית)
### עיקר
- [ ] T2 <מה> — <קבצים> · בדיקה: <טסט> · (REQ-001, AC-001, AC-002)
### סיום
- [ ] T9 <מקרי קצה / תיעוד> — … · (AC-007)

## 7. בדיקות
<מה ייבדק וכיצד>

## 8. פריסה וחזרה לאחור (rollout / rollback)

## 9. סיכונים ומה נבחן מחדש בהמשך
```
