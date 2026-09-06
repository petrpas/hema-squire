# Task: test suite inventory (read-only)

Do not modify or delete any test in this task. Analysis only.

## Context
The suite has grown to ~1000 tests against a brief that capped it at 40. Goal is to separate
tests that carry information from tests that carry none, so a pruning pass can follow.

## Steps

1. Enumerate every test function under `tests/`. Record file, name, parametrize expansion
   count, whether it is a Hypothesis property test, and runtime.
   Collect timings with `pytest --durations=0 -q > /tmp/durations.txt` and parse the file.
   Do not print raw pytest output into context.

2. Classify each test into exactly one bucket:
   - `KEEP/invariant` — asserts a domain rule that can plausibly break: VS format YYNNnnn,
     SPAYD payload construction, HEMA Ratings import mapping, multi-currency handling,
     auto/manual mode transitions.
   - `KEEP/contract` — API request/response schema, DB constraint, or external integration
     boundary (Fio, HEMA Ratings) faked at the edge rather than mocked internally.
   - `KEEP/regression` — pins a specific fixed bug. Must reference that bug in the name or a
     comment; if it does not, classify as UNCLEAR.
   - `KEEP/property` — Hypothesis test over a genuine combinatorial invariant, not a
     restatement of the implementation.
   - `DROP/framework` — asserts what the framework already guarantees: Pydantic type
     validation, required-field errors, SQLAlchemy defaults, route registration, plain
     serialization round-trips.
   - `DROP/trivial` — getters, constructors, enum membership, constants, lone
     `assert x is not None`.
   - `DROP/mock-theatre` — the only assertions are on mock call args or call counts; no
     observable behavior is checked.
   - `MERGE/duplicate` — same behavior already covered elsewhere. Name the sibling test.
   - `UNCLEAR` — intent cannot be determined. List separately. Do not guess.

3. Give a one-line justification for every DROP and MERGE candidate.

4. Flag any test referenced by an OpenSpec spec or change document. These require a spec
   update before removal — keep them out of the plain drop list.

## Deliverable

`docs/test-inventory.md` containing:
- Summary table: bucket × count × total runtime.
- Per-file breakdown.
- Ordered drop list with justifications.
- The 20 slowest tests, each marked as inherent cost or accidental (unnecessary DB round-trip,
  unscoped fixture, oversized Hypothesis budget).
- Proposed final test count and what it covers.