# Security baseline

- **Injection**: SQL always parameterized; no shell commands from user input; no dynamic code
  evaluation (`eval`, `exec`, `Function()`); safe XML parsing (disable DTD/external entities).
- **Input**: validate at the boundary — type, length, range, format, allowed values (whitelist).
  Reject, don't "fix", invalid input.
- **Output**: encode for the context (HTML, URL, JSON, SQL identifier, file path). Prevent path
  traversal: never build file paths from raw input.
- **Secrets**: never in source, config committed to git, logs, exceptions, or test data. Use the
  project's secret mechanism (environment, vault, protected config). If you find one in code,
  report it.
- **AuthN/AuthZ**: every endpoint/service operation checks authorization on the server side,
  including object-level checks (user may access *this* record). Deny by default.
- **Least privilege**: DB users for applications get `EXECUTE`/specific rights, not `db_owner`.
- **Sensitive data**: identify PII/financial data; mask in logs and non-PROD copies; encrypt
  where the project requires; minimize what you return in APIs.
- **Dependencies**: use only approved/existing packages; no new dependency without stating why,
  its license and maintenance status — new dependency = LARGE task.
- **Errors**: no stack traces, SQL, or internal hostnames in responses to callers.
- **Crypto**: never invent your own; use the platform's vetted libraries and current algorithms.
- **Deserialization**: no unsafe deserializers on untrusted data (`BinaryFormatter`, `pickle`,
  `yaml.load` without SafeLoader, etc.).
