## Why

The mode spec says a manual tournament is one Squire "runs nothing against", and the
substitution already keeps that silence. The organizer's cancellation does not: its mail
skips a hand entry only when the registration has no source row, which is true only on an
automatic tournament. On a manual one a hand entry becomes source row `man:N` and is
issued from it, so cancelling it, or a fencer imported from the organizer's list, mails
"Registrace zrušena" to people Squire has never written to (review of 2026-11-15, M1).
The same check guards the letter for cancelling one team.

The owner decided on 2026-11-16 that on a manual tournament an organizer's cancellation
mails nobody, imported and hand-entered alike.

## What Changes

- The letter for a cancelled registration and the letter for one cancelled team are not
  sent on a manual tournament, whatever the registration's origin or address.
- On a manual tournament, the cancellation dialog says nothing about mail and offers no
  note for the fencer, since nothing carries the note anywhere. The team-cancellation
  confirmation does not say the entering fencer is written to.
- Automatic tournaments are unchanged: a registration made in the application is mailed,
  and a hand entry or a registration with no address is not.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `registration`: "An organizer may cancel a registration": no mail on a manual
  tournament.
- `team-disciplines`: "Cancelling one team": no mail, and no promise of one in the
  confirmation, on a manual tournament.

## Impact

- `backend/app/emails.py`: `send_cancelled_by_organizer`, `send_team_cancelled`.
- `backend/app/routers/registrations.py`, `backend/app/routers/tournaments.py`: the
  callers, if the mode check lives there as it does for the substitution.
- `frontend/src/CancelRegistrationDialog.tsx` and the team-cancellation dialog in
  `TeamsPanel`: the mode decides whether the mail sentence and the note are shown.
- Tests in `test_organizer_cancel.py` and the team-cancellation tests.
