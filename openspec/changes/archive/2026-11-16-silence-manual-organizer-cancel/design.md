## Context

Two checks decide whether Squire writes to a registration. `dormant_by_origin` covers
every registration issued from a source row. `_entered_by_hand` (`emails.py`) narrows
that to dormant registrations without a source row. Organizer actions on a seat use the
narrow one (cancellation, team cancellation, substitution), so that an imported
registration on an automatic tournament still hears that the organizer cancelled it.

On a manual tournament the organizer's hand entries are written as source rows `man:N`
and issued like any imported row, so `_entered_by_hand` is false for them. The
substitution avoids this because its caller (`rules_api.py`) returns before mailing
unless `registrations_kept_by is SQUIRE`. The cancellations have no such guard.

## Goals / Non-Goals

**Goals:**
- An organizer's cancellation of a registration or a team mails nobody on a manual
  tournament.
- The dialogs on a manual tournament promise no mail and ask for no note.

**Non-Goals:**
- Changing what an automatic tournament mails, including an imported registration on
  one (it is still mailed, as the spec says).
- Teaching `_entered_by_hand` to recognise `man:N` rows. On a manual tournament the mode
  alone decides, so the origin does not need to be read there.

## Decisions

**D1. The mode is checked inside the two senders, not at their callers.** The
substitution checks it at its caller, but its sender is reached from one place.
`send_cancelled_by_organizer` and `send_team_cancelled` each state who is not written to,
and the manual tournament belongs on that list. A check inside the sender also protects
any later caller. `send_team_cancelled` already returns whether it sent, so the console's
"the fencer was told" line stays correct with no further change.
*Alternative:* a guard at each router, as the substitution has. Rejected because the
silence would then live in two routers rather than beside the rule it belongs to.

**D2. The dialogs read the mode from the tournament they already have.** The console
holds the tournament's `registrations_kept_by`. On a manual tournament
`CancelRegistrationDialog` drops the mail sentence and the note field, and sends no note.
The team confirmation drops its mail sentence.

## Risks / Trade-offs

- [An organizer on a manual tournament expected Squire to tell the fencer] → The dialog
  no longer promises it. The organizer keeps the list and is in contact with the fencer.
