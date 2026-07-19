## Why

There is no way to create an account from the application: the login screen offers only email + password sign-in, and new accounts exist only through seeding or the API. The backend signup endpoint (`POST /api/auth/signup`) already exists — the frontend window is missing. At the same time the UI language is hardcoded to Czech even though the localization spec promises the UI follows the user's preference.

## What Changes

- The login screen gains a "Create account" link opening a registration window with the fields: email, password, name, and preferred language (selection from the implemented localizations — currently CS and EN, derived from the bundled locale resources, not a hardcoded list).
- The window includes an optional HEMA Ratings step (per owner decision): search the fighters index by name, present candidates, and bind the confirmed profile at signup — the HR canonical name becomes the display name, as the fencer-accounts spec already requires. Skippable; binding remains available later on the Profile page.
- Preferred language is stored on the account (new column + migration), applied to the UI at login and after signup, and editable on the Profile page.
- No email verification (per owner decision — no auth email infrastructure yet); the account is active immediately and the fencer is logged in right after signup, landing on Fencer Home.
- Duplicate email and already-bound HR profile are rejected with clear messages.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `fencer-accounts`: the "Account creation with HR binding" requirement becomes a concrete self-service registration window (fields, optional HR step, immediate activation, auto-login); adds the preferred-language field to account creation.
- `localization`: adds a requirement that the UI language is a per-account preference chosen at signup, applied at login, and editable on the Profile page — replacing the hardcoded default.

## Impact

- Backend: `SignupIn`/`AccountOut`/`AccountUpdate` schemas + `language` column on the fencer model (alembic migration); signup endpoint stores the language; existing `/api/hr/search` (public) reused. Tests for language storage and signup paths.
- Frontend: `Login.tsx` gains the link; new signup window component; `i18n` applied from the account at login/signup; Profile page language selector; `api.ts`; cs/en i18n keys; `index.css`.
- No impact on tournament registration, payments, or the organizer console.
