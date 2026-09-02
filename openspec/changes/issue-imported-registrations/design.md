## Context

Squire holds three populations of fencer, and only one of them can be paid for.
An in-app registration is a `Registration` — it has a variable symbol, a frozen
total, a state and a credited amount. An imported row and a manually entered row
are `ImportedRow` records surfaced through `sheet.py`, and they have none of
those things. `etl-console` says so deliberately: such a row "SHALL NOT be given
a variable symbol or a payment instruction … it does not enrol them in the
application."

That was the right rule while the Payments phase did not exist. It is now the
reason the phase cannot be used at all on a migrated tournament. The pilot
`na-duel-2026` is the proof: 54 imported rows, 43 ingested bank transactions,
0 registrations, `vs_next_seq` still 1. `matching.py` resolves a payment through
`Registration.vs`, and `routers/payments.py:181` validates a manual link the same
way and answers `404 unknown_vs`. There is no VS in the tournament, so every
payment is both unmatchable and unlinkable, and the four resolution queues are
ornamental.

The constraints that shape the design are already written down elsewhere:

- **Price is frozen, never derived.** `models.py:566-569` — `total_amount` is
  "stored at registration exactly as … never recomputed on read, never moved by
  a later price or rate change." Whatever this change does, it must not
  introduce a registration whose total is computed on read.
- **Pricing already needs no registration.** `pricing.discipline_fee`,
  `weapon_rental_fee` and `afterparty_fee` take `(tournament, discipline, date)`.
  Nothing has to be invented to price a row.
- **VS is unique across the deployment**, not the tournament (`models.py:565`),
  allocated by one counter bump in `routers/registrations.py:106`, and never
  reused across registration cycles.
- **The lifecycle is a scheduler, not a request path.** `scheduler.py` expires
  reservations and sends reminders on its own clock, and `POST /payments/process`
  runs the same passes on demand. Anything issued into the wrong state is mailed
  without anyone asking.

## Goals / Non-Goals

**Goals:**

- A fencer list can be made billable in one deliberate action, after dedup.
- An issued registration is indistinguishable from an in-app one everywhere that
  money is concerned: matching, linking, crediting, tolerance, QR, export.
- What a fencer owes is what they would have owed on the day they registered.
- No mail reaches anyone as a consequence of this change, ever.
- The action is safe to run twice, and safe to run again after a later import.

**Non-Goals:**

- Accounts. This creates fencer records, not logins, and sends no invitations.
- Name-assisted matching. That is `add-name-assisted-payment-matching`, which
  depends on this change and is proposed separately.
- Changing what an in-app registration does, or how any payment is matched or
  credited once a VS exists.
- Reversing an issue. Allocated variable symbols are not reclaimed; the
  confirmation is the guard.

## Decisions

### Decision 1 — Issue real registrations rather than teach payments about rows

The alternative was to leave imported rows alone and extend payments to target
them: let the link dialog attach a transaction to a sheet row, and derive an
imported row's balance on read.

Rejected on two counts. First, deriving a balance on read contradicts
`models.py:566-569` directly — an imported fencer's debt would move every time
a fee was edited, which is the exact failure the frozen total exists to prevent.
Second, it splits the payment model in two: everything downstream of a match —
crediting, tolerance, partial payment, refunds, expiry, the paid state, the
confirmation mail, the QR code, `data-export` — is written against
`Registration`, and each would need a second branch for rows. The cost of that
is paid forever, by every future change to payments.

Issuing a real registration is the same operation the application already
performs, sourced from the sheet instead of a form submission. One model, and
the whole of payments works on the pilot unchanged.

### Decision 2 — Price at the row's registration moment, not at the moment of issuing

`ParsedFencer.registration_time` carries the moment the fencer actually
registered; the pilot's rows carry the Google Form timestamps. That is the date
handed to `pricing.*`.

The alternative — pricing at the moment of issuing — is simpler and wrong. A
roster imported after the early-bird deadline would be billed the late price for
fencers who registered in time, and the organizer would have no way to correct it
short of editing each total by hand. Pricing at the row's own moment makes the
issued total equal to the total the fencer would have had if they had registered
in-app that day, which is the only defensible definition.

The total is then written to `total_amount` and never recomputed, exactly as an
in-app registration's is.

### Decision 3 — Dormancy is a property of the registration, not of a filter

The clocks must never start for an issued registration. There are two ways to
achieve that: mark the registration, or teach `scheduler.py` to recognise
registrations of this origin.

Mark the registration. A stored flag is one thing to get right in one place and
is visible in the database when something goes wrong; an origin test scattered
through `_reminder_due`, the expiry pass, the seating settlement and
`POST /payments/process` is four places to forget it, and the cost of forgetting
is mail to 54 people.

The flag is also the honest data model: `registration` already treats dormancy as
a property a registration can have — "both clocks SHALL be dormant while the
tournament's payments feature is off". This change makes the same dormancy
reachable by a second cause, so the concept is not new, only its second origin.

Deliberately **not** modelled as a new `RegistrationState`. The four states
(`RESERVED`, `PAID`, `EXPIRED`, `CANCELLED`) describe where a registration stands
with respect to money, and an issued registration genuinely is reserved and
genuinely can become paid. Dormancy is orthogonal to state, and a fifth state
would need re-answering every question the other four already answer.

### Decision 4 — After dedup, and offered nowhere else

A variable symbol is unique across the deployment and never reused. Issuing one
to a row that a pending merge is about to collapse spends an identifier on a
record that will not exist, and leaves a merged-away registration to explain.

Deduplication concluding is therefore a precondition, not a suggestion, and the
action lives on the Fencers phase beside the other actions that operate on the
list as a whole. It is not offered on Import: the Import view records what a file
contained, and issuing is a decision about the roster, not about a batch.

### Decision 5 — Reuse the existing VS allocator, do not write a second one

`routers/registrations.py:106` allocates by an atomic `UPDATE … SET vs_next_seq =
vs_next_seq + 1 … RETURNING`, with a unique constraint on `Registration.vs` as
the backstop that turns a race into a retry. Issuing 54 registrations in one pass
uses that same allocator 54 times rather than reserving a block, so there is one
allocation path in the codebase and the uniqueness guarantee is not restated in a
second place where it could drift.

### Decision 6 — A row without a discipline is skipped and reported, not issued

A registration with a total of zero and no entries is not a useful record; it
would appear settled and would quietly absorb a payment. Such rows are left as
they are and named in the action's report, so the organizer can fix the row and
run again — which Decision 7 makes free.

### Decision 7 — Capacity does not apply to an issued roster

Found by trialling the pass against the pilot, where it produced five
registrations owing nothing at all. The pilot's SA holds 42 against 48 entrants
and its SB holds 28 against 30, so respecting capacity queued eight placements —
and because a substitute placement is not billed, five fencers came out owing
zero.

Capacity is a rule about admitting people. A fencer list is a record of people
already admitted, usually by an organizer who ran the registration elsewhere and
months earlier; asking Squire to re-decide it against a number typed into Setup
afterwards queues people who have already fenced, and does so in whatever order
the rows happen to be issued in. That the same rule also makes them free is what
settles it: an over-subscribed roster would issue registrations that read as
paid-up on arrival, which is the exact opposite of what issuing is for.

So every issued placement is seated, and issuing may leave a discipline over its
capacity. The capacity keeps governing everyone else — a fencer registering
afterwards into a discipline the roster has filled queues behind it as they would
behind any other full discipline — so the figure still means what it meant; it
simply does not get to overrule a record of what already happened.

### Decision 8 — Idempotent by construction

The pass selects rows that have no registration. Running it again therefore
issues nothing, and running it after a later import issues only the new rows.
This is what makes the action safe to offer without an undo: its only failure
mode is doing less than expected, never doing something twice.

## Risks / Trade-offs

**A registration reaching the scheduler without its dormancy mark mails people
who registered a season ago.** → This is the risk that matters, and the one to
test hardest. Coverage must include the scheduler and `POST /payments/process`
*running* against issued registrations and doing nothing — not merely the issuing
pass writing the flag. A test that asserts the flag is set proves nothing about
`_reminder_due`.

**Issuing is not reversible.** Variable symbols are allocated and not reclaimed,
and fencer records are created. → The confirmation states the count before the
action runs, and Decision 7 means an accidental second run is harmless. A
mistaken first run is recovered by deleting registrations, which is an existing
administrative capability, not something this change needs to invent.

**Creating fencer records could collide with real accounts on email.** → A row
whose email already belongs to a fencer record must reuse that record rather than
create a second one; the pilot has two such rows already. This is the one place
where the pass touches data that a person owns, so it reuses and never overwrites:
an existing record's name, HR binding and credentials are left exactly as they
are.

**Early-bird pricing depends on a timestamp the parser produced.** A row whose
`registration_time` is wrong is priced wrong. → The timestamp is already load-
bearing: it orders the fencer list. A wrong one is visible in the list before
issuing, and the total, once frozen, is editable by the organizer like any other.

**The pilot's 43 transactions will match all at once.** → Matching by VS requires
the VS to appear in the payment, and these payments predate any VS, so nothing
will auto-match. Money moves only where an organizer links it. That is the
expected outcome, not a defect, and it is exactly what
`add-name-assisted-payment-matching` addresses next.

## Migration Plan

One Alembic migration adding the dormancy mark, defaulting to "clocks run" so
every existing registration keeps its present behaviour. No backfill: no
registration issued before this change exists, by definition.

Rollback is the reverse migration. Registrations issued before a rollback would
lose their dormancy and become ordinary reserved registrations — which is to say
they would start expiring and being reminded. So the rollback is not safe once
the action has been used, and the migration should be treated as one-way in
practice.

## Open Questions

- Should an issued registration be visibly distinguished in the fencer list, or
  is the outstanding amount appearing enough? Distinguishing it would help an
  organizer understand why one row has a VS and another does not, but the list is
  already dense.
- Should the organizer be able to issue registrations for a *selection* of rows
  rather than the whole list? Not needed for the pilot, and the whole-list action
  is the one that composes with a rerun.
