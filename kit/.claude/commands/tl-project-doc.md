---
description: Build an evidence-based project document (purpose, architecture, modules, flows, data model, integrations, operations, risks) from the real code, databases and documents — Markdown, optionally an illustrated HTML version
argument-hint: "[scope: whole project or a module/folder] [language: he|ru|en] [html]"
---

Build the project document. Arguments: $ARGUMENTS

Read-only work on the project: do not modify production code. Output goes to
`.claude/tl-memory/project-doc/` (local, not committed) unless the user named another path.

1. **Scope and language.** Scope = the whole project unless a module/folder is given.
   Language: Hebrew by default (project documents rule in CORE.md); Russian or English if
   asked. Audience: a developer who joins the team.
2. **Start from what is known:** `.claude/tl-memory/PROJECT_CONTEXT.md` (if missing, say that
   `/tl-init` would help, and continue), `KNOWLEDGE.md` and the documents it lists (specs, ADRs,
   designs, analyses), `TECH_DEBT.md`, README and docs in the repository. If a previous version of the
   project document exists, update it and list what changed.
3. **Research in parallel** — `tl-researcher` subagents in one message:
   - focus `code` (project-wide): modules and responsibilities, layers, entry points, the 3–5
     main business flows with files, configuration, build/test commands;
   - focus `data`: main tables of this project (names found in code), keys, relations, volumes,
     which module reads/writes which table (read-only catalog queries via SQL MCP only —
     never open database files directly);
   - focus `docs`: business purpose, terms, processes, integrations described in documents.
4. **Write** `.claude/tl-memory/project-doc/PROJECT_DOC.md` following
   `.claude/skills/tl-architecture/references/project-doc-template.md`. Every statement with
   evidence; unconfirmed things go to "Open questions". No secrets (passwords, keys,
   connection strings with credentials) — name where they come from, never the values.
5. **Illustrated version** (if the user asked for `html`, or offer it): use the
   `oleg-skill-hesber` skill to produce `.claude/tl-memory/project-doc/PROJECT_DOC.html` with
   architecture, flow and data diagrams based on the same facts.
6. **Self-check before finishing:** pick 5 random statements from the document and re-verify
   each against its evidence; fix what does not hold.
7. Both files start with a `tl-meta` line (`type=project-doc`); run `python .claude/tech-lead-kit/scripts/tl_knowledge.py index`.
8. **Reply in Russian:** where the files are, the sections, the 3–5 most important
   observations (risks, surprises), the open questions, and an offer to `/tl-publish` it.
