# ChequeFlow

שירות עיבוד שיקים: שיק נסרק (סניף / מובייל / כספומט), ה-OCR מזהה סכום, תאריך וחתימה,
וכללי ההחלטה (`src/chequeflow/rules.py`) מאשרים אותו אוטומטית או מעבירים לבדיקת פקיד.

- קוד: `src/chequeflow/`
- בדיקות: `PYTHONPATH=src python -m unittest discover -s tests` (מתיקיית הפרויקט)
- סכמה: `sql/schema.sql`
- תיאור התהליך: `docs/process.docx`
- מסדי נתונים: `meet-chequemis` (שיקים, החלטות, בדיקות פקיד), `meet-checkov` (פקידים, יומן ביקורת)
