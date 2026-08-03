## Context

`frontend/src/App.tsx` (172 lines) is the whole navigation system: one `useState<View>`
plus five pieces of companion state (`tournament`, `initialPhase`, `tab`, `selectedSlug`,
`detailReadOnly`) and an early-return chain that picks the screen. Every screen therefore
takes navigation callbacks as props — `onProfile`, `onAdmin`, `onOrganizer`, `onFencer`,
`onLogout`, `onBack`, `onClose`, `onPick`, `onOpen` — and `AccountMenu` re-drills all five
of the menu ones through each screen. Nothing touches the History API.

Two hand-offs carry data, not just intent:

- `TournamentPicker.onPick(tournament, phase?)` hands `Console` a fully fetched
  `Tournament` object and an initial phase. `Console` has no way to fetch one itself.
- `FencerHome.onOpen(slug, readOnly?)` passes `tournament.date < today` as `readOnly` —
  the flag means "already held", not "organizer preview" as the change note assumed.

The frontend is React 18.3 + Vite 6 with `react-i18next`; `npm run lint` is `tsc -b
--noEmit`; `vitest` exists and runs two pure-logic suites (`validation.test.ts`,
`numeric.test.ts`) with no DOM testing setup. `backend/app/main.py` serves the API only —
in development Vite serves the frontend and proxies `/api` to `localhost:8000`.

The design system (`CLAUDE.md`, `openspec/squire-design-spec.md`) forbids spinners,
gradients, shadows, radii > 2px, emoji, default-blue links, and hexes outside `tokens.css`.
Links introduced by this change inherit that: they are `--ink` text, underlined, never blue.

## Goals / Non-Goals

**Goals:**
- Every screen has a URL; back, forward, and F5 behave as in any web app.
- A tournament is shareable as a link, and that link works for a logged-out visitor
  (Login, then the tournament) and for one who arrives mid-session.
- The console is reachable by URL alone — no picker hand-off required — and keeps its phase
  across refresh.
- `App.tsx` shrinks to a route table; screens lose the navigation-callback props.

**Non-Goals:**
- Changing what any screen displays or how it fetches, beyond console slug resolution and
  the detail's `readOnly` derivation.
- Server-side rendering, code-splitting per route, or scroll restoration beyond the
  browser's own.
- Putting within-screen state in the URL: the detail's `Tournament`/`Register` tabs, the
  Setup section tabs (`setup-navigation`), the preview tabs (`setup-preview`), dialogs, and
  sheet edits all stay in component state.
- Adding a DOM/routing test runner.

## Decisions

### D1 — `react-router-dom` v7 in declarative mode

`<BrowserRouter>` in `main.tsx` wrapping `<App/>`, and `<Routes>/<Route>` inside `App.tsx`.
Not `createBrowserRouter` with loaders: the data-router mode's payoff is loader/action-based
fetching, and every screen here already owns its fetching in `useEffect`. Rewriting fetches
into loaders would be a second change wearing this one's clothes.

*Alternatives:* a hand-rolled `pushState`/`popstate` hook (rejected by the owner — ~80 lines
of untested path matching, `replace`-vs-`push` and anchor-interception edge cases we would
own with no routing tests to catch regressions); hash routing (rejected — ugly shared links,
and no server-side reason for it once the deployment does history fallback, see D8).

### D2 — URL scheme (owner-chosen)

```
/                                  Fencer Home, Open tab
/?tab=announced|open|past|mine     Fencer Home on that filter tab
/t/:slug                           tournament detail (fencer-facing)
/organizer                         tournament picker
/organizer/:slug/console           console, default phase (load)
/organizer/:slug/console/:phase    console on that phase
/admin                             admin panel
/profile                           profile page
*                                  not-found screen
```

`/t/` is deliberately terse: it is the link organizers paste into chat messages and posters.
The organizer area is namespaced under `/organizer` so that fencer-facing and
organizer-facing URLs are distinguishable at a glance, and so `/organizer/:slug/...` can
grow later siblings without colliding with `/t/:slug`.

No route is introduced for the organizer's preview of the fencer faces: that preview lives
inside the console's Setup phase (`setup-preview`) and is reached as
`/organizer/:slug/console/setup`.

### D3 — The home filter tab is a query parameter, not a path segment

`?tab=mine` rather than `/mine`. The path `/` stays the canonical landing URL, an absent or
unrecognised `tab` resolves to Open (preserving `fencer-home`'s "the Open tab SHALL be
selected after login"), and the detail's close control can return to exactly the list it was
opened from by carrying that search string. Selecting a tab pushes a history entry, so back
steps between tabs — the fencer's mental model, since the tabs are the home page's only
navigation.

### D4 — Route layout: one pathless layout route for the fencer area

```
<Routes>
  <Route element={<RequireAuth/>}>          {/* auth gate, no path */}
    <Route element={<FencerLayout/>}>       {/* FencerShell + <Outlet/> */}
      <Route index element={<FencerHome/>}/>
      <Route path="t/:slug" element={<TournamentDetailRoute/>}/>
    </Route>
    <Route path="organizer" element={<TournamentPicker/>}/>
    <Route path="organizer/:slug/console" element={<ConsoleRoute/>}/>
    <Route path="organizer/:slug/console/:phase" element={<ConsoleRoute/>}/>
    <Route path="admin" element={<AdminPanel/>}/>
    <Route path="profile" element={<ProfilePage/>}/>
    <Route path="*" element={<NotFound/>}/>
  </Route>
</Routes>
```

`FencerLayout` is today's `FencerArea` with the `view` switch removed: it reads the tab from
`useSearchParams`, keeps the `useUpcoming` fetch and the account fetch, renders `FencerShell`
and an `<Outlet/>`. This is what keeps `fencer-home`'s "Tournament detail shares the home
heading" true by construction — the heading belongs to the layout route, so navigating
between `/` and `/t/:slug` never unmounts it, and neither list counts nor the account are
refetched when a tournament is opened.

### D5 — Navigation reaches screens through hooks, not props

`AccountMenu` uses `<Link>`/`useNavigate` internally for My Profile, Admin Panel, To Fencer,
To Organizer; only `onLogout` remains a prop, because logout also clears the token and the
authed flag. The five menu callbacks disappear from `Console`, `TournamentPicker`,
`AdminPanel`, `ProfilePage`, and `FencerLayout`. `AdminPanel`'s `onBack` — today "back to
console if one is loaded, else the picker" — becomes `navigate(-1)`, which is what the
control always meant.

### D6 — Things that are navigation become anchors

Tournament cards (`FencerHome`), picker rows (`TournamentPicker`), the four home filter tabs
(`FencerShell`), and the account-menu entries become `<Link>`s rather than `<button onClick>`,
so middle-click, ⌘/Ctrl-click, "copy link address", and hover-preview all work. They keep
their existing class names; the CSS gains `text-decoration: none; color: inherit; display:
block` on the card and tab link classes so the anchors render exactly as the buttons did (no
default blue, no underline, per the prohibitions). Console phase tabs stay in-page controls
driven by `navigate` — they carry no target worth opening in a new tab and are already a
`stage-control` widget.

### D7 — Auth gate renders Login in place, at the requested URL

`RequireAuth` holds the `authed` state and the post-auth `i18n.changeLanguage` effect that
`App` holds today. When not authed it renders `<Login/>` **at the current URL** instead of
`<Outlet/>`; on success it flips `authed`, the same URL re-renders as its real screen, and
the deep link is honoured with no navigation at all. That trivially satisfies "Login must not
leave a history entry that back would return to": no entry is ever pushed.

*Alternative considered:* redirect to `/login?next=<url>` and navigate back on success. It
gives Login a bookmarkable URL and a cleaner story for password managers, but needs `replace`
discipline on both hops and a `next` parameter that must be validated as same-origin before
being navigated to (an open-redirect footgun). Rejected as more surface for no user-visible
gain. Logout resets `authed` and navigates to `/` with `replace`, so back does not re-enter a
screen the user just left.

### D8 — Console self-loads; unknown slug and unknown phase both end at not-found

`ConsoleRoute` reads `:slug` and `:phase` from `useParams`, calls the existing
`api.tournament(slug)`, and renders:

- while pending — the design-system loading treatment already used elsewhere
  (`{t("common.loading")}` as plain text; no spinner);
- on 404/403 or any failure — `<NotFound/>`;
- otherwise `<Console tournament={…} phase={…}/>`.

`Console` stops taking `initialPhase` as seed state: the phase is now derived from the route
on every render, and its tab controls call `navigate(\`/organizer/${slug}/console/${phase}\`)`.
Phase switches push history entries, so back walks the phases and then leaves the console —
the point of putting the phase in the URL. `/organizer/:slug/console` with no phase segment
renders the `load` phase (it does **not** redirect, so the short URL stays valid and
shareable).

A `:phase` that is not one of the eight known phases renders the not-found screen rather than
silently falling back to `load`: a wrong URL should say so instead of pretending it worked.
The eight are `setup, load, parsing, matching, dedup, payments, export, teams` — the seven of
`etl-console` plus `teams` from `team-disciplines`, and the segment spellings are exactly the
existing `Phase` union, so the type is the single source of truth.

Tournament creation, which today calls `onPick(tournament, "setup")`, becomes
`navigate(\`/organizer/${slug}/console/setup\`)` — satisfying `tournament-admin`'s "the
creator lands in the console's Setup phase" unchanged.

### D9 — `readOnly` is derived from the tournament, not passed by the caller

`TournamentDetail` already fetches the tournament (it needs `detail.date` for the identity
lines), so it computes `readOnly = detail.date < today` itself and the prop disappears. This
is not just prop-plumbing: today a deep link or a Mine-tab entry for a past tournament would
arrive with `readOnly = false` and offer register/cancel controls on an event that has
already happened. Deriving it makes the rule hold for every entry point, which is what
`fencer-home`'s read-only requirement always meant.

### D10 — Not-found screen

A new `NotFound.tsx`: the page title, one line of prose, and a `<Link to="/">` home — built
from existing `login-page` / `login-card` classes so it needs no new CSS, in system copy
(sentence case, no exclamation marks, no emoji). New i18n keys `notFound.title`,
`notFound.body`, `notFound.home` in `cs.json` and `en.json`.

### D11 — Deployment must fall back to `index.html`

Vite's dev server already serves `index.html` for unknown paths, so development needs
nothing. There is no production static server in this repo yet (`backend/app/main.py` mounts
no static files), so nothing needs changing today — but whatever eventually serves the built
bundle must route unknown paths to `index.html`, or every deep link 404s before React loads.
Recorded here as a constraint on that future change; a task adds a line to `README.md` so it
is not rediscovered the hard way.

## Risks / Trade-offs

- **`App.tsx` is rewritten wholesale, with no routing tests to catch regressions.** →
  The route table is small and declarative, and the screens are moved unchanged; verification
  is the manual matrix in the proposal (back/forward, F5 on each route, logged-out deep link,
  nonsense slug, `?tab=`, middle-click) run once at the end of implementation.
- **Phase switches push history entries**, so leaving a console visited across eight phases
  takes eight backs. → Accepted deliberately: the alternative (`replace` on phase switch)
  breaks "back returns to the previous phase", which is a stated goal. Screens the user
  *replaced* rather than entered (logout, auth redirect) use `replace`.
- **Sharing a `/t/:slug` link to an unpublished or draft tournament** now silently depends on
  the API's visibility rules rather than on the link never existing. → The route surfaces
  whatever the API says: a slug the caller may not see resolves to not-found, the same as a
  slug that does not exist, so the URL leaks nothing about existence.
- **A new runtime dependency (~15 kB gzipped)** on a project with a deliberately small
  dependency list. → It is the de-facto standard, has no transitive dependencies of note in
  v7, and replaces code we would otherwise write and maintain ourselves.
- **`useSearchParams` re-renders the fencer layout on tab change**, where `useState` did
  before. → Identical cost in practice: the layout's fetches are keyed by tab and already
  cached in component state (`held`, `mine` are fetched once), and the layout does not unmount.
- **StrictMode double-invokes effects in development**, including `ConsoleRoute`'s fetch. →
  Already true of every existing screen's fetch; no new class of problem.
