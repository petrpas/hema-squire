One field, five writers, one migration and one cell. The order below is the
order of dependency: the helper, then the writers that use it, then the history,
then the surface that reads it.

## 1. The day-to-instant helper

- [x] 1.1 `setup.start_of_local_day(day, timezone) -> datetime` — the two lines already inside `opening_instant`, lifted out with its `fold=0` reasoning and its zone fallback (design D1)
- [x] 1.2 `opening_instant` delegates to it for the unset-time case, so the two do not drift. No behaviour change; the existing opening-time tests are the check
- [x] 1.3 A test that a day in a zone ahead of UTC becomes that zone's midnight and not UTC's, and one over a midnight the zone skips — no zone repeats midnight in 2026, so the skipped one is the edge that exists

## 2. The money paths

- [x] 2.1 `_settle` takes a keyword-only `value_date: date` and writes `start_of_local_day(value_date, tournament.timezone)` in place of `datetime.now(UTC)`. Required, not defaulted (design D2)
- [x] 2.2 Every caller of `_settle` supplies its own source's day: `transaction.date` from the matching pass and from `apply_payment_links`, `payment.received_on` from `credit_manual_payment`
- [x] 2.3 `resettle_within_tolerance` writes the day of the transaction `_settles_now` accepted, which the loop already holds (design D4)
- [x] 2.4 `routers/payments.py` reinstatement writes the day of the transaction it reinstates against. It settles inline rather than through `_settle`, so it converts the day itself
- [x] 2.5 `routers/registrations.py` hand mark is unchanged. Amend its docstring, which currently argues the general rule this change reverses, to name itself as the exception and say why (design D5)
- [x] 2.6 The model comment on `Registration.paid_at` states what the field now means and that one path is exempt — the field is read by four consumers and the meaning should not live only in a change document

## 3. Backend tests

- [x] 3.1 `test_matching.py`: a transaction dated before the import settles a registration on the transaction's day; two half-payments take the second's day
- [x] 3.2 `test_manual_payments.py`: a recorded payment's `received_on` is the paid date, not the moment it was typed
- [x] 3.3 `test_tolerance_resettle.py`: widening the tolerance dates the settlement to the transaction, not to the widening
- [x] 3.4 `test_payment_e2e.py`: reinstatement takes the transaction's day
- [x] 3.5 `test_manual_settlement.py`: the hand mark still stamps the moment of the mark, and unmarking still clears it
- [x] 3.6 A test on a tournament in a zone other than the default, asserting the stored instant is that zone's midnight — the assertion that fails if a later change reaches for `datetime.combine` directly
- [x] 3.7 Swept: no test asserted `paid_at` against a clock. The seven that name the field assert presence or absence, or set it as a fixture for a registration that is simply paid — none was a claim this change reverses

## 4. The history

- [x] 4.1 An Alembic data migration: for each registration with a non-null `paid_at` and at least one bank transaction matched to it, write the start of `MAX(bank_transactions.date)` in that tournament's zone (design D6)
- [x] 4.2 Rows with no matched transaction are left untouched, with the reason in the migration's docstring — hand marks correctly, recorded payments deliberately
- [x] 4.3 The down migration is a no-op with a comment saying the overwritten instants live on in `payment_events.created_at`, rather than a downgrade that claims to restore them
- [x] 4.4 A migration test over a fixture holding all four shapes: one transaction, two transactions, a recorded payment only, a hand mark only

## 5. The console cell

- [x] 5.1 `Console.tsx` renders `paid_at` and `expires_at` in the tournament's `timezone` — the value the component already holds and already passes to `registeredMoment` (design D7)
- [x] 5.2 The paid cell states a day alone; the expiry keeps the form it has
- [x] 5.3 `consoleCells.test.tsx`: the existing `paid_at` case asserts a day rendered in the tournament's zone rather than the browser's, plus a case for a reader west of the tournament and one for an expiry late in the local evening
