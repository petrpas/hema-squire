## Context

`POST /api/tournaments/{slug}/register` (`backend/app/routers/registrations.py:420`) takes `FencerDep`, the bearer account, and so do the `my-registration` family: read, amend, amend preview, payment instructions, cancel and the team roster `PUT`. They all find the registration by `(tournament, fencer)` through `get_my_registration`.

Passwordless fencer records already exist. They are created by issuing (`issuing._resolve_fencer`), by hand entry and by substitution. `issuing._resolve_fencer` already has the identity rule this change needs: reuse a record holding the address only where `name_key` agrees, otherwise create a record without an address. `Registration.contact_email` and `emails.recipient()` already route every send to a seat's own address. No message contains a URL today, and there is no setting naming the public origin.

Signup (`routers/auth.py`) creates the `Fencer` and returns a JWT at once. It refuses any address a `Fencer` holds, passwordless or not. A throwaway test confirmed the `409` against the `fencer-accounts` scenario "Signing up afterwards is not obstructed".

Owner decisions (2026-10-25):

- Register opens sign-in, offering "Create account" and "Register without signing up". Both open the same form; the guest variant has its own heading and no password.
- Always available on every automatic tournament with registration open. There is no Setup toggle.
- An address belonging to an account is refused for a guest, with sign-in offered.
- The manage link goes in guest mail only.
- There is no self-service resend of the manage link; the organizer helps, with a console action that sends it again (decided 2026-10-25, D12).
- Several people may be entered from one address, through the contact address.
- Account creation verifies the address. Guest entries do not. Existing accounts count as verified.

## Goals / Non-Goals

**Goals:**
- A guest registration that is lifecycle-identical to an account's, reached from the existing sign-in screen and form.
- One management surface for both: the `my-registration` endpoints and the detail page's management view, resolved from either credential.
- Mailed links that work on any device, are revocable, and leak nowhere.
- Verified signup, with takeover of a passwordless record on the verified address. This also fixes today's 409 for roster-enrolled fencers.

**Non-Goals:**
- No guest flow on manual tournaments: in-app registration never opens there (`tournament-mode`).
- No self-service resend (owner decision). The organizer's resend is D12.
- No merging of a guest's address-less record into a later account (the parent/child case). `fencer-accounts` leaves reconciliation unaddressed.
- No password reset. It is adjacent, since it reuses the mail-a-key machinery, but it was not asked for.
- No change to the console beyond what the data already shows.

## Decisions

**D1. The guest identity travels with the submission; nothing is created at form 1b.** `SignupForm` gains a `variant: "account" | "guest"` prop. The guest variant's submit calls `POST /api/auth/guest-check` with `{email}`, which answers `204` or `409 email_has_account`. It then hands `{email, display_name, hr_id, club, language}` up to `FencerLayout`, which holds it in React state in the outlet context, just as it holds the sign-in resume target, and returns to the registration tab. `TournamentFace` submits to `POST /api/tournaments/{slug}/guest-register` with `RegisterIn` plus a `guest` object.
*Alternative:* create the passwordless record at form 1b and hand back a short-lived guest token. Rejected: it leaves orphan records for every abandoned form, and it needs a third kind of credential.
*Trade-off:* a refresh between form 1b and submit loses the held identity, and the visitor fills in the short form again. This is accepted; nothing about it is persistent state.

**D2. One placement core, two entry points.** The body of `register` from the availability check to `rownumbers.allocate` is moved into `registration_core.create(session, tournament, fencer, data, *, contact_email)`, so the two routes cannot drift. `guest-register` resolves the fencer first, then calls it. Both routes commit and mail the same way. `guest-register` carries `@limiter.limit("3/minute")`, matching signup.

**D3. Guest identity resolution is its own function beside issuing's.** `guests.resolve(session, tournament, email, name, hr_id) -> (Fencer, contact_email | None)` applies the `guest-registration` order:

1. If a `Fencer` holds the address and has a `password_hash`, raise `409 email_has_account`.
2. If a passwordless record holds the address and `name_key` agrees, use it.
3. If a live registration on this tournament carries `contact_email == email` and its fencer's `name_key` agrees, raise `409 already_registered`.
4. If the address is held by a record naming somebody else, or in use as a contact address here, create a new record with no address and return the address as `contact_email`.
5. Otherwise, create a new record holding the address and bound to `hr_id` if given.

The "already registered" check for case 2 is the core's existing `(tournament, fencer)` check. It reuses the cancelled or expired row exactly as today. `name_key` is imported from where issuing takes it. The logic is not shared with `issuing._resolve_fencer`, because issuing's per-pass `claimed` set and its HR-verdict rule have no counterpart here. The two read alike on purpose.

**D4. The manage key is derived, not stored.** A mail must carry the key long after the registration was created: the scheduler's reminder runs days later. A hashed key cannot be mailed again, and a plaintext key in the database is a password column. So the key is `"{registration.id}.{mac}"`, where `mac = urlsafe_b64(HMAC-SHA256(settings.secret_key, f"manage|{id}|{generation}"))[:32]`. `Registration.manage_key_generation: Mapped[int | None]`: `None` means "not a guest registration, there is no link". The guest core sets it to `1`. Rotating increments it, and the takeover sets it to `None`. Verification parses the id, loads the registration, recomputes and compares with `hmac.compare_digest`. A missing registration, a `None` generation and a bad mac all raise the same `404 manage_key_invalid` (spec: the refusal does not reveal which registrations exist).
*Alternative:* store a random token and its hash, and mail the token only at creation. Rejected: later messages would have no link to carry.
*Trade-off:* rotating `secret_key` kills every manage link, exactly as it kills every session. A deployment that rotates it should say so.

**D5. One dependency resolves the registration being managed.** `ManagedRegistration = Annotated[Registration, Depends(managed_registration)]`. It reads the `X-Manage-Key` header first: if present, the key must name a registration of *this* tournament, otherwise `404 manage_key_invalid`. Otherwise it requires the bearer account and uses `get_my_registration`. Every `my-registration` endpoint switches from `FencerDep` plus `get_my_registration` to it. The ledger actor label for a guest action is `guest:<registration id>`, so a guest's amendment or cancellation is attributed in the journal. The URL paths stay `my-registration`; "my" is the bond the request presents.

**D6. Which messages carry the link.** `emails.manage_link(registration) -> str | None` returns `f"{settings.public_base_url}/t/{slug}/manage#{key}"` when `manage_key_generation is not None`, else `None`. Every send composes its footer through one helper that appends the link line when one exists. This is the same "one function because a fifteenth send will be added" reasoning as `recipient()`. A new setting `public_base_url` (`HEMA_SQUIRE_PUBLIC_BASE_URL`) is required whenever mail is real: startup refuses an SMTP configuration without it, as it refuses the dev secret. In dev it defaults to the Vite origin.

**D7. Rotation points.** `substitution.py` increments the generation when `recipient()` before and after the substitution differ, before composing the substitute's message, so the new link is what it carries. The verification takeover (D9) sets the generation to `None` on every registration the taken-over record holds. Cancellation does nothing to it.

**D8. Frontend manage route.** `routes.ts` gains `manage(slug, key)` and `verify(key)`. The `App.tsx` route `t/:slug/manage` renders `TournamentDetail` with `manageKey` read from `location.hash`, on the registration tab. `api.ts` takes an optional key on the six `my-registration` calls and sends it as `X-Manage-Key`. On `404 manage_key_invalid`, the registration tab renders the static dead-link statement. Successful `guest-register` responds with `{registration, manage_key}`, and the page `navigate(manage(slug, key), { replace: true })`. The key is never written to `localStorage`; it lives in the URL the guest bookmarked or was mailed.

**D9. Pending signups are their own table; a `Fencer` is always a verified account or a record.** `PendingSignup`: `email` (unique), `password_hash`, `display_name`, `hr_id`, `club`, `language`, `return_to` (a relative path, validated as starting with `/` and not `//`), `key_hash` (SHA-256 of a `secrets.token_urlsafe(32)`), `created_at`, `expires_at` (+48 h).

- `POST /signup`: refuse `409 email_already_registered` if a `Fencer` with a `password_hash` holds the address. Otherwise upsert the pending row (latest wins), mail the link and return `202 {pending: true}`.
- `POST /verify {key}`: look up by hash. Missing or expired → `410 verification_invalid`. Then:
  - If a passwordless `Fencer` holds the address, set its password, language and display name, keep its `hr_id` if set (else apply the pending one), write `FencerProfileAudit` rows for each changed field, and null the generation on its registrations.
  - Else if an account appeared on that address meanwhile, return `410`.
  - Else create the `Fencer`.

  Delete the pending row and return `TokenOut` plus `return_to`.
- `POST /login`: if no `Fencer` matches, but a pending row does and its password verifies, return `403 email_not_verified`. A wrong password on a pending address stays `401 invalid_credentials`, so the pending state is shown only to whoever knows the password.
- `POST /resend-verification {email, password}`: the same password proof; issue a fresh key and mail it. `@limiter.limit("3/minute")`.

No column on `fencers` and no migration of accounts: every existing `Fencer` with a password is, by construction, verified.
*Alternative:* an `email_verified_at` column on `fencers`. Rejected: an unverified `Fencer` would be a third kind of record that every query touching fencers (familiar faces, matching, admin list) must remember to exclude.

**D10. Signup's frontend outcome.** `SignupForm` (account variant), on `202`, replaces the form with the static "link sent to <address>" statement. `/verify#key` posts the key, stores the token, and navigates to `return_to` (or `home()`). `Login` on `403 email_not_verified` shows the statement and a tertiary "send the link again" action. The resume target that sign-in keeps today becomes the signup's `return_to`, so verification on another device still lands on the tournament.

**D11. Copy.** "Registrovat bez účtu" / "Register without signing up". The guest form's heading is "Registrace bez účtu", with the subtitle "Stejné údaje, jen bez hesla. Přihlášku pak upravíte přes odkaz v e-mailu." English: "Registering without an account" / "The same details, without a password. You manage your registration through the link in your e-mail." Sentence case, no exclamation marks. The owner's working titles were "Register without Sign up" and "The same minus password"; this is that wording, as polished copy for review.

**D12. The organizer sends a lost link again.** `POST /api/tournaments/{slug}/registrations/{id}/manage-link`, behind console access, mails `emails.send_manage_link`: a short letter whose link is `_letter`'s own footer. It sends the *current* key rather than rotating it, so a guest who finds the first mail after all is not left with a dead link; rotation stays tied to a change of hands (D7). A registration with no generation is refused `409 not_a_guest_registration`. The sheet row carries `guest`, and the fencer list offers the action (a mail icon, confirmed in `ResendManageLinkDialog`) only on such a row and only on a tournament Squire keeps.

**D13. The manage screen speaks the guest's language.** `GET my-registration` states `language` (the record's) only to a request presenting a manage key, and the page switches to it, since no account language exists to apply.

## Risks / Trade-offs

- [Guest entries are unverified, so anyone can enter a stranger's address and hold a seat that expires unpaid] → This is the same exposure an account had until now. The seat is bounded by the payment window. The rate limit applies. The victim receives a confirmation with a cancel link, and can free the seat themselves.
- [A forwarded guest mail grants management of that registration] → This is inherent in a mailed bearer link, and the owner accepted it for guests. It is scoped to one registration. Rotation on a change of hands bounds it.
- [Signup now depends on mail delivery; a misconfigured SMTP blocks every new account] → Startup refuses real mail without `public_base_url`. The deploy checklist (`add-deployment` 4.3) already round-trips a signup, and that step now has to include following the mailed link.
- [A typo'd account address leaves a pending row nobody can verify] → It expires in 48 h, and a correct signup on that address replaces it at once.
- [`/login` distinguishing pending from unknown reveals that an address signed up] → Only to someone presenting its password (D9).
- [Account holders lose instant signup, the shortest path to Register] → The guest path is now the shortest path. Verification returns the visitor to the tournament.

## Migration Plan

One Alembic revision adds the `pending_signups` table and `registrations.manage_key_generation` (nullable, no backfill: no existing registration is a guest registration). Downgrade drops both. Deploy needs `HEMA_SQUIRE_PUBLIC_BASE_URL` set before the new image starts, or startup refuses. Rollback: the old image ignores both, and any account verified in between is an ordinary `Fencer`.

## Open Questions

- ~~The copy in D11 is a proposal.~~ Confirmed by the owner as written on 2026-10-25.
- ~~An organizer asked for a lost link has nothing to resend it with.~~ Owner chose to add it now (2026-10-25): D12.
- ~~Substitution onto an account.~~ Confirmed by the owner (2026-10-25): a substitution that moves a guest registration onto a fencer with an account ends its manage link (generation set to `None`), as the takeover does; withdrawing it does not restore the link, and the organizer helps.
