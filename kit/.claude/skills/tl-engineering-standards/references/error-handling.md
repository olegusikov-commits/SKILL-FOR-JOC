# Error handling and logging

## Classify every failure
| Kind | Example | Handling |
|---|---|---|
| Programmer error / bug | null where impossible, invalid state | Fail fast (assert/throw); do not catch locally |
| Expected business outcome | not found, insufficient balance, duplicate | Explicit result or specific business exception; part of the contract |
| Invalid input | bad format, out of range | Validate at the boundary; return a clear 4xx / validation error |
| Transient infrastructure | timeout, deadlock (1205, -911/-913), 503 | Bounded retry with backoff + jitter, only if the operation is idempotent |
| Permanent infrastructure | auth failure, missing table, config error | Fail with a clear message; alert; no retry loop |

## Rules
1. **Never swallow.** No empty catch, no `catch { return null; }`, no `except: pass`,
   no ignored SQLCODE / Natural `*ERROR-NR`.
2. **Catch only what you can handle**, at the level that can decide what to do. Otherwise let
   it propagate to the boundary handler.
3. **Keep the cause.** Wrap with context (`throw new OrderSubmitException("...", ex)`,
   `raise ... from e`, `{ cause }` in Node); rethrow with `throw;` in C#, not `throw ex;`.
4. **One boundary handler** per entry point (API middleware, batch main, message consumer) maps
   errors to responses/return codes and logs once. Do not log-and-rethrow at every level.
5. **Resources are always released**: `using`/`await using`, RAII, `with`, `try/finally`,
   COBOL/Natural close/cleanup paragraphs on every path.
6. **Partial failure**: in multi-step operations, define what happens if step 3 of 5 fails
   (transaction, compensation, or idempotent retry). Write it down.
7. **Error messages**: for users — clear and safe (no stack traces, SQL, or internal names);
   for logs — full technical detail.

## Logging
- Structured (key=value / JSON) using the project's logger; never `Console.WriteLine`/`print`
  for production diagnostics.
- Include: operation, key business identifiers, correlation/request id, duration for I/O,
  outcome.
- Levels: ERROR = needs attention; WARN = unexpected but handled; INFO = business events at a
  sensible rate; DEBUG = developer detail.
- Never log secrets, passwords, tokens, full card/ID numbers, or other PII — mask them.
- Logs are for operations: every ERROR should answer "what failed, for which entity, why, and
  what should someone do".
