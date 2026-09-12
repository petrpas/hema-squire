## 1. Optional credential in the API

- [x] 1.1 Add `optional_fencer` to `app/auth.py`, returning `Fencer | None` — `None` only when no credential was presented, raising exactly as `current_fencer` does when one was presented and rejected; verify with tests asserting `None` for an absent header, a `Fencer` for a good token, and 401 for a malformed one and for a token whose account is gone
- [x] 1.2 Widen `_fencer_tournament_out` in `app/routers/tournaments.py` to take `Fencer | None`, skipping the registration-state and organizer lookups when it is `None`; verify `uv run basedpyright` is clean and the existing tournament-list tests still pass
- [x] 1.3 Make `OpenTournamentOut.my_registration_state` and `.organized` optional and omitted (not defaulted) when there is no fencer; verify a test asserts both keys are absent from an anonymous entry and present for a signed-in one
- [x] 1.4 Switch `open_tournaments` and `held_tournaments` to `optional_fencer`; verify tests that both answer the same tournaments in the same order with and without a credential, and that a rejected credential still yields 401 rather than an anonymous answer
- [x] 1.5 Confirm `/tournaments/mine` still refuses an absent credential with 401; verify with a test that names it, so the boundary is asserted rather than assumed

## 2. The fencer-facing detail stops carrying the organizer's business

- [x] 2.1 Enumerate the fields `frontend/src/TournamentDetail.tsx` and the surfaces it renders actually read from `api.tournament(slug)`, and record the list in the task's commit message; verify by grepping the detail page and its sections for every `detail.` access
- [x] 2.2 Add `FencerTournamentOut` in `app/schemas.py` holding exactly that subset and nothing the `public-browsing` spec withholds; verify `uv run basedpyright` is clean
- [x] 2.3 Add the fencer-facing detail route answering `FencerTournamentOut`, refusing an unpublished or cancelled tournament with the same not-found answer as an unknown slug, and taking no credential; verify tests for a published tournament, a draft, a cancelled tournament and an unknown slug
- [x] 2.4 Put `FencerDep` plus `require_console_access` on the existing full-payload `GET /tournaments/{slug}`; verify tests that a non-member is refused and a console team member is not
- [x] 2.5 Add the field-set test: the fencer-facing answer's keys asserted against the allowed set, so a field added to the schema later fails rather than leaks; verify it fails when `bank_account` is added to the schema on purpose and passes once removed
- [x] 2.6 Point `api.tournament` at the fencer-facing route and give the console its own client function for the full payload; verify `npm run typecheck` is clean and the console's Setup phase still reads every field it shows

## 3. Public routes and a shell with no account

- [x] 3.1 Extract sign-out (clear the token, navigate to `/`) into a helper both the gated and the public shell call, leaving `RequireAuth`'s outlet context for the screens that already read it; verify `npm run typecheck` and the existing auth tests
- [x] 3.2 Split `App.tsx` into a public group (`/`, `/t/:slug` under `FencerLayout`) and the gated group (everything else, unchanged under `RequireAuth`); verify tests that `/` and `/t/:slug` render without a token and that `/organizer`, `/admin` and `/profile` still render Login
- [x] 3.3 Make `FencerLayout` fetch the account only when a token is present and pass `account: null` otherwise; verify a test that the anonymous list renders with no account request issued
- [x] 3.4 Gate `?tab=mine` in the layout — resolving to `mine` with no account renders Login in place at that URL, and signing in shows the Mine tab; verify a test for both halves
- [x] 3.5 Have `FencerIdentity` offer sign-in in place of a name when there is no account, and drop `AccountMenu` entirely rather than render it empty; verify tests that the anonymous bar offers sign-in and that no profile, admin, picker, create or sign-out target is reachable
- [x] 3.6 Handle a rejected credential on a public route by discarding it and rendering the screen in its anonymous form at the same URL, rather than showing Login; verify a test for `/t/:slug` with a 401-answered session request

## 4. The bar carries the title; the tabs move to the main field

- [x] 4.1 Replace the logo button in `FencerShell` with the localized title and drop its `tab` and `counts` props; add `app.listTitle` to the cs and en bundles ("Šermířské turnaje a akce" / "HEMA Tournaments and Events"); verify a test that the bar renders the Czech string under a Czech UI and the English one under an English UI
- [x] 4.2 Render the tab band at the top of `FencerHome`'s main field, centred, keeping `useTabBand` and the scrolling-band CSS; verify tests that the band is in the main field and absent from the bar, and that the 390px layout still puts the band on its own full-width row
- [x] 4.3 Offer three tabs to an anonymous visitor and four to an account; verify a test that Mine is absent without an account
- [x] 4.4 Keep the band out of `TournamentDetail` and make its close control return to the tab the tournament was opened from; verify tests that no filter tab renders while a detail is open and that closing a detail opened from Announced returns to Announced
- [x] 4.5 Move the title/band CSS in `index.css` to sit with the components that own it, adding no hex value outside `tokens.css` and no radius over 2px; verify `npm run check` is clean and the design prohibitions hold by reading the diff

## 5. The default tab is resolved from the lists

- [x] 5.1 Move the Mine fetch from `FencerHome` into `FencerLayout`, issued alongside the upcoming lists and only for an account; verify a test that one visit issues the Mine request once and an anonymous visit issues none
- [x] 5.2 Resolve the default tab in `FencerLayout` — Mine, then Open, then Announced; anonymous starting at Open — latched once the lists arrive and never recomputed, showing the loading treatment until then; verify tests for each branch of the order, for the anonymous pair, and for a list that empties after landing leaving the visitor where they are
- [x] 5.3 Leave the URL as `/` and push no history entry when the default resolves; verify a test that the address bar still reads `/` after landing and that Back from a resolved landing leaves the application
- [x] 5.4 Keep an explicit `?tab=` exact, including an unrecognised value falling back to the resolved default; verify tests for `?tab=announced` on an account with a non-empty Mine, and for `?tab=archive`

## 6. Managing a tournament from its card

- [x] 6.1 Restructure the card so the heading area is the `/t/:slug` link and the card itself is a container, keeping its current appearance and whole-surface hover; verify tests that the card still opens the detail and that no interactive element nests inside an anchor
- [x] 6.2 Add the `Spravovat` link to `consolePath(slug)`, shown only when the entry's `organized` field says the account may manage it, on past and upcoming cards alike, and add the cs/en strings; verify tests for an owner, a console team member, a plain fencer, an anonymous visitor, and a past tournament
- [x] 6.3 Verify activating `Spravovat` opens the console and not the detail, and that middle-click opens the console in a new tab; assert both in tests

## 7. Creating a tournament from the account menu

- [x] 7.1 Move `TournamentCreateDialog` out of `TournamentPicker.tsx` into its own file unchanged; verify `npm run typecheck`, `npm run check`, and that the existing `tournamentCreate.test.tsx` passes untouched
- [x] 7.2 Add the create entry to `AccountMenu`, shown on the same predicate the picker uses today, opening the same dialog and landing in the console's Setup phase on confirmation; verify tests for an organizer seeing and using it and a plain fencer not being offered it
- [x] 7.3 Confirm the picker keeps its own create button and still lists drafts and cancelled tournaments; verify with a test naming a draft listed there and absent from every home tab

## 8. Language for a visitor with no account

- [x] 8.1 Render a public screen in the default locale for a visitor with no account, independent of the browser locale and of a preference left by an ended session; verify tests for a fresh anonymous visit and for a visit after a Czech-preferring account signs out
- [x] 8.2 Switch the UI to the account's preferred language on sign-in without a reload, on the screen the visitor is already on; verify a test that signs in from the list and asserts the Czech strings appear

## 9. Finishing

- [x] 9.1 Run the backend gates from `backend/`: `uv run ruff check .`, `uv run basedpyright`, and `uv run pytest tests/ -q --maxfail=3 --tb=short --show-capture=no`; all clean
- [x] 9.2 Run the frontend gates from `frontend/`: `npm run typecheck`, `npm run check`, `npm test`, `npm run build`; all clean
- [x] 9.3 Walk the change in the running app **as an anonymous visitor** — landing tab (Announced, nothing being open), tab band centred in the field, title in the bar, sign-in in the identity's place, no account menu, no Spravovat, and the full detail at `/t/:slug` — each confirmed against its scenario in `specs/`. The signed-in walks (Moje default, Spravovat, create from the menu, register-then-sign-in) are left to a human: driving them needs a password typed into the form, which the agent does not do. Their DOM is asserted in `publicHome.test.tsx` and `publicDetail.test.tsx`.
- [x] 9.4 Run `uv run deptry .` and read its answer; no dependency changed, so it should report nothing new

## 10. Sign-in can be declined

- [x] 10.1 Give `Login` an optional `onCancel`: a way back on the form and on Escape, absent where no caller offers one; split `SignupForm` into its own file on the way, the file having outgrown one (~360 lines), and give the two link controls stable class names so a test names the one it means
- [x] 10.2 Wire it where sign-in stands in front of something: `FencerLayout` drops the prompt and leaves the visitor on the page behind it, `?tab=mine` and the gated URLs under `RequireAuth` fall back to the tournament list; verify tests for declining the register prompt, Escape doing the same, and the Mine gate landing on a readable tab
- [x] 10.3 Let Escape unwind one screen at a time inside account creation — the pending hemaratings candidate, then the search, then back to sign-in; verify a test that Escape on the signup form returns to sign-in without taking the caller's cancel

## 11. The account menu says where it leads

- [x] 11.1 Narrow the picker's listing to what the caller may open — owned or a seat on the console team — and carry that set's size on the account as `organized_count`, so the menu can ask without a listing; verify tests for a stranger's tournament being absent, a team seat adding one, and the count following both
- [x] 11.2 Drop the To Fencer entry (the logo is that way back), rename To Organizer to My tournaments and show it only where the count is non-zero, and rename New tournament to Create tournament; verify tests for the entry appearing, hiding, and no home link left in the dropdown
- [x] 11.3 Point the console's logo at the tournament list rather than the picker, so the landmark means one thing everywhere; verify a test on the console's `.logo-button` href
