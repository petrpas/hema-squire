## Context

Individual placements are decided in two places with the same line —
`RegistrationDiscipline(discipline=d, is_substitute=d.slug in full)` — in
`routers.registrations` (submission) and `amendment.apply_amendment`, where `full` comes
from `availability.full_disciplines` or is everything once seating has settled. After
`manual-entry-registers`, hand entry on an automatic tournament reuses the submission's
placement. `admit_substitute` and `return_to_queue` each act on one
`(registration, discipline)` placement. `scheduler._demote` already moves a whole
registration.

Owner decisions (2026-09-24): a general condition set in the core, offered in the form as
one tick; a registration waiting for its condition holds no seat anywhere.

## Goals / Non-Goals

**Goals:**
- One invariant — a condition is wholly seated or wholly queued — held by construction in
  one placement function and in the two organizer actions.
- Today's behaviour exactly, for every registration without a condition.

**Non-Goals:**
- A per-discipline tick in the form (the core allows it; the form does not offer it yet).
- Teams in the condition.
- Automatic seating of anyone (`paying-substitutes`).

## Decisions

### D1. The condition is a flag on the placement

`RegistrationDiscipline.conditional: bool`, default false. The condition of a registration
is its conditional entries. A per-registration list of slugs was the alternative; the flag
keeps the condition attached to the rows that are placed, survives a discipline rename,
and makes the invariant a statement about sibling rows (`all(e.is_substitute for e in
conditional)` or `none`). The form's tick sets the flag on every individual entry of the
submission.

A condition of exactly one discipline is refused at the schema: it would mean nothing a
plain entry does not.

### D2. One placement function

`placement.place(entries, full, settled) -> None` sets `is_substitute` on a registration's
individual entries:

```
if settled:                     every entry queued
elif any(e.conditional and e.slug in full for e in entries):
                                every entry queued          # waits whole
else:                           each entry queued iff its slug in full
```

Submission, amendment and hand entry call it; the two inline sites go. `full` is computed
as today, excluding the registration's own seats on amendment as today.

### D3. Promotion and return act on the set

`admit_substitute(reg, slug)`:
- if the registration has a condition and it is not met, the set to seat is the
  conditional entries plus the promoted one; every discipline in it must have
  `taken_seats < capacity`, else `409 condition_discipline_full` naming the first full one;
- otherwise the promoted entry alone, as today.
Repricing, window and mail are unchanged; the mail names every discipline seated.

`return_to_queue(reg, slug)`:
- if the entry is conditional, every seated entry of the registration is returned;
- otherwise that entry alone.
Queue moments are left alone, as the organizer's return always does.

### D4. The Queue roster reads the condition from the row

`sheet.base_rows` carries `conditional: [slug, …]` beside `disciplines`/`substitute_for`.
The roster's arrow cell (from `queue-rosters`) extends its rule: a queued row of a
registration with an unmet condition needs a free place in every conditional discipline
and in its own; the free counts per discipline are already in the `/queue` summary. The
row's text names the other conditional disciplines.

### D5. Amendment refusal where credit exists

`apply_amendment` computes the new placement before committing; if the registration was
not wholly queued, will be wholly queued, and holds credit
(`credited_local_cents > 0 or credited_eur_cents > 0`), it refuses
`amendment_would_queue_paid`. The amendment form asks the server for a preview of the
placement (the price preview endpoint already re-prices a proposed selection; it returns
the placement too) so it can state the consequence before submitting.

### D6. Export document

`export_json` bumps its schema version and carries `conditional` per entry; older
documents import with no condition.

## Risks / Trade-offs

- [A conditional registration first in line can look "skipped" to the fencer] → their
  detail states which discipline is full; the queue view states what it waits for.
- [Organizer surprise: ↓ on one row moves several] → the arrow's hint on a conditional row
  says it returns the whole registration.
- [Preview and submit racing on capacity] → the submit re-places on the server; the
  preview is a statement, not a reservation.
- [Mail wording for a waiting-whole registration] → confirmation states the condition and
  the full discipline; covered by tests on the catalog keys.

## Migration Plan

Add `registration_disciplines.conditional` not null default false. No registration is
re-placed.

## Open Questions

None.
