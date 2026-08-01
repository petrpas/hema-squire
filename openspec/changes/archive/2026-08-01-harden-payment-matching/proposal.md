## Why

Five gaps in payment matching each end the same way: a transaction the system could have resolved lands in the organizer's manual queue, or worse, quietly does the wrong thing.

**Partial payments are never aggregated.** Matching compares a *single* transaction against the full amount due. Two transfers carrying the same VS — an installment, a correction after an underpayment, a bank that split the transfer, someone covering an amendment surcharge — each fail tolerance independently and both land flagged. The registration never becomes paid even though the account holds the full amount.

**VS parsing is narrower than the spec requires.** `openspec/specs/payments/spec.md` says ingestion parses message fields for a VS; the implementation requires a literal `VS` token (`VS_IN_MESSAGE = r"\bVS[:\s]*(\d{1,10})\b"`) and reads only `column16`, the message. A foreign payer following the instruction *"put 2605003 in the payment message"* writes a bare number and does not match. Fio places SEPA references in other columns depending on the originating bank, and none of those columns is currently read — `bank.py` maps eight columns and the rest are discarded at parse time.

**A single transfer covering several registrations is manual-only.** `apply_payment_links` supports one transaction paying many registrations, but only after the organizer builds the link by hand. A club paying for six members in one transfer is routine in this domain.

**`reminder_day` is not validated against `reservation_validity_days`.** `run_tournament_tick` expires before reminding, correctly. But an organizer who sets `reminder_day >= reservation_validity_days` gets a reservation that is always expired before the reminder fires, and no reminder is ever sent — silently. The defaults (5 and 10) are fine; nothing stops a bad edit.

**A manual link over-credits every registration it covers.** `apply_payment_links` adds the *full* transaction amount to each linked registration's `amount_paid_cents`. One transfer covering two fencers therefore leaves both looking overpaid and both eligible for a refund that is not owed. This is live in the working tree as of the reservation-lifecycle change, which introduced the credit; it must not reach a real tournament.

## What Changes

- Matching evaluates the **sum of all VS-matched transactions** against the amount due rather than one transaction in isolation. A payment below the amount due is credited as a partial payment and leaves the reservation reserved with a recorded balance, instead of being flagged and discarded. The aggregate reaching the amount due within tolerance marks the registration paid.
- A partial payment does **not** change the reservation's expiry. The window is the window; a reservation that expires holding a partial payment is announced as such — a distinct audit event, an organizer-visible marker, and an expiry email that tells the fencer their money is with the organizer rather than implying it is lost.
- The fencer is told the outstanding balance when a partial payment is recorded, rather than being left to work out the difference.
- Ingestion captures the transaction's other text-bearing Fio fields — user identification, comment, specification, and the specific symbol — and matching searches all of them for a VS, not just the message.
- A **bare numeric token** resolving to an issued VS matches automatically **when the transaction also covers that registration's outstanding balance within tolerance**. A bare token whose amount does not check out becomes a pre-filled candidate for the organizer instead of an automatic match, so a coincidental order or invoice number cannot attach itself to a fencer's registration unassisted.
- A transaction whose text carries **several** VS values is treated as a multi-registration payment: when the sum of those registrations' amounts due matches the transaction within tolerance, all are marked paid and the equivalent of a payment link is created automatically. The auto-created link is a removable rule like any manual one, so removing it reverts every registration it touched. Where the sum does not match, the transaction is presented as a pre-filled candidate rather than a bare unmatched row.
- A transaction covering several registrations **distributes** its amount across them, each credited its own amount due, rather than crediting each in full. **BREAKING** relative to the uncommitted reservation-lifecycle work, which credits in full; no released behaviour changes.
- Matching re-evaluates transactions that are still flagged, so two half-payments arriving in separate statements aggregate and both become matched. Transactions the organizer has explicitly resolved — manually linked, marked for refund, or set aside as another tournament's — are never reconsidered.
- Tournament update rejects `reminder_day >= reservation_validity_days` with a clear message.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `payments`: MODIFIED `Amount tolerance` — the comparison is against the aggregate of VS-matched transactions, and a shortfall is credited as a partial payment rather than discarded. ADDED `Partial payments` — the recorded balance, the fencer notification, and what happens when a reservation expires holding money. MODIFIED `Foreign transfers without a VS field` — all text-bearing fields are searched, and bare numeric tokens match automatically under the amount guard. ADDED `Multi-registration payments` — auto-detected multi-VS transfers become removable rules. MODIFIED `Manual matching` — a link covering several registrations distributes its amount. MODIFIED `Automatic matching outcome` — flagged transactions are re-evaluated, organizer-resolved ones are not.
- `tournament-admin`: MODIFIED `Payment and reservation parameters` — the reminder day must precede the reservation window.

## Impact

**Ordering.** This change modifies `Amount tolerance` and `Payment and reservation parameters`, all of which the reservation-lifecycle and add-dual-currency-prices changes also modify. Its delta blocks are written on top of both changes' post-state and assume they archive first. It consumes `Registration.amount_paid_cents` / `outstanding_cents` from the reservation-lifecycle change and `amount_paid_eur_cents` / `outstanding_eur_cents` / the no-conversion currency-lane selection from add-dual-currency-prices — aggregation happens **within** each currency lane, never across them. The bare-number rule is safe only because the structured-VS change makes a VS a 7-digit value with a known prefix. **Land it after all three.**

**Backend.** `bank.py`: additional Fio columns on `IncomingTransaction` (JSON and CSV paths) and matching `BankTransaction` columns. `models.py` and one additive Alembic revision for those columns. `matching.py`: the aggregate comparison, partial crediting, the widened VS scan across fields, the bare-token amount guard, multi-VS detection, the re-evaluation pass, and the distributed credit in `apply_payment_links` / `unapply_payment_link`. `rules.py`: auto-created `payment_link` rules that revert cleanly. `scheduler.py`: the expired-holding-money audit event. `schemas.py`: the reminder-day validation. `emails.py` and cs/en locales: the outstanding-balance notice and the revised expiry notice.

**Frontend.** `MatchPanel.tsx` / `MatchDialog.tsx`: pre-filled candidates, the partial-balance column, and a marker for reservations that expired holding money. i18n cs/en.

**Tests.** No existing test asserts the single-transaction comparison directly, so the suite should stay green; `test_matching.py` gains the aggregate, bare-token, multi-VS, and re-evaluation cases.
