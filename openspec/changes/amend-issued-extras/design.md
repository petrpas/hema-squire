# Design

## Context

`edit-issued-disciplines` (archived 2026-09-06) opened the disciplines cell on
an issued registration and built the amendment behind it: `amendment.
apply_amendment` replaces a selection, re-prices through
`pricing.registration_total`, records a `registration_amended` event, marks a
refund where the registration is now overpaid, and mails the surcharge notice
only where the correction leaves the fencer owing more. The rule kind
`discipline_amendment` carries the decision so it appears in the manual-edits
log and can be withdrawn there.

The rentals cell is the same problem one field over, and — since issuing began
pricing rentals through the tournament's items — the same money. Two facts
decide the shape of this change:

- `apply_amendment` already takes `extras` and replaces the registration's
  selections from it. The pricing half is done.
- Everything around it says *disciplines*: the kind's name, its validation
  (`amendment_is_a_disciplines_edit`), `amendments_for`, `issued_selection`,
  `reapply_amendments`, and the frontend's `ruleKindFor`.

## Goals / Non-Goals

**Goals.** A rentals cell that opens and moves the money with the table. A rule
kind that the third and fourth priced field can join without a third and fourth
copy of the plumbing. Two fields amendable on one row without either
overwriting the other.

**Non-goals.** Opening the afterparty column (it is a tick, not a text cell, and
needs a control this change does not design). A merchandise column (there is
none; extras outside rentals and the afterparty reach the table only as the
notes summary). Any change to what the fencer may do to their own registration.

## Decisions

### D1. One kind carrying its field, not a kind per field

`discipline_amendment` becomes `registration_amendment`, and the field it amends
is read from `payload["field"]` — which the payload already carries, since every
amendment is a cell edit and every cell edit states its field.

The alternative was `rental_amendment` beside it, sharing `apply_amendment` and
duplicating the rest. Rejected: the duplicated rest is exactly where a drift
would hurt — one kind validating and the other not, one withdrawing per-field
and the other not — and the owner's reading is that the afterparty and
merchandise are the same operation again, so the copy would be made twice more.

The rename costs an Alembic migration: one row in the live database holds
`kind = 'discipline_amendment'`. Rules are replayed by kind, so a stale kind is
not a cosmetic problem — the rule would stop being applied.

### D2. Replay and withdrawal become per-field

`amendments_for(target)` and `issued_selection(target)` answer for the row as a
whole today, which is right while one field is amendable and wrong the moment
two are. Both become per-field: the amendments standing against *this field* of
this row, and what the registration was issued with *for this field*.

`reapply_amendments` then rebuilds the whole registration from every field at
once — the last amendment standing for each field, and the issued value for
each field that has none — because `apply_amendment` states a whole
registration, not a difference. Rebuilding one field while passing `None` for
the others would reprice against a stale selection.

`base` (what the row was issued with) is recorded per field on the first
amendment of that field, exactly as it is recorded today, and read from the
earliest amendment of the same field.

### D3. A rentals amendment replaces rentals and nothing else

`apply_amendment(extras=...)` deletes every `RegistrationExtra` and recreates
the list it is given. A rentals amendment therefore passes **the whole extras
set**: the registration's non-rental selections as they stand, plus one
selection per named rental item.

The legacy `weapon_rentals` list is written to match, through the `fields`
parameter the fencer's path already uses. It is what the fencer list displays,
what the confirmation mail lists, and where a name nothing lends survives — so
it must state what the organizer typed, including the part nothing prices.

### D4. An unlendable name is kept, not refused

Settled by the owner on 2026-09-06 for the import path and reaffirmed here for
the typed one: the edit is applied, nothing is billed for the unlendable item,
and the row states it. A refusal would leave the worse record standing — the
organizer is usually correcting *towards* the truth in one step and away from a
misspelling in another — and the offered list is not always complete at the
moment the roster is corrected.

What is added is that the row says so **as a problem**, not only as an italic in
the rentals cell. Hence the problem marker joining the fencer list's columns.

### D5. The problem's words are the frontend's

The unpriced names travel as data (`unpriced_rentals`, already on the row), and
the sentence naming them is composed in the console from a translated string. A
sentence stitched in `sheet.py` would be the first server-generated Czech in a
table whose every other word is translated in the client, and it would be wrong
for an English-speaking organizer.

Parse problems keep coming from the parser as text; the two are concatenated for
display, the row's own problem first.

## Risks / Trade-offs

- **The migration.** A rule whose kind is not migrated silently stops applying,
  and the registration keeps a total nothing explains. The migration is a single
  `UPDATE`, and the downgrade reverses it.
- **Free text against exact names.** A typo becomes an unpriced item rather than
  an error. That is the owner's decision (D4), and the problem marker is what
  keeps it from being silent — but it does mean a misspelled rental reads as a
  correction rather than as a mistake until someone reads the marker.
- **Two amendments, one row, one replay.** The per-field rebuild is more code
  than the single-field one it replaces, and its failure mode is the quiet kind:
  a field left out of the rebuild would be repriced away. Task 4.2 is the test
  that would catch it.

## Migration Plan

One Alembic revision: `UPDATE rules SET kind = 'registration_amendment' WHERE
kind = 'discipline_amendment'`, reversed on downgrade. No schema change — the
kind is a string column.

## Open Questions

None. The afterparty and merchandise columns are deliberately left for the
change that gives them cells.
