## Context

`Login.tsx` renders both the sign-in form and the signup form (as `SignupForm`), sharing one `useTranslation()` call for sign-in and its own for signup. Sign-in currently follows the global `i18n.language` — whatever a previous session, browser detection, or a just-changed signup selector last left it at — so a first-time or logged-out visitor can land on a Czech (or other) sign-in screen unpredictably. The signup form's language `<select>` initializes from `i18n.language` too, with no deliberate default.

`HRSearch.tsx` exports `HRSearchPicker`, a shared name+nationality search component used in two places: inside `Login.tsx`'s signup HR step, and inside `ProfilePage.tsx`'s HR-binding step. It currently always offers an "Any nationality" option and defaults the nationality filter to empty, and its own "Search" button is separate from the "Cancel" button that the *caller* (`Login.tsx`) renders after it — so today they can't share a layout without either merging them into one component or fighting cross-component CSS.

## Goals / Non-Goals

**Goals:**
- Sign-in always renders in English, independent of any stored/detected language.
- Signup's language selector defaults to English but remains fully changeable.
- Signup's tiskopis line becomes two independently anchored labels.
- Signup's nationality picker requires a selection and defaults to Czech, without touching the Profile page's picker.
- Signup's Search/Cancel buttons share a style and sit together, centered, with breathing room from the field above.

**Non-Goals:**
- No change to the Profile page's HR search behavior or layout.
- No change to the tournament-creation or registration-form tiskopis lines (single-line layout stays as shipped in `graphical-remodel`) — only the signup form's line was flagged.
- No backend or API changes; `hrNationalities()` and `hrSearch()` are unchanged.
- No change to how language switches once an account exists (Profile page language preference, tournament communication language) — only the *default* for new signups.

## Decisions

**Sign-in pinned to English via a second `useTranslation` call, not global state.** `Login()` will call `useTranslation(undefined, { lng: "en" })` alongside the existing hook, and use that translator only in the sign-in-mode JSX. This resolves English strings for that render without touching `i18n.language` — so it can't leak into or get clobbered by the signup form's own language switching, and there's no mount/unmount cleanup to get wrong. Alternative considered: call `i18n.changeLanguage("en")` on mount and restore on unmount — rejected because it mutates shared global state that `SignupForm` (a sibling, not a child) also reads, risking visible flicker or races between the two.

**Signup's `language` state initializes to the literal `"en"`**, not `i18n.language`. The selector still lists all implemented locales and `changeLanguage` still fires on selection, per existing behavior — only the initial highlighted value changes.

**Tiskopis line becomes two `<span>`s in a flex row** (`.tiskopis-row { display:flex; justify-content:space-between }`), each styled with the existing `.tiskopis-number` treatment (uppercase-adjacent label look, `--font-data`, `--ink-faded`). The i18n key `signup.formNumber` is trimmed to just "tiskopis č. 1" / "form no. 1"; a new `signup.formTitle` key holds "Založení účtu" / "Account creation". Only this one usage changes — `picker.formNumber` and `form.formNumber` (used elsewhere) are untouched, per Non-Goals.

**`HRSearchPicker` gains two independent optional props: `requireNationality?: boolean` and `onCancel?: () => void`.** Neither changes behavior unless supplied:
- `requireNationality`: omits the "Any nationality" `<option>`; once the nationality list loads, if no nationality is yet selected the component defaults to the first entry whose value starts with `cz`/`CZ` (case-insensitive), falling back to the list's first entry if no Czech-coded entry exists. This avoids hardcoding an exact nationality string (`"CZE"` in the stub data, unverified for the live hemaratings.com index) that might not match production data.
- `onCancel`: when provided, the Search button and a same-styled `secondary` Cancel button render together in a centered row (`.hr-search-actions`) with top padding separating them from the fields above; without it, Search renders alone exactly as before (Profile page behavior unchanged).

`Login.tsx`'s `SignupForm` passes both props and removes its own now-redundant standalone Cancel button (the one that used to sit below `<HRSearchPicker>`).

Alternative considered for the button-row requirement: leave `HRSearchPicker` untouched and have `Login.tsx` wrap it plus an external Cancel button in a flex container from outside. Rejected — the Search button lives inside `HRSearchPicker`'s own JSX tree, so an outside wrapper can't put it in the same flex row as an external Cancel button without reaching into the child's internals; passing `onCancel` in is the direct way to get one row.

**Localization spec default changes from Czech to English**, per the owner's explicit choice to amend rather than leave the spec inconsistent with what signup actually does now.

## Risks / Trade-offs

- [Hardcoding "Czech" as a default risks not matching the live HR index's actual nationality string format] → Match by `cz`-prefix case-insensitively against the fetched list rather than an exact literal; fall back to the list's first entry if no match, so the picker never ends up with an invalid/blank selection.
- [Pinning sign-in to English via a second `useTranslation` call is an easy pattern to forget and accidentally revert if someone refactors `Login.tsx`] → Keep the English-only requirement documented in `localization`'s scenario coverage (see specs delta) so a regression is spec-testable, not just tribal knowledge.
- [Changing the documented default language is a real behavior change for every new signup, not just a visual tweak] → Confirmed explicitly with the owner before drafting this change (see conversation); captured as a MODIFIED requirement in the localization delta spec, not silently folded into implementation.

## Migration Plan

Frontend-only; no data migration. Existing accounts are unaffected (their stored `language` preference is unchanged) — this only changes what a *new* signup defaults to before the fencer picks something else, and what the sign-in screen (which has no account context yet) renders in. Rollback is a plain revert of the frontend commit(s).
