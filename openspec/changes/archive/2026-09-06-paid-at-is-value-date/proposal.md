## Why

Every settled registration carries a paid date the console shows in the column
headed *Zaplaceno*, and on every one of them that date is the day somebody
pressed import. `paid_at` is written as `datetime.now(UTC)` at all five places a
registration becomes paid (`matching.py:299`, `matching.py:955`,
`routers/payments.py:684`, `routers/registrations.py:846`, and the recorded-payment
path that runs through the first of them) — while the day the money actually
arrived is sitting in the row beside it, parsed and stored, as
`BankTransaction.date` or `ManualPayment.received_on`.

So the column answers a question nobody asked. An organizer reading it wants to
know when a fencer paid — to answer *the money left my account on Tuesday, why
does the roster say Friday*, to see who paid before the window closed, to
reconcile a fortnight of statements imported in one sitting and now all bearing
one date. What it tells them instead is when Squire last ran, which is a fact
they already have and never needed a column for.

Nothing was decided here. `paid_at` appears in no spec; it is a field that got a
clock because a clock was the nearest thing to hand.

## What Changes

- **The paid date is the day the money arrived.** Where a bank transaction
  settles a registration, `paid_at` SHALL be that transaction's statement date;
  where a payment the organizer recorded settles it, the `received_on` they
  entered. **BREAKING** for readers of the field's old meaning — the console
  column, the canonical JSON export and the Sheets mirror all change what they
  state for the same registration.
- **The day is stored as its own start in the tournament's zone.** A statement
  gives a day, not a clock. The field stays a timestamp and takes midnight in
  `Tournament.timezone`, the zone every other date on that tournament's timeline
  is already read in (`setup.zone_for`). No column changes type, no export
  changes shape, and the one path that genuinely knows a clock time — the
  organizer's hand mark — keeps it.
- **A settlement that no money arrived for keeps the clock.** Marking a
  registration settled by hand is not a payment and has no statement day behind
  it. It goes on stamping the moment of the mark, which is the moment the thing
  it records happened.
- **Widening the tolerance credits the day of the transaction it accepted.** A
  registration that settles because the organizer widened the tolerance settles
  on money that arrived earlier; the decision is the organizer's, the date is
  the money's.
- **Historical rows are recomputed where the answer exists.** A migration
  rewrites `paid_at` from the latest bank transaction matched to that
  registration. Rows with no matched transaction — hand marks, and payments
  predating the link — are left exactly as they are rather than being given an
  invented day.
- **The column is read in the tournament's zone.** `Console.tsx` renders
  `paid_at` through `new Date(...).toLocaleDateString("cs")`, which is the
  reader's zone: with midnight stored, an organizer west of the tournament would
  read the previous day. It joins the registration moment and the seating queue
  in being read where the tournament is. The `expires_at` cell shares that one
  expression and the same fault — an expiry at 23:00 local already reads as the
  next day for a reader further east — so it is fixed in the same line rather
  than left as the one cell in the table that is not read where the tournament
  is.

Not in scope: a second field recording when Squire learned of the payment. The
payment events already carry that, timestamped, per transaction; a column
duplicating them would be answering the question this change is removing.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `payments`: what a registration's paid date means, and which of the paths that
  settle a registration take a statement day rather than a clock
- `etl-console`: the paid-date column in the Payments phase table is read in the
  tournament's own zone, as the registration moment beside it already is

## Impact

- `backend/app/matching.py` — the settle in `_credit` and the tolerance-widened
  settle; both need the date in hand passed down rather than read off the clock
- `backend/app/routers/payments.py` — organizer reinstatement of a late payment
- `backend/app/routers/registrations.py` — the hand mark, which is unchanged and
  documented as deliberately unchanged
- `backend/app/setup.py` — a helper turning a tournament-local day into the
  instant that starts it, beside `local_date`
- `backend/alembic/versions/` — one data migration over `registrations` joined to
  `bank_transactions`
- `frontend/src/Console.tsx` — the `paid_at` cell
- Readers of the field's value: `export_json.py`, `sheet.py`, and any downstream
  consumer of an exported document
