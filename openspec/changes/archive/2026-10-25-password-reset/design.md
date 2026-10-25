## Context

A password is set in exactly one place today: signup. Since `guest-registration`, that means verification, which copies `PendingSignup.password_hash` onto a `Fencer`. Nothing changes a password afterwards. `auth.create_token` issues an HS256 JWT holding `sub` and `exp` (14 days, `settings.token_ttl_hours`). `_presented_fencer` decodes the token and loads the fencer. There is no server-side session, so nothing can end a session before `exp`.

`guest-registration` (in progress, backend tasks 1–2 done) supplies the pieces this change reuses:

- `settings.public_base_url`, and the startup refusal of real SMTP without it.
- The pattern from `routers/auth.py`: a `secrets.token_urlsafe(32)` key, its SHA-256 in the database (`_key_hash`), an expiry checked through `_aware`, one row per address with the latest winning (`_issue_key`), and the key carried in the URL fragment.
- `account_holding(session, email)`, which defines "an address with an account" as a record holding the address *and* credentials.
- `audit_change` in `routers/accounts.py`.

Owner decisions (2026-10-25):

- A password change signs out every other session.
- An address without an account is answered as such, not with a uniform "if it exists, we sent it".
- The link lives for one hour.
- A password change on the Profile page is part of this change, and mails a notice.

## Goals / Non-Goals

**Goals:**
- A fencer who forgot their password regains the account through their mailbox alone.
- A fencer who suspects their password is known can change it and end every other session.
- No session is ended by deploying this change.

**Non-Goals:**
- An administrative password reset. The Admin manages roles and HR bindings, and a reset an Admin could trigger would hand them the account. The mailed link already serves every account that has its mailbox.
- Changing the account's e-mail address.
- A "sign out everywhere" action separate from a password change.
- A notice mail after a reset. The reset was itself proven through that mailbox, so a notice would tell its reader only what they just did.
- Turning a record without credentials into an account through reset. Verified signup already does that and collects the name and language a reset would not.

## Decisions

**D1. Reset keys are their own table, one row per account.** `PasswordReset`: `fencer_id` (unique FK), `key_hash` (unique, 64), `created_at`, `expires_at` (+1 h). A request upserts the row and issues a fresh key, so the latest request wins and the earlier link stops working. Confirm looks the row up by hash, refuses a missing or expired row with `410 reset_invalid`, sets the password and deletes the row. A row is created only for an `account_holding` fencer.
*Alternative:* derive the key, as `managekey` does, as an HMAC over `(fencer.id, expiry, password_hash)`. It needs no table, and it is single-use because the password hash changes. Rejected: it cannot honour "the latest request wins", since every unexpired link would stay valid until one was used. The manage key needed derivation because later mails must carry it again. A reset key is mailed exactly once, so the stored-hash pattern from `PendingSignup` fits, and keeping the two key kinds on separate patterns is clearer.
*Alternative:* two columns on `fencers`. Rejected: it keeps a transient secret on the identity row that every fencer query loads.

**D2. Sessions end through a watermark, not a session table.** A nullable `Fencer.sessions_valid_from: Mapped[datetime | None]` is added. `create_token` adds `iat` (integer seconds). `_presented_fencer`, after loading the fencer, refuses with `401 invalid_token` when `sessions_valid_from` is set and the token's `iat` is missing or earlier than it. A password change, by either path, sets `sessions_valid_from = now` truncated to whole seconds and then issues the new token, whose `iat` is the same second or later, so it passes. `None` means "never changed", so no existing token is touched (spec: deploying signs nobody out). A token without `iat` is accepted only while the watermark is `None`, which covers tokens issued before this deploy.
The refusal reuses `invalid_token`, so `RequireAuth`'s existing 401 handling shows sign-in at the current URL with no new frontend branch.
*Alternative:* a token generation counter stored on the fencer and embedded in the JWT. This is equivalent, but it needs a backfill to `0` and a claim on every token. The timestamp also answers "since when", which is useful in the audit trail.
*Trade-off:* two changes within the same second on two devices both survive. This is not reachable by a person.

**D3. One function changes a password.** `auth.set_password(session, fencer, password) -> str` sets the hash, sets the watermark, writes a `FencerProfileAudit` row with `field="password"` and `old_value`/`new_value` both `None`, and returns a new token. Both the reset confirm and the profile change call it, so neither path can forget the watermark. `audit_change` is not used here, because it would write the hash into the trail.

**D4. Endpoints.**
- `POST /api/auth/password-reset {email}`, `@limiter.limit("3/minute")`. If `account_holding` finds an account, upsert the row, commit, mail it, and return `202 {email}`. Otherwise return `404 no_account`. A record without credentials and a pending signup both come out as `no_account`, because `account_holding` already excludes them.
- `POST /api/auth/password-reset/inspect {key}` returns `{email}` for a live key, or `410 reset_invalid`, and consumes nothing (D6).
- `POST /api/auth/password-reset/confirm {key, password}`, where `password` uses `Field(min_length=constraints.PASSWORD_MIN_LENGTH)`, and `@limiter.limit("10/minute")` as `verify` has. Too short a password is a 422 that consumes nothing (spec: the link remains usable). On success it returns `TokenOut`.
- `POST /api/account/password {current_password, new_password}`, which needs a bearer account. A wrong current password returns `403 wrong_password`, not 401, so the frontend does not read it as a lost session. On success it returns `TokenOut` and mails the notice after commit.

**D5. Mails.** `emails.send_password_reset(mailer, fencer, key)` sends `{public_base_url}/reset#<key>`. `emails.send_password_changed(mailer, fencer)` names Forgot password, without a link, since the sign-in screen is where it lives. Both are written in `fencer.language`, as the verification mail is, because no tournament's communication language applies. Both go to `fencer.email` directly: an account always holds an address, and `recipient()` is about registrations.

**D6. Frontend.** `routes.ts` gains `resetPassword(key)` → `/reset#key`, routed in `App.tsx` as a public screen beside `/verify`.
- Forgot password is a `LoginMode` (`"forgot"`), not a route. Sign-in renders in place, either over the page that raised it (`FencerLayout`'s prompt) or at a gated URL (`RequireAuth`). Navigating away from it would leave the prompt standing over the new route, or lose the gated destination. Account creation is a mode for the same reason. `Login.tsx` shows a tertiary "Forgot password" link under the password field. The typed address carries over in component state, so it never enters a URL.
- `ForgotPassword.tsx`, rendered by `Login` in that mode, holds its own `<form id="forgot-password">` with an `email` field (`autocomplete="username"`). After submitting, it shows the static "link sent to <address>, it works for one hour" statement. On `no_account` it shows the statement with a Create account action.
- `ResetPassword.tsx` reads the key from `location.hash`. On mount it posts the key to `POST /api/auth/password-reset/inspect {key}`, which returns `{email}` without consuming the key, or `410 reset_invalid`. That lets a dead link be stated before anyone types a password. It then shows `<form id="reset-password">`, holding a read-only `username` field filled with that address and a `new-password` field. A password manager needs the identifier inside the submitted form to offer to update the right credential (spec). On success the screen stores the token and navigates to `home()` with `replace`. On `410` at either step it shows the static dead-link statement. Its new-request action opens sign-in in the forgot mode through the layout's `onSignIn`.
  `inspect` takes the key in a POST body, never in a query string, so the key stays out of access logs, as the fragment already keeps it out of the request line. It shares confirm's rate limit.
- `ProfilePage.tsx` is already 320 lines. Following the frontend convention, it is split into `frontend/src/profile/` with one file per section, and `PasswordDialog.tsx` (a `Modal`) holds `<form id="change-password">` with `current-password` and `new-password` fields. It opens from a `link-button` in the Account section's `rail-card-heading`, to the right of the heading: hardly anyone uses it, and fields rendered on the page were autofilled by password managers on every visit. On success it replaces the stored token, closes, and the section states the change in static text.
All copy is sentence case, with no exclamation marks.

**D7. Copy (proposed, for review).** "Zapomenuté heslo" / "Forgot password". The request heading is "Obnovení hesla" / "Reset your password". Sent: "Odkaz jsme poslali na {email}. Platí jednu hodinu." / "We sent a link to {email}. It works for one hour." No account: "Na této adrese účet není." / "No account uses this address." Dead link: "Tento odkaz už neplatí." / "This link is no longer valid." Profile section: "Heslo" / "Password". Changed: "Heslo je změněné. Ostatní přihlášení byla ukončena." / "Password changed. Other sessions were signed out."

## Risks / Trade-offs

- [Anyone can trigger a reset mail to someone's address] → It changes nothing until the link is followed (spec), it is rate-limited, and the mail says to ignore it if unrequested.
- [A reset depends on mail delivery] → It is the same dependency verified signup already introduced, and the deploy checklist already round-trips a mailed link.
- [The `no_account` answer confirms which addresses have accounts] → Signup's `409` and `guest-check` already do, and the owner chose clarity. The endpoint is rate-limited like signup.
- [A stolen session can change the password and lock the owner out] → It needs the current password, and the notice goes to the account's address, which the thief does not control, so the owner can reset back.
- [The `sessions_valid_from` check adds one comparison to every authenticated request] → The fencer row is already loaded there, so it costs no extra query.

## Migration Plan

One Alembic revision, after `guest-registration`'s, creates `password_resets` and adds the nullable `fencers.sessions_valid_from` with no backfill. Downgrade drops both. Deploy needs nothing new, because `public_base_url` is already required. Rollback: the old image ignores both, and any password changed in between stays changed, since the hash column is shared.

## Open Questions

- The Czech and English copy in D7 is proposed and should be confirmed before the i18n strings are written.
- Whether iCloud Keychain and Google Password Manager actually offer the update from the reset form (D6). This is checked by hand during the close-out walk; it cannot be tested automatically.
