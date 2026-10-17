# ADR template (write in Hebrew)

Save as `.claude/tl-memory/adr/ADR-NNN-<short-name>.md`; NNN = next number after the highest
existing ADR. One decision per ADR. Never rewrite an accepted ADR — supersede it with a new one.

```markdown
<!-- tl-meta: type=adr; id=ADR-NNN; status=proposed; date=<YYYY-MM-DD>; area=<רכיבים, טבלאות, ממשקים>; title=<כותרת> -->
# ADR-NNN: <כותרת ההחלטה>

**סטטוס:** Proposed | Accepted | Deprecated | Superseded by ADR-XXX
**תאריך:** <YYYY-MM-DD>
**מחליטים:** <מי צריך לאשר>

## הקשר
<מה המצב, אילו כוחות פועלים: דרישות, אילוצים, נפחים, מערכות קיימות>

## ההחלטה
<מה הוחלט, במשפט או שניים, בצורה חד-משמעית>

## חלופות שנשקלו

### חלופה א': <שם>
| מימד | הערכה |
|---|---|
| מורכבות | נמוכה / בינונית / גבוהה |
| עלות | ... |
| ביצועים / סקיילביליות | ... |
| התאמה למערכות קיימות | ... |
| היכרות הצוות | ... |

**יתרונות:** ...
**חסרונות:** ...

### חלופה ב': <שם>
(אותו מבנה)

## ניתוח שיקולים (trade-offs)
<למה ההחלטה עדיפה ביחס לדרישות, מה ויתרנו עליו>

## השלכות
- מה נהיה קל יותר: ...
- מה נהיה קשה יותר: ...
- מה נצטרך לבחון מחדש ומתי: ...

## משימות המשך
1. [ ] ...
```
