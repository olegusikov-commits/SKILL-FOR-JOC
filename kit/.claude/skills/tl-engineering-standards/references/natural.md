# Natural (Software AG) standard

Follow the existing library conventions first (object naming, data area usage, error handling
routine). The rules below apply where they don't conflict; if they do, say so.

## Structure
- **Structured mode** only for new/changed code (no reporting mode).
- Separate responsibilities into objects: maps (screen I/O) ↔ programs (flow) ↔ **subprograms**
  (`CALLNAT`, business logic and data access) ↔ external subroutines (`PERFORM`) for shared logic.
- The interface of a subprogram is its **PDA** (parameter data area) — treat it as a contract;
  change it additively and list all callers.
- Avoid **GDA** (global data area) for new logic — it is hidden coupling. Pass data through PDAs.
- LDAs for local layouts; reuse DDM-based views instead of redefining fields.
- Keep objects small and focused; a program with many unrelated blocks should be split.
- Encoding: Hebrew comments/text only where the library's code page supports it.

## Database access (Adabas)
- Know the **descriptors / super-descriptors** of the file (DDM) before writing access logic —
  same principle as "schema first" in SQL.
- `FIND` / `READ LOGICAL BY <descriptor>` with `STARTING FROM` / `ENDING AT` to limit the range;
  avoid `READ PHYSICAL` (full file pass) except for deliberate batch passes.
- No N+1 nested loops (a `FIND` inside every record of an outer `READ`) on large files without a
  reason — consider a super-descriptor, a different access path, or a two-pass approach.
- `FIND NUMBER` / `HISTOGRAM` for counts and value distribution instead of reading records.
- Use `RETAIN`/limits deliberately; always handle the "not found" case (`IF NO RECORDS FOUND`).
- Updates: `GET`/`FIND` with hold → `UPDATE`/`STORE`/`DELETE` → `END TRANSACTION`. Keep
  transactions short; in batch, `END TRANSACTION` every N records (parameter) to release the
  hold queue, with restart logic.
- Natural for DB2: SQL rules from the `tl-sql-engineering` skill apply (host variable types, SQLCODE).

## Control flow and errors
- `DECIDE ON` / `DECIDE FOR` instead of nested `IF`s; `ESCAPE` used deliberately and readably.
- `ON ERROR` block in programs (or the shop's central error routine): record `*ERROR-NR`,
  `*ERROR-LINE`, `*PROGRAM`, key data; `BACKOUT TRANSACTION` when updates are pending.
- No literal business values spread through code — constants in a data area / parameter file.

## Changes to legacy objects
- Smallest change, existing style; list impacted objects (callers via XREF/Predict if available,
  PDAs, maps, DDMs, batch jobs).
- Provide test steps and expected results for TEST.
