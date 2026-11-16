## 1. Regression tests first

- [x] 1.1 Recreate the five P3 probes from `openspec/payments_gaps.md` as tests in `backend/tests/` (disable EUR, tighten tolerance, remove-and-re-record a payment, reverse a credit, revoke a waiver), each running the real tick after the window and asserting the registration is not expired. They fail on `main`. Payment-link removal has no test of its own: it reverses through the same `ledger.reverse` the credit-reversal test covers.
- [x] 1.2 Test that the tick clears the window of a reserved settled registration and leaves an expired registration's window untouched.

## 2. Window closed on settlement

- [x] 2.1 In `scheduler.process_expiries`, bulk-clear `expires_at` on the tournament's `RESERVED`, settled registrations before selecting overdue ones (design D1).

## 3. One reopening rule

- [x] 3.1 Add `setup.reopen_window(tournament, registration, was_settled)`: fresh `payment_window` and `reminded_at = None` where the reading was lost, clocks run and the registration is not fully queued (design D2).
- [x] 3.2 Move the amendment's inline reopening onto it.
- [x] 3.3 Wire credit reversal, payment-link removal, recorded-payment removal and waiver revocation through `ledger.reverse` and `ledger.revoke_waiver` (design D3).

## 4. Tournament settings

- [x] 4.1 In `update_tournament`, refuse `409 eur_credits_present: <n>`, before the commit, when the update would leave EUR credit without a lane (design D5); test both scenarios.
- [x] 4.2 Snapshot settled reserved ids around updates touching tolerance, EUR, local currency or the payments feature, and reopen the window of each that dropped (design D4).
- [x] 4.3 Frontend: map `eur_credits_present` to a Czech and English sentence with the count on the Setup save.

## 5. Cleanup and checks

- [x] 5.1 Rewrite the `resettle_within_tolerance` docstring (design D6).
- [x] 5.2 `pytest tests -k "money or payment or amend or waiver or tolerance" -q`, `ruff check`, `basedpyright`, and from `frontend/` `npm run typecheck` and `npm run check`.
