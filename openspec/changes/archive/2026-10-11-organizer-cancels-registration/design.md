## Context

`rules.create_rule` writes a `row_delete` for any row. Replay marks the row `_deleted`,
and every table after the deleting phase drops it. The registration behind it is never
consulted. `my-registration/cancel` is the only path to `RegistrationState.CANCELLED`:
it stamps `cancelled_at` and records `refundable`/`refund_state` for a settled
registration. No mail is sent and nobody is promoted.

`sheet.base_rows` leaves cancelled registrations out. A registration issued for a
source row takes that row's id, and `_add_source_rows` adds source rows with
`setdefault`. Once such a registration is cancelled, its id is free again and the
imported (or hand) row comes back as an unissued row, which `issuing.pending` would
offer to the next pass.

Owner decisions (2026-10-11): split deletion from cancellation, mail the fencer, handle
money as the fencer's own cancellation does, make manual mode as similar as possible,
and leave already-deleted rows alone.

## Goals / Non-Goals

**Goals:**
- One cancellation, reached by two actors, with identical effects on the registration.
- Deletion cannot take a live registration out of sight.
- Cancelling an issued registration cannot be undone by the next intake pass.

**Non-Goals:**
- Automatic promotion from the queue into the freed seat.
- Refunds through Squire.
- Merges that absorb a live registration's row (deduplication). They stay as they are;
  see Risks.
- Migrating rows already deleted while holding a live registration.

## Decisions

### D1. One cancellation helper, two routes

A `cancel(registration, tournament, now)` helper in the registrations router module,
beside `cancel_registration`, does what
`cancel_registration` does today: state, `cancelled_at`, and refund state for a settled
registration. The fencer's route and the new organizer route
`POST /api/tournaments/{slug}/registrations/{registration_id}/cancel` both call it. The
organizer route takes `{note?: str}` (≤ 500 chars), requires console access and
publication, and refuses with 409 `registration_not_live` a registration that is
already cancelled or expired.

*Why not a rule:* a cancellation is a state change with a mail, not a projection edit.
A rule would be withdrawable, and the owner wants it irreversible.

### D2. The refusal lives in `create_rule`

`row_delete` on a target whose registration (`amendment.registration_for_row`) is live
(`amendment.is_live`) answers 409 `row_has_registration`, the code `field_edit` already
uses for the same reason. It sits in the one place every rule passes through, so no
route can go around it. `row_restore` stays unrestricted, which is what lets an
organizer bring back a pre-existing deleted row and cancel it.

### D3. The mail follows the substitution's suppression

`emails.send_cancelled_by_organizer(mailer, tournament, registration, note)` sends
nothing for a registration entered by hand (`_entered_by_hand`) or with no address
(`recipient` returns None). This is the rule `send_substitution` follows, and the
nearest precedent for an organizer acting on someone's seat. On a manual tournament an
issued registration with an address is therefore mailed, "as similar as possible" to
automatic. The mail is sent after commit, so a failed send does not undo the
cancellation.

Content: the tournament, `_summary_lines` of what was held, the organizer's note when
given, and, for a settled registration, one line that a refund is settled with the
organizer.

### D4. A cancelled issued registration's source row stays out

`base_rows` reads the `source_row_id`s of the tournament's cancelled registrations and
does not add those source rows. The row number stays allocated (`rownumbers` keys by
row id and is not touched). `issuing.pending` reads from the same rows, so it can no
longer see the row. This applies to fencer cancellations too, which had the same
latent defect.

### D5. The console

On the Fencers phase, a row with a live registration (`registration_id` is a number,
state reserved or paid, not deleted) shows **Zrušit registraci** (`IconUserX`,
outline) in the slot where the delete icon stands. It opens a `Modal` that states
what will happen (seat freed, mail sent or not, refund noted where paid), with an
optional note field and a destructive confirm. The row then leaves the table on
refresh, as a self-cancelled registration does. Import never lists registrations, so
it is unaffected.

## Risks / Trade-offs

- **A merge can still absorb a live registration's row** and so hide it. → This is
  rare: deduplication runs before issuing, and in-app registrations enter bound. It is
  left as a known gap and recorded here, not fixed.
- **A cancellation in error is final.** → The confirmation states it. The person
  registers again or is entered by hand.
- **Mail on manual tournaments** reaches people who registered elsewhere. → This is the
  same exposure as a substitution's mail today. The owner asked for "as similar as
  possible".

## Migration Plan

No schema change. The rows already deleted (e.g. 5 on `na-duel-2026`) stay deleted. Deploy
is the ordinary one.
