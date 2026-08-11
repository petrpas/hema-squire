Change: add-url-routing
Why
The frontend has no notion of URLs. Navigation is a single useState<View> in App.tsx ("home" | "tournament" | "picker" | "console" | "admin" | "profile") and screen changes never touch the History API — no pushState, no popstate listener, no hash. From the browser's point of view the entire app is one history entry, with three user-visible consequences:

The back button exits the app instead of returning to the previous screen — on mobile the system back gesture does the same, which reads as a broken app.
No shareable links. An organizer cannot send fencers a URL for a specific tournament; every visitor lands on home and must find the tournament manually. For a registration system whose core loop is "send people a link", this is the most damaging consequence.
Refresh resets everything. F5 anywhere returns to home and discards the selected tournament and console phase.
What Changes
Introduce react-router-dom (new dependency) and replace the view state machine in App.tsx with routes. The View type, setView callbacks, and the prop-drilled navigation handlers (onProfile, onAdmin, onOrganizer, onFencer, onBack) are replaced by route navigation; screens keep their own data-fetching behaviour.
URL scheme (final naming to be settled in design.md, but the shape is):
/ — FencerHome
/t/:slug — TournamentDetail, fencer-facing; the read-only organizer preview (today's detailReadOnly flag) becomes its own URL rather than invisible state, e.g. /organizer/:slug/preview
/organizer — TournamentPicker
/organizer/:slug/console/:phase? — Console; phase in the URL so refresh and back/forward preserve it, defaulting to load when absent
/admin — AdminPanel
/profile — ProfilePage
unknown paths — a minimal not-found screen offering the way home, styled within the design system
Console becomes self-loading. Today Console receives a full Tournament object from TournamentPicker via onPick; a deep link has no picker to pass it. Console (or a thin route wrapper) SHALL resolve the tournament from :slug itself, reusing the existing API, and render the design-system loading treatment meanwhile. A slug the caller may not access or that does not exist yields the not-found screen, not a blank console.
Auth gate becomes a redirect with return-to. Today !authed renders <Login> in place and the intended destination is lost. An unauthenticated visit to any route SHALL show Login and, on success, land on the originally requested URL. Logout returns to /.
Back/forward semantics: screen-to-screen transitions push history entries; within-screen state that is not in the URL (filters, dialog open/close, sheet edits) does not. Login must not create a history entry that back would return to after authentication.
Not in scope: any change to what the screens display or how they fetch beyond the Console slug-resolution above; server-side rendering; introducing a frontend test runner (Playwright routing smoke tests are a natural follow-up change once routing exists and would give stable URLs to screenshot-test against, but adding the runner is its own piece of work).

Capabilities
New Capabilities
routing: the URL scheme, history semantics (back/forward, refresh), deep-link resolution including the unauthenticated case, and not-found behaviour.
Modified Capabilities
etl-console: the console is reachable and reloadable by URL (slug + phase) rather than only via the picker's in-memory hand-off.
fencer-home: tournament entries link to /t/:slug URLs (real anchors, so middle-click and copy-link work) rather than invoking state callbacks.
(Verify against current specs during propose — if the picker hand-off or detail read-only mode is specified elsewhere, e.g. setup-navigation or tournament-admin, the delta lands there instead.)

Impact
Frontend (frontend/src/): App.tsx (route table replaces the view state machine; largest diff), main.tsx (router provider), Console.tsx (accept slug, self-load, phase from route), TournamentPicker.tsx (onPick becomes navigation), TournamentDetail.tsx (readOnly from route), FencerHome.tsx (anchors), Login.tsx (return-to), api.ts only if no fetch-tournament-by-slug call exists yet; i18n strings for the not-found screen; index.css only if not-found needs anything beyond existing classes. New dependency react-router-dom in package.json.

Backend: no API change expected. The deployment that serves the built frontend MUST fall back to index.html for unknown paths (history-API fallback), or deep links 404 at the server before React loads — verify how the app is served and adjust if needed. Vite dev server handles this out of the box.

Design constraints: the not-found screen and any loading state are subject to CLAUDE.md / openspec/squire-design-spec.md — no spinners, gradients, shadows, radii > 2px, or hexes outside tokens.css.

Verification: no frontend test runner (npm run lint is tsc -b --noEmit), so verification is typecheck, build, and driving the app: back/forward across all screens, F5 on each route, a deep link to /organizer/:slug/console/payments while logged out (expect Login, then that console phase), a nonsense slug, and middle-clicking a tournament link from home.