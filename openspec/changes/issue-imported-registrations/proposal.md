## Why

A tournament whose fencers were imported cannot take a payment. Not badly — at
all. The pilot `na-duel-2026` carries 54 imported rows, 43 ingested bank
transactions, and **zero registrations**: no variable symbol has ever been
issued (`vs_next_seq` is still 1), so nothing can match, and
`POST /payments/link` resolves the VS an organizer types against
`Registration.vs` and answers `404 unknown_vs` for every value that exists.
Every one of the 43 payments is permanently unmatchable and unlinkable, and the
four resolution queues have no reachable destination.

This is not an oversight. `etl-console`'s "Manual entry of a fencer" says it
outright: a row entered by hand "SHALL NOT be given a variable symbol or a
payment instruction … It states who is competing; it does not enrol them in the
application." An imported row is the same kind of record. The rule is right for
the moment a row arrives — a row that dedup may merge away must not burn a VS —
but it leaves no later moment at which a roster becomes billable, and the
Payments phase silently assumes a population that registered in-app.

The missing quantity is smaller than it looks. What a fencer owes is already
derivable from what they entered: `pricing.discipline_fee`,
`weapon_rental_fee` and `afterparty_fee` all take `(tournament, discipline,
date)` and need no `Registration` at all, and an imported row carries its
disciplines, its rentals, its afterparty and — in `ParsedFencer.registration_time`
— the moment it was registered, which is the date early-bird pricing must be
read at.

## What Changes

- **A new console action issues registrations for the fencer list.** Offered on
  the Fencers phase, after deduplication, never automatically at import: rows a
  dedup merge is about to collapse must not each take a variable symbol first.
- **A row without a fencer record gains one.** 52 of the pilot's 54 rows have no
  `Fencer` behind them. The record created is a fencer of the tournament, not an
  account: no credentials, no invitation, no mail.
- **The registration is priced from the row and frozen.** Its total is computed
  from the row's own disciplines, rentals and afterparty at the row's own
  registration moment, so early-bird applies exactly as it did when the fencer
  signed up — and is then stored in `total_amount` rather than derived on read,
  as `models.py` requires of every registration ("never recomputed on read,
  never moved by a later price or rate change").
- **Its lifecycle clocks are dormant.** No payment window opens, no due date is
  set, it never expires for non-payment, and no reminder is ever sent for it.
  This is not a new idea: `registration` already makes both clocks dormant for a
  registration taken while payments were off, and says its total is still
  computed and presented "as a statement of what the tournament costs rather
  than a demand". An issued registration is dormant for the same reason by a
  different cause — its origin rather than the tournament's configuration.
- **A variable symbol is issued**, from the tournament's own sequence, so the
  fencer can be paid for, quoted a QR code, matched and linked exactly as an
  in-app registration is. This is the whole point: one payment model, not two.
- **Issuing is idempotent and repeatable.** A row that already has a
  registration is left alone, so the action can be run again after a later
  import or a manual entry without disturbing what it did before.
- Czech and English strings for the action, its confirmation and its report.

Not in scope: any change to matching, crediting, tolerance or refunds; the
name-assisted matching that this unblocks is
`add-name-assisted-payment-matching`, proposed separately and dependent on this.
Also out of scope: turning an issued registration into an account the fencer can
log into. That is a larger question about identity, and nothing here forecloses
it.

## Capabilities

### New Capabilities
- `imported-registrations`: how a fencer list becomes billable — the issuing
  action and where it is offered, what a row must have before it can be issued,
  how the total is computed and frozen from the row's own answers at its own
  moment, the variable symbol, the dormant lifecycle clocks, idempotence on
  rerun, and what the action reports.

### Modified Capabilities
- `etl-console`: "Manual entry of a fencer" currently states flatly that such a
  row is never given a variable symbol or a payment instruction. That stays true
  of the moment a row is entered or imported, and gains its counterpart — the
  later, explicit action by which the organizer issues registrations for the
  list, and the fact that it is offered only after deduplication.
- `registration`: "Reservation lifecycle" gains the second cause of dormant
  clocks. Today they are dormant only while the payments feature is off; a
  registration issued for an imported or manually entered row SHALL have them
  dormant by origin, permanently, and SHALL NOT acquire a due date when anything
  about the tournament later changes — the same protection the spec already
  gives a registration taken while payments were off.
- `table-import`: "Clearing the tournament's imported content" promises that
  nothing cleared remains visible or countable. A registration issued for a
  cleared row now stands in that row's place on the fencer list, so the capability
  gains the rule that such registrations go with their rows — and that a clear is
  refused where one of them holds credit, which is the rule a tournament is
  already deleted under.
- `fencer-accounts`: "Account creation with HR binding" describes the fencer
  record as something a person creates for themselves. It gains the statement
  that a fencer record MAY exist without an account — created by the organizer
  on the tournament's behalf, holding no credentials, sending no invitation, and
  claiming no HR profile the row had not already been matched to.

## Impact

**Backend** (`backend/app/`): a new module for the issuing pass (reading sheet
rows, creating `Fencer` and `Registration`, pricing via the existing
`pricing.py` functions, allocating VS through the existing sequence in
`routers/registrations.py:106` rather than a second allocator); `models.py`
gains the mark that makes a registration's clocks dormant by origin, with an
Alembic migration; `scheduler.py` must honour that mark in `_reminder_due` and
in expiry, which is where a wrong answer would mail 54 people; a router endpoint
on the console's Fencers phase.

**Frontend** (`frontend/src/`): an action on the Fencers phase with a
confirmation stating how many rows will be issued and that mail will not be
sent; `api.ts`; `i18n/{en,cs}.json`. The sheet's `outstanding` column starts
carrying values for these rows, with no change to `SheetArea` — it already
renders `outstanding_amount` for registration-backed rows.

**Data**: this creates real fencers and registrations from imported rows and
allocates variable symbols, which is not reversible by re-running the action.
The confirmation is the guard, and `data-export` carries the results like any
other registration.

**Risk**: the lifecycle mark is the one that matters. A registration that
reaches `scheduler.py` without it opens a payment window and sends expiry and
reminder mail to people who registered a year ago. Tests must cover the
scheduler seeing an issued registration and doing nothing, not merely the
issuing pass writing the mark.

**Verification**: `pytest` for pricing at the row's own moment (early-bird on
and off), VS allocation and uniqueness, idempotent rerun, and the scheduler
leaving issued registrations alone; `vitest` for the action and its
confirmation; then the pilot itself — 54 rows issued, and the 43 waiting
transactions become linkable.
