---
name: tl-engineering-standards
description: Tech Lead coding standard for writing and changing production code in C#/.NET, C++, Python, Node.js, COBOL and Natural — structure, boundaries, naming, error handling, testing, security, and per-language rules. Use whenever implementing, refactoring or fixing code (not only when asked about "standards"), and when reviewing code quality. Prevents junior-style code — monolithic classes, logic in the wrong layer, swallowed errors, no tests, short-sighted design.
---

# Engineering Standards (Tech Lead level)

The goal: code that a strong Tech Lead would merge without rework, and that the next developer
can change safely a year from now.

## How to work (every implementation)
1. **Orient.** Read `.claude/tl-memory/PROJECT_CONTEXT.md` if present. Find the module you are
   changing, its callers, its tests, and 1–2 similar existing implementations. Detect the
   language/runtime version from project files (`*.csproj` `TargetFramework`,
   `pyproject.toml`/`requirements*.txt`, `package.json` `engines`, compiler flags/`CMakeLists.txt`)
   and do not use features above that version.
2. **Classify** the task SMALL / LARGE (see core rules). LARGE → design and approval first.
3. **Plan the change in steps** that each compile and keep tests green. Say the plan briefly.
4. **Implement** following the principles below + the language file.
5. **Test**: add/adjust tests; run them if you can. If you cannot run them, say exactly what
   the user must run.
6. **Self-review** against the checklist at the bottom before reporting.

## Principles (detail: `references/principles.md`)
- **Structure by responsibility, not by convenience.** Presentation/API ↔ application (use
  cases) ↔ domain (rules) ↔ infrastructure (DB, files, MQ, HTTP). Domain does not depend on
  infrastructure. Respect the project's existing layering; if there is none, do not dump code
  into one class — create the smallest sensible structure and explain it.
- **Small units.** Functions do one thing (guideline: < 40 lines, ≤ 4 parameters, nesting
  ≤ 3). Classes/modules have one reason to change. A file growing past ~400 lines is a signal
  to split.
- **Names tell intent.** `CalculateLateFee(invoice, asOfDate)`, not `Process(data, flag)`.
  No abbreviations except domain-standard ones. Boolean names read as questions (`isActive`).
- **No magic values.** Business constants have names and one home; configuration lives in
  config, not code.
- **Dependencies are explicit** (constructor/parameters), not hidden in statics/singletons, so
  code is testable.
- **Immutability and pure functions** for domain logic wherever practical.
- **Duplication**: remove real duplication of knowledge (business rules); tolerate incidental
  similarity. Three similar cases before an abstraction.
- **Errors**: see `references/error-handling.md`. Never swallow; keep the cause; map at boundaries.
- **Security**: see `references/security.md`. Validate input at the boundary; parameterized SQL;
  no secrets in code/logs.
- **Tests**: see `references/testing.md`.
- **Data access**: follow the `tl-sql-engineering` skill for any SQL.

## Language files — load the one you need
| Language | File |
|---|---|
| C# / .NET (incl. web services, Web API, WCF/ASMX legacy) | `references/csharp.md` |
| C++ | `references/cpp.md` |
| Python | `references/python.md` |
| Node.js (JavaScript/TypeScript) | `references/nodejs.md` |
| COBOL (z/OS, batch & online, DB2) | `references/cobol.md` |
| Natural (Software AG) | `references/natural.md` |

## Comments
- Hebrew, and only for **why**: business rule, non-obvious decision, workaround with reason,
  link to ADR. Do not narrate what the code does.
- Public APIs (classes, endpoints, procedures, copybooks) get a short contract comment.
- `TODO` only with a reason and an entry in the tech debt register (`TECH_DEBT.md`, location in
  `.claude/tl-memory/KNOWLEDGE.md`).

## Refactoring while implementing
- Do not mix refactoring and behavior change in one step. Refactor first (tests green), then
  change behavior.
- Out-of-scope problems you notice: do not fix silently — mention them and add to TECH_DEBT.md.

## Self-review checklist (before saying "done")
- [ ] Follows existing project conventions; no parallel style introduced.
- [ ] Each new/changed unit has one responsibility; no logic in the wrong layer.
- [ ] Names express intent; no magic values; no dead code or commented-out code.
- [ ] All error paths handled deliberately; resources released (using/RAII/finally/with).
- [ ] Inputs validated at the boundary; no secrets; SQL parameterized and index-aware.
- [ ] Concurrency/idempotency considered where the code can run twice or in parallel.
- [ ] Tests cover the new behavior and the failure paths; existing tests still pass.
- [ ] Logs are useful (context, correlation id) and contain no PII/secrets.
- [ ] Backward compatibility of public contracts (APIs, DTOs, procedures, copybooks, files).
- [ ] Hebrew why-comments where needed; debt recorded.
