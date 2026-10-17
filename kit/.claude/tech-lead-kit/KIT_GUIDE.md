# Tech Lead Kit — how to use it in this project

This project has the Tech Lead Kit installed (local, not committed). You know its commands and
use them; the user may also ask in plain words — then follow the same path and, in one line,
name the command that does it next time. Never force a command on a small question.

## Which command for which request
| The user wants… | Use |
|---|---|
| to start working with the kit in this project, or the kit was updated | `/tl-init` |
| a requirement / specification (אפיון) from a business request | `/tl-spec new <name>` → user fills the form → `/tl-spec SPEC-nnn` |
| to check a specification someone wrote | `/tl-spec check <file>` |
| a new module, service, endpoint, integration, schema change (LARGE) | `/tl-design <task or SPEC-nnn>` → approval → `/tl-implement` |
| code written or changed (SMALL, or an approved design / spec) | `/tl-implement <task, SPEC-nnn or design path>` — the only command that writes production code |
| a review of changes before commit | `/tl-review [files]` |
| SQL, procedures, indexes, query performance | `/tl-sql <task>` |
| technical debt audit / what to refactor | `/tl-debt [path]` |
| numbers: improve a metric, evaluate an idea or code, a data question | `/tl-an-learn <topic>` once, then `/tl-an <task>` |
| an explanation with diagrams | `/oleg-skill-hesber <what>` |
| a full project document | `/tl-project-doc [module] [ru\|en] [html]` |
| approved documents shared with the team and every agent | `/tl-publish` (automatic when `auto_publish` is on) |

## The usual path of a business change
`/tl-an-learn` (once per topic) → `/tl-spec` (approved) → `/tl-design` if LARGE → `/tl-implement`
(every AC becomes a test) → `/tl-review` → `/tl-an` to verify the effect on data.
Code that already exists: `/tl-review` for quality, `/tl-an` for "does it meet the task and what
does it give".

## Documents the kit writes — where and how to use them
- Map of all of them: `.claude/tl-memory/KNOWLEDGE.md` (type, id, status, area, location). Read it
  at the start of every task and open the documents whose `area` touches the task.
- Drafts and working files live in `.claude/tl-memory/` (local). Approved documents live in the
  project (default `docs/specs`, `docs/adr`, `docs/design`, `docs/project`, `docs/explain`,
  `docs/analysis`) and are listed in the knowledge block of `AGENTS.md`, so teammates and other
  agents see them too.
- Settings: `.claude/tl-memory/publish.json`. With `"auto_publish": true` every document is
  published as soon as it is approved (specs, ADRs, designs) or finished (project document,
  explanations, analysis reports): run `python .claude/tech-lead-kit/scripts/tl_knowledge.py
  publish <file>`, fix what its check reports, and tell the user what moved (they commit).
- When you answer from a document, cite it (`SPEC-001 REQ-004`, `ADR-002`, report path).
