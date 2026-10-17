# Демо: проверка всех возможностей kit

Это **не часть kit** — на рабочий компьютер переносить не нужно. Демо проверяет kit целиком
на учебном проекте ChequeFlow (обработка чеков) с синтетическими данными, в которых заранее
спрятаны закономерности и ловушки.

| Файл | Что это |
|---|---|
| `project/` | Учебный проект (Python): правила авто-разрешения чеков, тесты, схема, задача CHQ-512 |
| `make_demo.py` | Генерирует данные: `chequemis.db` (36 000 чеков), `checkov.db`, `docs/process.docx` на иврите |
| `patches/` | Изменения для сценариев: реализация CHQ-512 с дефектами, изменение для ревью с проблемами |
| `reference_answers.py` | Эталонные ответы, посчитанные напрямую по данным |
| `EXPECTED.md` | Что спрятано и что должен найти каждый сценарий (карточка оценки) |
| `run_demo.py` | Ставит kit в копию проекта, подключает базы как MCP `meet-chequemis` / `meet-checkov`, запускает команды в headless Claude Code |
| `RESULTS.md` | Результаты последнего прогона |

## Запуск (Linux / облако)
```
uv tool install mcp-server-sqlite --with "mcp<2"
python demo/run_demo.py setup /tmp/demo
python demo/run_demo.py run /tmp/demo init        # затем любой сценарий: python demo/run_demo.py list
python demo/reference_answers.py /tmp/demo/base/chequemis.db
```
Базы в демо — SQLite, а не SQL Server / DB2: аналитик сам адаптирует диалект. Это проверяет и
его способность работать с другим движком.
