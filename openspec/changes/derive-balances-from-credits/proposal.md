## Why

A registration's balance is a pair of live counters, `amount_paid_cents` and
`amount_paid_eur_cents`, moved by `+=` and `-=` at six places. Nothing records
the individual credits they are the sum of, so the figure cannot be recomputed,
cannot be checked, and cannot say what it is made of. Whether a registration is
paid is a second stored fact — `state = PAID` — assigned at ten more places and
free to disagree with the money: the tolerance, a waiver, and an amendment each
produce a paid registration that owes something, and the three are told apart
only by reading three further fields.

The consequences are already visible in the code. `clear_payments` refuses
outright the moment any transaction holds credit, because unwinding it is
impossible; its docstring calls the alternative "a tournament whose books do not
add up and nothing to say why". `unapply_payment_link` has a branch that deletes
the rule while leaving its credit in the counter, orphaning money whose only
record was that rule. Re-registration zeroes the local counter and leaves the
EUR one standing. Crediting is idempotent only because `BankTransaction.status`
happens to move out of the matcher's candidate set — a mutable flag on the
source row, not a record that the credit was made.

Three separate places have already reached the right conclusion independently
and each stored it somewhere else: `payment_link` rules record their per-VS
split on the rule payload "so removing it later reverts exactly what happened";
`ManualPayment` reverses "this row's own `amount_cents` — never a figure derived
from today's balance, which is the mistake the payment-link rules were built to
avoid"; and `Rule`/`RuleJournalEntry` is an append-only journal with soft delete
and deterministic replay. What is missing is the step where those become one
table.

## What Changes

- **BREAKING** A new `payment_credits` journal is the only place a credit is
  recorded. One row per amount credited to one registration: the amount, the
  currency it arrived in, the day it arrived, what carried it (an ingested
  transaction or a payment recorded by hand), and what decided it (automatic VS
  match, a payment link, a reinstatement, a refund hold). Rows are appended and
  reversed, never edited and never deleted.
- **BREAKING** `Registration.amount_paid_cents` and `amount_paid_eur_cents` are
  removed. What a registration has been credited in a lane is the sum of its
  live credits in that lane, and is computed in SQL as well as in Python, so
  every query that filters or counts on it still can.
- **BREAKING** A new `payment_waivers` journal records the settled-by-hand mark
  the same way: who granted it, when, why, and who revoked it.
  `Registration.settled_by_hand_at` and `settled_by_hand_reason` are removed and
  become readings of the latest live waiver. A waiver credits nothing and so is
  deliberately not a row in the credit journal; it is a different kind of fact.
- **BREAKING** `RegistrationState.PAID` is removed from the stored enum, which
  keeps `reserved`, `expired` and `cancelled` — the lifecycle, which is a
  decision, and stays stored. Whether a registration is settled becomes a
  derivation: a live waiver, or a lane whose outstanding balance is within
  tolerance. The lifecycle wins where the two meet, so a registration credited
  after it expired reads expired, exactly as it does today.
- **BREAKING** `Registration.paid_at` is removed. The day a registration became
  paid is the value date of the credit that first brought it within tolerance,
  found by replaying its live credits in the order they were appended; for a
  waiver it is the day the waiver was granted. The `payments` requirement
  forbidding this reconstruction is withdrawn, its stated reason — that credits
  "are amounts and not a history" — having been what this change removes.
- The wire keeps `paid` as a state an organizer and a fencer read: the API
  composes `reserved | paid | expired | cancelled` from the lifecycle and the
  derivation. No client changes what it reads.
- An organizer may reverse **one** credited bank transaction, releasing its
  credit through the journal. Today only a hand-drawn link and a recorded
  payment can be taken back; an automatically matched transaction cannot, which
  is what leaves `unapply_payment_link` orphaning money.
- Clearing a tournament's payments still refuses while any transaction holds
  credit. The mechanical reason for the refusal is gone; the substantive one —
  that a credited payment was acted on and mail may have gone out — is not.
- Every place that credits or reverses does so by appending to the journal
  through one function. The six `+=`/`-=` sites become one.
- Crediting is idempotent on the credit's own source: a source row that already
  has a live credit against a registration is not credited again, whatever the
  state of the source. Detecting that two *different* source rows are the same
  real payment — the same transfer ingested from the Fio API and from a CSV
  export under two external ids — is **out of scope** and is its own change;
  the journal makes such a pair visible for the first time by listing both
  credits side by side.

## Capabilities

### New Capabilities
- `payment-ledger`: the credit journal and the waiver journal — what a row
  holds, what may append one, what reversal means and what it may not do, how a
  registration's credited amount, outstanding balance, settled state and paid
  date are each derived from them, and the guarantee that appending is
  idempotent on a credit's source.

### Modified Capabilities
- `payments`: the outstanding balance and the settled state become derivations
  rather than stored figures; the paid date is reconstructed from the credit
  that completed the registration, withdrawing the requirement that forbade it;
  the settled-by-hand mark becomes a journal entry rather than two fields; a
  credit's provenance is answered by the credit itself rather than by asking two
  tables which one holds it.
- `payments-clearing`: the refusal to clear while money is credited stands and
  is restated on its substantive grounds, and a new action reverses a single
  credited transaction, which is what an organizer needed the blanket clear for.
- `registration`: a registration's credited amount stops being a figure it
  records and becomes the sum of the credits held against it, so what is owed
  follows a reversal as immediately as it follows a recomputed total.

The reservation lifecycle needs no delta. It states outcomes — a paid
reservation is confirmed, an unpaid one expires — and never says how many states
are stored or which of them holds "paid", so every sentence in it stays true
while the enum loses a value.

`edit-rules` needs no delta: it names the manual payment link only as one of the
actions that create a rule, which stays true. Where the link's credits are
recorded is stated in `payments`, and that is where it changes.

## Impact

- Backend: `app/models.py` (two new tables, four removed columns, one enum value
  removed, the derived properties and their SQL expressions), `app/matching.py`
  (all crediting through the journal; `_settle` stops assigning a state),
  `app/routers/payments.py` (reinstate, refund hold, recorded payments, the new
  single-transaction reversal), `app/routers/registrations.py` (the waiver
  endpoints, re-registration), `app/availability.py` (`live_registration`),
  `app/scheduler.py` (four passes that must ask the derivation, not the enum),
  `app/amendment.py`, `app/sheet.py`, `app/paymentsclear.py`, `app/export_json.py`.
- Data: two new tables; `registrations` loses `amount_paid_cents`,
  `amount_paid_eur_cents`, `paid_at`, `settled_by_hand_at`,
  `settled_by_hand_reason`; `RegistrationState` loses `paid`. **No backfill.**
  The owner has decided the existing data is test data, to be dropped and
  re-imported, so the migration is destructive by design and says so.
- Frontend: nothing forced. Every field the console and the fencer pages read —
  `row.paid`, `row.state`, `row.paid_at`, `row.settled_by_hand` and its reason,
  the outstanding amount and its currency, the credited amounts in the
  expired-holding view — keeps its name, its type and its meaning; only where
  the API gets them from changes. The one addition is the reversal action on a
  credited transaction, which is new UI and is part of this change rather than a
  follow-up.
- Out of scope, each named as its own change: detecting that two source rows are
  the same real payment; a reader for the `payment_events` trail; a console view
  of the waiver journal.
