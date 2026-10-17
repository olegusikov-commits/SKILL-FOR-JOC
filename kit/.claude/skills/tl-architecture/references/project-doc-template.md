# Project document template

Used by `/tl-project-doc`. Default language Hebrew (headings and text), technical names in
English. Every statement is backed by evidence (path, `file:line`, `table`, document); what
could not be confirmed goes to "Open questions", never into the body as fact.
Skip a section that does not apply (say "לא רלוונטי" in one line), do not pad.

```markdown
# <Project name> — מסמך פרויקט
גרסה / תאריך · מקורות: קוד (commit/branch), מסדי נתונים (שרת/סביבה), מסמכים

## 1. מטרה והקשר עסקי
What the system does, for whom, which business process it serves. 5–8 lines.

## 2. תמונה כללית (ארכיטקטורה)
Context diagram (system + users + external systems) and container/module diagram.
Mermaid is NOT rendered in VS Code without extensions → use ASCII diagrams in Markdown,
or the HTML version (oleg-skill-hesber) for real diagrams.

## 3. מודולים ואחריות
| Module / project | Responsibility | Layer | Main entry points | Path |

## 4. תהליכים עיקריים
For the 3–5 most important business flows: steps from entry point to data, with files and
tables involved. One short sequence per flow.

## 5. מודל נתונים
Main tables (from the real catalog via SQL MCP): purpose, key, important columns, relations,
volume. Which module reads/writes which table (from code).

## 6. אינטגרציות
External systems, protocol, direction, frequency, error handling, owner.

## 7. תצורה וסביבות
Configuration files and keys (no secret values!), environments (DEV/TEST/PROD), feature flags.

## 8. בנייה, בדיקות ופריסה
Build / test / run commands exactly as configured in the project; CI if present.

## 9. תפעול
Logging, monitoring, batch jobs and schedule, typical failures and what to do.

## 10. אבטחה
Authentication/authorization, sensitive data, where secrets come from (not their values).

## 11. סיכונים, חוב טכני ותצפיות
From TECH_DEBT.md and from what you saw. Link items (TD-NNN).

## 12. מילון מונחים
| Term | Meaning | Where in code/data |

## 13. שאלות פתוחות
What could not be confirmed and whom to ask.
```
