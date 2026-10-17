---
name: tl-architecture
description: Architect-level design before coding — requirements, options with trade-offs, module/service boundaries, API and web-service contracts, data design, integration with mainframe (COBOL/Natural/DB2 z/OS) and SQL Server systems, and Architecture Decision Records (ADR). Use for every LARGE task (new module/service/endpoint, schema change, new integration, cross-module change), when choosing between technologies or patterns (modular monolith vs microservices, sync vs async, REST vs SOAP vs MQ), or when reviewing a design.
---

# Architecture & Design (before code)

Based on Anthropic's `system-design` and `architecture` frameworks, adapted to this
environment: offline, Windows, SQL Server 2019/2022 + DB2 z/OS, COBOL/Natural legacy next to
C#/Python/Node services.

The junior mistake this prevents: jumping into code, putting everything into one place,
and discovering constraints after the code is written.

## Process
Write the design to `.claude/tl-memory/design/<YYYY-MM-DD>-<short-name>.md` (Hebrew), using
`references/design-doc-template.md`. Keep it proportional — one page for a medium change,
more only when the problem needs it.

### 1. Understand the problem
- Restate the goal in 2–3 sentences. What business outcome? Who are the users/consumers?
- **Functional requirements** — what it must do (list).
- **Non-functional requirements** — volume (rows, requests/sec, batch window), latency,
  availability, consistency, security/compliance, auditability.
- **Constraints** — existing systems that must not change, technologies allowed, deadlines,
  team skills, mainframe windows, DBA/ops processes.
- **Open questions** — ask the user now; do not invent business rules.

### 2. Explore the current state
- Read `PROJECT_CONTEXT.md`, the relevant code, and the existing ADRs and specs listed in
  `.claude/tl-memory/KNOWLEDGE.md` (local and published). An approved spec gives the requirements.
- Use the SQL MCP (read-only) to inspect the real tables, indexes and procedures involved.
- Identify who owns which data, and all consumers of what you will change.

### 3. Options (at least two real ones)
For each option: short description, how it fits existing architecture, complexity, risk,
performance at expected volume, operability, cost of change later, effort.
"Do the minimal change inside the existing structure" is always one of the options.

### 4. Decide and design
- Recommend one option with reasoning in terms of the requirements.
- Define: module/service boundaries, responsibilities, **contracts** (API/WSDL/message/
  procedure/copybook signatures), data model changes, error handling and retries,
  transactions/consistency, security, logging/monitoring, migration & rollout, tests.
- Show a simple diagram (ASCII) of components and data flow.
- State what you would revisit when volume or requirements grow.

### 5. ADR
For significant decisions (technology, pattern, boundary, data ownership, contract style),
write `.claude/tl-memory/adr/ADR-NNN-<short-name>.md` from `references/adr-template.md`.
The number comes from `python .claude/tech-lead-kit/scripts/tl_knowledge.py next-id ADR` (counts
local and published ADRs). Status: `Proposed` until the user approves.

### 6. STOP for approval
Present the design summary in Russian: the problem, the options, the recommendation, risks,
the implementation plan as small steps, and the questions. **Do not write production code until
the user approves.** After approval: set ADR status to `Accepted`, then implement with the
`tl-engineering-standards` skill (and `tl-sql-engineering` for SQL).

## Topic references — load as needed
- Modular monolith vs microservices, boundaries → `references/boundaries-and-services.md`
- REST / SOAP / gRPC / MQ contracts, versioning, idempotency → `references/api-and-integration.md`
- Mainframe ↔ distributed integration (COBOL, Natural, DB2 z/OS, CICS, batch) →
  `references/mainframe-integration.md`
- Templates → `references/design-doc-template.md`, `references/adr-template.md`

## Design review checklist (also used by the architect reviewer)
- [ ] Requirements, NFRs and constraints explicit; open questions listed, not assumed.
- [ ] At least two options compared honestly, including the minimal one.
- [ ] Clear boundaries; each component has one responsibility and owns its data.
- [ ] Contracts defined and versionable; backward compatibility for existing consumers.
- [ ] Failure modes: timeouts, retries (idempotent only), partial failure, duplicates.
- [ ] Data: schema verified against the real DB; volume and index strategy considered.
- [ ] Security and audit addressed.
- [ ] Rollout and rollback plan; migration steps (expand → migrate → contract).
- [ ] Testability: how each part is tested.
- [ ] Complexity proportional to the problem — no microservices/queues/frameworks without need.
