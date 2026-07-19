## 1. Backend — language on the account

- [x] 1.1 Add `language` column to `Fencer` (`String(10)`, default `"cs"`) with an alembic migration; add `language` to `SignupIn` (validated against implemented locales), `AccountOut`, and `AccountUpdate` (audited profile change); store it in `signup`
- [x] 1.2 Backend tests: signup stores the chosen language; default applies when omitted; invalid language rejected; language change via account update is audited; existing signup paths (HR-bound, plain, duplicate email, bound HR conflict) still pass

## 2. Frontend — registration window

- [x] 2.1 Add `api.signup` to `api.ts`; "Create account" link on `Login.tsx` toggling a signup form in the same card style: email, password, name, language `<select>` populated from the i18n resource keys; selector switches the form language immediately
- [x] 2.2 Optional HR step: search-by-name candidates via `api.hrSearch` (reuse/extract the Profile page match UI), confirm → canonical name shown in the name field + `hr_id` sent, clearable before submit, skippable
- [x] 2.3 Submit flow: signup → `setToken` → `i18n.changeLanguage` → Fencer Home; inline localized errors for duplicate email, bound HR profile, missing HR profile, short password

## 3. Frontend — language application & Profile

- [x] 3.1 Apply `account.language` via `i18n.changeLanguage` when the account payload loads after login/boot
- [x] 3.2 Language selector on the Profile page saving through the account update endpoint and switching the UI immediately

## 4. Polish & verification

- [x] 4.1 cs/en i18n keys (signup form, HR step, errors, language labels) and any `index.css` additions
- [x] 4.2 Frontend build + full backend test suite pass
- [x] 4.3 E2E via dev servers: sign up in EN → UI in English, lands on Fencer Home; re-login renders English; HR step binds and shows canonical name; duplicate email rejected; Profile language switch persists
