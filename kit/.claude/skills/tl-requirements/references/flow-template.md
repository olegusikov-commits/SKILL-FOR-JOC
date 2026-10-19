# FLOW.md — the stage checklist of one task

`spec_tool.py new` writes `FLOW.md` next to `REQUEST.md`. Every kit command that works on the task
ticks its stage (`- [x]`, date, link to what it wrote) and rewrites the `Дальше:` line;
`/tl-go` and `tl_knowledge.py status` read it to answer "where am I and what is next".
Stages the level skips are marked `- [x] … — пропущено (MVP)`. When the task is closed:
`status=done`. Local working file — never published.

Levels (`level=` in tl-meta; the user changes it with one answer):
- `mvp` — one short document "requirement + solution" (`SPEC.md` with the template's MVP part:
  goal, main REQ/AC, contract, task plan) → one approval → code with tests of the main AC →
  code check (BLOCKER only). Edge cases, NFR and docs go to the plan as later tasks.
- `standard` — spec (no backtest without a number to prove) → design only if LARGE → code → code check.
- `full` — everything: backtest of the effect, skeptics, effect check after the change.

<!-- template:begin -->
<!-- tl-meta: type=flow; id=SPEC-NNN; status=active; level=LEVEL; date=YYYY-MM-DD; area=; title=TITLE -->
# FLOW SPEC-NNN — TITLE

Уровень: LEVEL · одна строка = один этап; галочка — этап пройден.

- [ ] 0 Вход — маршрут выбран
- [ ] 1 Приём — REQUEST.md (что и зачем)
- [ ] 2 Изучение — код, данные, документы (NOTES.md)
- [ ] 3 Уточнение — вопросы и ответы (הבהרות)
- [ ] 4 Требование — SPEC.md утверждён
- [ ] 5 Технический дизайн — design + ADR + план задач утверждены (только LARGE)
- [ ] 6 Код — все задачи плана [x], тесты зелёные
- [ ] 7 Проверка кода — BLOCKER исправлены
- [ ] 8 Проверка эффекта — вердикт по данным (по желанию; обязательно для full)
- [ ] 9 Публикация — документы в docs/, commit делает пользователь

Дальше: /tl-spec SPEC-NNN
<!-- template:end -->
