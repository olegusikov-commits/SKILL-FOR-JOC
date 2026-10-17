# C# / .NET standard

Detect `TargetFramework` (`net8.0`, `net6.0`, `net48`…) and `LangVersion`/`Nullable` in the
`.csproj`; do not use features the project cannot compile.

## Structure
- Solution split by responsibility: `*.Api` / `*.Application` / `*.Domain` / `*.Infrastructure`
  (or the project's existing equivalent). Domain references nothing infrastructural.
- Controllers / endpoints / WCF / ASMX services are thin: validate → call application service →
  map result. No SQL, no business rules there.
- Dependency injection through the built-in container (or the project's container); constructor
  injection; no `new` of services inside business code; no static service locators.
- Configuration through the Options pattern (`IOptions<T>`) with validation at startup.

## Language
- Nullable reference types enabled for new code; no `!` to silence warnings without a reason.
- `record` / immutable types for DTOs and value objects; `sealed` by default for classes not
  designed for inheritance.
- Guard clauses at public entry points (`ArgumentNullException.ThrowIfNull`, range checks).
- `async`/`await` all the way: no `.Result`, `.Wait()`, `async void` (except event handlers);
  pass `CancellationToken` through I/O calls; `ConfigureAwait(false)` in library code.
- `using` / `await using` for every `IDisposable` (connections, commands, streams).
- LINQ: no multiple enumeration of expensive sequences; materialize deliberately.
- Exceptions: specific domain exceptions; `throw;` to rethrow; never `catch (Exception)` except
  in the boundary handler.

## Web API / services
- ASP.NET Core: errors as `ProblemDetails`; consistent status codes; model validation
  (DataAnnotations / FluentValidation per project).
- Version public APIs; changes are additive.
- `HttpClient` via `IHttpClientFactory` / typed clients, with timeouts and a resilience policy
  (Polly or built-in resilience) for transient failures only.
- Legacy WCF/ASMX: never change existing contracts (DataContract/WSDL) incompatibly.

## Data access
- Follow the project choice (EF Core / Dapper / ADO.NET).
- ADO.NET / Dapper: parameters with explicit types:
  `cmd.Parameters.Add("@Code", SqlDbType.VarChar, 20).Value = code;`
  — **not** `AddWithValue` (infers `nvarchar` → implicit conversion → index scan).
- EF Core: projections (`Select`) for reads, `AsNoTracking()` for read-only queries, avoid N+1
  (`Include` or projection), inspect generated SQL for hot paths, no `ToList()` before filters.
- Call stored procedures with `CommandType.StoredProcedure` and typed parameters.
- Transactions owned by the application layer (unit of work), short.

## Logging
`ILogger<T>` with message templates (`_logger.LogInformation("Order {OrderId} cancelled", id)`),
not string interpolation; scopes for correlation ids.

## Tests
xUnit/NUnit/MSTest per project; FluentAssertions if present; `WebApplicationFactory` for API
tests; fakes for repositories in use-case tests.
