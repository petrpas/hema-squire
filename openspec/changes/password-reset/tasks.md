## 0. Precondition

- [x] 0.1 `guest-registration` is committed (its `public_base_url`, startup refusal and Alembic head are what this change builds on); rebase the revision below onto its head

## 1. Data

- [x] 1.1 `models.py`: `PasswordReset` (fencer_id unique FK, key_hash unique, created_at, expires_at) and nullable `Fencer.sessions_valid_from`, each with a comment pointing at design D1/D2
- [x] 1.2 Alembic revision creating `password_resets` and adding the nullable column, no backfill; downgrade drops both

## 2. Sessions (backend)

- [x] 2.1 `auth.create_token` stamps `iat` (integer seconds); `_presented_fencer` refuses `401 invalid_token` when `sessions_valid_from` is set and `iat` is missing or earlier
- [x] 2.2 `auth.set_password(session, fencer, password) -> str`: hash, watermark truncated to the second, `FencerProfileAudit` row `field="password"` with both values `None`, returns a fresh token (D3)
- [x] 2.3 Tests: a token issued before a change is refused and the returned one accepted; a pre-deploy token without `iat` still works while the watermark is empty; an untouched account keeps its sessions

## 3. Reset and change (backend)

- [x] 3.1 `POST /api/auth/password-reset`: `account_holding` → upsert row, 1 h key, commit, mail, `202 {email}`; else `404 no_account`; 3/minute
- [x] 3.2 `POST /api/auth/password-reset/inspect` (`{email}` or `410 reset_invalid`, consumes nothing) and `/confirm` (min length via `constraints.PASSWORD_MIN_LENGTH`, `set_password`, delete row, `TokenOut`); both 10/minute
- [x] 3.3 `POST /api/account/password`: verify current (`403 wrong_password`), `set_password`, commit, mail the notice, `TokenOut`
- [x] 3.4 `emails.py`: `send_password_reset` (`{public_base_url}/reset#<key>`) and `send_password_changed`, in `fencer.language`; cs/en strings in `locales/`
- [x] 3.5 Tests: request mails a link and the old password still works; no-account answer for an unknown address, a passwordless record and a pending signup, with no mail; link single-use, refused at 61 min, replaced by a newer request; too-short password leaves the link usable; reset signs out a second session and the returned token works; profile change with a wrong current password changes nothing and mails nothing; a right one mails the notice and signs out the other session
- [x] 3.6 `uv run ruff check .` and `uv run basedpyright` clean

## 4. Frontend

- [x] 4.1 `routes.ts`: `resetPassword(key)`; `App.tsx` route for `reset` (forgot password is a `LoginMode`, design D6)
- [x] 4.2 `api.ts`: `requestPasswordReset`, `inspectPasswordReset`, `confirmPasswordReset`, `changePassword`
- [x] 4.3 `Login.tsx`: tertiary "Forgot password" link opening the `forgot` mode with the typed address
- [x] 4.4 `ForgotPassword.tsx`: own form `id`, e-mail field as `username`, static sent statement with the address and the hour, no-account statement with Create account
- [x] 4.5 `ResetPassword.tsx`: key from the hash, inspect on mount, read-only `username` + `new-password` form, store token and `navigate(home(), { replace: true })`, static dead-link statement with a new-request action
- [x] 4.6 Split `ProfilePage.tsx` into `frontend/src/profile/` one section per file, thin orchestrator; add `PasswordDialog.tsx` (`Modal`, opened from a link beside the Account heading; `current-password`, `new-password`, own form `id`, replaces the stored token, static outcome line, `wrong_password` stated in place)
- [x] 4.7 i18n cs/en per design D7 once the owner has confirmed the copy; sentence case, no exclamation marks
- [x] 4.8 Tests: Forgot password carries the address; sent and no-account statements; reset screen shows the dead-link statement on 410 without a form; successful reset stores the token and lands home; profile section refuses a wrong current password in place
- [x] 4.9 `npm run typecheck`, `npm run check`, `npm test` clean

## 5. Close-out

- [ ] 5.1 Walk request → mail (outbox) → reset → home, and the profile change with a second signed-in browser, on a phone width and at desktop; check the password manager offers to update the credential in Chrome and Safari
- [ ] 5.2 Settle the open questions in design.md with the owner before archiving
