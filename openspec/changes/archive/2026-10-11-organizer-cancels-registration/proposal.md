## Why

An organizer has no way to cancel a registration. Only the fencer can do that. The
one tool the organizer has is **Smazat**, a reversible rule that takes a row out of
the tables and leaves the registration behind it untouched. That registration still
holds its seat. On an automatic tournament it also keeps receiving reminders and the
expiry notice, and a payment quoting its variable symbol is still credited to it.
All of this happens in a registration the Payments phase no longer lists.
`public-entrant-lists` stopped counting such rows on the public pages, but only as a
display rule, and left the seat itself to this change.

## What Changes

- **Smazat is for rows without a live registration.** On a row standing for a live
  registration, it is no longer offered, and the server refuses it. Import noise,
  duplicates, hand rows not yet issued, and expired registrations can still be
  deleted and restored as before.
- **A new organizer action, Zrušit registraci**, takes the place of Smazat on such a
  row, on the fencer list. It is confirmed and irreversible. It does to the
  registration exactly what the fencer's own cancellation does: the state becomes
  cancelled, the seat is freed, the clocks stop, and where money was credited the
  refund state is recorded as it is for the fencer. Nobody is promoted
  automatically: as today, the organizer promotes from the queue by hand.
- **The fencer is told by mail**, under the rule every organizer action on a seat
  already follows (a substitution's mail is the model): a registration entered by
  hand is sent nothing, and a registration with no address is sent nothing. The
  organizer may add a short note to the mail.
- **Manual mode works the same way.** A cancelled registration issued from an
  imported row SHALL NOT bring that row back as a fresh, unissued row, so the next
  issuing pass cannot recreate the person the organizer just cancelled.
- **Rows already deleted while holding a live registration are left as they are.**
  No migration. The organizer can restore such a row and cancel the registration.

## Capabilities

### New Capabilities
<!-- none -->

### Modified Capabilities
- `registration`: a new requirement that an organizer may cancel a registration,
  with the same effect as the fencer's own cancellation, plus a mail.
- `etl-console`: **Reversible row deletion** no longer applies to a row standing for
  a live registration. That row offers Zrušit registraci instead.
- `imported-registrations`: a cancelled issued registration keeps its source row out
  of the fencer list and out of issuing.
- `public-entrants`: the count's accepted gap now concerns only rows deleted before
  this change.

## Impact

- **Backend**: a cancellation helper shared by `my-registration/cancel` and a new
  `POST /api/tournaments/{slug}/registrations/{id}/cancel` (console access,
  published only). `rules.create_rule` refuses `row_delete` on a live registration's
  row. `emails.send_cancelled_by_organizer`, with cs/en catalog strings.
  `sheet.base_rows` keeps a cancelled registration's source row out.
- **Frontend**: `SheetArea`/`Console` row actions offer Zrušit in place of Smazat on
  a live registration's row, through a `Modal` with an optional note. i18n cs/en.
- **Tests**: the refusal, the cancellation's effects (seat, clocks, refund state,
  mail and its suppression), the manual-mode source row, and the UI's action
  choice.
