# CLAUDE.md — разработка Tech Lead Kit

Этот репозиторий — **сам kit** (файлы для Claude Code), а не проект, в который он ставится.
Kit переносится на рабочий компьютер через USB: Windows 11, VS Code + расширение Claude Code,
без интернета, без плагинов и hooks.

## Язык
- Общение с владельцем — **русский**. Документы репозитория (`README.md`, `docs/*.md`) — русский.
- Инструкции внутри kit (`kit/.claude/**`: CORE, skills, commands, agents) — **английский**
  (точнее выполняются, экономят контекст). Шаблоны документов, которые kit создаёт, — на языке
  результата (иврит для ADR/дизайна, русский для отчётов аналитика).
- `docs/GUIDE.html` (русский) и `docs/GUIDE.he.html` (иврит, RTL) обновляются **вместе**.

## Структура
```
kit/.claude/            ← то, что install.cmd копирует в <проект>\.claude\
  tech-lead-kit/CORE.md   правила, загружаются ВСЕГДА — держать ≤ 120 строк
  tech-lead-kit/VERSION   semver; повышать при каждом изменении kit
  tech-lead-kit/scripts/  tl_knowledge.py — карта знаний KNOWLEDGE.md и публикация в проект
  skills/ commands/ agents/
install.cmd, uninstall.cmd   Windows-установщик (CRLF!)
docs/                   BRIEF.md, ANALYST_DESIGN.md, SPEC_DESIGN.md, GUIDE.html, GUIDE.he.html
tests/                  автотесты (stdlib unittest), в ZIP не входят
demo/                   учебный проект + прогон всех команд в headless Claude Code, в ZIP не входит
```

## Правила изменения kit
- **Имена:** skills, commands, agents — с префиксом `tl-`. Установщик прячет от git и удаляет по
  маскам `tl-*`. Исключение — `oleg-skill-hesber`, он прописан в `install.cmd`/`uninstall.cmd`
  явно; новое исключение = правка обоих скриптов.
- **Без плагинов и hooks.** Только обычные файлы в `.claude/`.
- **Python-скрипты kit** — только стандартная библиотека, Python 3.8+ (на работе 3.12+). Вывод в
  UTF-8 (`sys.stdout.reconfigure`), потому что консоль Windows и иврит.
- **`.cmd` хранятся с CRLF** (`.gitattributes: *.cmd -text`). Редактировать, сохраняя CRLF.
  Внутри блоков `( … )` в cmd — никаких меток и `goto`.
- **CORE.md короткий**: подробности — в `references/` skills, они грузятся только когда нужны.
- **Базы — только через SQL MCP** (`meet-checkov`, `meet-chequemis`). PROD — только чтение;
  аналитик: сначала TEST, на PROD — агрегаты по плану, одобренному один раз на тему.
- Новая команда → добавить её в `CORE.md` («Where things live»), `README.md`, обе версии GUIDE.
- **Каждый документ, который пишет kit, начинается со строки `tl-meta`** (type, id, status, date,
  area, title) — по ней `tl_knowledge.py index` строит `KNOWLEDGE.md`. Новый шаблон документа →
  строка `tl-meta` в шаблоне + путь в `TemplateMetaTests` (`tests/test_kit_structure.py`); команда,
  которая пишет документ, в конце запускает `tl_knowledge.py index`.
- **Kit никогда не делает commit/push** в проекте. В репозиторий проекта попадают только
  утверждённые документы через `/tl-publish` (`docs/` + блок в `AGENTS.md`), без ссылок на команды
  kit, `.claude/`, строк PROD и секретов.
- Любое упомянутое в kit имя файла (`references/…`, `scripts/…`, `.claude/…`) должно существовать
  — это проверяет тест.

## Проверка перед commit
```
python -m unittest discover -s tests          # структура kit, an_stats, an_doc2text, spec_tool, tl_knowledge
```
Большие изменения поведения — прогнать демо (`demo/README.md`) и обновить `demo/RESULTS.md`:
```
uv tool install mcp-server-sqlite --with "mcp<2"
python demo/run_demo.py setup /tmp/demo && python demo/run_demo.py run /tmp/demo init
python demo/run_demo.py run-all /tmp/demo 4    # все сценарии по зависимостям, 4 параллельно (~$30)
python demo/check_runs.py /tmp/demo
```
`demo/EXPECTED.md` и `demo/reference_answers.py` — эталон; в копию проекта для Claude они не
попадают.

## Выпуск ZIP для USB
```
git archive --format=zip --prefix=tech-lead-kit-<VERSION>/ -o tech-lead-kit-<VERSION>.zip HEAD \
    install.cmd uninstall.cmd README.md .gitattributes kit docs
```
Проверить в распакованном архиве: `install.cmd` с CRLF, `VERSION`, `an_stats.py --selftest`.
