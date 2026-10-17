---
description: Publish approved kit documents (specs, ADRs, designs, the project document, explanations, analysis reports) into the project's docs, so every teammate and every AI agent in the project sees them; updates the knowledge block in AGENTS.md / CLAUDE.md; never commits
argument-hint: "[paths or ids of documents — default: all approved documents that are still local]"
---

Publish to the project: $ARGUMENTS

Kit documents live in `.claude/tl-memory/` — local and hidden from git. Publishing moves the
approved ones into the project's repository and writes a short, tool-neutral knowledge block into
`AGENTS.md` at the project root (read by Claude Code through an `@AGENTS.md` line in the project's
root `CLAUDE.md` — the team's file, not `.claude/CLAUDE.md` — and by other agents directly). The kit itself, drafts, analysis working files and queries stay local.
Tool: `python .claude/tech-lead-kit/scripts/tl_knowledge.py` (or `py -3 …`).

1. **Settings.** If `.claude/tl-memory/publish.json` does not exist, propose the defaults in one
   short message and wait for a yes (or changes): documents under `docs/` — `specs/`, `adr/`,
   `design/`, `project/`, `explain/`, `analysis/`, `specs/checks/`, `TECH_DEBT.md`; knowledge
   block in `AGENTS.md`; one line `@AGENTS.md` in the root `CLAUDE.md`. If a proposed folder already exists
   with the team's own files (e.g. their `docs/adr/`), say so and propose another. Then write the file:
   `{"docs_root": "docs", "folders": {"spec": "specs", …}, "agents_file": "AGENTS.md",
   "claude_md_import": true}` (only the keys that differ from the defaults are needed).
2. **Facts for all agents.** No `PROJECT_CONTEXT.md` → skip this step and suggest `/tl-init`. If
   `PROJECT_CONTEXT.md` has no block between
   `<!-- tl-agents:begin -->` and `<!-- tl-agents:end -->`, add one: at most 12 lines in Hebrew —
   what the project is, build and test commands, where the main code is, the database aliases
   (MCP server names) and "PROD is read-only", key conventions. No secrets, no host names, no
   connection strings.
3. **Select** the documents: those named in the arguments; otherwise the local specs, ADRs and
   designs in `KNOWLEDGE.md` with status `approved` / `accepted`. Other kinds (analysis reports,
   explanations, the project document, the debt register) only when the user names them; a draft
   only when the user asks for it explicitly. Show the list and **STOP** until the user says yes.
4. **Make each one fit for the team** — run `tl_knowledge.py check <file>` and fix every issue in
   the document itself: links to local-only files (queries, topic files) → inline the needed
   content or drop the link; mentions of kit commands → plain words; rows of PROD data → only
   aggregates; secrets → never. Make sure its `tl-meta` `area` names the code paths, tables and
   terms it covers — that is how agents find it.
5. **Publish:** `tl_knowledge.py publish <files…>` (refuses a file that `check` still finds
   issues in; moves Markdown with its HTML twin, rebuilds `KNOWLEDGE.md`, updates the block in
   `AGENTS.md` and the import in `CLAUDE.md`). Destination exists with other content → do not use
   `--force`; show the difference and ask. A moved analysis report → update its link in
   `analysis/INDEX.md` and the topic's `JOURNAL.md` to the new path.
6. **Do not commit or push.** Reply in Russian: what moved where, the new knowledge block, the
   `git status --short` of the published paths, and that the user reviews and commits them like
   any other change. From now on, update a published document in place (it is the master copy).
