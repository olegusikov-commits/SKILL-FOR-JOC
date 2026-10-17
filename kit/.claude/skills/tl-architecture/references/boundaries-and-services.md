# Boundaries: modular monolith vs microservices

## Default position
Start from a **well-structured modular application** with clear module boundaries.
Extract a separate service only when there is a concrete reason. "Microservices" is a deployment
and organizational choice, not a quality badge — a badly bounded set of services is worse than a
monolith (distributed monolith: all the coupling plus network failures).

## Reasons that justify a separate service
- Different **scaling** profile (one part needs 10x resources).
- Different **availability / release cadence** requirements, owned by a different team.
- Strong **isolation** need (security zone, regulatory boundary, fault isolation).
- Different **technology** genuinely required (e.g. Python ML next to .NET core).
- Integration façade in front of a legacy system (mainframe gateway) used by several consumers.

## Reasons that do NOT justify it
"It's modern", "smaller code", "we might need to scale", "each table gets a service",
one developer, no CI/CD/monitoring for multiple services.

## How to find boundaries
- By **business capability** (customers, orders, billing, payments), not by technical layer.
- Each boundary **owns its data**: only it writes its tables. Others get data through its API,
  events, or a published read model/view.
- High cohesion inside (things that change together stay together), low coupling between.
- Test: can you describe the module's responsibility in one sentence without "and"?
- Test: will a typical business change touch one module or five?

## Inside a modular monolith
- One folder/project/namespace per module with an explicit public interface; internals are not
  referenced from other modules (enforce with project references / internal visibility /
  architecture tests if available).
- Cross-module calls go through the public interface or in-process events.
- Separate schemas or table prefixes per module in the database when possible.

## If you do split into services
- One service = one bounded context = its own data store/schema.
- Communication: synchronous (REST/gRPC) for queries that need an immediate answer; asynchronous
  (MQ/events) for commands/notifications that can be delayed — prefer async between services to
  avoid chains of synchronous calls.
- No distributed transactions; use **transactional outbox** for reliable event publishing and
  **sagas** (with compensations) for multi-service workflows.
- Every service: health checks, structured logs with correlation id propagated across calls,
  timeouts, retries with backoff for transient errors, idempotent consumers, versioned contracts.
- Record the split decision in an ADR, including the operational cost accepted.
