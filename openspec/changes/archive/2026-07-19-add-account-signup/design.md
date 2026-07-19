## Context

`POST /api/auth/signup` already accepts email, password (min 8), optional `display_name`, optional `hr_id`, and club: with `hr_id` it validates against the HR index, enforces one-account-per-HR, and takes the HR canonical name as display name; without it `display_name` is required. `GET /api/hr/search` is public (no auth dependency), so HR matching works pre-auth. The frontend has no signup UI and no `api.signup`; `Login.tsx` is a plain email+password card. i18n (`frontend/src/i18n/index.ts`) auto-discovers `./*.json` locales but hardcodes `lng: "cs"` and nothing ever calls `changeLanguage`. The `Fencer` model has no language field; the `language` column that exists belongs to `Tournament` (communication language). Alembic handles schema migrations.

## Goals / Non-Goals

**Goals:**
- Self-service registration window reachable from the login screen: email, password, name, preferred language, optional HR binding step.
- Per-account UI language: chosen at signup, persisted, applied at login/signup, editable on the Profile page.
- Auto-login after signup, landing on Fencer Home.

**Non-Goals:**
- No email verification or password reset (future changes; no auth email infrastructure yet).
- No change to tournament registration, communication language, or HR index/refresh mechanics.
- No new localizations — the selector lists whatever locales are bundled.

## Decisions

- **D1 — Reuse the existing signup endpoint; extend, don't fork.** Add `language` to `SignupIn` (validated against implemented locales, default `cs`), a `language` column on `Fencer` (`String(10)`, default `"cs"`, alembic migration), and expose it in `AccountOut` + allow it in `AccountUpdate` (audited like other profile fields). Alternative (separate `/api/auth/register` endpoint) rejected: the current endpoint already implements every rule including HR binding.
- **D2 — Signup window as a mode of the login screen.** `Login.tsx` gets a "Create account" link toggling to a signup form (same `login-page`/`login-card` styling) rather than a new route/view — pre-auth there is no router state to speak of, and login/signup share the card look. Fields: email, password, name, language `<select>`. The language options come from the i18n resource keys (`Object.keys(i18n resources)`), so adding a locale JSON automatically extends the selector. Changing the selector immediately switches the form's own language.
- **D3 — Optional HR step inside the window.** Below the name field, a "Find my HEMA Ratings profile" section mirrors the Profile page's match UI: search `/api/hr/search` by the typed name (+ optional nationality filter), list candidates (name, nationality, club), confirm one → the form shows the HR canonical name as the account name and sends `hr_id` on submit. A confirmed profile can be cleared before submitting; skipping leaves plain `display_name` signup. Alternative (bind only post-signup on Profile) was declined by the owner. Component is extracted/shared with `ProfilePage`'s `HRMatchSection` where practical rather than duplicated.
- **D4 — Language application points.** After signup: `setToken` → `i18n.changeLanguage(chosen)` → Fencer Home. After login and on app boot with a valid token: the account payload (`api.account()`) carries `language`; the app applies it once the account loads. The pre-auth screens keep the current default (`cs`) plus the selector on the signup form. Alternative (persist in localStorage as the primary source) rejected per owner decision — the account is the source of truth so the preference follows the user across devices.
- **D5 — Errors.** Map `409 email_already_registered`, `409 hr_id_already_bound` (directs to account recovery wording per existing spec), `404 hr_profile_not_found`, and password-too-short validation to localized messages inline in the form.

## Risks / Trade-offs

- [Fencers who sign up bound to HR get the HR canonical name, possibly overriding what they typed] → the form makes this visible before submit (name field shows the confirmed canonical name); existing spec mandates this behavior.
- [No email verification means typo'd emails create orphan accounts] → accepted by owner decision; revisit with the future email-infrastructure change.
- [Language applied only after account load could flash Czech briefly for EN users] → apply as soon as the account payload arrives; acceptable cosmetic cost.
- [Shared HR-match component refactor could disturb `ProfilePage`] → keep the extraction minimal; if risky, duplicate the small section instead and note it.

## Migration Plan

Alembic migration adds `fencers.language` (nullable-with-default backfill to `cs`). Purely additive; rollback = drop column + revert.

## Open Questions

- None.
