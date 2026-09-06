## Context

`Registration.paid_at` is a nullable `DateTime(timezone=True)` written at five
places and read at four. Every write is the clock:

| where | when it fires | what it writes today |
| --- | --- | --- |
| `matching.py:299` (`_settle`) | a credit covers the balance | `datetime.now(UTC)` |
| `matching.py:955` (`resettle_within_tolerance`) | the organizer widened the tolerance | `datetime.now(UTC)` |
| `routers/payments.py:684` | the organizer reinstates a late payment | `datetime.now(UTC)` |
| `routers/registrations.py:846` | the organizer marks a registration settled by hand | `_now()` |
| `matching.py:771`, `:861`, `registrations.py:523` | a credit is withdrawn | `None` |

`_settle` is the funnel: both a bank transaction and a payment recorded by hand
reach it, the second passing `transaction=None` and naming itself in `origin`
(design `add-manual-payment-entry` D3). So the money paths are two writes, not
four.

The reads are the console's `paid_at` column (`Console.tsx:131`, `:506`), the
canonical JSON export (`export_json.py:86`), the Sheets mirror
(`sheet.py:298`), and the registration DTO (`schemas.py:904`). Nothing
*schedules* off it — reminders and expiry read `expires_at`, dormancy reads the
tournament — so its value is a record, and changing that value cannot move a
deadline or send a mail.

The day the money arrived is already stored on both sources: `BankTransaction.date`,
parsed from the statement at ingestion, and `ManualPayment.received_on`, which the
organizer types and whose model comment already draws exactly the distinction this
change is making — *"the date the organizer says the money arrived, which is not
the date they typed it in"*.

`paid_at` appears in no spec in `openspec/specs/`.

## Goals / Non-Goals

**Goals:**

- `paid_at` states the day the money arrived, on every path where a day is known.
- One rule reaching both money paths, not a rule per path.
- Historical rows recomputed where the answer is recoverable, and left alone
  where it is not.
- The console reads the value in the tournament's zone, as its neighbouring
  columns already do.

**Non-Goals:**

- Recording, in a new field, when Squire learned of a payment. `payment_events`
  already carries that per transaction with its own timestamp.
- Changing the type of the column, the shape of the export, or the API contract.
- Reconstructing a ledger of which credit came from where. The credit counters
  are two integers (`amount_paid_cents`, `amount_paid_eur_cents`), deliberately
  (`payments`, *A registration has one outstanding balance*), and this change
  does not turn them into a history.

## Decisions

### D1 — The field keeps its type; a day becomes the instant that starts it locally

A statement gives a day. `paid_at` is a timestamp. Rather than migrate the
column to `Date` — which would rewrite the model, the schema, the DTO, the
export field list, the Sheets mirror and every test that reads an ISO datetime,
and would throw away the real clock time the hand mark legitimately knows — the
day is stored as the instant it begins in `Tournament.timezone`.

That zone is not a new idea here. It is what `registration_opens_time` is read
in, what `local_date` measures whole-day boundaries with, and what the fencer
table's registration moment and the seating queue's entries are shown in. A day
from a Czech bank belongs to the Czech day, not to whatever day it was in UTC.

`setup.opening_instant` already computes exactly this value when it is given no
time of day. Rather than call a function named for the registration opening from
the payments path, extract its two lines as `setup.start_of_local_day(day,
timezone)` and have `opening_instant` delegate to it for the unset-time case —
so the two stay one implementation, and `fold=0` on the autumn repeat and the
zone fallback are decided once.

*Alternative rejected:* store midnight UTC. It makes the stored instant
meaningless in every zone including the tournament's, and puts a payment made on
the 1st into the 31st for any organizer reading it from the Americas.

### D2 — `_settle` is told the value date; it does not derive one

`_settle` already receives `transaction: BankTransaction | None`, so it *could*
read `transaction.date` and fall back to the clock when the transaction is None.
It should not: the None branch is the recorded-payment path, which knows a
better day than the clock — `payment.received_on` — and a fallback that quietly
loses it is the bug this change exists to remove.

So `_settle` takes a keyword-only `value_date: date`, and each caller supplies
the day its own source states: `transaction.date` from the matching pass and the
payment-link path, `payment.received_on` from `credit_manual_payment`. A
required argument, not a defaulted one, so a future third route into `_settle`
cannot silently inherit the clock.

### D3 — The completing source's day, and what that costs out of order

A registration settled by two half-payments takes the day of the one that
completed it — the transaction in hand at `_settle`.

Where statements are imported in order, that is the day the last of the money
arrived, which is the honest answer. Where they are imported out of order — a
January statement uploaded after a February one — the completing transaction can
be the *earlier* day, and `paid_at` will name a day on which the registration
was not in fact yet covered.

Accepted, rather than fixed, because fixing it means knowing every credit's day
at settle time, and the credit counters do not keep one: they are two integers.
Reconstructing the maximum would mean querying `bank_transactions` and
`manual_payments` back for the registration on every settle, and would still miss
credits made through a payment link that names several registrations, where the
transaction carries no `matched_registration_id`. A rare mis-dating by a few days
on an out-of-order import is a smaller wrong than a per-settle reconstruction
that is itself incomplete.

*Alternative considered:* the day of the first credit. Rejected — it dates a
registration as paid while it was still owing.

### D4 — Widening the tolerance takes the transaction's day

`resettle_within_tolerance` settles registrations on money that is already in
the account: the organizer changed what "close enough" means, and a transaction
that was `partial` becomes `matched`. `_settles_now` hands back the registration
for a transaction that is right there in the loop, so its date is available and
it is the day the money arrived. The organizer's decision is recorded where
decisions are recorded — the `tolerance_widened` reason and the payment event.

### D5 — A hand mark keeps the clock, and says why

Marking a registration settled by hand records no payment. There is no statement
day and no `received_on`; the only day anyone knows is the day of the mark, and
`registrations.py:846` already stamps exactly that. It is unchanged, and its
docstring — which currently argues that `paid_at` answers *when this became
paid* — is amended to say that this is now the exception and to name the reason,
so that the next reader does not take it for the general rule.

Organizer reinstatement (`payments.py:684`) is the opposite case: a transaction
is in hand, and it takes that transaction's date like any other credit. It sets
`paid_at` inline rather than through `_settle`, so it converts the day itself.

### D6 — The migration reconstructs from the latest matched transaction

One data migration over `registrations` where `paid_at IS NOT NULL`, joined to
`bank_transactions` on `matched_registration_id`, taking `MAX(date)` per
registration and writing the start of that day in the tournament's zone.

The latest rather than the earliest, because a registration settled by two
statements was covered when the second arrived. This is the same rule D3 lands
on for in-order imports, and it is the best reconstruction available: at
migration time the whole history *is* visible, which is precisely what the live
path lacks.

Rows with no matched transaction keep their value: hand marks (correctly — D5),
and registrations settled by a recorded payment. The second could in principle be
recovered from `manual_payments`, but a registration may hold both a transaction
and a recorded payment, and deciding which wins is a rule with no reader asking
for it; those rows are few and an organizer who cares can read the recorded
payment's own `received_on`, which is displayed. Left alone, they keep a value
that is wrong by a day or two rather than gaining one that is wrong by a rule.

Irreversible in the sense that the overwritten import instants are not recoverable
from `registrations` — but they are recoverable in substance from
`payment_events.created_at`, which timestamps the `payment_matched` event for
every one of these rows. The down migration is therefore a no-op with a comment
saying so, rather than a lie about restoring what it cannot.

### D7 — The console cell is read in the tournament's zone

`Console.tsx:506` renders both `expires_at` and `paid_at` with
`new Date(value).toLocaleDateString("cs")` — the reader's browser zone. With a
clock value near mid-day this was invisible; with midnight stored it is a
guaranteed off-by-one-day for any reader west of the tournament.

The cell takes the `timezone` the component already receives and already passes
to `registeredMoment` for the neighbouring column. `expires_at` is a genuine
instant and is fixed alongside it for the same reason — an expiry at 23:00 local
already reads as the next day in Berlin today.

## Risks / Trade-offs

- **A date that moves backwards for a row an organizer has already read.** →
  Unavoidable, and the point of the change; the value it moves *from* is the
  import instant, which no organizer chose to record. The payment events keep
  the old instant for anyone reconciling against a previous export.
- **Out-of-order statement import names a day the registration was not yet
  covered (D3).** → Bounded by the gap between the two statements; the
  transaction list shows both days, and the payments console links the
  transactions to the registration.
- **An exported document's `paid_at` changes meaning without changing shape.** →
  Any downstream consumer parsing an ISO datetime keeps parsing. What changes is
  which day it names, and the export carries the transaction rows beside it.
- **A tournament whose stored zone identifier has since been dropped from the
  zone database.** → `_zone` already falls back to the default rather than
  failing, and the migration uses the same helper, so a broken identifier costs
  at most an hour, not a row.

## Migration Plan

1. `setup.start_of_local_day` extracted, `opening_instant` delegating to it —
   no behaviour change, covered by the existing opening-time tests.
2. The five write sites, then the console cell.
3. The data migration, which depends on nothing above it and can be applied
   before or after the deploy; the two together make the column consistent, and
   either alone leaves it consistent for a subset of rows.

Rollback: reverting the code returns new settlements to the import instant.
Rows the migration rewrote stay rewritten; see D6 on why that is acceptable.

## Open Questions

None. The three that this change opened — the storage of a bare day, the day a
tolerance-widened settlement takes, and what to do with history — were decided
by the owner before it was written (D1, D4, D6).
