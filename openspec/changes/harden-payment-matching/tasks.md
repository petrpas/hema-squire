## 1. Prerequisites

- [ ] 1.1 Confirm `fix-reservation-lifecycle` is merged — `Registration.amount_paid_cents` and `outstanding_cents` are consumed throughout this change
- [ ] 1.2 Confirm `add-structured-vs` is merged — bare-token matching is safe only against 7-digit structured symbols
- [ ] 1.3 Confirm `add-dual-currency-prices` is merged — `amount_paid_eur_cents`, `outstanding_eur_cents`, and the currency-lane selection in `matching.py` (no conversion, `currency_not_accepted`) are the base this change's per-currency aggregation is layered on
- [ ] 1.4 Confirm all three are archived before this change's spec deltas are, since `Amount tolerance` and `Payment and reservation parameters` are layered on their post-state

## 2. Widened transaction capture

- [ ] 2.1 Add `user_identification`, `comment`, `specification`, and `specific_symbol` to `IncomingTransaction` in `backend/app/bank.py`
- [ ] 2.2 Map them in `_FIO_COLUMNS` (`column7`, `column25`, `column18`, `column6`) for the JSON path
- [ ] 2.3 Map them in `_CSV_FIELDS` (Uživatelská identifikace, Komentář, Upřesnění, SS) for the statement-import path
- [ ] 2.4 Add matching nullable columns to `BankTransaction` in `backend/app/models.py` and one additive Alembic revision; historical rows stay NULL and no transaction changes status because of the migration
- [ ] 2.5 Add a `searchable_text` helper on `BankTransaction` returning the text-bearing fields, deliberately excluding `payer_name` and `payer_account`
- [ ] 2.6 Verify the column mapping against a real Fio statement from the tournament's own account before first live use, and extend the mapping if a bank places its reference elsewhere

## 3. Aggregate crediting

- [ ] 3.1 In `backend/app/matching.py`, restructure the comparison: credit the counter for the transaction's own currency lane (`amount_paid_cents` or `amount_paid_eur_cents`) for any VS-matched transaction in a currency the tournament accepts, then decide state from that same lane's outstanding (`outstanding_cents` or `outstanding_eur_cents`)
- [ ] 3.2 Mark the registration `PAID` when the remaining balance in that currency is within tolerance of zero
- [ ] 3.3 Leave the registration `RESERVED` with the credit recorded when it still owes more than tolerance in that currency, and record the transaction with a new `partial` status rather than flagging it
- [ ] 3.4 Route a credit beyond tolerance in the other direction to overpayment handling and `refund_state` for that currency, as the reservation-lifecycle change specifies
- [ ] 3.5 Leave the not-accepted-currency path (`currency_not_accepted`) unchanged and crediting nothing
- [ ] 3.6 Confirm the two currency lanes are never summed: a registration part-paid in each is flagged for the organizer rather than read as settled
- [ ] 3.7 Exclude `partial` transactions from the unmatched and flagged queues in `backend/app/routers/payments.py` — there is nothing for the organizer to do about them
- [ ] 3.8 Send the payment-received email only on the transition to `PAID`, never on a partial credit

## 4. Re-evaluation of flagged transactions

- [ ] 4.1 Extend the matching pass to re-examine transactions still in `flagged` alongside newly pending ones
- [ ] 4.2 Exclude terminal, organizer-decided states from re-evaluation: `matched`, manually linked, marked for refund, and set aside as another tournament's
- [ ] 4.3 Add a last-evaluated timestamp to `BankTransaction` and surface it, so a transaction leaving the queue between passes is explicable
- [ ] 4.4 Confirm re-evaluation is idempotent: a transaction already credited is not credited twice on a later pass

## 5. Widened VS parsing

- [ ] 5.1 Rewrite `effective_vs` to scan `searchable_text` rather than the message alone, keeping `transaction.vs` as the first source
- [ ] 5.2 Keep the labelled-VS pattern, widened to all searchable fields, matching on the number as today
- [ ] 5.3 Add bare-token detection for 7-digit numbers resolving to an issued VS
- [ ] 5.4 Gate a bare-token match on the transaction also covering that registration's outstanding within tolerance; otherwise attach it as a candidate and neither match nor credit
- [ ] 5.5 Ensure `payer_name` and `payer_account` are never scanned for bare tokens
- [ ] 5.6 Expose detected candidates on the transaction so the manual dialog can pre-fill them

## 6. Multi-registration payments

- [ ] 6.1 Detect several distinct issued VS in one transaction's searchable text
- [ ] 6.2 Sum those registrations' outstanding balances **in the transaction's own currency lane** and compare against the transaction amount within tolerance — no conversion
- [ ] 6.3 On a match, create a `payment_link` rule carrying those VS through the existing rules engine rather than paying the registrations directly
- [ ] 6.4 Mark the rule as automatically created so the console can distinguish it from a manual link
- [ ] 6.5 On a mismatch, leave the transaction unmatched with the detected VS attached as candidates — no subset search
- [ ] 6.6 Confirm `unapply_payment_link` reverts an auto-created link exactly as it reverts a manual one, with no second revert path

## 7. Distributed credit in payment links

- [ ] 7.1 Fix `apply_payment_links` to credit each registration its own outstanding balance **in the transaction's own currency lane**, in VS order, capped by what remains of the transaction, instead of crediting the full amount to each
- [ ] 7.2 Record the amount credited per VS on the rule at apply time, so a revert undoes what happened rather than what would happen against today's balances
- [ ] 7.3 Update `unapply_payment_link` to subtract the recorded per-VS amounts
- [ ] 7.4 Pin the arithmetic with a test before changing anything else in this group

## 8. Partial payments and expiry

- [ ] 8.1 In `backend/app/scheduler.py`, detect a reservation expiring with `amount_paid_cents > 0` and record a distinct `expired_holding_payment` audit event
- [ ] 8.2 Mark such registrations for organizer attention and list them separately from ordinary expiries in the console
- [ ] 8.3 Add `send_partial_payment_received` to `backend/app/emails.py`, stating the outstanding amount with its currency
- [ ] 8.4 Branch the expiry notice: when a partial payment is held, state that the organizer holds it and will be in contact, without implying loss or promising a seat
- [ ] 8.5 Add all new strings to the cs and en locales, with no hardcoded currency units
- [ ] 8.6 Confirm the reservation-lifecycle grace path settles a reinstated registration correctly once the earlier partial credit is counted

## 9. Reminder day validation

- [ ] 9.1 Validate `reminder_day < reservation_validity_days` on tournament update in `backend/app/schemas.py`, rejecting with a message naming both values
- [ ] 9.2 Ensure the validation fires when either field changes, including a shortened validity against an existing reminder day
- [ ] 9.3 Do not migrate existing tournaments; the validation applies on the next edit

## 10. Frontend

- [ ] 10.1 Pre-fill detected variable symbols in `MatchDialog.tsx` when opening a candidate transaction
- [ ] 10.2 Show the credited amount and outstanding balance on reserved registrations in `MatchPanel.tsx`
- [ ] 10.3 Present reservations that expired holding a payment as their own list, distinct from ordinary expiries
- [ ] 10.4 Mark automatically created payment links as such in the rules view
- [ ] 10.5 Add cs and en i18n strings for all of the above

## 11. Tests

- [ ] 11.1 Two half-payments with one VS in a single import aggregate to paid
- [ ] 11.2 Two half-payments arriving in separate imports aggregate to paid, exercising re-evaluation
- [ ] 11.2a Two half-payments in different currencies (one CZK, one EUR) on the same VS are credited to their own lanes and never summed; the registration stays reserved unless one lane alone reaches its own total within tolerance
- [ ] 11.3 A partial payment leaves the reservation reserved with the correct balance and notifies the fencer
- [ ] 11.4 A partial payment does not extend the validity window, and expiry with a credit recorded writes `expired_holding_payment` and sends the branched notice
- [ ] 11.5 The remaining balance arriving inside the grace period reinstates and settles the registration
- [ ] 11.6 A labelled VS in a non-message field matches; a labelled VS in the message still matches as before
- [ ] 11.7 A bare numeric VS with a covering amount matches automatically; the same token with an unrelated amount becomes a candidate and credits nothing
- [ ] 11.8 A digit sequence in `payer_name` or `payer_account` matching an issued VS is not treated as a variable symbol
- [ ] 11.9 One transfer listing three VS with a matching sum pays all three and creates a removable auto-created rule; removing it reverts all three
- [ ] 11.10 A multi-VS transfer whose sum does not match stays unmatched with candidates pre-filled, and no subset is settled
- [ ] 11.11 A manual link of 3500 across two registrations owing 1750 each credits 1750 to each, marks both paid, and records neither as overpaid
- [ ] 11.12 Removing a distributed link removes exactly the recorded per-VS amounts
- [ ] 11.13 An organizer-resolved transaction is untouched by a later matching pass
- [ ] 11.14 A re-evaluated transaction already credited is not credited twice
- [ ] 11.15 `reminder_day >= reservation_validity_days` is rejected in both directions of edit
- [ ] 11.16 The existing matching and registration suites stay green

## 12. Verification

- [ ] 12.1 Run the full backend test suite
- [ ] 12.2 Run `openspec validate harden-payment-matching --strict`
- [ ] 12.3 Dry-run the migration on a copy of `backend/hema_squire.sqlite` and confirm no transaction changes status as a result of it
- [ ] 12.4 Run one matching pass against the copy and review which previously flagged transactions resolve, confirming each is a genuine aggregation rather than a false positive
