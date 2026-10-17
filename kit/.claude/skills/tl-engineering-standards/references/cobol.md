# COBOL (z/OS) standard

Legacy code is the norm here: **follow the shop's existing conventions first** (paragraph
naming, PERFORM style, copybook layout, abend routine). The rules below apply where they don't
conflict with the shop standard; if they do, say so.

## Encoding and comments
- Source is EBCDIC on the mainframe. Hebrew comments only if the member already contains Hebrew
  and the code page supports it (CCSID 424 / 12712); otherwise English. Never change column
  layout (sequence area 1–6, indicator 7, Area A 8–11, Area B 12–72) or encoding.
- Keep line length within column 72 unless the compiler options allow otherwise.

## Program structure
- Clear top-down structure with numbered paragraphs, e.g.
  `0000-MAIN`, `1000-INITIALIZE`, `2000-PROCESS-RECORD`, `3000-FINALIZE`, `9000-ERROR`,
  `9999-ABEND` (or the shop's scheme).
- `0000-MAIN` reads like a table of contents: PERFORM init, PERFORM process UNTIL end, PERFORM
  finalize, GOBACK.
- One paragraph = one purpose; keep paragraphs short. Separate: input handling, business rules,
  DB2/file access, output formatting. Large shared logic goes into a **called subprogram** with a
  LINKAGE SECTION copybook as its contract.
- No `GO TO` except the shop's allowed pattern (e.g. to the paragraph EXIT); never `ALTER`.
- Use scope terminators (`END-IF`, `END-EVALUATE`, `END-PERFORM`, `END-READ`, `END-EXEC`
  where applicable); `EVALUATE` instead of deep nested `IF`.

## Data
- Level-88 condition names for status/flag values (`88 ORDER-CANCELLED VALUE 'C'.`) — no
  literal comparisons scattered in the logic.
- Numeric business data: `COMP-3` (packed decimal) with correct sign and precision; binary
  `COMP`/`COMP-5` for counters/indices; `ROUNDED` and `ON SIZE ERROR` for business arithmetic.
- Record layouts, interfaces and DB2 host structures from **copybooks / DCLGEN** — never
  re-declared by hand in the program.
- Initialize working storage deliberately (`INITIALIZE`, VALUE clauses); no reliance on
  leftover values between calls/transactions.
- No hard-coded business values (rates, dates, codes): parameter table, control file, or a
  constants copybook.

## I/O and error handling
- Check **FILE STATUS after every file operation**; check **SQLCODE after every SQL** statement
  (see `tl-sql-engineering` → `db2-zos.md`); CICS: use `RESP`/`RESP2` on every command, not `HANDLE CONDITION`.
- One error/abend paragraph that records program, paragraph, key data, SQLCODE/file status,
  and sets `RETURN-CODE` / abends according to the shop standard.
- Batch: meaningful return codes (0/4/8/12/16 per shop convention), counters of records read /
  written / rejected printed at the end, checkpoint/restart for long jobs, commit frequency
  from a parameter.

## CICS online
- Pseudo-conversational design; no long-running work in a transaction; COMMAREA/channel
  layout in a copybook and versioned.
- Short units of work; no holding locks across user interaction.

## Changes to legacy programs
- Change the smallest area possible; keep the existing style of the program.
- List impacted copybooks, called/calling programs, JCL, and DB2 packages (BIND/REBIND).
- Provide test data and expected results (before/after) for the user to run on TEST.
