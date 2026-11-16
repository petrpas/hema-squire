## 1. Missing currency

- [x] 1.1 `ParsedStatementRow.currency` optional, prompt rule 8, `to_transaction` takes the local currency (design D1); test a EUR tournament's statement with no currency.

## 2. Identical rows

- [x] 2.1 Occurrence ordinal in `statements.parse` → `to_transaction` (design D2); update `test_a_statement_that_repeats_a_row_exactly`, test the re-upload.

## 3. Bare-token tolerance

- [x] 3.1 `_tolerance_cents` in the bare-token check (design D3); test the 470 Kč top-up.

## 4. Checks

- [x] 4.1 Scoped pytest, `ruff check`, `basedpyright`.
