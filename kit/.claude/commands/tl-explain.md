---
description: Explanation with diagrams — explain how a process, module, flow or integration works, or build the evidence-based project document (purpose, architecture, modules, flows, data, operations, risks); illustrated offline HTML with SVG diagrams + Markdown
argument-hint: "project [module/folder] [he|ru|en] | <what to explain> [he|ru|en]"
---

Explain: $ARGUMENTS

Read-only work on the project: do not modify production code. Language: Hebrew by default
(project documents rule in CORE); Russian or English if asked. Write by
`.claude/tech-lead-kit/WRITING.md` — facts with evidence, no filler. Diagrams and the HTML file:
the `oleg-skill-hesber` skill (inline SVG, offline, light/dark, RTL).

**Mode by the first word:**

## `project [module]` — the project document
Output: `.claude/tl-memory/project-doc/PROJECT_DOC.md` + `PROJECT_DOC.html`, or — if
`KNOWLEDGE.md` shows the project document as published — that published file (update in place).
Audience: a developer who joins the team.
1. **Start from what is known:** `PROJECT_CONTEXT.md` (if missing, say that `/tl-init` would help,
   and continue), `KNOWLEDGE.md` and the documents it lists (specs, ADRs, designs, analyses),
   `TECH_DEBT.md`, README and docs in the repository. A previous version exists → update it and
   list what changed.
2. **Research in parallel** — `tl-researcher` subagents in one message, each with its budget:
   - `code` (project-wide): modules and responsibilities, layers, entry points, the 3–5 main
     business flows with files, configuration, build/test commands;
   - `data`: main tables of this project (names found in code), keys, relations, sizes, which
     module reads/writes which table (catalog only, through the registered data sources);
   - `docs`: business purpose, terms, processes, integrations described in documents.
3. **Write** `PROJECT_DOC.md` following
   `.claude/skills/tl-architecture/references/project-doc-template.md`. Every statement with
   evidence; unconfirmed things go to "Open questions". No secrets — name where they come from.
4. **Illustrated version:** `PROJECT_DOC.html` with architecture, main flows (sequence) and the
   data model as diagrams, built from the same facts.
5. **Self-check:** pick 5 statements and re-verify each against its evidence; fix what does not hold.
6. Both files start with a `tl-meta` line (`type=project-doc`); run
   `python .claude/tech-lead-kit/scripts/tl_knowledge.py index`.

## `<what to explain>` — an explanation of one subject
A process, module, data flow, integration, installation or "how X decides Y".
1. Find the facts: the code paths and tables involved (search; a `tl-researcher` with focus `code`
   for a large area), documents of the area from `KNOWLEDGE.md`.
2. Follow the `oleg-skill-hesber` skill: one HTML file in `.claude/tl-memory/hesber/` with 2–5
   diagrams that each answer one question (what talks to what; in which order; what decides; what
   is stored where), short text next to each, every fact traceable to `file:line` or a document.
3. `tl-meta` line `type=explain`; run `tl_knowledge.py index`.

**Reply in Russian:** where the files are, what each diagram shows, the 3–5 most important
observations (risks, surprises), open questions, an offer to `/tl-publish` it. End with the step card.
