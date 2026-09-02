## 1. Backend: the clear

- [x] 1.1 New module for the clear, modelled on `importclear.py` — the same "delete the data rather than mark it" stance, ordered by dependency in one transaction
- [x] 1.2 Remove the tournament's `BankTransaction` rows whatever their status, and the `PaymentEvent` rows that name them. Children first and explicitly: SQLite has no `ON DELETE CASCADE` here and the relationships do not delete-orphan
- [x] 1.3 Remove the stored statement interpretations — `ImportDecision` of kind `statement_row` — so a re-import reads the file again. The point of the change; without it the clear defeats the next import invisibly
- [x] 1.4 Remove `payment_link` rules and their journal entries: they name transactions that no longer exist. Follow `importclear`'s treatment, including soft-deleted rules
- [x] 1.5 Refuse where any transaction is credited, raising a stated error carrying the count, and remove nothing at all — not the uncredited transactions, not the interpretations
- [x] 1.6 Leave registrations, fencers, imported rows, batches and every payment setting untouched
- [x] 1.7 A count function stating what would be removed and what stands in the way, so the console can state a refusal before the organizer commits

## 2. Backend: the endpoints

- [x] 2.1 `DELETE /payments` on the payments router, guarded by `require_console_access` and `bank.require_payments_enabled` as its neighbours are; 409 with the credited count where refused, mirroring `clear_import`'s shape
- [x] 2.2 `GET` for the count, or carry it on an existing payments read, so the card can state both numbers before acting
- [x] 2.3 Tests: the clear removes transactions, payment events, interpretations and links; refused without console access; refused where payments are disabled

## 3. Backend: the properties that matter

- [x] 3.1 **Re-import after a clear re-reads the file.** Import a statement with a fake parser, clear, import the same bytes again, and assert the parser was called again for every row — the property the change exists for, and the one a clear of transactions alone would fail
- [x] 3.2 **A refusal is total.** With one credited transaction among forty unresolved ones, assert the endpoint refuses *and* that all forty-one transactions, the credited registration's `amount_paid_cents` and state, and every stored interpretation survived. Assert the survival, not the status code
- [x] 3.3 The roster survives: fencers, registrations, variable symbols, totals and states unchanged by a clear
- [x] 3.4 The two clears are independent: clearing payments leaves imported rows and batches; clearing imports leaves transactions (beyond what `issue-imported-registrations` already decided about linked ones)
- [x] 3.5 A Fio-polled transaction clears like an imported one

## 4. Frontend: the card

- [x] 4.1 New card on the Payments phase beside `IntakePanel`, following `QueueCard`/rail conventions
- [x] 4.2 State the count of payments that would be removed
- [x] 4.3 Where credited transactions block it, state that plainly instead of offering a control that fails — as `IntakePanel` does for a missing Fio token
- [x] 4.4 Static confirmation before it runs, stating the count and that it cannot be undone, distinguishable from unlinking a single transaction (design prohibitions: no animated confirmations)
- [x] 4.5 Report what was removed; refresh the sheet and the queues through the console's existing reload signal
- [x] 4.6 `api.ts` and Czech and English strings for the action, its confirmation, its refusal and its report
- [x] 4.7 Tests: the count renders; the refusal renders instead of the button and says why; confirming calls the endpoint and reports; the failure path states itself

## 5. Verification

- [x] 5.1 `pytest` 946 passed, `ruff check .` clean
- [x] 5.2 `vitest` 309 passed, `npm run lint` and `npm run build` clean
- [ ] 5.3 Against the pilot: the count endpoint reads correctly on the live data — `{"payments": 43, "credited": 0}` against 43 transactions and 48 stored readings — but the clear itself was **not** run. Those 43 are the *correctly* read import made after the delimiter fix, so clearing them would destroy good data to prove a button works. Left for the owner, who now has the button the two hand-written SQL clears stood in for

## 6. Notes from implementation

- [x] 6.1 Both load-bearing tests were verified against deliberately broken implementations rather than trusted because they passed. Removing the stored-reading deletion fails `test_re_import_after_a_clear_reads_the_file_again` and `test_the_stored_readings_go_with_them`; clearing the uncredited remainder instead of refusing totally fails the refusal tests. A clear of transactions alone passes everything else in the file
- [x] 6.2 The confirm control read identically to the control that opens it, so the modal's button could not be told apart from the action's. Follows the import clear's house pattern instead — an ellipsis on the opener (`Clear payments…`), a decisive verb on the confirm (`remove permanently`)
