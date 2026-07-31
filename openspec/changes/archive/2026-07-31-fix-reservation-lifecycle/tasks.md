## 1. Data model and migration

- [x] 1.1 Add `Tournament.expiry_grace_hours: int` (default 48) and `Tournament.amendments_close: date | None` to `backend/app/models.py`, with comments explaining that grace is capacity-gated and that an unset amendments_close means "same window as registration"
- [x] 1.2 Add `Registration.amount_paid_cents: int` (default 0) to `backend/app/models.py`, documenting that it holds the primary-currency figure at the rate applied when each payment was matched
- [x] 1.3 Add a `Registration.outstanding_cents` derived property returning `total_amount * 100 - amount_paid_cents`, and use it everywhere the balance is needed — never store the difference
- [x] 1.4 Add the new `PaymentEvent` kinds used by later tasks: `reinstated_in_grace`, `reinstated_by_organizer`, `marked_for_refund`, `registration_amended`
- [x] 1.5 Write one additive Alembic revision creating the three columns with their defaults, plus a data step setting `amount_paid_cents = total_amount * 100` where `state = 'paid'`
- [x] 1.6 Run the migration against a copy of `backend/hema_squire.sqlite` and confirm no row acquires a balance it did not have (paid rows read as settled, all others zero)

## 2. Re-registration after expiry

- [x] 2.1 In `backend/app/routers/registrations.py`, extend the `already_registered` guard so `EXPIRED` is exempt alongside `CANCELLED`
- [x] 2.2 Extend the existing row-reuse branch to reset the expired row's lifecycle fields as it does for a cancelled one, and reset `amount_paid_cents` to 0 so a new cycle starts from a clean balance
- [x] 2.3 Confirm capacity is re-evaluated on the re-registration path so a filled discipline places the returning fencer in the substitute queue rather than seating them
- [x] 2.4 Confirm a fresh VS is issued on re-registration (current `next_vs` behaviour) and note in a comment why the previous cycle's VS is not reused

## 3. Amendment window configuration

- [x] 3.1 Expose `amendments_close` and `expiry_grace_hours` in the tournament update and read schemas in `backend/app/schemas.py`
- [x] 3.2 Validate on tournament update that `amendments_close` does not fall after `registration_closes` when both are set, rejecting with a distinct localized reason
- [x] 3.3 Validate that `expiry_grace_hours` is non-negative, accepting 0 as "no automatic reinstatement"
- [x] 3.4 Add an `amendment_availability` helper alongside `setup.registration_availability` that returns the closed reason when past `amendments_close`, falling back to registration availability when it is unset

## 4. Registration amendment endpoint

- [x] 4.1 Add `POST /my-registration/amend` in `backend/app/routers/registrations.py` accepting the same selection payload as `register`, reusing `_resolve_selection` and `_validate_options`
- [x] 4.2 Gate the endpoint on `amendment_availability`, and reject `EXPIRED` and `CANCELLED` registrations with a reason directing the fencer to register again
- [x] 4.3 Implement the `RESERVED` branch: replace discipline and extra selections, recompute `total_amount`, and leave `vs` and `expires_at` untouched — assign neither on this path
- [x] 4.4 Implement the `PAID` branch: recompute `total_amount`, keep the state `PAID`, and set `refund_state = PENDING` when the recomputed total falls below `amount_paid_cents`
- [x] 4.5 Add a full discipline as a substitute entry (`is_substitute=True`) instead of rejecting the amendment, mirroring the `register` capacity handling
- [x] 4.6 Record a `registration_amended` payment event carrying the old and new totals
- [x] 4.7 Extend `registration_out` and `RegistrationOut` with the outstanding amount so the fencer's own views can present it

## 5. Grace reinstatement in matching

- [x] 5.1 In `backend/app/matching.py`, insert a grace branch before the existing non-`RESERVED` flag: an `EXPIRED` registration within `expires_at + expiry_grace_hours` whose seated disciplines all still have free places is reinstated to `RESERVED` and falls through to the normal tolerance comparison
- [x] 5.2 Record the reinstatement as a `reinstated_in_grace` payment event, distinct from `payment_matched`
- [x] 5.3 Flag with distinct reasons when the payment does not qualify: `expired_outside_grace` and `expired_seat_taken`, so the console can explain which applies
- [x] 5.4 Flag a payment landing on a `CANCELLED` registration for refund and never reinstate it, whatever the timing
- [x] 5.5 Credit `amount_paid_cents` with the converted amount at the point the match is recorded, using the existing `paid_cents_in_primary` conversion
- [x] 5.6 Compare against `outstanding_cents` rather than `total_amount * 100` so an amended registration is owed the difference
- [x] 5.7 Subtract the credited amount symmetrically in `unapply_payment_link`, and credit it in `apply_payment_links`

## 6. Organizer actions on a flagged transaction

- [x] 6.1 Add a reinstate action in `backend/app/routers/payments.py` that applies the same effect as the automatic grace branch, refusing where capacity is gone, and audits as `reinstated_by_organizer`
- [x] 6.2 Add a mark-for-refund action that records the amount against the fencer, sets `refund_state = PENDING`, and audits as `marked_for_refund`
- [x] 6.3 Ensure both actions leave the transaction resolved rather than flagged, so it no longer appears in the flagged queue
- [x] 6.4 Restrict both actions to console access, consistent with the other organizer endpoints

## 7. Emails and localization

- [x] 7.1 Add `send_amendment_confirmation` to `backend/app/emails.py`, carrying the updated summary, the new amount, and the QR against the unchanged VS
- [x] 7.2 Add `send_surcharge_due` carrying payment instructions for the outstanding difference against the same VS
- [x] 7.3 Add `send_reservation_reinstated` for a payment accepted within grace
- [x] 7.4 Add `send_payment_after_expiry` stating that the payment arrived, that the reservation had expired, and that the organizer will be in contact — without promising a seat
- [x] 7.5 Add all four to the cs and en locales, following the existing message conventions

## 8. Frontend

- [x] 8.1 Add the amendment entry point to the fencer's registration view (`FencerHome.tsx` / `TournamentDetail.tsx`), reusing the registration checklist form, hidden once the amendment window has closed
- [x] 8.2 Present the outstanding amount with its currency alongside the total when it is non-zero
- [x] 8.3 Add the reinstate and mark-for-refund actions to the flagged-transaction rows — `MatchPanel.tsx` is the unrelated HR-matching panel (`phase === "matching"`); the payments phase had no transaction UI at all, so this added a new `PaymentsPanel.tsx` wired to `phase === "payments"` instead, showing reinstate only where the backend reports capacity allows
- [x] 8.4 Add the amendments-close date and expiry grace period to the Setup panel
- [x] 8.5 Add the cs and en i18n strings for all of the above, with no hardcoded currency units

## 9. Tests

- [x] 9.1 Update `backend/tests/test_registration_gating.py` and `test_registrations.py` where they assert the blanket 409, turning the expired case into positive re-registration coverage — neither file actually asserted this for an expired (as opposed to still-reserved) registration; nothing to update, fresh coverage added in `test_reservation_lifecycle.py` instead
- [x] 9.2 Re-registration after expiry: seat free becomes reserved with a fresh VS and window; seat taken becomes a substitute placement
- [x] 9.3 Reserved amendment: VS and `expires_at` are byte-identical before and after, total is recomputed, confirmation reissued
- [x] 9.4 Paid amendment upward stays paid with the correct outstanding; paid amendment downward sets `refund_state = PENDING` with a negative outstanding
- [x] 9.5 Amendment adding a full discipline is accepted as a substitute entry; amendment after `amendments_close` is rejected; amendment on expired or cancelled is rejected
- [x] 9.6 Payment inside grace with a free seat reinstates and pays, and records `reinstated_in_grace`
- [x] 9.7 Payment inside grace with the seat taken stays flagged and displaces no substitute; payment outside grace stays flagged with its own reason
- [x] 9.8 Payment on a cancelled registration never reinstates and routes to refund
- [x] 9.9 Organizer reinstate and mark-for-refund each resolve the transaction and write their audit events
- [x] 9.10 `amount_paid_cents` is credited on match and reverted by `unapply_payment_link`; a foreign-currency credit is unchanged by a later exchange-rate edit
- [x] 9.11 `amendments_close` after `registration_closes` is rejected; `expiry_grace_hours = 0` disables automatic reinstatement

## 10. Verification

- [x] 10.1 Run the full backend test suite and confirm no pre-existing test regressed beyond the ones updated in 9.1 — 293 passed, 0 failed
- [x] 10.2 Run `openspec validate fix-reservation-lifecycle --strict` and confirm the deltas match the implemented behaviour — valid
- [x] 10.3 Walk the three defect paths in the running app: register, let expire, register again; register, pay, amend upward; pay after expiry inside and outside grace — all three confirmed against a live uvicorn instance
