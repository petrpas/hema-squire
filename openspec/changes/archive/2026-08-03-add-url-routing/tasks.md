## 1. Dependency and router shell

- [x] 1.1 Add `react-router-dom` (v7) to `frontend/package.json` dependencies and install it
- [x] 1.2 Wrap `<App/>` in `<BrowserRouter>` in `frontend/src/main.tsx`
- [x] 1.3 Add `routes.ts` (or a constant block in `App.tsx`) holding the path builders — `home(tab?)`, `detail(slug)`, `picker()`, `console(slug, phase?)`, `admin()`, `profile()` — so no path string is spelled out twice

## 2. Not-found screen

- [x] 2.1 Create `frontend/src/NotFound.tsx`: title, one line of prose, a `<Link to="/">` home, built from the existing `login-page`/`login-card` classes
- [x] 2.2 Add `notFound.title`, `notFound.body`, `notFound.home` to `frontend/src/i18n/cs.json` and `en.json`, in system copy (sentence case, no exclamation marks, no emoji)
- [x] 2.3 Confirm the screen needs no new CSS; if it does, add it to `index.css` using only `tokens.css` values (no radius > 2px, no shadow, no default-blue link)

## 3. Auth gate

- [x] 3.1 Create `RequireAuth` (in `App.tsx` or `frontend/src/RequireAuth.tsx`): holds the `authed` state seeded from `getToken()`, plus the post-auth `i18n.changeLanguage(account.language)` effect moved out of `App`
- [x] 3.2 When not authed, render `<Login onLogin={…}/>` in place at the current URL and render `<Outlet/>` otherwise — no redirect, so the requested URL and its query string survive login and no history entry is pushed
- [x] 3.3 Expose logout through the gate: clear the token, drop `authed`, and `navigate("/", { replace: true })`

## 4. Route table replaces the view state machine

- [x] 4.1 Rewrite `App.tsx` as the route table from design D4: `RequireAuth` → `FencerLayout` (index `/`, `t/:slug`), `organizer`, `organizer/:slug/console`, `organizer/:slug/console/:phase`, `admin`, `profile`, `*`
- [x] 4.2 Delete the `View` type and the `tournament` / `initialPhase` / `tab` / `selectedSlug` / `detailReadOnly` state along with it
- [x] 4.3 Turn `FencerArea` into `FencerLayout` (`frontend/src/FencerLayout.tsx`): keeps the account and `useUpcoming` fetches, reads the tab from `useSearchParams` with an unrecognised or absent value resolving to `open`, renders `FencerShell` around an `<Outlet/>`

## 5. Screens lose their navigation props

- [x] 5.1 `AccountMenu`: render My Profile / Admin Panel / To Fencer / To Organizer as `<Link>`s that close the dropdown; keep only `account` and `onLogout` as props
- [x] 5.2 Drop `onProfile` / `onAdmin` / `onOrganizer` / `onFencer` from `FencerShell`, `Console`, `TournamentPicker`, `AdminPanel`, `ProfilePage` and their call sites
- [x] 5.3 `AdminPanel`: replace `onBack` with `navigate(-1)`
- [x] 5.4 Thread `onLogout` from `RequireAuth` to every screen that renders `AccountMenu` (context or a prop, whichever keeps the diff smaller)

## 6. Fencer Home: tab in the URL, cards as links

- [x] 6.1 `FencerShell`: the four filter tabs become `<Link to={`/?tab=…`}>` keeping the `stage-control` classes and the active marker and tab counts
- [x] 6.2 `FencerHome`: `TournamentCard` becomes a `<Link to={`/t/${slug}`}>` with the `rail-card home-card` classes; drop the `onOpen` prop and the `readOnly` argument it passed
- [x] 6.3 `index.css`: give the card and tab link classes `text-decoration: none; color: inherit` (and `display: block` where the button was block-level) so the anchors render exactly as the buttons did
- [x] 6.4 Verify keyboard focus and the focus ring still land on cards and tabs as anchors, using the existing focus treatment (never the browser default outline)

## 7. Tournament detail

- [x] 7.1 Add a thin `TournamentDetailRoute` (or read the param inside `TournamentDetail`) that takes `:slug` from `useParams`
- [x] 7.2 Derive `readOnly` inside `TournamentDetail` as `detail.date < today` and delete the `readOnly` prop
- [x] 7.3 Close control navigates to Fencer Home carrying the filter tab the detail was opened from, falling back to `/` when the page was reached by URL; keep its accessible name
- [x] 7.4 Confirm the `Tournament`/`Register` tab stays component state and pushes no history entry

## 8. Console self-loads from the slug

- [x] 8.1 Add `ConsoleRoute`: reads `:slug` and `:phase`, fetches `api.tournament(slug)`, shows `t("common.loading")` as static text while pending, renders `<NotFound/>` on failure or on a `:phase` outside the `Phase` union, and `<Console/>` otherwise
- [x] 8.2 `Console`: replace `initialPhase` seed state with the phase from the route; phase tab clicks call `navigate(consolePath(slug, phase))` (push, not replace); no phase segment means `load`
- [x] 8.3 `Console`: take the tournament as a prop from the route wrapper, dropping the picker hand-off assumption everywhere it is relied on
- [x] 8.4 `TournamentPicker`: rows become `<Link to={consolePath(slug)}>`; `onPick` disappears; creating a tournament navigates to `consolePath(newSlug, "setup")`

## 9. Documentation and deployment note

- [x] 9.1 Add a line to `README.md` stating that any server hosting the built frontend must fall back to `index.html` for unknown paths, or deep links 404 before React loads (Vite dev does this already)
- [x] 9.2 Update `CLAUDE.md`'s frontend conventions only if the route table warrants a note about where navigation lives

## 10. Verification

- [x] 10.1 `npm run lint` (tsc) and `npm run build` clean
- [x] 10.2 `npm test` (vitest) still green
- [x] 10.3 Drive back/forward across home → detail → picker → console → admin → profile, confirming each step returns to the previous screen and never exits the app
- [x] 10.4 F5 on `/`, `/?tab=mine`, `/t/<slug>`, `/organizer`, `/organizer/<slug>/console`, `/organizer/<slug>/console/payments`, `/admin`, `/profile` — each redisplays its own screen
- [x] 10.5 Logged out, follow `/organizer/<slug>/console/payments`: Login appears, and after authenticating that phase opens; Back does not return to Login
- [x] 10.6 `/t/no-such-tournament`, `/organizer/no-such-tournament/console`, `/organizer/<slug>/console/invoicing`, and `/nonsense` all reach the not-found screen
- [x] 10.7 Middle-click a tournament card and a filter tab: both open in a new tab at the right URL; "copy link address" yields `/t/<slug>` and `/?tab=…`
- [x] 10.8 Open a past tournament from a `/t/<slug>` link and confirm it is read-only (no register, payment, or cancel controls)
- [x] 10.9 Create a tournament from the picker and confirm the URL is `/organizer/<new-slug>/console/setup`
- [x] 10.10 Log out from the console and confirm Back does not re-enter it
