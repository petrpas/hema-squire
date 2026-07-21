## 1. Sign-in language

- [x] 1.1 In `Login.tsx`, add a second `useTranslation(undefined, { lng: "en" })` call and use it exclusively in the sign-in-mode JSX (not in `SignupForm`).
- [x] 1.2 Verify the sign-in screen renders in English even when `i18n.language` is Czech (or another locale) at the time it mounts.

## 2. Signup language default

- [x] 2.1 In `SignupForm`, initialize the `language` state to the literal `"en"` instead of `i18n.language`.
- [x] 2.2 Verify the selector still lists every implemented locale and still switches the form's language immediately on change.

## 3. Split tiskopis line

- [x] 3.1 Add `signup.formTitle` ("Založení účtu" / "Account creation") to `i18n/cs.json` and `en.json`; trim `signup.formNumber` down to just the form-number text ("tiskopis č. 1" / "form no. 1").
- [x] 3.2 In `Login.tsx`, render the two strings as separate spans in a new `.tiskopis-row` flex container (title left-anchored, number right-anchored), replacing the single `<p className="tiskopis-number">`.
- [x] 3.3 Add `.tiskopis-row` to `index.css` (`display: flex; justify-content: space-between`), reusing `.tiskopis-number`'s text styling on each span.

## 4. Required nationality in signup's HR search

- [x] 4.1 Add an optional `requireNationality?: boolean` prop to `HRSearchPicker` (`HRSearch.tsx`). When true, omit the "Any nationality" `<option>`.
- [x] 4.2 When `requireNationality` is true and the nationality list loads with nothing selected yet, default to the first entry matching `cz`/`CZ` case-insensitively, falling back to the list's first entry if none match.
- [x] 4.3 Pass `requireNationality` from `Login.tsx`'s `SignupForm` usage of `HRSearchPicker`. Leave `ProfilePage.tsx`'s usage unchanged (prop omitted).

## 5. Search/Cancel button row

- [x] 5.1 Add an optional `onCancel?: () => void` prop to `HRSearchPicker`. When provided, render the Search button and a same-styled (`secondary`) Cancel button together in a centered `.hr-search-actions` row; when omitted, render Search alone as today.
- [x] 5.2 Add `.hr-search-actions` to `index.css`: centered flex row, gap between buttons, top padding separating the row from the fields above.
- [x] 5.3 In `Login.tsx`'s `SignupForm`, pass `onCancel={() => setShowHrSearch(false)}` into `HRSearchPicker` and remove the now-redundant standalone Cancel button that used to render after it.

## 6. Spec sync and verification

- [x] 6.1 Confirm the `localization` delta spec's MODIFIED requirement matches what's implemented (English default, English-only sign-in).
- [x] 6.2 Run `npm run lint` (tsc) and `npm run build` in `frontend/` to confirm no regressions.
- [x] 6.3 Manually verify in the dev server: sign-in stays English after switching signup to Czech and back; signup defaults to English; the tiskopis line shows two anchored labels; the nationality select has no "any" option and starts on a Czech entry; Search/Cancel share styling, centered, with top padding; Profile page's HR search is visually and behaviorally unchanged. Screenshot-verified all six; also found and fixed a real bug along the way — the signup form's dropdown pre-selected "English" but the surrounding copy still rendered in Czech until the global i18n instance was synced on mount.
