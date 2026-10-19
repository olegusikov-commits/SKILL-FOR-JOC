# New service — checklist (design and MVP)

Use when the task creates a new service, API or endpoint ("build a microservice that returns X").
Start from what the project already has: an existing service is the template — same stack,
folder layout, logging, configuration, error format, test style. A new pattern needs an ADR.

## Decide first (design / spec section 19)
| Question | Default when nobody knows |
|---|---|
| New service or an endpoint in an existing one? | Endpoint in the existing service unless it owns other data, scales differently or is deployed by another team (`boundaries-and-services.md`) |
| Who calls it, how often, how fast? | Write the numbers; unknown → `[הנחה]` + a question |
| Contract style | REST/JSON like the project's other APIs; SOAP/MQ only if the callers need it (`api-and-integration.md`) |
| Data access | Read through an index that serves the main search (check the catalog); a stored procedure if the project does so |
| Volume of one answer | Paged (keyset), a hard maximum page size |
| Security | Caller authentication as the other services; least-privilege DB user; mask sensitive fields |

## Contract first
For each operation: route / name, input fields with types and which are required, output, error
codes (validation, not found, conflict, unavailable), paging, idempotency for writes, version in
the path or header. Write it in the design (and an OpenAPI / WSDL file if the project keeps them).

## Skeleton (task T1–T3 of the plan)
- Layers: API (validation, mapping) → application (use case) → data access (one repository per
  aggregate). No SQL in controllers, no HTTP in the data layer.
- Configuration from the environment / config files of the project; no secrets in code or repo.
- Logging: one line per request with a correlation id, duration and result; no PII.
- Health / readiness endpoint; timeouts on every outbound call (DB, HTTP, MQ); bounded retries
  only for idempotent calls.
- Errors: one error format for the whole API; expected failures are typed, bugs fail fast.

## Tests
- Unit tests for the application layer: every AC of the spec → a test named with the AC id.
- Contract tests: request / response shape, error codes, paging boundaries (0, 1, max, max+1).
- Data access against TEST (or the project's test DB) for the main query; the query plan uses the
  index chosen in the design.

## Done for MVP
Main scenarios work end to end with tests; contract written; health, logging, config in place.
Later tasks in the plan: edge cases beyond the main AC, load test, dashboards, full docs.

## Per stack
The language reference of `tl-engineering-standards` (`csharp.md`, `python.md`, `nodejs.md`) has
the stack's conventions; follow the project's existing service where they differ.
