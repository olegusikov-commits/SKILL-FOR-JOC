# Integration between mainframe (z/OS) and distributed systems

Typical landscape: COBOL/Natural programs (batch + CICS online) on DB2 z/OS / Adabas, next to
.NET / Python / Node services on SQL Server. Most real-world bugs live at this boundary.

## Integration options
| Option | When | Key concerns |
|---|---|---|
| Direct DB2 access from distributed code (DRDA/ODBC/JDBC) | Read access to mainframe data, simple cases | Bypasses business rules in COBOL; locking impact on online/batch; dynamic SQL cost (CPU/MIPS); use parameter markers |
| Calling DB2 stored procedures (native or COBOL external) | Reuse mainframe business logic with a clear contract | Procedure is the contract; result-set and error conventions; WLM environment |
| CICS web services / z/OS Connect REST APIs | Exposing online transactions as services | Contract versioning, COMMAREA/channel ↔ JSON mapping, timeouts, CICS region capacity |
| MQ | Async integration, decoupling availability, batch ↔ online | Message format (copybook-based or JSON), EBCDIC/ASCII conversion, idempotency, ordering |
| File transfer (batch) | Large volumes, nightly windows | Record layout copybook, control totals, restart, duplicate/partial files |
| Replication / CDC to SQL Server | Reporting/analytics on mainframe data without load on z/OS | Latency, data ownership (read-only copy!), schema drift |

Rule: **one system owns each piece of data**. A replicated copy is read-only. Never write the
same business entity from both sides without an explicit synchronization design (ADR).

## Data conversion pitfalls (always address in the design)
- **Encoding**: EBCDIC (Hebrew code page CCSID 424 / 12712) ↔ Unicode (UTF-8/UTF-16). Hebrew
  text direction (visual vs logical order) in legacy data — verify with real samples.
- **Packed decimal (COMP-3) / zoned decimal** ↔ `decimal` — precision and sign handling;
  never convert through `float`/`double`.
- **Dates**: legacy formats (`YYYYMMDD` numeric, Julian `YYDDD`, `0`/`99999999` as "no date")
  → explicit mapping rules.
- **Fixed-length fields**: trailing spaces, low-values (`X'00'`), high-values — define trimming
  and null semantics.
- **Codes and flags**: map 1-char codes to enums with a documented table; unknown codes handled.

## Performance & capacity
- Mainframe CPU is billed — chatty fine-grained calls from distributed code to DB2/CICS are
  expensive. Prefer coarse-grained operations and batching.
- Respect batch windows and online peak hours; heavy reads on DB2 z/OS PROD during the online
  day may hurt CICS users (locks, CPU).
- Distributed SQL against DB2 z/OS: parameter markers (statement cache), `FETCH FIRST n ROWS`,
  `WITH UR` only for approximate reporting, short units of work, explicit commit.

## Change coordination
Changes on the mainframe side involve: copybooks, DCLGEN, programs to recompile, BIND/REBIND of
packages, JCL, CICS definitions, DBA DDL. The design must list these and the deployment order
relative to the distributed side (expand → migrate → contract).
