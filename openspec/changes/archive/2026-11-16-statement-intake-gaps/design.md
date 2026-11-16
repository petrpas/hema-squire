## Context

`bank.ParsedStatementRow.currency` defaults to `"CZK"`, the interpreter prompt says "default to CZK", and `to_transaction` falls back to `"CZK"` again. `to_transaction` derives `external_id` as `row:<fingerprint>` where the bank gave none; ingestion dedupes on it. `matching._evaluate_single_vs` computes the bare-token tolerance from `due_cents`.

## Decisions

### D1. Missing currency is `None` until it reaches the tournament

`ParsedStatementRow.currency: str | None = None`; prompt rule 8 says to return null where the row states no currency. `to_transaction(row, raw, local_currency, occurrence)` substitutes the tournament's local currency. Readings already stored keep their explicit `"CZK"` — reinterpreting cached rows would spend model calls to change what a past import already ingested.

### D2. Occurrence ordinal, first occurrence unchanged

`statements.parse` counts fingerprints while it walks the rows and passes the count: occurrence 1 keeps `row:<fp>`, occurrence n ≥ 2 gets `row:<fp>:<n>`. Keeping the first unchanged means every transaction already ingested keeps colliding with its re-import. The interpretation cache stays keyed by the fingerprint alone — identical rows have one reading.

Risk accepted: of two overlapping statements, one holding only the second of two identical payments would ingest it again. Requires two identical id-less payments, split across statement boundaries.

### D3. Bare-token tolerance from the total

Replace `due_cents * percent / 100` with `_tolerance_cents(registration, tournament, which)`. The multi-symbol sum check keeps its tolerance on the summed dues: there is no single total to take it from, and it was not part of the finding.
