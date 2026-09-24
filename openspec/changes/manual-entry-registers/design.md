## Context

`POST /{slug}/manual-rows` (`routers/manual_api.py`) validates the entry and writes a
`ManualRow` via `manualrows.create`. That row joins the fencer list as a source record;
the next payment intake issues it (`issuing._issue_one`): a `Fencer` without password
(`_resolve_fencer`, which claims an existing record only on a same-name address match),
a `Registration` with `clocks_dormant=True`, a VS only where Squire keeps the list, and
every discipline **seated regardless of capacity**.

Dormancy has one decision point, `setup.dormancy_cause`, which answers
`DORMANT_ISSUED_FROM_IMPORT` for any `clocks_dormant` registration. Fencer mail is guarded
at composition by `emails._payment_mail_suppressed` (payments off, or `clocks_dormant`),
but `send_promoted` does not consult it with payments on, and the confirmation path is
separate.

In-app placement lives in `routers.registrations.register` and `availability` —
per-discipline seat or queue, queue for everything once `seating_has_settled`.

The Import phase is always offered; `import_table` accepts an upload on any tournament.

Owner decisions (2026-09-24): import is manual-mode only; on an automatic tournament a
hand entry is a registration at once — capacity applies (full → queue), no account, no
clocks, no mail; existing automatic tournaments with imported rows are not dealt with.

## Goals / Non-Goals

**Goals:**
- One kind of entrant on an automatic tournament: a registration.
- A hand-entered registration that no clock moves and no mail reaches, and that money
  still finds.

**Non-Goals:**
- Migrating or cleaning imported rows on existing automatic tournaments.
- Changing manual mode in any way.
- Teams by hand (the dialog offers no team discipline today and still does not).

## Decisions

### D1. Branch in the endpoint; share placement with in-app registration

`create_manual_row` keeps its validation and branches on `registrations_kept_by`:
manual → `manualrows.create` as today; automatic → a new `handentry.register(...)` that
builds `Fencer`, `Registration` and entries. Placement per discipline goes through the
same function in-app submission uses (extracted if it is inline in `register`), so that
"placed exactly as an in-app submission is" holds by sharing code, including the
settled-seating branch. The response type becomes a union the dialog can read (a row id
or a registration id); the dialog only needs to close and refresh.

*Alternative:* write a `ManualRow` and issue it on the spot. Rejected: issuing seats past
capacity by design (a roster is a record of who fenced), which is the opposite of what an
entry at the door must do, and flipping that inside issuing would put a mode branch in the
one place that is meant to be mode-blind.

### D2. `clocks_dormant` stays the stored origin; the cause is told apart by `source_row_id`

A hand entry sets `clocks_dormant=True` and has no `source_row_id`; an issued registration
has one. `dormancy_cause` returns a new `DORMANT_ENTERED_BY_HAND` for the former. No new
column: the origin is already recoverable from what is stored, which is the condition the
spec puts on storing a cause.

### D3. Silence is one guard, extended to the two mails that bypass it

`_payment_mail_suppressed` already silences every `clocks_dormant` registration's payment
mail. `send_promoted` (payments-on branch and payments-off branch) and the
confirmation path gain the same guard, so a hand entry is never written to. This also
silences promotion of an *issued* dormant registration, which today would mail a person
who registered through someone else's form — consistent with `imported-registrations`'
"never sent anything". The mails added by `demotion-hardening` already go through the
guard. The discipline-correction surcharge keeps its `despite_dormancy` exception for
issued registrations only; for a hand entry the owner's rule is no mail at all, so the
exception is narrowed to registrations with a `source_row_id`.

### D4. Fencer identity: reuse `_resolve_fencer`'s address rule, refuse the certain duplicate

A typed address held by no fencer record goes on the new record. An address held by a
record that already has a registration on this tournament refuses the entry
(`already_registered`, naming it) — the one duplicate that is certain, and the unique
`(tournament, fencer)` constraint would refuse it anyway, less legibly. An address held by
a record with no registration here does not attach: the new record carries no address,
as issuing does for an address that names someone else. Name-only likeness goes to
deduplication.

### D5. Import refused at the upload, hidden in the console

`import_table` refuses an automatic tournament (`import_needs_manual_mode`, 409) before
reading the file. `offeredPhases` drops `import` on an automatic tournament. Clear stays
available through the API (nothing offers it in the console on an automatic tournament,
and existing rows are the owner's to leave).

## Risks / Trade-offs

- [Deduplication of two registrations — a hand entry and an in-app one without a shared
  address] → dedup already sees registrations; verify in implementation that resolving a
  registration–registration pair offers a sane outcome (delete one, keep the other), and
  if it does not, record it as a follow-up rather than widen this change.
- [An organizer who wanted to seat past capacity at the door] → raise capacity in Setup,
  or promote into a freed place; stated in the dialog's hint.
- [Silencing promotion mail for issued registrations changes today's behaviour] → it
  aligns with the stated rule that issued registrations are never written to; noted in
  the delta.
- [Existing automatic tournaments with imported rows keep an Import phase they cannot
  reach] → owner's call; the rows stay in the fencer list.

## Migration Plan

No storage change. Deploy backend and frontend together; the dialog's response handling
must accept the new shape.

## Open Questions

None.
