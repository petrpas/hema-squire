## 1. Model

- [x] 1.1 `PendingEmailChange` model (fencer_id unique, new_email, key_hash unique, created_at) and an Alembic migration
- [x] 1.2 `account_deletion` removes a pending change with its account; the column inventory test covers the new table; `retention` deletes an expired one

## 2. Backend

- [x] 2.1 `update_account` refuses `email` with 422 `email_change_needs_confirmation` and applies nothing
- [x] 2.2 `POST /api/account/email` (5/minute): verifies the current password (403 `wrong_password`), refuses an unchanged address and one any other fencer record holds (409), replaces any pending row, and mails the link to the new address
- [x] 2.3 Inspect and confirm endpoints beside the reset ones (10/minute): an unknown, used or expired key answers as a reset's does; a key whose address was taken meanwhile answers 409 `email_taken` and changes nothing
- [x] 2.4 Confirmation: set the address, audit old → new, end every earlier session through a helper shared with `set_password`, delete the pending row, return a token, and mail the notice to the old address
- [x] 2.5 Letters `send_email_change_link` and `send_email_changed_notice`, cs and en, the notice naming the new address and the privacy contact
- [x] 2.6 Tests: each scenario of "Address change", plus the refused PATCH; move test helpers that set an address through PATCH

## 3. Frontend

- [x] 3.1 `api.ts`: `requestEmailChange`, `inspectEmailChange`, `confirmEmailChange`; drop `email` from `updateAccount`
- [x] 3.2 `AccountSection`: address read-only, with a "Change the address" quiet link; `EmailChangeDialog` (current password, new address, static sent state); password-manager attributes as in `PasswordDialog`
- [x] 3.3 `routes.ts` `confirmEmail(key)` and a route in `App.tsx`; a confirmation screen that confirms, stores the token and states the outcome, with static statements for a dead link and a taken address
- [x] 3.4 i18n cs and en, sentence case, no exclamation marks
- [x] 3.5 Component tests for the dialog and the confirmation screen

## 4. Checks and rollout

- [x] 4.1 `uv run ruff check .`, `uv run basedpyright`, scoped pytest; `npm run typecheck`, `npm run check`, scoped vitest
- [x] 4.2 Commit the proposal together with the implementation, not before: until it ships, the repository should not describe the gap
