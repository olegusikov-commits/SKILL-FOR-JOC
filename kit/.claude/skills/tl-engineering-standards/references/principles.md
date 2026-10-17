# Design principles in code (anti-monolith, anti-junior)

## Layering
```
[ API / UI / Batch entry ]   controllers, web service endpoints, CLI, COBOL main paragraphs
          │  calls
[ Application / use cases ]  orchestrates one business operation, owns the transaction
          │  calls
[ Domain ]                   business rules, entities, value objects, calculations — pure
          ▲  implemented by
[ Infrastructure ]           repositories, SQL, MQ, HTTP clients, files — behind interfaces
```
- Entry points are thin: parse/validate input → call one use case → map result/errors.
- Use cases do not contain SQL or HTTP details; they call interfaces (ports).
- Domain code has no I/O and is trivially unit-testable.
- Infrastructure adapts external systems to the interfaces the application defines.
- This applies in every language. In COBOL it means: separate paragraphs/subprograms for
  input handling, business rules, and DB access — not one 3,000-line PROCEDURE DIVISION.

## Modularity
- Group code **by business capability** (orders, billing, customers) before grouping by
  technical type. A module exposes a small public surface and hides its internals.
- Modules talk through explicit interfaces or events, not by reaching into each other's tables.
  **Shared database tables between modules are coupling** — if unavoidable, one module owns
  writes, others read via a view/API.
- A change to one business feature should touch one module, ideally.

## Thinking ahead (what a Tech Lead asks before coding)
- **What will change?** New product types, new channels, new rules, regulatory changes — isolate
  them behind a strategy/table/config, but only when the change is likely, not "just in case".
- **Volume:** how many rows/requests now and in 3 years? Is anything O(n²) or loading all rows
  into memory?
- **Failure:** what if the DB/service is slow or down, the message is duplicated, the job dies
  half-way? → timeouts, retries with backoff for transient errors only, idempotency,
  restartability.
- **Concurrency:** can two users/jobs do this at once? → optimistic concurrency (row version),
  unique constraints, proper transaction scope.
- **Operations:** how will someone diagnose this at 2am? → structured logs with correlation id,
  clear error messages, metrics where the project has them.
- **Contract evolution:** who consumes this API/file/procedure/copybook? How do we change it
  without breaking them? → versioning, additive changes, tolerant readers.

## SOLID — pragmatically
- **S**: one reason to change per unit. The most violated and most important.
- **O**: extend by adding code (new strategy/handler) for the variation points you actually have.
- **L**: subtypes must honor the base contract; if you need `if (x is Special)`, the hierarchy is wrong.
- **I**: small, focused interfaces; consumers do not depend on methods they don't use.
- **D**: high-level policy depends on abstractions; wire implementations at the entry point.

## Anti-patterns to refuse
- God class / "Manager" / "Helper" / "Utils" collecting unrelated logic.
- Business logic in controllers, UI events, triggers, or SQL strings scattered in UI code.
- Copy-paste of a business rule into several places.
- Boolean/flag parameters switching behavior (`Save(order, true, false)`).
- Static mutable state, service locators, hidden I/O in constructors.
- Catch-all exception handlers that log and continue.
- Premature abstraction: interfaces with one implementation and no test/boundary reason,
  generic frameworks for a single use.
- "Temporary" hacks without a TECH_DEBT entry.

## Integration patterns (microservices & web services)
- Synchronous call (REST/SOAP/gRPC) when the caller needs the answer now; always with timeout,
  and a decision about retries and what happens on failure.
- Asynchronous messaging (MQ) when the work can happen later or must survive outages; consumers
  must be **idempotent** (dedupe by message id / business key).
- Never do a distributed transaction across services by hand; use outbox pattern or a saga, and
  record the choice in an ADR.
- Contracts (OpenAPI/WSDL/schemas/copybooks) are versioned and changed additively.
