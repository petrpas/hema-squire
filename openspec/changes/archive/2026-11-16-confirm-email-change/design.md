## Context

`update_account` writes `email` after checking only that no other account holds it.
Signup verifies the address by link (`PendingSignup`), and a password reset mails a
hashed, single-use one-hour key (`PasswordReset`, spec `password-reset`). The Profile
password change asks for the current password, ends other sessions through
`set_password`'s `sessions_valid_from` watermark, and mails a notice. An address change
should take the same path.

## Goals / Non-Goals

**Goals:**
- No address reaches an account without the current password and without the new
  mailbox following a link.
- The old address hears of the change, and other sessions end.

**Non-Goals:**
- Storing the deployment Owner by id instead of by address. Once an address needs
  confirmation, the configured address can no longer be claimed without its mailbox.
- Attaching guest registrations or imported records that carry the new address. The
  address change attaches nothing, as before.
- Changing how team membership or ownership transfer look an address up.

## Decisions

**D1. A `PendingEmailChange` row per account, modelled on `PasswordReset`.** It holds
`fencer_id` (unique), `new_email`, `key_hash` (SHA-256, unique) and `created_at`. A new
request replaces the row, so only the latest link works. The key travels in the URL
fragment, as a reset's does. *Alternative:* reusing `PasswordReset` with a kind column.
Rejected because the two links do different things and expire independently, and one
row per account per kind is simpler as two tables.

**D2. Where the request is checked.** The current password must verify (403
`wrong_password`, as the password change answers). The new address must differ from the
current one and must not be held by any other fencer record (409
`email_already_registered`), as `update_account` already requires. `fencers.email` is
unique, so a record without credentials holding the address, such as a guest or a roster
entry, blocks the change as an account would. Owner decision 2026-11-16: such a change is
refused, not merged. Merging two records is left for a later change, if one is ever
needed. The check runs again at confirmation, since a record may have taken the address
in the meantime; the link then leads to a statement that the address is taken, and
nothing changes.

**D3. Confirmation ends every session, signs the confirming browser in, and notifies.**
The confirmation endpoint bumps `sessions_valid_from` through one helper shared with
`set_password`, returns a fresh token, writes the audit entry
(`field="email"`, old → new), deletes the pending row, and mails the notice to the old
address in the account's language. The notice names the new address and says that
anyone who did not make the change should write to the operator's contact, since a reset
would now go to the new address. The browser that asked may be a different one from the
browser that confirms; signing in the confirming browser matches what a reset does.

**D4. `PATCH /api/account` refuses `email` outright (422 `email_change_needs_confirmation`)
rather than ignoring it.** A client sending it would otherwise believe it had saved. The
frontend stops sending it.

**D5. Rate limits.** The request uses `5/minute`, like the password change, because it
checks the password. The confirmation uses `10/minute`, like a reset confirmation.

## Risks / Trade-offs

- [The old mailbox is lost and the account holder did not make the change] → The notice
  names the operator's contact. Restoring the account is a manual operator step and is
  out of scope.
- [The owner's own address change moves the Owner role] → It already works this way
  (`is_deployment_owner` compares addresses), and the confirmation now proves the new
  mailbox. The one account concerned is the operator's, who also sets
  `HEMA_SQUIRE_OWNER_EMAIL`, so the dialog carries no extra warning for it.

## Migration Plan

One Alembic migration creates `pending_email_changes`. Existing accounts are untouched,
and no session is ended by deploying.
