## Why

A fencer who forgets their password has no way back into their account. Squire offers no reset by e-mail, no password change on the Profile page and no administrative reset, so the account and every registration and payment under it are stranded. Asking the owner to edit the database is the only path. Nor can a fencer who suspects someone else knows their password change it: a session token stays valid for 14 days (`config.py` `token_ttl_hours`) and nothing can end it early.

`guest-registration` has just built what a reset needs: a public origin for links in mail (`public_base_url`), the mail-a-single-use-key pattern with only the key's hash stored (`PendingSignup`), and a screen that consumes a key from the URL fragment. Its design names password reset as an adjacent non-goal. This change takes it up.

## What Changes

- **"Forgot password" on the sign-in screen.** It turns the sign-in form, in place, into one asking for the account's e-mail. Submitting mails a link to that address and states that it was sent. Where the address holds no account (no record, a record without credentials, or a signup still pending), the screen says so plainly and offers account creation, since signup and `guest-check` already reveal whether an address has an account (owner decision 2026-10-25).
- **The reset link.** It opens a screen for the new password. Saving it sets the password, signs the fencer in on that browser and lands them on Fencer Home. A link works once, expires one hour after it was mailed, and a newer request replaces it. An expired or used link leads to a static statement offering a new request.
- **A password change signs out every other session** (owner decision). This applies to a reset and to a change on the Profile page. Tokens issued before the change stop being accepted; the browser that made the change keeps a fresh one.
- **Changing the password on the Profile page** (owner decision). This takes the current password and a new one, mails no link, and sends a notice to the account's address that the password was changed, because anyone holding a signed-in browser could make this change.
- The new-password forms declare themselves to password managers as the existing account forms do.

## Capabilities

### New Capabilities
- `password-reset`: the reset request, the mailed link, and the new-password screen; how an address without an account is answered; and what a password change does to existing sessions, whichever way it was made.

### Modified Capabilities
- `profile-page`: a new requirement covers the password change, a quiet link beside the Account heading that opens a dialog: the current password is required, a notice is mailed, and other sessions end. Made alongside: "HEMA Ratings section — bound state" makes the HRID itself the external link, replacing the separate "View profile on hemaratings.com" line.

## Impact

- **Depends on `guest-registration`**, for `public_base_url`, its startup refusal and the key-in-fragment screen pattern. It lands after it.
- **Backend.** A new `password_resets` table (one row per account: key hash, expiry) and a nullable `Fencer.sessions_valid_from`, in one Alembic revision. `auth.create_token` stamps `iat`, and `_presented_fencer` refuses a token issued before `sessions_valid_from`. `routers/auth.py` gains `POST /api/auth/password-reset` and `POST /api/auth/password-reset/confirm`, both rate-limited. `routers/accounts.py` gains `POST /api/account/password`. `emails.py` gains the reset mail and the password-changed notice, cs/en.
- **Frontend.** `Login.tsx` gains the "Forgot password" link. It gains a forgot mode beside account creation (`ForgotPassword.tsx`) and a reset screen routed in `App.tsx` from `routes.ts`, and a password-change link and dialog in the profile's Account section. `api.ts` adds the three calls, and i18n adds cs/en strings.
- **Tests.** Backend: link single-use, one-hour expiry and replacement; the no-account answer, including a passwordless record and a pending signup; old tokens refused after a reset and after a profile change while the new one works; wrong current password refused; notice mailed. Frontend: the request and reset screens, the dead-link statement, and the profile section.
- **Operational.** Every password change signs the account out everywhere else. Deploying the `iat` check does not sign anyone out, because `sessions_valid_from` starts empty.
