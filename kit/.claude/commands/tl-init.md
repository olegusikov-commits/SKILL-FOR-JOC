---
description: Set the kit up in this project (first time and after every kit update) — kit self-check and time limits, project map, data sources registry (databases through MCP or command-line clients), knowledge map; replaces the built-in /init
argument-hint: "[optional notes about the project]"
---

Initialize the Tech Lead Kit memory for this project. User notes: $ARGUMENTS

Goal: create `.claude/tl-memory/PROJECT_CONTEXT.md` — a concise (≤ 150 lines) map of the project
that every future task reads first. If it already exists, update it instead of overwriting, and
show what changed.

Steps:
1. Create folders if missing: `.claude/tl-memory/adr/`, `.claude/tl-memory/design/`,
   `.claude/tl-memory/spec/`.
   Create `.claude/tl-memory/TECH_DEBT.md` from the template in the `tl-tech-debt` skill if no
   debt register exists (check `KNOWLEDGE.md` — it may be published to `docs/`).
2. **Kit self-check** — is the kit loaded, and what else could Claude use instead of it:
   `python .claude/tech-lead-kit/scripts/tl_doctor.py` (on Windows `py -3 …` if `python` is missing).
   - ERROR → the kit does not work as designed; tell the user exactly what to do (usually run
     `install.cmd` again, then start a new Claude Code session) and continue only with what works.
   - WARN about a skill / agent / command / plugin / MCP server that is not the kit's: read its
     description (open the file) and decide whether it **overlaps** kit work (writing or reviewing
     code, SQL, specs, analysis, documents, tests). Overlapping ones go to the report with a
     recommendation: remove, rename, or keep and the kit ignores it for kit work (CORE "Kit tools
     first"). A name identical to a kit name is always a conflict.
   - WARN about other instruction files (`CLAUDE.md`, `CLAUDE.local.md`, `AGENTS.md`, rules,
     the personal `~/.claude/CLAUDE.md`): read them and list every rule that contradicts CORE
     (language of comments, commits, database access, skipping tests…). Do not edit them; ask the
     user which rule wins and record the answer under "Known risks & observations".
   - WARN "no time limit for MCP calls" → ask once (buttons, "применить (рекомендуется)") and run
     `python .claude/tech-lead-kit/scripts/tl_doctor.py --apply-limits`; tell the user the limits
     work from the next Claude Code session. Suggest a per-server `"timeout"` in `.mcp.json` for
     database servers (shorter for PROD) — the team's file, the user decides.
   - A root `CLAUDE.md` (e.g. from the built-in `/init`) is a source of build/test commands and
     conventions: use it in step 3 and list contradictions with CORE. The built-in `/init` is not
     needed — this command does it.
   - Record a 3–6 line summary under `## סביבת Claude` in `PROJECT_CONTEXT.md` (kit version,
     conflicts and decisions). Do not copy it into the `tl-agents` block.
3. Explore the repository (read-only):
   - Languages, frameworks and **exact versions** (`*.csproj`/`*.sln`, `pyproject.toml`/
     `requirements*.txt`, `package.json`/`.nvmrc`, `CMakeLists.txt`/`*.vcxproj`, COBOL/Natural
     source folders, JCL, copybooks, DDL folders).
   - Structure: main modules/projects and their responsibilities; entry points (APIs, web
     services, batch jobs, CICS transactions, CLIs); layering as it **actually** is.
   - Build, test, lint commands as they are configured in the project.
   - Conventions observed: naming, folder layout, error handling, logging, data access style,
     migration/DDL folder and naming, comment language.
   - Integrations: external services, MQ, files, mainframe interfaces.
4. **Data sources** (read-only) — every way this project reaches a database:
   - MCP servers that look like databases (`tl_doctor.py` lists them), command-line clients it
     found (`sqlcmd`, `db2`), connection settings in the code and config (names only — never copy
     passwords or connection strings).
   - For each MCP source: the engine detection probe from
     `.claude/skills/tl-sql-engineering/references/mcp-catalog-queries.md` (one call each).
   - **Ask the user** (buttons) which source is PROD and which is TEST — do not guess; until
     answered every source is PROD.
   - Write `.claude/tl-memory/data-sources.json`:
     `{"sources": [{"alias": "<short name>", "access": "mcp|cli", "server": "<MCP server name>",
     "client": "<cli name>", "engine": "sqlserver|db2-zos", "version": "…", "env": "PROD|TEST",
     "databases": ["…"], "read_only": true, "notes": "…"}]}` — no secrets.
   - List the main schemas/tables used by this project's code (search the code for table names)
     with their row counts from the catalog; do not dump the whole catalog.
5. Write `PROJECT_CONTEXT.md` (Hebrew headings and notes, technical names in English) with
   sections: Overview · Stack & versions · Structure & modules · Entry points · Build/Test
   commands · Conventions · Databases (data source alias → access, engine/version/compat
   level/environment/databases/main schemas and sizes) · Installed packages (where library
   sources live: `node_modules`, venv `site-packages`, NuGet cache — for checking APIs) · Integrations · Known risks & observations · Open questions · סביבת Claude (step 2).
   End it with a block for **all agents** (it is copied into `AGENTS.md` by `/tl-publish`):
   `<!-- tl-agents:begin -->` … `<!-- tl-agents:end -->`, at most 12 lines in Hebrew — what the
   project is, build/test commands, where the main code is, data source aliases
   and "PROD is read-only", key conventions. No secrets, host names or connection strings.
6. Rebuild the knowledge map: `python .claude/tech-lead-kit/scripts/tl_knowledge.py index`. If it lists documents without `tl-meta` (e.g.
   written by an older kit version), add the line to each — type by folder, status and `area`
   from the content — and rebuild. Also run this after every kit update. If `publish.json` has
   `"auto_publish": true`, also run `tl_knowledge.py block` so `AGENTS.md` gets the project facts
   from the first day, and tell the user which files to commit.
7. Record the kit version: `python .claude/tech-lead-kit/scripts/tl_knowledge.py status --mark-init`.
8. Report to the user in Russian: the kit self-check (version, limits, conflicts found and what
   you recommend), data sources (PROD/TEST), a short summary, the questions you need answered,
   and the top 3–5 observations (risks / debt candidates — add them to TECH_DEBT.md). End with
   the step card; next: `/tl-go`.
