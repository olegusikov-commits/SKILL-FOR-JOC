# Бриф (утверждён)

## Цель
Чтобы Claude Code в VS Code писал код как Tech Lead вместе с архитектором: думал наперёд,
проектировал до кодирования, разделял ответственность и писал SQL уровня DBA.

## Проблема сегодня
Claude пишет как junior-программист:
- не думает наперёд;
- часто пишет монолитно, без границ и слоёв;
- пишет SQL низкого уровня.

## Окружение и ограничения
| Параметр | Значение |
|---|---|
| ОС | Windows 11 |
| Инструмент | VS Code + расширение Claude Code |
| Плагины | Запрещены компанией, поэтому используются только файлы в `.claude/` |
| Hooks | Не используются |
| Перенос | Через USB |
| Установка | Только в выбранные проекты, локально, не коммитится в репозиторий компании |
| MCP | `meet-checkov`, `meet-chequemis`, подключены к PROD и TEST. PROD: только SELECT. TEST: всё |

## Стек
C++, C#, Python, Node.js, COBOL, Natural, микросервисы, web services, SQL,
DB2 for z/OS, stored procedures, SQL Server 2019 + 2022.

## Решения
| Вопрос | Решение |
|---|---|
| Язык общения | Русский, если не попрошу другой |
| Комментарии в коде и документы | Иврит (для мейнфрейма с учётом кодировки EBCDIC) |
| Язык инструкций skills | Английский (точнее выполняется, экономит контекст) |
| Утверждение дизайна | LARGE-задачи: стоп и утверждение. SMALL-задачи: сразу |
| Основа | Взяты `system-design`, `architecture`, `tech-debt` от Anthropic и дополнены стандартом кода и SQL |
| Принудительное соблюдение без hooks | Процесс в командах + независимые subagent-ревьюеры + опциональные permissions для MCP |
| Названия | Префикс `tl-`, чтобы не конфликтовать со встроенными `/review`, `/init` и т.п. |
| Подключение правил | `.claude/CLAUDE.md` → `@tech-lead-kit/CORE.md` (работает во всех версиях) |
| Память проекта | `.claude/tl-memory/`: PROJECT_CONTEXT, ADR, design, TECH_DEBT (локально) |

## Состав
- `CORE.md`: правила, действующие всегда (классификация задач, 12 инженерных правил, протокол MCP, Definition of Done).
- Skills: `tl-engineering-standards`, `tl-architecture`, `tl-sql-engineering`, `tl-tech-debt`.
- Commands: `/tl-init`, `/tl-design`, `/tl-implement`, `/tl-review`, `/tl-sql`, `/tl-debt`.
- Agents: `tl-architect-reviewer`, `tl-sql-reviewer`.
- `install.cmd` / `uninstall.cmd`.
