## Context

Money reaches a registration by four routes, and all four end at the same two
lines of code:

```python
def _credit(registration, which, amount_cents):
    if which == "local": registration.amount_paid_cents += amount_cents
    else:                registration.amount_paid_eur_cents += amount_cents
```

The routes are an automatic VS match (`matching._evaluate_single_vs`), a
`payment_link` rule applied over one or more registrations
(`matching.apply_payment_links`), a payment the organizer recorded
(`routers/payments.record_manual_payment`), and two organizer decisions on a
flagged transaction — reinstate and mark-for-refund — which credit inline in
`routers/payments`. Three sites subtract: withdrawing a link, removing a
recorded payment, and re-registration, which sets the local counter to zero and
leaves the EUR one alone.

Nothing between the source row and the counter is recorded. What survives is
scattered and shaped three different ways:

| route | what remembers the amount | reversible |
|---|---|---|
| auto VS match | `bank_transactions.amount_cents` + `matched_registration_id` | no |
| payment link | `rules.payload["credited"]`, a `{vs: cents}` map | yes |
| recorded payment | `manual_payments.amount_cents`, soft-deleted | yes |
| reinstate / refund hold | the transaction's amount, by inference | no |
| waiver | nothing; it credits nothing | n/a |

Idempotence is nowhere in that table. Re-running the matcher does not
double-credit because `match_new_transactions` selects only transactions whose
`status` is `NULL` or `flagged`, and crediting moves the status out of that set.
The guard is a mutable workflow flag on the source row, and there is no way to
ask whether a credit was already made.

Two further facts shape the design. `Registration.total_amount` is a stored
figure but a genuinely recomputable one — `pricing.registration_total` prices
the registration's own selection at `_priced_on(registration)`, so it is a cache
of a pure function and not a mystery sum; it stays. And `Rule` /
`RuleJournalEntry` is already an append-only journal with soft delete and
deterministic replay, so the pattern this change needs is one the project
already runs.

The owner has decided (2026-09-09) that existing data is test data: it will be
dropped and re-imported. There is no backfill to design.

## Goals / Non-Goals

**Goals:**

- One record per credit, naming what carried it, and one function that appends
  it. A registration's credited amount is the sum of its live credits and is
  stored nowhere.
- Whether a registration is settled follows deterministically from money and
  waivers. It is not assignable.
- Crediting the same source twice is impossible, guarded by the credit's own
  identity rather than by a flag on the source.
- Reversal returns exactly what was credited, and leaves the reversal readable.
- The derivations work in SQL, so seat counting, the scheduler's passes and the
  console's queries stay single queries.
- A missed call site is a type error, not a silent behaviour change.

**Non-Goals:**

- Deciding that two different source rows are the same real payment. The same
  transfer ingested twice under two external ids yields two credits, and this
  change makes that visible rather than resolving it. Its own change.
- Reading the `payment_events` trail. It keeps being written exactly as now and
  keeps having no reader beyond the expired-holding queue. Its own change.
- A console view of the waiver journal. The journal is built here; who reads it
  is a separate question with its own placement decisions.
- Changing what any client reads. The wire keeps `paid` as a state.
- Recomputing `total_amount`. It is a cache of a pure function and stays.

## Decisions

### D1 — Two journals, not one table with a `kind`

`payment_credits` holds money. `payment_waivers` holds the organizer's
statement that no money was ever meant to pass. They are not two flavours of one
thing: a credit has an amount, a currency and a value date and sums into a
balance; a waiver has none of those and forgives whatever stood at the moment it
was given. Putting them in one table means a `kind` column that half the columns
are null for, and a balance query that must remember to exclude one kind — the
exact shape of mistake `amount_paid_cents` already makes when a reader forgets
that a waiver credits nothing.

The two are read together in exactly one place, the settled derivation (D5),
which is one expression in one module.

*Alternative considered:* a single `payment_facts` table with a `kind`
discriminator. Rejected for the above; also it would put a waiver into every
list of payments the console shows, where it does not belong.

### D2 — A credit names its source, and that is what makes appending idempotent

```
payment_credits
  id
  tournament_id, registration_id
  amount_cents, currency          -- as it arrived
  value_date                      -- the day it arrived
  source_kind                     -- bank_transaction | manual_payment
  source_id                       -- the row in that table
  origin                          -- auto_vs | payment_link | reinstate
                                  --  | refund_hold | recorded
  rule_id                         -- the payment_link rule, where one decided it
  created_at
  reversed_at, reversed_by, reversed_reason
```

`(registration_id, source_kind, source_id)` is unique among live rows, enforced
by a partial unique index. That is the whole of the idempotence guarantee: a
transaction cannot be credited to a registration twice, whatever
`transaction.status` says, whatever order the matcher runs in, and however many
times a payment link is re-applied. A second attempt is refused by the database
rather than discovered later by a reconciliation report.

It is scoped per registration rather than per source row because one
transaction legitimately credits several registrations — that is what a payment
link is — and each of those is one credit.

`origin` is not the same question as `source_kind`. The source says what carried
the money; the origin says what decided to credit it. A transaction credited by
an automatic match and the same transaction credited by an organizer's link are
the same source with different origins, and the console tells them apart today
by reading `status_reason`, which the journal now records at the credit itself.

*Alternative considered:* leaving idempotence to `transaction.status`, as today,
and making the journal purely descriptive. Rejected: the whole complaint is that
the balance rests on a flag rather than on a record. A descriptive journal that
can silently disagree with the counters is the worst of both.

### D3 — `transaction.status` and `matched_registration_id` stay, demoted

`status` remains what it honestly is — the matcher's queue state
(`unmatched`, `flagged`, `likely`, `partial`, `matched`, `resolved`,
`other_tournament`), which drives the console's queues and is genuinely a
workflow fact. It stops being consulted as "has this been credited". That
question is `select 1 from payment_credits where source... and reversed_at is
null`, and every caller asks it that way.

`matched_registration_id` likewise stays as the matcher's outcome —
which registration this transaction resolved to — and stops being the credited
test in `paymentsclear._credited` and in `unapply_payment_link`'s `auto_matched`
branch, both of which become journal queries.

### D4 — Reversal is a field on the row, not a compensating row

A reversed credit sets `reversed_at`, `reversed_by`, `reversed_reason`, and the
balance sums rows where `reversed_at is null`. It does not append a negative
credit.

The project already makes this choice twice, in `Rule.deleted_at` and
`ManualPayment.removed_at`, and both docstrings say why: the record must survive,
and the reversal must be recognisable *as* a reversal rather than as another
entry. A negative row would appear in every list of a registration's payments as
a payment, which it is not, and would require every reader to remember the sign.

Reversal is once and irreversible. Re-crediting after a reversal is a new credit
with a new id, which is what `ManualPayment` already means by "a correction is a
removal and a new record; there is no edit".

*Alternative considered:* strict append-only with signed compensating rows,
which is what double-entry bookkeeping would do. Rejected on the two grounds
above and on consistency: a third soft-delete idiom in the same codebase costs
more than the purity buys.

### D5 — Settled is derived; the lifecycle stays stored and wins

`RegistrationState` keeps `reserved`, `expired`, `cancelled`. `paid` leaves it.

The three that remain are decisions somebody or something made — a fencer
registered, a window closed, a fencer withdrew — and a decision belongs in
storage. `paid` was never a decision; it was a reading of the money that
happened to be written down, which is why three different code paths could each
produce a paid registration that owes something.

```
credited(lane)   = Σ live credits in that lane
outstanding(lane) = total(lane)*100 − credited(lane)
paid_lane        = eur where the EUR lane holds credit and the local one does
                   not, else local          (the rule `remaining_cents` uses today)
waived           = a live waiver exists
settled          = waived
                 ∨ (credited(paid_lane) > 0
                    ∧ outstanding(paid_lane) ≤ tolerance(paid_lane))
```

**The `credited > 0` term is load-bearing and is not a rounding guard.** Without
it, every registration that was never asked for anything reads as settled,
because its outstanding is zero and so is its tolerance. Two such registrations
exist in quantity: a fully-queued one — `pricing._registration_selection`
excludes substitute entries and waitlisted teams, so a registration entirely
below the line is priced at zero — and any registration on a tournament that
charges nothing. Today both sit at `reserved`; without the term both would start
reading `paid`, and a fencer waiting in a queue would appear on the roster as
having paid.

"Owes nothing" and "has paid" are different statements, and the derivation must
not collapse them. A registration priced at zero is settled by nothing, waived
by nobody, and reads reserved, exactly as it does now.

The term is `credited > 0` rather than `total > 0` because of the case where an
amendment removes everything a paid fencer had bought: the total drops to zero,
the credit stands, and the registration must keep reading paid while its balance
reads as the overpayment it now is. That is what happens today, and
`credited > 0` preserves it where `total > 0` would break it.

Where the lifecycle and the derivation meet, the lifecycle wins:

```
wire_state = cancelled  if state is CANCELLED
           | expired    if state is EXPIRED
           | paid       if settled
           | reserved
```

This is not a new rule. `mark_transaction_for_refund` credits an expired
registration today and leaves it expired, and the expired-holding queue exists
precisely to list registrations that are expired while holding money. Stating
the precedence makes that behaviour a rule instead of a consequence.

**Removing `PAID` from the enum is the safety mechanism, not a tidiness.** There
are 25 references to `RegistrationState.PAID` across nine backend modules, four
of them in `scheduler.py` and `availability.py` where getting it wrong expires
or unseats people who have paid. If `PAID` remained in the enum and merely
stopped being assigned, every one of those sites would keep type-checking and
quietly start matching nothing. Removing the value turns each into an
`AttributeError` that basedpyright reports before the code runs.

### D6 — The credit stores the currency; the lane is derived

A credit records the currency the money arrived in. Which lane it counts toward
follows by comparing that currency to the tournament's, exactly as
`matching.match_currency` decides it today. Storing the lane instead would bake
a tournament-level fact into every row, and a lane is not a property of a
payment.

The two lanes are still never summed. Nothing here relaxes that.

### D7 — `paid_at` is the value date of the credit that completed the balance

Live credits in `created_at` order — the order they were appended, which is the
order Squire learned of them — are accumulated until `outstanding(paid_lane)`
first falls within tolerance. That credit's `value_date` is the paid date. Where
the registration is settled by a waiver alone, it is the waiver's `created_at`.

It is a function in `app/ledger.py` taking the registration and its tournament,
not a property on the model. The derivation needs the tournament twice — for
the tolerance, and to turn the credit's bare day into the instant that day
begins where the tournament is held — and `app/setup.py`, which owns that one
conversion, imports `app.models`, so a model property could not reach it
without a cycle. A zero-argument property would in any case hide two
dependencies it cannot honestly do without. Its two readers, `sheet.base_rows`
and the registration detail, both sit above `ledger` in the import graph.

The `payments` spec forbids exactly this reconstruction today, on the stated
ground that credits "are amounts and not a history". They now are a history, so
the prohibition is withdrawn rather than worked around. Everything else that
requirement says survives: the date is the day the money arrived and not the day
Squire learned of it, a registration settled by several credits takes the day of
the one that completed it, and a tolerance widening takes the accepted
transaction's day — which now falls out of the derivation instead of needing a
rule of its own.

### D8 — A `payment_link` rule stops carrying `credited`

`rules.payload["credited"]` was a private journal inside a rule payload. Its job
is now done by credit rows carrying that rule's id. Withdrawing the rule reverses
exactly the live credits that name it — which is the same guarantee, expressed
where every other credit already lives, and correct in the cases the payload
version got wrong.

Specifically, `unapply_payment_link` today skips reversal when
`registration.state != PAID`, leaving the credit in the counter while deleting
the only record of it. With credits as rows there is nothing to decide: the
rule's live credits are reversed, and whether the registration is settled
afterwards is a derivation that re-answers itself.

`_apply_opaque` stays the replay handler for `payment_link`, and the rail keeps
showing nothing for the Payments phase. That is correct and unrelated; the note
that started this work records why.

### D9 — Derivations are `hybrid_property` with SQL expressions

Every derived figure is defined once on `Registration` and usable from both
Python and a `WHERE` clause: a correlated scalar subquery over
`payment_credits` for the credited sums, an `EXISTS` over `payment_waivers` for
the waiver, and expressions composed from those for `outstanding`, `settled` and
`live_registration()`.

This is what keeps `availability.live_registration()` a single predicate, the
scheduler's four passes single queries, and `sheet.base_rows` free of an N+1.
The cost is a correlated subquery per registration on those queries; at a few
hundred registrations per tournament, against an indexed
`(registration_id, reversed_at)`, that is not a figure worth optimising before
it is measured.

*Alternative considered:* a database view of balances joined where needed.
Equivalent in effect, worse in the ORM: the properties would not compose into
the existing predicates without rewriting each query around the join.

### D10 — Clearing keeps its refusal; a single transaction gains a reversal

`clear_payments` still raises `CreditedTransactionsError` while any transaction
holds a live credit. The mechanical reason is gone — reversing the credits and
letting the balances recompute is now trivially safe — but the substantive one
stands unchanged: a credited payment was acted on, a fencer may have been told
by mail that they are paid, and "that import never happened" is not a thing
anyone can say about it afterwards.

What the blanket clear was being reached for instead becomes its own action: an
organizer may reverse one credited bank transaction, which appends the reversal
and returns the transaction to the unmatched queue. That is the operation that
was missing — a hand-drawn link and a recorded payment can both already be taken
back, and an automatically matched transaction could not.

### D11 — The migration is destructive and says so

No backfill. The migration drops `amount_paid_cents`, `amount_paid_eur_cents`,
`paid_at`, `settled_by_hand_at` and `settled_by_hand_reason`, removes `paid`
from the state enum, and creates the two journals empty. Registrations holding
`paid` become `reserved` and, with no credits behind them, read as unsettled.

This is only correct because the owner has decided the data is test data to be
dropped and re-imported (2026-09-09). The migration's docstring records that
decision and that the operation is not reversible, so that nobody later reads it
as a template for a migration against real books.

## Risks / Trade-offs

**A lifecycle pass reads the enum and silently matches nothing** → Removing
`PAID` from the enum makes every such site fail to type-check (D5). The four
highest-consequence ones — `availability.live_registration`,
`scheduler`'s reminder, expiry and demotion passes — get a test each that asserts
a settled registration is not reminded, not expired and not demoted.

**Correlated subqueries on every registration read** → Indexed on
`(registration_id, reversed_at)` and `(registration_id, revoked_at)`. Bounded by
tournament size, which is hundreds. If it ever bites, D9's view is the escape and
does not change any requirement.

**A reversal strands a registration that has since moved on** → Reversal is
defined as reversing the credit and nothing else. What the registration reads
afterwards is a derivation, so there is no second state to get wrong; a
registration that stops being settled reads reserved, and if the money mattered
to a seat it is the seating pass that says so. This is the case
`unapply_payment_link` gets wrong today by refusing to reverse at all.

**Two credits for one real payment ingested twice** → Out of scope by decision,
and the journal is what makes the pair visible. The partial unique index
prevents the same source row crediting twice; it cannot know two source rows are
one transfer.

**`payment_events` still has no reader** → Unchanged by this work, and one of
its stated non-goals. The credit and waiver journals answer most of what the
event trail was being asked for, which may shrink that change or retire it.

## Migration Plan

One Alembic revision, destructive, in this order: create `payment_credits` and
`payment_waivers` with their indexes; drop the five registration columns; narrow
the `RegistrationState` enum. No data is carried across. Rollback is restoring
the previous revision and re-importing, which is the same operation the owner has
already accepted as the plan for the data itself.

## Open Questions

None. The four that shaped this design were decided by the owner on 2026-09-09:
clearing keeps its refusal but gains a single-transaction reversal; cross-source
duplicate detection is deferred to its own change; the waiver becomes an
append-only journal in this change; and `paid_at` is derived from the credit
journal.
