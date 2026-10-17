# Intake form (טופס דרישה)

The form a person fills **before** the analyst starts: short, free text, every field optional
except section 1. `spec_tool.py new <slug>` copies the template below into
`.claude/tl-memory/spec/SPEC-nnn-<slug>/REQUEST.md` with the id and date filled in.

How the analyst uses it:
- It is the primary statement of intent — quote it as `[מקור: טופס הדרישה §n]`.
- Empty fields are not questions for the user: fill them from knowledge, code, data and documents
  first, and ask only what is still missing and changes the spec.
- Section 8 sets the shape of the spec: short or full, audience, optional parts.
- Never delete what the person wrote. If you fill the form yourself from a conversation, mark
  your additions `[הושלם ע"י המנתח]`.

<!-- template:begin -->
<!-- tl-meta: type=request; id=SPEC-NNN; status=draft; date=YYYY-MM-DD; area=; title=TITLE -->
# טופס דרישה: TITLE

> ממלאים מה שידוע. שדה בלי תשובה — משאירים ריק: המנתח ישלים מהקוד, מהנתונים ומהמסמכים,
> ויסמן מה הוא הניח. אפשר לכתוב בחופשיות ובנקודות. דוגמאות עדיפות על הגדרות.

## 1. מה צריך ולמה (חובה)
- **מה רוצים שיקרה:**
- **הבעיה היום / למה עכשיו:**
- **מי ביקש, ומי יאשר את האפיון:**

## 2. איך נדע שהצלחנו
- **מדד ויעד:** (למשל: שיעור האישור האוטומטי יעלה מ-8% ל-15%)
- **גבול שאסור לחצות:** (למשל: שיעור הטעויות באישורים החדשים עד 2%)
- **איך ומתי בודקים:**

## 3. היקף
- **בתוך ההיקף:**
- **מחוץ להיקף / מה אסור לשנות:**

## 4. כללים ודוגמאות שכבר ידועים לי
- **כללים, ספים, חריגים** (בשפה חופשית):
- **דוגמאות:**

| מקרה | מה צריך לקרות |
|---|---|
|  |  |

## 5. מקורות
- **מסמכים, קבצים, משימות קשורות:**
- **קוד / מודולים שנראים קשורים:**
- **טבלאות / נתונים:**
- **אנשים שיודעים (לשאלות):**

## 6. אילוצים
- **מועד / גרסה / חלון פריסה:**
- **מערכות שאסור לשנות, תלויות** (mainframe, ממשקים, דוחות):
- **אבטחה, הרשאות, ביקורת, רגולציה:**

## 7. מה עוד לא ברור לי
- **שאלות, ספקות, רעיונות:**

## 8. איך לבנות את האפיון (לא חובה)
- **רמת פירוט:** קצר (שינוי קטן) / מלא
- **קהל:** מפתחים / QA / גורם עסקי
- **חלקים נוספים:** מסכים · דוחות · הודעות למשתמש · ממשקים · מיגרציה · תרחישי בדיקה מפורטים
<!-- template:end -->
