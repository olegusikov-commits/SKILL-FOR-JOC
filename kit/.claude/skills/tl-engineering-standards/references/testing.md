# Testing standard

## What to test
- **Domain/business rules**: unit tests, many, fast, no I/O. Cover boundaries, invalid
  input, and each business branch.
- **Use cases / services**: tests with fake or in-memory adapters for infrastructure.
- **Data access / SQL**: integration tests against a real TEST database or container where
  the project supports it; at minimum, a documented manual verification query.
- **API / web service contracts**: tests that the request/response shape and status codes are
  stable.
- **Bug fix**: first a test that reproduces the bug (fails), then the fix (passes).

## How
- Follow the project's existing test framework and folder layout (xUnit/NUnit/MSTest,
  GoogleTest/Catch2, pytest, Jest/Vitest/node:test, COBOL unit test tooling if any).
- Name tests by behavior: `CancelOrder_WhenAlreadyShipped_ReturnsNotCancellable`.
- Arrange–Act–Assert, one behavior per test, no logic (loops/ifs) in tests.
- Test behavior through public interfaces, not private methods or implementation details.
- Deterministic: inject clock, random, and IDs; no dependence on test order, current date,
  or shared mutable state.
- Mocks only at architectural boundaries (DB, HTTP, MQ, clock). Over-mocking = brittle tests.
- Test data builders/factories instead of copy-pasted setup.

## Legacy code without tests
- Before changing it, add **characterization tests** that pin the current behavior around the
  area you touch, then change.
- If that is impossible (e.g. mainframe online program), write a manual test script: inputs,
  expected outputs, DB state before/after — and add it to the change description.

## Reporting
State in the final report: which tests were added, which were run, results, and what could not
be run here (e.g. no DB access, mainframe compile) with the exact command/steps for the user.
