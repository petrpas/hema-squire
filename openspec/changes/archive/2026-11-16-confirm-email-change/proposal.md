## Why

Squire treats an account's address as proof of who it belongs to: team membership,
ownership transfer and the deployment Owner role are granted by address, and a password
reset goes to it. Changing the address on the Profile page, though, asks for neither the
current password nor proof that the new mailbox is the account holder's, and nobody is
told. That is the one place where an address reaches an account unverified, and so the
one place where those grants can be reached without the mailbox behind them.

Owner decision of 2026-11-16: an address change asks for the current password, is
confirmed by a link mailed to the new address, is announced to the old one, and ends the
account's other sessions.

## What Changes

- **BREAKING (API):** `PATCH /api/account` no longer accepts `email`. A request carrying
  it is refused, and the other fields in the same request are not applied.
- New `POST /api/account/email`: takes the current password and the new address,
  refuses a wrong password or an address another record holds, and mails a one-hour
  confirmation link to the new address. The address stays as it was until the link is
  followed. Rate-limited as the password change is.
- New confirmation: following the link sets the address, records it in the audit trail,
  ends every session signed in before it, signs the confirming browser in, and mails a
  notice to the old address.
- Profile page: the address is shown read-only, with a quiet "Change the address" link
  that opens a dialog, as the password change does. A new route in `routes.ts` receives
  the link.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `profile-page`: "Account information section" stops offering the address as an
  ordinary edit. A new requirement, "Address change", covers the dialog, the link, the
  confirmation, the notice and the sessions.
- `data-retention`: an expired address change is deleted with the other expired tokens.

## Impact

- Backend: `routers/accounts.py` (refusal in `update_account`, the request endpoint),
  the confirmation endpoint beside the password-reset ones, a `PendingEmailChange` model
  and Alembic migration, two new letters in `emails.py`, and `account_deletion.py`, which
  must remove a pending change with its account, and `retention.py`, which deletes an
  expired one.
- Frontend: `profile/AccountSection.tsx`, a new `profile/EmailChangeDialog.tsx`, a
  confirmation screen, `routes.ts`, `App.tsx`, `api.ts`, i18n in cs and en.
- Test helpers that change an address through `PATCH` move to the new flow, or write
  the model directly.
