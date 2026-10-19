# Topic memory — layout and templates

All files are in Russian. Technical names (tables, columns, files) stay as they are.

```
.claude/tl-memory/analysis/
├── INDEX.md                    all topics: slug, title, status, KPI now, last report
└── <topic-slug>/               short latin slug, e.g. claims-auto-approval
    ├── TOPIC.md                profile, assumptions, questions
    ├── DATA_MAP.md             sources, tables, joins, outcome field, decision-time fields, glossary
    ├── LOGIC_AS_IS.md          how the process decides today (decision table, file:line)
    ├── BASELINE.md             calibrated baseline numbers with links to queries
    ├── HYPOTHESES.md           register H-001… with verdicts
    ├── JOURNAL.md              chronological log: what was done, where we stopped, next step
    ├── queries/                every SQL that produced a number (NNN-short-name.sql)
    └── reports/                YYYY-MM-DD-<subject>.md
```

Create files lazily: only when there is content for them.

## INDEX.md
```markdown
# Темы анализа

| Тема (slug) | Название | Статус | KPI сейчас | Последний отчёт |
|---|---|---|---|---|
| claims-auto-approval | Автоматическое одобрение заявок (пример) | изучена | 8,1% (2026-10) | reports/2026-10-17-... |
```
Status: `изучается` · `изучена` · `в анализе` · `отчёт готов` · `закрыта`.

## TOPIC.md
```markdown
<!-- tl-meta: type=analysis-topic; id=<topic-slug>; status=<статус из INDEX>; date=<YYYY-MM-DD>; area=<таблицы, модули, термины>; title=<Название темы> -->
# <Название темы>

## Профиль
| Поле | Значение | Источник |
|---|---|---|
| Объект анализа | Чек | объяснение пользователя |
| Процесс / решение | Авто-одобрение заявки (пример) | код: src/...:12 |
| Цель (KPI) | Доля авто-одобренных заявок ↑ | |
| Формула KPI | COUNT(авто-разрешённые) / COUNT(все поступившие) за период | queries/001-... |
| Эталон (истина) | Решение פקיד: таблица.колонка | DATA_MAP |
| Ограничитель (guardrail) | Ошибочные авто-разрешения ≤ 2% (верхняя граница 95%) | пользователь |
| Определение ошибки | ... | вопрос В-1 |
| Источник данных | алиас из data-sources.json, PROD/TEST, движок | |
| Период анализа | ... (почему такой) | |
| Сценарий | decision-automation | |

## Допущения
- Д-1: ... (на чём основано; какие выводы от него зависят)

## Вопросы
| # | Вопрос | Предложенный ответ (на чём основан) | Ответ пользователя | Статус |
|---|---|---|---|---|
| В-1 | ... | ... | | открыт |

## Статус
Где остановились и что дальше (одна-две строки; подробности — в JOURNAL.md).
```

## DATA_MAP.md
```markdown
# Карта данных

## Источник
Сервер MCP, база, движок, среда (PROD/TEST), объёмы по месяцам (ссылка на запрос).

## Таблицы и связи
| Таблица | Что хранит | Ключ | Связь | Строк | Поле даты (индекс?) |
|---|---|---|---|---|---|

## Поле-эталон (outcome)
Где хранится решение человека / итог; значения и их доли; у каких объектов эталона нет.

## Поля по времени появления  ← главное для защиты от утечки из будущего
| Поле | Известно в момент автоматического решения? | Кто/когда заполняет | Доказательство |
|---|---|---|---|
| ocr_amount | да | OCR при поступлении | код: ...:40 |
| risk_flag | **нет** | פקיד при проверке | документ: ..., данные: NULL у непроверенных |

## Качество данных
Пропуски, дубликаты, странные значения, изменения формата по времени.

## Глоссарий
| Термин бизнеса | Значение | Таблица / колонка / код |
|---|---|---|
```

## LOGIC_AS_IS.md
```markdown
# Текущая логика решения

Точка входа: файл:строка. Версия / дата изменения, если видна.

| # | Условие | Порог / значение | Что происходит, если не выполнено | Причина (reason code) | Где в коде |
|---|---|---|---|---|---|
| 1 | Уверенность OCR суммы | ≥ 0.95 | к פקיד | LOW_OCR | src/rules.py:31 |

Порядок проверки условий: ...
Непонятные места / расхождения с документацией: ...
```

## BASELINE.md
```markdown
# Базовая линия (<дата>, период <с–по>)

| Метрика | Значение | Метка | Запрос |
|---|---|---|---|
| KPI | 8,1% | ИЗМЕРЕНО | queries/003-baseline-kpi.sql |

Калибровка: известное значение X, получено Y → совпадает / не совпадает (почему).
По месяцам: ...
Причины, по которым объект не прошёл автоматически: ...
Потолок возможностей: ...
```

## HYPOTHESES.md
```markdown
# Реестр гипотез

| ID | Гипотеза (условие) | Механизм: почему должно работать | Прирост KPI | Ошибка: факт / верхняя граница | Стабильность | Вердикт | Статус |
|---|---|---|---|---|---|---|---|
| H-001 | ... | ... | +4,2 п.п. | 0,6% / 1,1% | 6/6 мес. | PASS | рекомендована |
```
Verdicts: `PASS` · `PASS С УСЛОВИЯМИ` · `FAIL` · `МАЛО ДАННЫХ` · `ОТКЛОНЕНА КРИТИКОМ`.
Never delete rows: a rejected hypothesis is knowledge ("this was tried and does not work, because…").

## JOURNAL.md
```markdown
# Журнал
## 2026-10-17
- Изучение темы: найдено ..., создан DATA_MAP.
- Остановились на: ... Следующий шаг: ...
```

## queries/
One file per query that produced a number used anywhere: `NNN-short-name.sql`.
Header comment: purpose, server, environment, period, date run, result summary.
