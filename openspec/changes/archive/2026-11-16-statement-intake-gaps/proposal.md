## Why

Three smaller findings of the payments audit (`openspec/payments_gaps.md`, P5–P7) each mis-read a real payment: a statement row with no currency column is read as CZK even on a EUR tournament, so every such payment is refused as an unaccepted currency; two identical payments from a bank that numbers nothing collapse into one, and the second is counted as a duplicate indistinguishable from a re-import; and a bare variable symbol's amount is judged against a tolerance computed from what is still owed rather than from the total, so a top-up is held to a narrower window than the same top-up quoting its symbol in the field.

## What Changes

- A row of an interpreted statement that states no currency is read in the tournament's local currency. The interpreter reports a missing currency as missing instead of defaulting it to CZK.
- A row with no bank identifier is identified by its content **and the number of identical rows before it in the same statement**. Two identical payments are both ingested; the same statement uploaded again still collides row for row. The first occurrence keeps the identifier it has today, so nothing already imported is read differently.
- The bare-token amount check uses the tolerance every other path uses, computed from the registration's total in that currency.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `payments-intake`: a row with no currency is in the tournament's local currency; identical id-less rows in one statement are distinct transactions.
- `payments`: the bare-token check's tolerance is the total's.

## Impact

- `backend/app/bank.py` (`ParsedStatementRow.currency`, the interpreter prompt, `to_transaction`), `backend/app/statements.py` (occurrence ordinal), `backend/app/matching.py` (bare-token tolerance).
- Readings already cached per row keep the currency they were given; only rows interpreted from now on are read with the local default.
- `tests/test_statement_import.py` asserts the old collapse and changes with it.
