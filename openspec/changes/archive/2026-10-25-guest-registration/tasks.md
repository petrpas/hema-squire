## 1. Data and settings

- [x] 1.1 `models.py`: `PendingSignup` (email unique, password_hash, display_name, hr_id, club, language, return_to, key_hash, created_at, expires_at) and `Registration.manage_key_generation: Mapped[int | None]`, each with a comment pointing at design D4/D9
- [x] 1.2 Alembic revision creating `pending_signups` and adding the nullable column; downgrade drops both
- [x] 1.3 `config.py`: `public_base_url`; `main.py` refuses to start with `smtp_host` set and `public_base_url` empty, beside the dev-secret refusal

## 2. Verified signup (backend)

- [x] 2.1 `routers/auth.py` signup: 409 only for an address held by a `Fencer` with a password; upsert the pending row (latest wins), mail the verification link, return 202
- [x] 2.2 `POST /api/auth/verify`: hash lookup, 48 h expiry, single use → `410 verification_invalid`; create the account or take over the passwordless record (password, language, name; HR kept if set, else applied; `FencerProfileAudit` per changed field; null `manage_key_generation` on its registrations); return token and `return_to`
- [x] 2.3 `POST /login`: `403 email_not_verified` only when a pending row matches and its password verifies; `POST /api/auth/resend-verification` with the same proof, rate-limited 3/minute
- [x] 2.4 `emails.py`: the localized verification mail (cs/en) carrying `{public_base_url}/verify#<key>`; `return_to` validated as a relative path
- [x] 2.5 Update `conftest.auth_headers` to sign up through the mailbox and verify, so every existing test still gets an account
- [x] 2.6 Tests: pending cannot sign in and is told so; resend replaces the key; link single-use and expired at 49 h; latest signup wins; takeover of a roster-issued record keeps its id, registrations and HR binding; a contact-address-only registration is not taken over; account address still 409
- [x] 2.7 `uv run ruff check .` and `uv run basedpyright` clean

## 3. Guest registration (backend)

- [x] 3.1 Factor `register`'s body into one placement core taking `(tournament, fencer, data, contact_email)`; `register` calls it unchanged in behaviour
- [x] 3.2 `guests.resolve`: the five-step order of design D3, with `name_key`, raising `email_has_account` / `already_registered`
- [x] 3.3 `POST /api/auth/guest-check` (204 / 409, rate-limited) and `POST /api/tournaments/{slug}/guest-register` (rate-limited 3/minute) setting `manage_key_generation = 1` and returning `{registration, manage_key}`
- [x] 3.4 Manage key: derive and verify per D4 (`hmac.compare_digest`, one `404 manage_key_invalid` for every refusal)
- [x] 3.5 `managed_registration` dependency (D5); switch all `my-registration` endpoints to it; ledger actor `guest:<id>` for guest actions
- [x] 3.6 `emails.manage_link` and a single footer helper used by every send; link only where the generation is set
- [x] 3.7 `substitution.py`: bump the generation when `recipient()` changes, before composing the substitute's message
- [x] 3.8 Tests: a guest registration is placed, priced, windowed and mailed like an account's; parent with two children (address on first record, contact address on second, both links to one address); the same child twice refused; returning guest reuses the record; account address refused at check and at submit; a key opens its registration and is refused for another registration, another tournament and account-only endpoints; every guest send carries the link and no account send does; substitution to a new address kills the old key and mails a working one; keeping the address keeps the key; takeover kills the key; amendment window still binds through the link
- [x] 3.9 `uv run ruff check .` and `uv run basedpyright` clean
- [x] 3.10 Organizer resend (D12): `POST …/registrations/{id}/manage-link`, `emails.send_manage_link`, `guest` on the sheet row, tests
- [x] 3.11 Manage-key reads state the guest's `language` (D13)

## 4. Frontend

- [x] 4.1 `routes.ts`: `manage(slug, key)` and `verify(key)`; `App.tsx` routes for `t/:slug/manage` and `verify`
- [x] 4.2 `api.ts`: `guestCheck`, `guestRegister`, `verify`, `resendVerification`; optional manage key on the six `my-registration` calls sent as `X-Manage-Key`; signup handles 202
- [x] 4.3 `Login.tsx`: the "Register without signing up" entry when raised by Register (not on gated URLs); replace the needs-an-account line; on `email_not_verified` the static statement and the resend action
- [x] 4.4 `SignupForm.tsx`: `variant` prop — guest heading/subtitle, no password field, own form `id`, e-mail autocomplete `email`; account variant shows "link sent" on 202. Split along component seams if it passes ~300 lines
- [x] 4.5 `FencerLayout` holds the guest identity in the outlet context; the registration form states "registering without an account as …" with a change action, and submits through `guestRegister`, then `navigate(manage(slug, key), { replace: true })`; `email_has_account` / `already_registered` refusals stated in place
- [x] 4.6 Manage screen: `TournamentDetail` reads the key from the hash, opens the registration tab with the management view, shell anonymous; the static dead-link statement on `manage_key_invalid`
- [x] 4.7 Verify screen: posts the key, stores the token, lands on `return_to` or `home()`; static invalid-link statement offering sign-in and account creation
- [x] 4.8 i18n cs/en for every new string, sentence case, per design D11 once the owner has confirmed the copy
- [x] 4.9 Tests: both entries open one form differing only in heading and password; guest identity returns to the checklist with nothing posted; manage screen renders the registration anonymously; dead link statement; verify lands on the return path
- [x] 4.11 Console: mail icon on a guest row of the fencer list (automatic tournaments only), `ResendManageLinkDialog` asking then stating "sent"; manage screen switches to the stated language
- [x] 4.10 `npm run typecheck`, `npm run check`, `npm test` clean

## 5. Close-out

- [ ] 5.1 Walk the guest flow and the signup verification in the running app (outbox mails), on a phone width and at desktop
- [x] 5.2 Settle the open questions in design.md with the owner before archiving
