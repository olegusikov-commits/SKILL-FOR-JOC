# Tech Lead Kit — how to use it in this project

This project has the Tech Lead Kit installed (local, not committed). You know its routes and use
them; the user may also ask in plain words — then follow the same route and, in one line, name the
command that does it next time. Never force a command on a small question.

## Routes — one goal each
| Route · command | The user wants… (example) | Modes | Result |
|---|---|---|---|
| Navigator `/tl-go` | "I want X, which command?" · "where did I stop?" | `<request in words>` → propose route(s), confirm · no args → open work + next step · `new <request>` → the whole task FLOW | the chosen route, started after "yes" |
| Setup `/tl-init` | first time in a project; after a kit update | — | project map, data sources, kit self-check (`tl_doctor.py`), limits |
| Requirement (אפיון) `/tl-spec` | "a business request — what exactly must be done?" | `new <name>` interview, written **together** with the user · `complete SPEC-nnn` close gaps with the user · `SPEC-nnn` build alone · `check <file>` review someone's spec | `SPEC.md` + `SPEC.html`, stop for approval |
| Technical design `/tl-design` | LARGE change: **how** to build it — options, cost, risk, the choice, the plan | `SPEC-nnn` or a task | design + ADR + task plan, stop for approval |
| Code `/tl-implement` | "write / fix the code" — approved design, spec, or a small fix | task · `SPEC-nnn` · design path (resumes at the first open task) | code + tests (every AC → a test) |
| SQL `/tl-sql` | queries, procedures, indexes | `build` from a requirement · `check <file/procedure>` correctness, results, edge cases, speed, safety · `tune` slow query/report: DBA options | SQL with the access path / check report |
| Code check `/tl-review` | "the code is ready — check it before git / colleagues" | files or current changes | BLOCKER / MAJOR / MINOR + requirement coverage |
| Analysis `/tl-an` | numbers: improve a metric, evaluate an idea, "does the code meet the task" | `learn <topic>` · a task · `verify SPEC-nnn` | report with numbers and a verdict |
| Explanation `/tl-explain` | "explain how X works", project document, onboarding | `project [module] [he\|ru\|en]` · `<what to explain>` | HTML with SVG diagrams + Markdown |
| Code health `/tl-debt` | "what is bad in the existing code, what first" | path / module | debt register with priorities |
| Publish `/tl-publish` | share approved documents with the team and every agent | paths / ids | `docs/` + block in `AGENTS.md` (automatic when `auto_publish` is on) |
| Learning `/tl-retro` | "you keep doing X wrong", "remember that…", "what have you learned here?" | no args → observations → proposals (buttons) · `show [kit]` · `term <word>` · `forget <id>` · `share` (glossary to the team) | lessons, terms, profile, project skills `tlp-*` → `ACTIVE.md` |

Choosing: **the smallest route that safely closes the task**; risk, an unclear goal or a wide reach
move it one step up (code → design → requirement). The built-in `/init` is not needed: `/tl-init`
does it locally and deeper; the team's shared file is `AGENTS.md` through `/tl-publish`.
Kit scripts run with `python …`; on Windows `py -3 …` if `python` is missing.

## Depth levels — fast and good, no work for the sake of work
| Level | When | Stages | Approvals |
|---|---|---|---|
| `mvp` (default for something new) | a working result fast | one short `SPEC.md` "requirement + solution" (goal, main REQ/AC, contract, task plan) → code + tests of the main AC → code check, BLOCKER only | one |
| `standard` | a feature in existing code | spec (no backtest without a number to prove) → design only if LARGE → code → code check | 1–2 |
| `full` | money, decision rules, PROD data, regulation | all: effect backtest, skeptics, effect check after | 2 + verdict |

Every check runs once, by one owner: no agent review of a design (the user approves it); skeptic
one round, only at `full` or when the document has numbers / decision tables; `tl-sql-reviewer`
only when SQL changed. What is postponed for speed becomes a task in the plan or `TECH_DEBT.md`.

## FLOW of a new task (`/tl-go new <request>`)
One folder per task: `.claude/tl-memory/spec/SPEC-nnn-<slug>/` with `REQUEST.md`, `SPEC.md`,
`FLOW.md` (stage checklist + `Дальше:` line, `skills/tl-requirements/references/flow-template.md`).
Each command ticks its stage and rewrites `Дальше:`. The FLOW runs stage after stage and stops only at
gates; in a new session `/tl-go` reads `FLOW.md` and continues.

| # | Stage | Command | Skills | Agents | Output | Gate |
|---|---|---|---|---|---|---|
| 0 | Entry | `/tl-go` | — | — | route + level, `FLOW.md` | confirm (buttons) |
| 1 | Intake: what and why | `/tl-spec new` | `tl-requirements` | — | `REQUEST.md` (kit drafts it from the request) | — |
| 2 | Learn: code, data, docs | `/tl-spec` | `tl-requirements`, `tl-sql-engineering` | `tl-researcher` ×(1–3) | `NOTES.md` | budgets below |
| 3 | Clarify | `/tl-spec` | `tl-requirements` | — | "הבהרות" section | ≤ 5 questions (mvp ≤ 3) |
| 4 | Requirement | `/tl-spec` | `tl-requirements` (+ `tl-analytics` backtest at `full`) | `tl-spec-skeptic` (rules above) | `SPEC.md` + `SPEC.html` | **approval** |
| 5 | Technical design (LARGE; at `mvp` it is part of `SPEC.md`) | `/tl-design` | `tl-architecture` (+ `tl-sql-engineering`) | — | design + ADR + task plan | **approval** |
| 6 | Code | `/tl-implement` | `tl-engineering-standards` + language file, `tl-sql-engineering` | — | code + tests, `[x]` in the plan | red test > 3 tries → stop |
| 7 | Code check | `/tl-review` | `tl-engineering-standards`, `tl-tech-debt` | `tl-architect-reviewer`, `tl-sql-reviewer` (SQL) | findings + coverage | fix now / debt / keep |
| 8 | Effect check (optional; `full`) | `/tl-an verify` | `tl-analytics` | `tl-an-skeptic` | report | verdict |
| 9 | Publish | `/tl-publish` | — | — | `docs/`, `AGENTS.md` | the user commits |

Short routes use the same stages: small fix = 0 → 6 → 7; SQL = 0 → `/tl-sql` → 7; data question =
0 → `/tl-an`; understand = 0 → `/tl-explain`; code health = 0 → `/tl-debt`.

## Questions — buttons, asked once
Ask only what code, data and documents cannot answer and what changes the result. Use the
AskUserQuestion tool: up to 4 questions per call, 2–4 options each, **your proposed answer first**
with "(рекомендуется)" and one line why; the user can always type their own. Order: impact ×
uncertainty. No tool → the same list as numbered text. Write the answers into the document
(section "הבהרות" → `### <date>` → `- ש: … → ת: …`) and apply them to the sections they change.
Unanswered → proposed answer as `[הנחה]`; never block other work on an answer.

## Loop limits — never spin, never hang
| Loop | Limit | At the limit |
|---|---|---|
| Clarify | ≤ 5 questions, one round (mvp ≤ 3) | proposed answers become `[הנחה]` |
| Research subagent | its `maxTurns`; ≤ 10 database queries, ≤ 1 heavy | partial result + "НЕ ЗАВЕРШЕНО" |
| Query → error → fix | ≤ 3 fixes per error; after a timeout only a narrower query, once | stop, show the query and the error |
| Skeptic → fix | 1 round | open findings stay listed in the document |
| Lint → fix | ≤ 3 passes | remaining findings in the reply |
| Code → test → fix | ≤ 3 tries per red test | stop: test, error, hypothesis |
| Review → fix → re-review | ≤ 2 rounds for BLOCKERs | list what is left, ask |
| Retro proposals | ≤ 8 per round (2 question calls); a rejected one again only with new evidence | the rest waits in `INBOX.md` |

At a limit: stop and report what is done, what is left and why — never continue silently. Before a
step that may take long, tell the user in one line what you are starting. Long shell commands get a
timeout; database work follows CORE "Data sources".
Database queries: `python .claude/tech-lead-kit/scripts/tl_sql.py check` before sending, `guard` for
MCP, `run` for command-line sources (hard timeout, CSV, journal `tl-memory/sql-journal.csv`).
A query hangs: the user presses Stop / Esc, then `/tasks` to stop a background task; the server may
still run it — ask the DBA to kill the session. `tl_doctor.py --apply-settings` (in `/tl-init`) sets
time limits for MCP calls.

Before showing a document: `python .claude/tech-lead-kit/scripts/tl_knowledge.py style <file>`
(WRITING.md notes; advice, fix what is true).

## Agents — only the kit's
Kit agents load CLAUDE.md (these rules) and preload their skills; the built-in Explore and Plan start
without CLAUDE.md, and general-purpose and agents of the user folder, plugins or the project have no
kit skills — `/tl-init` denies them in this project's personal `.claude/settings.local.json` (other
projects and the global `~/.claude` files are not changed; the global CLAUDE.md is loaded together
with the kit rules, contradictions are reported by `tl_doctor`). Delegate only when it keeps the main context clean or gives an
independent view:

| Need | Agent |
|---|---|
| search wider than ~5 files; code / data / documents research | `tl-researcher` (focus `search`, `code`, `data`, `docs`) |
| sizes, plans, blocking, options for a slow or big data problem | `tl-dba` |
| independent code review | `tl-architect-reviewer`, `tl-sql-reviewer` (SQL) |
| challenge a spec / an analysis | `tl-spec-skeptic`, `tl-an-skeptic` |

Everything else — reading a few files, planning, small edits — you do yourself, without an agent.
Give every agent the task, the paths, its budget and what to return.

## Learning — the kit gets better in this project
The last import of CORE (`ACTIVE.md`) is what the user approved: follow it like the user's own words;
CORE wins over it. Note an observation — one line, once per event, no secrets or personal data:
`python .claude/tech-lead-kit/scripts/tl_learn.py note <kind> <scope> "<what happened>"` — when the user
corrects you or rewrites your result (`correction`), a check finds your own mistake: a BLOCKER in code you
wrote, a red test after "done" (`mistake`), the user uses a term you did not know (`term`), asks for another
language, length or format (`style`), makes the same choice again (`habit`) or repeats the same steps
(`procedure`), or the kit itself got in your way (`kit`). Scope: `project`, `route:/tl-sql`,
`skill:<name>`, `agent:<name>`, `area:<topic>`, `kit`. Failed queries are collected by `harvest`, not noted.
"Remember …" / "запомни …" / "תזכור …" is an approval: write it at once (`/tl-retro` rules), then `render`.
When `note` or `ACTIVE.md` says observations wait, add `· /tl-retro` to the `Дальше:` line. Memory files
change only through `/tl-retro` or such a request (`.claude/tech-lead-kit/LEARNING.md`).

## Step card — the end of every command reply
```
Маршрут: <route> · этап <n>/<m> «<stage>» — <готово | ждёт утверждения | остановлено: причина>
Дальше: <exact next command or phrase>   ·   или /tl-go
```

## Documents the kit writes — where and how to use them
- Map of all of them: `.claude/tl-memory/KNOWLEDGE.md` (type, id, status, area, location). Read it
  at the start of every task and open the documents whose `area` touches the task.
- Drafts and working files live in `.claude/tl-memory/` (local). Approved documents live in the
  project (default `docs/specs`, `docs/adr`, `docs/design`, `docs/project`, `docs/explain`,
  `docs/analysis`) and are listed in the knowledge block of `AGENTS.md`.
- Writing standard for every document: `.claude/tech-lead-kit/WRITING.md`.
- Settings: `.claude/tl-memory/publish.json`. With `"auto_publish": true` every document is
  published as soon as it is approved (specs, ADRs, designs) or finished (project document,
  explanations, analysis reports): run `python .claude/tech-lead-kit/scripts/tl_knowledge.py
  publish <file>`, fix what its check reports, and tell the user what moved (they commit).
- When you answer from a document, cite it (`SPEC-001 REQ-004`, `ADR-002`, report path).
