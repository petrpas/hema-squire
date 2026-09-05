## Why

Two fencers on the pilot cannot be billed, and nothing the organizer can do
fixes it.

`na-duel-2026`'s fencer list holds Jindřich Pekárek and Václav Pekárek —
evidently brothers, entered by one parent on one address. Issuing skips both
with `email_taken`: `Fencer.email` is unique and not nullable, a fencer
registers once per tournament, so two rows sharing an address resolve to one
fencer and only the first can be issued a registration. Without a registration
they are invisible to every surface that addresses one — which is how this
surfaced at all, with the organizer unable to find either of them in the manual
payment-link dialog, because `nameresolve.roster` selects fencers through a live
registration.

The console's answer was to fix the row. The console cannot: `email` is neither
a column of the fencer table nor an editable one. And if it were, the remedy on
offer would be for the organizer to invent two contact addresses they do not
have, in order to satisfy a schema constraint — writing false data into the one
field that is supposed to be a way of reaching a person.

The address is not there because Squire does anything with it for such a record.
It is there because `Fencer.email` is the account identity. The specs already
say what these records are not: created on the tournament's behalf, holding no
credentials, never mailed, not an account anyone can log into
(`fencer-accounts`, "A fencer record may exist without an account"). An identity
for logging in is precisely what a record that cannot log in does not need.

## What Changes

- **`Fencer.email` becomes nullable.** A fencer record the organizer creates on
  the tournament's behalf may hold no address at all. The unique index stays:
  both SQLite and Postgres admit any number of NULLs under one.
- **`email_taken` and `no_email` stop being reasons a row cannot be issued.**
  Every row that states a name and a discipline becomes billable. The two
  Pekáreks issue.
- **An address is claimed once.** Where a row's address already belongs to a
  fencer, that record is reused as it is today — an existing account keeps its
  identity. Where a second row of the same list repeats an address the pass has
  just used, the second fencer is created **without one**: the address is the
  first person's, and asserting it as the second's would be a claim nobody made.
- **A message with no recipient cannot be built.** This is the risk the change
  turns on. `emails.py` passes `fencer.email` as the recipient at roughly
  fifteen call sites, and an addressless fencer is exactly an issued-registration
  fencer, which nothing currently mails — but by two guards coinciding
  (`clocks_dormant` stops the scheduler, `_payment_mail_suppressed` stops the
  organizer), not by an enforced invariant. That is the shape of the bug found
  as task 7.2b of `issue-imported-registrations`: dormancy stopped the
  scheduler and did not stop the organizer. The refusal moves to the boundary,
  where a recipientless message is a programming error rather than a silent
  no-op, and the tests assert the boundary rather than the coincidence.
- **The skip reasons the console states move with the pass.** `issuing.would_skip`,
  `GET /import/issue`'s `skipped` list, the intake pre-flight and the link
  dialog's "these fencers have no registration" notice all name reasons that
  stop existing.
- Czech and English strings for the reasons that go.

Not in scope: turning a record created this way into an account the person can
log into. `issue-imported-registrations` already puts that out of scope, and
this narrows it by one step worth stating — a person whose record carries no
address who later signs up with their own gets a second record, and no history
follows them across. That is the same unsolved problem, not a new one.

Also not in scope: showing or editing `email` on the fencer table. It was the
remedy for a failure this change removes.

**Depends on `issue-imported-registrations`**, which is implemented but not
archived: the requirement this change modifies ("A fencer record may exist
without an account") lives in that change's delta and not yet in the main specs.

## Capabilities

### New Capabilities

None. This removes a constraint rather than adding a behaviour.

### Modified Capabilities

- `fencer-accounts`: "A fencer record may exist without an account" gains the
  address. A record created on the tournament's behalf SHALL be able to hold
  none; an address SHALL be claimed by at most one record; a message SHALL NOT be
  constructed without a recipient; and the requirement's present scenario about
  signing up afterwards — which assumes the record carries the person's address —
  states what happens when it does not.
- `imported-registrations`: gains what a row must have to be issued — a name and
  a discipline, and nothing about an address. The capability never fixed
  `no_email` or `email_taken`; they were reasons the implementation invented on
  its own, which is part of why they went unexamined.

## Impact

**Backend** (`backend/app/`): `models.py` — `Fencer.email` nullable, and
`TeamMember`'s docstring, which rests design team-disciplines D4 on "`Fencer.email`
is unique and non-nullable", restated on the part that survives (a roster member
is not a fencer because identity is local to the roster, not because of the
column). An Alembic migration dropping the NOT NULL; no backfill, since every
existing row has an address. `issuing.py` — `_resolve_fencer` and `_issue_one`
lose two skip reasons and gain the once-claimed rule; `would_skip` follows.
`emails.py` or `mail.py` — the recipient guard. `auth.py`, `routers/accounts.py`
(the uniqueness probe), `routers/admin.py`, `routers/manual_api.py`,
`routers/registrations.py`, `routers/tournaments.py`, `export_json.py` and
`sheet.py` all read `Fencer.email` and are checked for None-tolerance.

**Frontend** (`frontend/src/`): `api.ts` if the skip reason union is typed;
`i18n/{en,cs}.json` lose two reason strings. No component changes — the surfaces
that name skipped rows simply have fewer to name.

**Data**: existing rows are unaffected. New records created by issuing may carry
NULL where a row's address was already claimed.

**Risk**: mail. A path that reaches `build_message` with `None` today would
crash or, worse, construct a message with no recipient; after this it must be
refused at the boundary and covered by a test that calls the mail path directly
against an addressless fencer, not one that asserts the fencer is dormant.

**Verification**: `pytest` for issuing two rows that share an address, the
recipient guard, and the readers that touch `Fencer.email`; `vitest` for the
strings; then the pilot — 53 rows pending, 51 issued today, and 53 after.
