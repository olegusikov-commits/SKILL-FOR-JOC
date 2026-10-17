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
4. Databases via SQL MCP servers `meet-checkov` and `meet-chequemis` (read-only):
   - For each server: run the engine detection probe from
     `.claude/skills/tl-sql-engineering/references/mcp-catalog-queries.md`.
   - **Ask the user** which server/database is PROD and which is TEST (do not guess), and
     record it. Until answered, treat both as PROD.
   - List main schemas/tables used by this project's code (search the code for table names),
     do not dump the whole catalog.
5. Write `PROJECT_CONTEXT.md` (Hebrew headings and notes, technical names in English) with
   sections: Overview · Stack & versions · Structure & modules · Entry points · Build/Test
   commands · Conventions · Databases (server → engine/version/compat level/environment/
   databases/main schemas) · Integrations · Known risks & observations · Open questions · סביבת Claude (step 2).
   End it with a block for **all agents** (it is copied into `AGENTS.md` by `/tl-publish`):
   `<!-- tl-agents:begin -->` … `<!-- tl-agents:end -->`, at most 12 lines in Hebrew — what the
   project is, build/test commands, where the main code is, database aliases (MCP server names)
   and "PROD is read-only", key conventions. No secrets, host names or connection strings.
6. Rebuild the knowledge map: `python .claude/tech-lead-kit/scripts/tl_knowledge.py index`. If it lists documents without `tl-meta` (e.g.
   written by an older kit version), add the line to each — type by folder, status and `area`
   from the content — and rebuild. Also run this after every kit update. If `publish.json` has
   `"auto_publish": true`, also run `tl_knowledge.py block` so `AGENTS.md` gets the project facts
   from the first day, and tell the user which files to commit.
7. Report to the user in Russian: the kit self-check (version, conflicts
   found and what you recommend), a short summary, the questions you need answered, and the
   top 3–5 observations (risks / debt candidates — add them to TECH_DEBT.md).
