# APIs, web services and integration contracts

## Choosing the style
| Style | Use when | Watch out |
|---|---|---|
| REST/JSON | Resource-oriented APIs, web/mobile/consumers in many languages | Consistent resource naming, status codes, pagination, versioning |
| SOAP/WSDL | Existing enterprise consumers, mainframe/CICS web services, WS-Security required | Contract-first; never break the WSDL; namespaces versioned |
| gRPC | Internal high-throughput service-to-service in compatible stacks | Tooling/proxy support in the company network |
| MQ (IBM MQ etc.) | Async, guaranteed delivery, decoupling from mainframe/batch, load leveling | Idempotent consumers, poison messages, ordering assumptions, DLQ |
| File transfer / batch | Large volumes on a schedule, mainframe batch windows | Record layout contract (copybook), control totals, restart |

## Contract rules (all styles)
- Contract-first: define the request/response/message schema before implementation
  (OpenAPI, WSDL/XSD, JSON schema, copybook).
- Changes are **additive**: new optional fields, new endpoints/operations. Removing or renaming
  = new version (`/v2`, new namespace, new message type) with a deprecation period.
- Consumers are **tolerant readers**: ignore unknown fields.
- Explicit types and formats: dates ISO-8601 with timezone, money as decimal strings or minor
  units with currency, enumerations documented, encoding (UTF-8 vs EBCDIC/Hebrew) stated.
- Errors are part of the contract: REST → ProblemDetails (RFC 7807/9457) with stable error codes;
  SOAP → defined faults; MQ → error/reply queues and DLQ.

## REST specifics
- Nouns for resources, HTTP verbs for actions, plural collections (`/orders/{id}`).
- Status codes: 200/201/204, 400 validation, 401/403, 404, 409 conflict, 422 business rule,
  429, 5xx only for server faults.
- Pagination (keyset/cursor for large sets), filtering and sorting parameters whitelisted.
- Idempotency: `PUT`/`DELETE` idempotent by design; for `POST` that creates/charges, support an
  `Idempotency-Key` header or a business key with a unique constraint.
- Optimistic concurrency with `ETag`/`If-Match` or a row-version field where updates compete.

## Reliability
- Every outbound call: timeout, bounded retry with exponential backoff + jitter **only for
  transient errors and idempotent operations**, circuit breaker for unstable dependencies.
- At-least-once delivery is the reality for messaging → consumers deduplicate (message id or
  business key stored with a unique constraint).
- Correlation id generated at the edge and propagated through HTTP headers / MQ message
  properties / logs.

## Security
Authentication at the gateway/service per company standard; authorization per operation and per
object; input validation against the schema; no sensitive data in URLs; TLS everywhere.
