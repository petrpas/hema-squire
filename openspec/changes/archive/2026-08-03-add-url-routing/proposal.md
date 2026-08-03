## Why

The frontend has no notion of URLs. Navigation is a single `useState<View>` in `App.tsx`
(`"home" | "tournament" | "picker" | "console" | "admin" | "profile"`) and screen changes
never touch the History API — no `pushState`, no `popstate` listener, no hash. From the
browser's point of view the whole app is one history entry, with three user-visible
consequences:

- **Back exits the app** instead of returning to the previous screen; on mobile the system
  back gesture does the same, which reads as a broken app.
- **No shareable links.** An organizer cannot send fencers a URL for a specific tournament;
  every visitor lands on Fencer Home and must find the tournament manually. For a
  registration system whose core loop is "send people a link", this is the most damaging
  consequence.
- **Refresh resets everything.** F5 anywhere returns to home and discards the selected
  tournament, home tab, and console phase.

## What Changes

- Introduce `react-router-dom` (new dependency) and replace the view state machine in
  `App.tsx` with a route table. The `View` type, the `setView` callbacks, and the
  prop-drilled navigation handlers (`onProfile`, `onAdmin`, `onOrganizer`, `onFencer`,
  `onBack`, `onClose`, `onPick`, `onOpen`) give way to route navigation; screens keep their
  own data-fetching behaviour.
- **URL scheme** (owner-chosen, short form):

  | path | screen |
  | --- | --- |
  | `/` | Fencer Home, Open tab (spec default) |
  | `/?tab=announced\|open\|past\|mine` | Fencer Home on that filter tab |
  | `/t/:slug` | tournament detail, fencer-facing |
  | `/organizer` | tournament picker |
  | `/organizer/:slug/console/:phase?` | ETL console; phase defaults to `load` |
  | `/admin` | admin panel |
  | `/profile` | profile page |
  | anything else | a minimal not-found screen offering the way home |

- **The home tab moves into the URL** as a `?tab=` query parameter, so a tab survives F5,
  is shareable, and takes part in back/forward. Absent or unrecognised values resolve to
  Open, keeping `fencer-home`'s "the Open tab SHALL be selected after login".
- **Console becomes self-loading.** Today `Console` receives a full `Tournament` object
  from `TournamentPicker` via `onPick`; a deep link has no picker to hand one over. The
  console (through a thin route wrapper) resolves the tournament from `:slug` itself using
  the existing `api.tournament(slug)`, and shows the design-system loading treatment
  meanwhile. A slug that does not exist or that the caller may not open yields the
  not-found screen, not a blank console.
- **Auth gate becomes a redirect with return-to.** Today `!authed` renders `<Login>` in
  place and the intended destination is lost. An unauthenticated visit to any route shows
  Login and, on success, lands on the originally requested URL (query string included).
  Logout returns to `/`. Login must not leave a history entry that back would return to
  after authentication.
- **Back/forward semantics.** Screen-to-screen transitions and home-tab selection push
  history entries; within-screen state that is not in the URL (detail's tournament/register
  tab, setup section tabs, dialogs, sheet edits) does not. The tournament detail's close
  control returns to the list it was opened from — now expressed as navigating back to `/`
  with that tab, satisfying the existing `fencer-home` requirement.
- **Correction to the draft note:** `TournamentDetail`'s `readOnly` flag is not an organizer
  preview — `FencerHome` passes `tournament.date < today`, i.e. "this tournament has already
  been held, so offer no register/pay/cancel actions". It therefore needs no URL of its own;
  the detail derives it from the tournament date it already fetches, which additionally makes
  a *deep link* to a past tournament read-only (today it would not be). No
  `/organizer/:slug/preview` route is introduced; the organizer's preview of the fencer faces
  lives inside the console's Setup phase (`setup-preview`) and stays there.

**Not in scope:** any change to what the screens display or how they fetch, beyond the
console's slug resolution and the detail's `readOnly` derivation; server-side rendering;
a routing test runner (Playwright smoke tests become a natural follow-up once stable URLs
exist, but adding the runner is its own change).

## Capabilities

### New Capabilities
- `routing`: the URL scheme, history semantics (back/forward, refresh), deep-link
  resolution including the unauthenticated case, and not-found behaviour.

### Modified Capabilities
- `etl-console`: the console is reachable and reloadable by URL (slug + phase) and resolves
  its tournament from the slug, rather than depending on the picker's in-memory hand-off.
- `fencer-home`: tournament entries and the filter tabs become real links carrying `/t/:slug`
  and `?tab=` URLs (so middle-click, copy-link and back work); the detail's read-only mode
  is stated as a property of the tournament's date rather than of how the page was opened.

`tournament-admin` keeps its "creator lands in the console's Setup phase" requirement
unchanged — it is satisfied by navigating to `/organizer/:slug/console/setup`, which is an
implementation detail, not a requirement change. `setup-navigation` and `setup-preview` are
untouched: their tabs stay within-screen state.

## Impact

**Frontend (`frontend/src/`)** — `App.tsx` (route table replaces the view state machine;
largest diff), `main.tsx` (router provider), `Console.tsx` (accepts a slug, self-loads,
takes the phase from the route), `TournamentPicker.tsx` (`onPick` becomes navigation),
`TournamentDetail.tsx` (derives `readOnly`, close navigates), `FencerHome.tsx` +
`FencerShell.tsx` (anchors for cards and tabs), `AccountMenu.tsx` (menu entries become
links), `Login.tsx` (return-to), `AdminPanel.tsx` / `ProfilePage.tsx` (nav props drop). New
`NotFound.tsx`; i18n strings (`cs`, `en`) for the not-found screen; `index.css` only if the
not-found screen needs anything beyond existing classes. `api.ts` needs no new call —
`api.tournament(slug)` already exists. New dependency `react-router-dom` in `package.json`.

**Backend** — no API change. The dev server (Vite) does history-API fallback out of the
box; `backend/app/main.py` serves no static frontend today, so nothing there needs a
fallback yet. Whatever eventually serves the built bundle MUST fall back to `index.html`
for unknown paths, or deep links 404 before React loads — recorded in design as a
deployment constraint.

**Design constraints** — the not-found screen and any loading state are bound by
`CLAUDE.md` / `openspec/squire-design-spec.md`: no spinners, gradients, shadows, radii
> 2px, emoji, or hexes outside `tokens.css`.

**Verification** — the frontend has no routing test runner (`npm run lint` is
`tsc -b --noEmit`), so verification is typecheck, build, `vitest run` for the existing unit
tests, and driving the app: back/forward across all screens, F5 on each route, a deep link
to `/organizer/:slug/console/payments` while logged out (expect Login, then that phase), a
nonsense slug, `/?tab=mine` on refresh, and middle-clicking a tournament card from home.
