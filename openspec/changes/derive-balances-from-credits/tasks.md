## 1. The two journals

- [x] 1.1 `PaymentCredit` in `app/models.py` — `tournament_id`, `registration_id`, `amount_cents`, `currency`, `value_date`, `source_kind` (`bank_transaction` | `manual_payment`), `source_id`, `origin` (`auto_vs` | `payment_link` | `reinstate` | `refund_hold` | `recorded`), `rule_id`, `created_at`, `reversed_at`, `reversed_by`, `reversed_reason`; docstring stating that the balance is its sum and that nothing edits a row
- [x] 1.2 `PaymentWaiver` in `app/models.py` — `tournament_id`, `registration_id`, `reason`, `granted_by` (label, as `ManualPayment.recorded_by` is), `created_at`, `revoked_at`, `revoked_by`; docstring stating that it carries no amount and why
- [x] 1.3 Partial unique index on `(registration_id, source_kind, source_id)` where `reversed_at is null`, and indexes on `(registration_id, reversed_at)` and `(registration_id, revoked_at)`
- [x] 1.4 Alembic revision: create both tables, drop `amount_paid_cents`, `amount_paid_eur_cents`, `paid_at`, `settled_by_hand_at`, `settled_by_hand_reason`, narrow `RegistrationState` to `reserved | expired | cancelled`; docstring recording the owner decision of 2026-09-09 that the data is test data and that the revision is destructive and not a template

## 2. Appending and reversing

- [x] 2.1 `app/ledger.py` — `credit(session, registration, *, amount_cents, currency, value_date, source_kind, source_id, origin, rule_id=None)` appending one entry, returning it, and returning the existing entry unchanged where a live one already covers that pair
- [x] 2.2 `ledger.reverse(session, credit, *, by, reason)` — sets the three reversal fields, refuses an already-reversed entry
- [x] 2.3 `ledger.reverse_for_rule` and `ledger.reverse_for_source` — every live entry naming a rule, or a source row, reversed together
- [x] 2.4 `ledger.grant_waiver` / `ledger.revoke_waiver`, and `active_waiver(registration)`
- [x] 2.5 Tests: a second `credit` on the same pair writes nothing and moves nothing; a credit for the same source against a *different* registration is written; reversing twice is refused; reversing releases exactly the entry's own amount

## 3. Derivations on `Registration`

- [x] 3.1 `credited_local_cents` / `credited_eur_cents` as `hybrid_property` with correlated-subquery expressions over live credits, the lane decided by comparing the entry's currency to the tournament's
- [x] 3.2 Rebuild `outstanding_cents`, `outstanding_eur_cents`, `outstanding_in`, `remaining_cents`, `balance_cents` on top of them, keeping every rule those already carry (the lane the money came in; the tolerance decides the state, not the figure; a waiver owes nothing)
- [x] 3.3 `waived` as a `hybrid_property` over `PaymentWaiver`; `waiver_reason` reading the latest live entry
- [x] 3.4 `settled` as a `hybrid_property`: `waived ∨ (credited(paid_lane) > 0 ∧ outstanding_in(paid_lane) ≤ tolerance(paid_lane))`; the `credited > 0` term keeps a fully-queued or zero-priced registration out of the paid state, and is `credited` rather than `total` so that an amendment down to nothing leaves a paid registration paid (design D5)
- [x] 3.5 `wire_state`: `cancelled` → `expired` → `paid` if settled → `reserved`, in that precedence
- [x] 3.6 `ledger.paid_at(registration, tournament)` — live credits in `created_at` order until the balance first falls within tolerance, that entry's `value_date` as an instant in the tournament's zone; the waiver's `created_at` where a waiver alone settles it. A function and not a model property: `setup.start_of_local_day` is what turns a day into an instant and `app.setup` imports `app.models` (design D7)
- [x] 3.7 Tests: each derivation in Python and in a `WHERE` clause agree on the same fixtures; an expired registration credited in full reads expired; a waived registration reads paid with zero credits; `paid_at` takes the completing credit's day and does not move when a later credit lands
- [x] 3.8 Tests for the zero-total cases specifically, since they are what a naive derivation gets wrong: a fully-queued registration reads reserved and is absent from every paid count; a registration on a tournament pricing at zero reads reserved; a paid registration amended down to a zero total still reads paid with its balance stating the overpayment

## 4. Crediting routes moved onto the journal

- [x] 4.1 `matching._credit` becomes a call to `ledger.credit` with `origin="auto_vs"`; `_settle` stops assigning `RegistrationState.PAID` and decides only the mail, the refund state and the event
- [x] 4.2 `matching.apply_payment_links` credits through the ledger with `origin="payment_link"` and the rule's id; the `credited` payload is no longer written
- [x] 4.3 `matching.unapply_payment_link` becomes `ledger.reverse_for_rule` — unconditional, dropping the `state != PAID` and `auto_matched` branches that leave credits orphaned
- [x] 4.4 `routers/payments.record_manual_payment` and `remove_manual_payment` credit and reverse through the ledger with `origin="recorded"`
- [x] 4.5 `routers/payments.reinstate_transaction` and `mark_transaction_for_refund` credit through the ledger with `origin="reinstate"` / `"refund_hold"`; reinstate returns the registration to `RESERVED` rather than assigning paid
- [x] 4.6 `matching.resettle_within_tolerance` credits nothing and assigns nothing — it re-reads the derivation and sends the mail; confirm this is now the whole of it
- [x] 4.7 `routers/registrations.register` stops zeroing a counter on a fresh cycle: the previous cycle's credits are reversed with a stated reason, both lanes alike, closing the EUR asymmetry
- [x] 4.8 Tests: crediting once per route writes one entry with the right origin; withdrawing a link reverses its entries whatever became of the registration; a fresh registration cycle leaves no credit counting in either lane

## 5. The waiver endpoints

- [x] 5.1 `routers/registrations.mark_settled` writes a waiver entry instead of two fields; unmark revokes the latest live entry
- [x] 5.2 Keep the refusals as specified: a reason required where `feature_payments` is on; not offered on a registration the money settled; unmark refused where no live waiver exists
- [x] 5.3 Keep both `PaymentEvent` writes (`settled_by_hand`, `unsettled_by_hand`) exactly as they are — the event trail is out of scope
- [x] 5.4 Tests: waive, revoke, waive again leaves three readable entries with their own reasons; the balance reads waived throughout the live ones and reads owed between them

## 6. Lifecycle readers

- [x] 6.1 `availability.live_registration()` — `settled | (RESERVED & window open)`
- [x] 6.2 `scheduler` reminder, expiry, demotion and settlement passes ask `settled` rather than the enum; verify each still runs as one query
- [x] 6.3 `nameresolve`, `routers/tournaments` (two sites, plus the participant-list query), `amendment`, `sheet.base_rows`
- [x] 6.4 `sheet.base_rows` emits `state` as the composed wire state and `paid` as the derivation, so the console reads exactly what it reads today
- [x] 6.5 Tests, one per pass: a settled registration is not reminded, does not expire, is not demoted, and is not moved by seating settlement

## 7. Transaction reversal and clearing

- [x] 7.1 `POST /payments/transactions/{id}/reverse` — reverses every live credit that transaction carried, returns it to the unmatched queue, refuses a transaction holding no live credit
- [x] 7.2 A preflight the console can call, stating which registrations stop reading as paid
- [x] 7.3 `paymentsclear._credited` counts transactions holding a live credit rather than reading `matched_registration_id`
- [x] 7.4 Console: the reversal action on a credited transaction, stating its consequence before it is confirmed
- [x] 7.5 Tests: reversing an auto-matched transaction unsettles its registration and clears the way for a clear; a reversed credit does not hold the clear; a transaction covering three registrations reverses all three

## 8. Export and the rest of the surface

- [x] 8.1 `export_json` exports both journals and stops exporting the dropped columns; round-trip test
- [x] 8.2 `routers/payments.expired_holding` reads the derived credited sums
- [x] 8.3 Grep for every remaining reference to the five dropped columns and to `RegistrationState.PAID`; basedpyright reports the misses, and the count should reach zero

## 9. Gates

- [x] 9.1 `uv run ruff check .` and `uv run basedpyright` clean from `backend/`
- [x] 9.2 `uv run pytest -q` green; confirm no test asserted against a stored counter in a way that hid a derivation bug
- [x] 9.3 `npm run typecheck` and `npm run check` clean from `frontend/` — expected to pass untouched, and worth confirming rather than assuming
