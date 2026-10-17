# Node.js standard (JavaScript / TypeScript)

Detect the Node version (`package.json` `engines`, `.nvmrc`), module system (ESM/CommonJS),
TypeScript usage and lint config. Prefer TypeScript with `strict` when the project uses it.

## Structure
- Layers: `routes/controllers` (thin) → `services/use-cases` → `domain` → `repositories/clients`.
- One central error-handling middleware; route handlers do not format errors themselves.
- Configuration from environment, validated at startup (zod/joi/envalid); fail fast on missing
  config.
- Graceful shutdown: stop accepting requests, finish in-flight work, close DB pools.

## Code
- `async`/`await`; every promise awaited or explicitly handled; no floating promises;
  `Promise.all` for independent I/O, with concurrency limits for large fan-out.
- No synchronous I/O (`fs.readFileSync`, `execSync`) in request paths.
- Validate all external input (body, query, headers, messages) with a schema at the boundary.
- No `any` in TypeScript without a reason; types for DTOs and domain objects.
- Errors: subclasses of `Error` with `cause`; never throw strings; map to HTTP status in the
  error middleware.
- Structured logging (pino/winston per project) with request id; no `console.log` in production code.
- Timeouts on every outbound HTTP/DB call.

## Data access
- SQL Server (`mssql`): typed parameters —
  `request.input('code', sql.VarChar(20), code)` then `request.query('... WHERE Code = @code')`.
  Use a single shared connection pool.
- DB2 (`ibm_db`): prepared statements with `?` markers.
- No string-built SQL, ever. Transactions via the driver's transaction API, short.

## Dependencies & security
`npm ci` with the lockfile; no new package without justification (LARGE task); `helmet`,
CORS and rate limiting for public HTTP services per project; never `eval`/`new Function`.

## Tests
Jest/Vitest/node:test per project; supertest for HTTP; fake repositories for services.
