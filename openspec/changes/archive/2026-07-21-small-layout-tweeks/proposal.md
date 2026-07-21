## Why

A first pass over the newly remodeled login/signup screens surfaced four small but concrete UX gaps: the sign-in screen inherits whatever language was last active instead of staying predictable for an unauthenticated visitor, the signup language selector defaults to whatever the browser/session already has set instead of a clear default, the HR nationality picker's "any nationality" option makes an already-heavy signup step easer to misuse, and two related buttons in the signup HR-search step (Search / Cancel) don't share a visual treatment or spacing. These are pre-launch polish items on the account-creation path, the first thing every new fencer sees.

## What Changes

- The sign-in (login) screen SHALL always render in English, regardless of the browser locale or any previously stored account/session language preference. No language selector is added to it.
- The signup form's language selector SHALL default to English on first render (the fencer can still change it, switching the form's own language immediately, per existing behavior). **BREAKING**: changes the documented default UI language for new accounts from Czech to English.
- The signup form's tiskopis line ("Založení účtu — tiskopis č. 1") SHALL split into two labels within the same row: the form title left-anchored, the form number right-anchored — instead of one em-dash-joined string.
- The HR nationality picker, when used inside the signup form specifically, SHALL drop the "Any nationality" option and require a selection, defaulting to Czech. The same picker on the Profile page keeps today's behavior (nationality optional, "Any nationality" available) — this is scoped to signup only.
- The signup HR-search step's "Search" and "Cancel" buttons SHALL share the same button style, be laid out together in a centered row, with spacing separating them from the name search field above.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `localization`: the "Per-account UI language preference" requirement's stated default changes from Czech to English for new accounts created via the signup form.

## Impact

- `frontend/src/Login.tsx` — sign-in mode forced to English via a locale-pinned translator; signup form's language state defaults to English; tiskopis line split into two labels; wires `onCancel`/`requireNationality` into `HRSearchPicker`.
- `frontend/src/HRSearch.tsx` — new optional `requireNationality` and `onCancel` props; nationality select and action-button layout change only when those props are supplied (Profile page's existing usage is unaffected).
- `frontend/src/index.css` — new layout rules for the split tiskopis row and the centered search/cancel button row.
- `frontend/src/i18n/en.json`, `cs.json` — `signup.formNumber` value shortened (form-number only); new `signup.formTitle` key.
- `openspec/specs/localization/spec.md` — delta updates the default-language requirement text and scenario.
- No backend changes; no API changes.
