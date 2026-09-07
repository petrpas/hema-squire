## Why

Squire polls Fio's REST API for a tournament's payments, gates the deposit payment
mode on a configured token, and offers a poll action in the intake panel — but no
screen has ever let an organizer record the token. `tournament-admin` already says
"the organizer records a bank feed token" and `payments-intake` already says "where
a token is configured", with nowhere to do either. The only way to configure one
today is a hand-written `PATCH` against the tournament, which is how every test in
the suite does it and is not something an organizer can do.

The account and the feed that reads it are one subject, so the control belongs on
the bank account the organizer has just typed — and only where that account is a Fio
one, since the token means nothing anywhere else.

## What Changes

- The bank account section on `PAYMENTS` gains a **set / reset feed token** action
  on the same line as the account field, right-aligned. It is available only while
  the typed account is a Fio account, and stated as unavailable otherwise, naming
  the reason.
- The action is decided from the value the organizer is *typing*, not from the saved
  one, so an account that has just become a Fio account enables it at once. Because
  the control shares the account's line, nothing on the page moves when it does.
- The action opens a small write-only form: a field for the token, a short note on
  making a **read-only** token in Fio internet banking, and a way to remove a token
  already recorded. The stored token is never shown — the server has never returned
  it and will not start.
- Recording a token verifies it against Fio before storing it. A token Fio rejects
  is refused at the field with a reason, so a mistyped token is not discovered weeks
  later by a scheduler sweep the organizer cannot see.
- The account section states whether a token is recorded, so the organizer can tell
  a configured feed from an unconfigured one without opening the form.

## Capabilities

### New Capabilities

None. Every behaviour this change touches is already owned by an existing spec.

### Modified Capabilities

- `tournament-admin`: the bank feed token becomes an organizer-editable setting with
  a stated place, a Fio-only availability rule, a write-only editing model, and
  verification on save. The spec currently names the token as a precondition of the
  deposit mode without saying where it is recorded.

`setup-navigation` is deliberately not modified: the token control sits inside the
bank account section, which that spec already allocates to `PAYMENTS`, and its "one
field, one editor" rule already covers a field that governs completeness. No section
is added, moved or split.

## Impact

- `backend/app/bank.py` — a token verification call against the Fio API.
- `backend/app/routers/tournaments.py` — a `PUT`/`DELETE` pair on
  `/{slug}/fio-token`, the one way a token is recorded or removed.
- `backend/app/schemas.py` — `fio_token` leaves `TournamentUpdate`; `TournamentOut`
  keeps returning only `fio_token_configured`.
- `backend/tests/` — the fourteen tests that set a token by `PATCH` move to the new
  endpoint against a stubbed Fio client.
- `frontend/src/accounts.ts` — a Fio test over either account form (bank code `2010`
  in CZ, `8330` in SK), the only copy of that knowledge.
- `frontend/src/setup/BankAccountSection.tsx` — the action on the account's line, and
  the form it opens (a new file under `frontend/src/setup/`).
- `frontend/src/i18n/{en,cs}.json` — the action, the form, the read-only-token advice,
  and the verification failure.
- No migration: `Tournament.fio_token` already exists.
