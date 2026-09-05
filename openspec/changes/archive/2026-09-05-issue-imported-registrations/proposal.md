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
- **A variable symbol is issued only where Squire keeps the registrations**,
  from the tournament's own sequence, so the
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
allocates variable symbols on a Squire-kept tournament, which is not reversible
by re-running the action.
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


## Revision, 2026-09-05: no variable symbol in manual mode

**A symbol Squire mints after the fact was never on any payment.** A variable
symbol is a shortcut that lets a payment find its registration without anybody
reading the message; it is not the registration's identity, and a registration
without one is resolved by the payer's own words like the tenth of payments that
carry no usable symbol on any tournament (`name-assisted-matching`). On a manual
tournament the fencers registered through the organizer's own form and paid with
whatever reference that form told them — or with none. A number invented a season
later, which Squire has never shown to anybody, cannot match an incoming payment
and exists only to be looked at. It is not free either: a variable symbol is
unique across the deployment and never reused, so issuing fifty of them for a
past tournament burns fifty numbers out of a namespace every future tournament
shares.

So issuing SHALL allocate a symbol only on a tournament whose registrations
Squire keeps. On a manual one it creates the fencer, the registration, the
entries and the frozen price, and stops there.

Two things follow, and the second is a sequencing constraint rather than a
design point.

**The reason for waiting on deduplication changes.** It was that a row a merge
may collapse must not spend an identifier first. With no identifier spent there
is nothing to waste — but there is still a reason to wait, and it has to be
stated as the reason it actually is: a merge after issuing leaves two
registrations for one person, and the merge collapses rows, not registrations.

**The code SHALL NOT change before name-assisted matching lands.** Manual
linking addresses a registration by its variable symbol and by nothing else —
`candidate_vs`, a typed symbol, `unknown_vs`. Removing the symbol today would
leave an organizer with no way to reconcile a payment at all until
`add-name-assisted-payment-matching` gives them one by name. The two land
together or the manual path goes backwards.


## Revision, 2026-09-05: issuing is not an action, and the gate moves to matching

**Nobody was ever going to press it.** The issuing action was offered on the
Fencers phase — which is phase three of nine, two ahead of Deduplication
(`Console.tsx:54`) — while this proposal's own text said it is offered "after
deduplication". Nothing enforced that but a 409 the organizer meets *before* the
duplicates they would have to resolve, so the control the roster depends on was
reachable only in the state where it refuses. Its name says what the data model
does ("issue registrations") rather than what the organizer wants (to be able to
reconcile payments), and the phase where the absence hurts — Platby, with 43
transactions and nothing to match them against — said nothing about it at all.
An organizer had no path from the symptom to the cause.

So the action stops being an action.

**Issuing runs as the first step of payment intake.** Importing a statement and
polling the bank both issue registrations for the fencer list before matching
anything. The pass is idempotent by construction (Decision 8), so running it on
every intake costs nothing after the first and keeps a roster that gained rows
between two statements up to date without anybody remembering to.

**Deduplication becomes a precondition of matching, not of issuing.** This closes
open task 7.4. The original gate rested on a variable symbol that a merge would
strand, and Decision 9 removed the symbol from the manual path, leaving the gate
resting on nothing there. The argument that survives is about registrations, not
symbols: a merge collapses *rows*, so issuing before the verdicts leaves one
person holding two registrations and the merge with nothing to collapse. Moving
the gate to intake enforces that by the order of the phases rather than by an
error message, and puts the refusal where the organizer is already trying to do
the thing it blocks.

**The report moves into the operation's conclusion.** With no confirmation
dialog there is nowhere for the skipped rows to be named, and naming them is
half the value of the pass — a row with no discipline, no e-mail, no name, or an
e-mail another row already claimed is a row whose payments will not reconcile
until the organizer fixes it. The intake operation's conclusion carries it,
beside what the statement itself did.

**The notice survives the dialog.** Issuing is irreversible and, where Squire
keeps the registrations, spends variable symbols out of a deployment-wide
sequence that never recycles. The intake panel states that before the upload
rather than after it — the panel's established idiom is to say what an action
will and will not do instead of offering a control that surprises (design
add-payments-intake D5).

**A tournament Squire collects nothing for issues on entering the Payments
phase.** Where payments are boned out there is no intake to hang the pass on, and
the roster would never gain totals, an outstanding column, or a line in the
export. Such a tournament mints no symbols at all (Decision 9), so the pass is
cheap and carries no irreversible cost worth a confirmation: it runs when the
organizer opens Platby with the duplicates settled.

### Capabilities affected by this revision

- `imported-registrations`: "Issuing registrations for the fencer list" is
  rewritten. It is no longer offered as an action, no longer confirmed, and no
  longer gated on dedup itself; it runs on intake and on entering a boned-out
  Payments phase, and reports through the operation's conclusion.
- `etl-console`: "Manual entry of a fencer" currently points at "the separate,
  explicit action that issues registrations … offered after deduplication".
  That action no longer exists; the sentence has to point at intake instead.
- `payments-intake`: two new requirements — intake issues registrations for the
  fencer list before it matches anything, and intake is refused while duplicate
  groups are pending, naming the count and pointing at Deduplication. "Every
  intake action is reachable from the console" is modified alongside them: an
  action now states what it will irreversibly do before it runs, not only why it
  cannot run.
