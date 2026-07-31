## Why

Three states a registration can enter today have no way out. An unpaid reservation that expires leaves the row in `EXPIRED`, and the registration guard exempts only `CANCELLED` — so the fencer gets `409 already_registered` forever, locked out of a tournament with open seats by a hold that was meant to be released cheaply. A fencer who wants to add an afterparty ticket after registering has no amendment endpoint, so the only path is cancel-and-re-register, which resets `paid_at` and issues a new VS: an already-paid fencer loses the association with their money and the QR code in their inbox points at a dead VS. And a payment landing on an already-expired reservation is flagged with no organizer action available — manual matching only links to `RESERVED` registrations — so the transaction sits flagged, the money sits in the account, and the fencer believes they paid.

The second of these also undermines the reservation model itself: if the selection cannot change after payment, the rational move is to delay payment until certain — exactly the behaviour the short window exists to prevent. All three will occur at the first real tournament; a payment sent on the last day of the window and credited the next morning is routine.

## What Changes

- An expired reservation becomes re-registerable on the same terms as a cancelled one: the existing row is reused in place, a fresh window opens, a fresh VS is issued, and capacity is re-checked at that moment — if the discipline filled meanwhile the fencer enters the substitute queue. Re-registration stays uncapped.
- A new fencer-facing amendment endpoint on the fencer's own registration recomputes the total from current pricing and branches on state: a `RESERVED` amendment replaces the selection while **keeping the VS and the existing `expires_at`** (amending must not renew the hold); a `PAID` amendment that raises the total records a surcharge against the same VS and stays `PAID`; a `PAID` amendment that lowers it records an overpayment into the existing refund tracking. Adding a discipline that is full adds it as a substitute entry rather than rejecting the whole amendment.
- Registration gains `amount_paid_cents` — the payment total in the tournament's primary currency — making the outstanding balance a derived quantity (`total_amount * 100 - amount_paid_cents`) rather than a second running total. This is the single representation of "what is still owed on this VS" that the later payment-matching change will consume for aggregation.
- A new `Tournament.amendments_close` date freezes the roster for amendments independently of registration close, defaulting to the registration-closes behaviour when unset.
- A VS-matched payment arriving within a new `Tournament.expiry_grace_hours` (default 48) of expiry reinstates the reservation and marks it paid **when the discipline still has a free seat**, audited as its own payment event. Outside grace, or when the seat is gone, the transaction stays flagged and the organizer gains two explicit console actions on it: reinstate, and mark for refund. Payments landing on a `CANCELLED` registration always go to the refund path and never reinstate.
- The fencer is notified in both directions — reinstated, or "payment received but the reservation had expired, the organizer will be in touch" — rather than being left with only the earlier expiry email.

## Capabilities

### New Capabilities

None. All behaviour extends existing capabilities.

### Modified Capabilities

- `registration`: MODIFIED `Reservation lifecycle` — an expired reservation is re-registerable, with capacity re-checked at re-registration. ADDED `Registration amendment` — the state branching above, the VS/expiry stability guarantee on a reserved amendment, and the amendment window.
- `payments`: ADDED `Payments arriving after expiry` — grace reinstatement subject to capacity, the organizer's reinstate and mark-for-refund actions outside grace, fencer notification in both directions, and cancelled-registration handling. MODIFIED `Amount tolerance` — the amount due is expressed against the recorded payment total so a surcharge or an overpayment is representable, without changing the tolerance rule itself.
- `tournament-admin`: MODIFIED `Payment and reservation parameters` — adds the expiry grace period to the configurable set. MODIFIED `Registration window` — adds the optional amendments-close date.

## Impact

**Backend.** `models.py`: `Tournament.expiry_grace_hours`, `Tournament.amendments_close`, `Registration.amount_paid_cents`, new `PaymentEvent` kinds (`reinstated_in_grace`, `amended`, `marked_for_refund`). One Alembic revision, additive, defaulting `expiry_grace_hours` to 48 and `amount_paid_cents` to `total_amount * 100` for existing `PAID` rows so historical balances read as settled. `routers/registrations.py`: the re-registration guard at the `already_registered` check, and the new amendment endpoint. `matching.py`: the grace branch before the `registration.state != RESERVED` flag, the capacity check on reinstatement, and writing `amount_paid_cents` on a match. `routers/payments.py`: the two console actions on a flagged transaction. `schemas.py`, `emails.py` and the cs/en locales: amendment confirmation, reinstatement notice, expired-but-paid notice.

**Frontend.** `FencerHome.tsx` / `TournamentDetail.tsx`: the amendment entry point and the outstanding-balance display; `MatchPanel.tsx`: the reinstate and mark-for-refund actions on a flagged transaction; i18n cs/en.

**Tests.** `test_registration_gating.py` and `test_registrations.py` assert the current blanket 409 and will need updating. New coverage for each amendment branch, VS and `expires_at` stability across a reserved amendment, the grace boundary in both directions, and the cancelled-registration refund path.

**Sequencing.** This change ships before the structured-VS, multi-currency-residual, and payment-matching-hardening changes; the `amount_paid_cents` representation fixed here is the contract the matching change builds aggregation on.
