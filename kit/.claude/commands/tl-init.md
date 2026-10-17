---
description: Analyze this project and create the Tech Lead project memory (PROJECT_CONTEXT.md, ADR/design folders, tech debt register)
argument-hint: "[optional notes about the project]"
---

Initialize the Tech Lead Kit memory for this project. User notes: $ARGUMENTS

Goal: create `.claude/tl-memory/PROJECT_CONTEXT.md` — a concise (≤ 150 lines) map of the project
that every future task reads first. If it already exists, update it instead of overwriting, and
show what changed.

Steps:
1. Create folders if missing: `.claude/tl-memory/adr/`, `.claude/tl-memory/design/`,
   `.claude/tl-memory/spec/`.
   Create `.claude/tl-memory/TECH_DEBT.md` from the template in the `tl-tech-debt` skill if missing.
2. Explore the repository (read-only):
   - Languages, frameworks and **exact versions** (`*.csproj`/`*.sln`, `pyproject.toml`/
     `requirements*.txt`, `package.json`/`.nvmrc`, `CMakeLists.txt`/`*.vcxproj`, COBOL/Natural
     source folders, JCL, copybooks, DDL folders).
   - Structure: main modules/projects and their responsibilities; entry points (APIs, web
     services, batch jobs, CICS transactions, CLIs); layering as it **actually** is.
   - Build, test, lint commands as they are configured in the project.
   - Conventions observed: naming, folder layout, error handling, logging, data access style,
     migration/DDL folder and naming, comment language.
   - Integrations: external services, MQ, files, mainframe interfaces.
3. Databases via SQL MCP servers `meet-checkov` and `meet-chequemis` (read-only):
   - For each server: run the engine detection probe from
     `.claude/skills/tl-sql-engineering/references/mcp-catalog-queries.md`.
   - **Ask the user** which server/database is PROD and which is TEST (do not guess), and
     record it. Until answered, treat both as PROD.
   - List main schemas/tables used by this project's code (search the code for table names),
     do not dump the whole catalog.
4. Write `PROJECT_CONTEXT.md` (Hebrew headings and notes, technical names in English) with
   sections: Overview · Stack & versions · Structure & modules · Entry points · Build/Test
   commands · Conventions · Databases (server → engine/version/compat level/environment/
   databases/main schemas) · Integrations · Known risks & observations · Open questions.
   End it with a block for **all agents** (it is copied into `AGENTS.md` by `/tl-publish`):
   `<!-- tl-agents:begin -->` … `<!-- tl-agents:end -->`, at most 12 lines in Hebrew — what the
   project is, build/test commands, where the main code is, database aliases (MCP server names)
   and "PROD is read-only", key conventions. No secrets, host names or connection strings.
5. Rebuild the knowledge map: `python .claude/tech-lead-kit/scripts/tl_knowledge.py index`.
6. Report to the user in Russian: a short summary, the questions you need answered, and the
   top 3–5 observations (risks / debt candidates — add them to TECH_DEBT.md).
