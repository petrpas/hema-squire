## MODIFIED Requirements

### Requirement: Every screen has a URL
The application SHALL address each of its screens by a URL, and the browser's address bar
SHALL always name the screen on display. The scheme SHALL be:

| path | screen | credential |
| --- | --- | --- |
| `/` | the tournament list, on its default tab | public |
| `/?tab=announced` \| `open` \| `past` | the tournament list on that filter tab | public |
| `/?tab=mine` | the tournament list on the Mine tab | required |
| `/t/:slug` | the tournament's fencer-facing detail page | public |
| `/organizer` | the tournament picker | required |
| `/organizer/:slug/console` | that tournament's console, Load phase | required |
| `/organizer/:slug/console/:phase` | that tournament's console on that phase | required |
| `/admin` | the admin panel | required |
| `/profile` | the profile page | required |

Navigating to a screen SHALL change the URL, and entering a URL SHALL open that screen, in
both directions and for every row of the table. No screen SHALL be reachable only through
in-memory state.

A row marked public SHALL render for a visitor holding no credential. A row marked required
SHALL present the sign-in screen instead, per `Unauthenticated visits keep their destination`.

#### Scenario: Address bar follows navigation
- **WHEN** an organizer moves from the tournament list to the picker and opens a tournament's console
- **THEN** the address bar reads `/`, then `/organizer`, then `/organizer/<slug>/console/setup` or the phase opened, without the page being reloaded

#### Scenario: URL opens the screen
- **WHEN** a logged-in fencer types `/t/spring-open-2026` into a fresh tab
- **THEN** the tournament detail page for `spring-open-2026` opens directly, with no intermediate landing on the tournament list

#### Scenario: Public URL opens without a credential
- **WHEN** a visitor holding no credential types `/t/spring-open-2026` into a fresh tab
- **THEN** that tournament's detail page opens, and the sign-in screen is not shown

#### Scenario: Console short URL keeps working
- **WHEN** a logged-in organizer opens `/organizer/spring-open-2026/console`
- **THEN** the console opens on the Load phase and the URL is left as typed

### Requirement: Unauthenticated visits keep their destination
An unauthenticated visit to a route that requires a credential SHALL present the Login screen
while leaving the requested URL in the address bar, and on successful authentication SHALL
show the originally requested screen — path, tournament slug, console phase, and query string
alike. Logging in SHALL NOT leave a history entry that Back would return to afterwards.
Logging out SHALL return to `/`, which is public and therefore still renders.

An unauthenticated visit to a public route SHALL NOT present the Login screen. The tournament
list and a tournament's detail are readable without an account (`public-browsing`); gating
them would be the thing this rule exists to prevent.

A stored credential that the server rejects SHALL be treated as an unauthenticated visit
rather than as an authenticated one. WHEN the request that establishes the session is
answered with 401, the stored credential SHALL be discarded. On a route requiring a
credential the Login screen SHALL then be presented — at the URL the visitor is on, so an
expired session costs them the session and not their destination as well. On a public route
the screen SHALL be shown in its anonymous form instead, since the visitor can still read it.

Any other failure of that request — a lost network, a name-resolution failure, a server
error — SHALL NOT discard the credential and SHALL NOT sign the visitor out. Those failures
resolve themselves, and ending a session over one loses the visitor's place for a reason
that was never about their credential.

The gate SHALL NOT present an authenticated shell on the strength of a stored credential
alone. A shell rendered with an empty identity and empty lists, because the credential
behind it was rejected, is indistinguishable from a broken application and does not tell
the visitor they need to sign in.

#### Scenario: Deep link survives login
- **WHEN** a logged-out visitor follows `/organizer/spring-open-2026/console/payments`
- **THEN** Login is shown, and after they authenticate the Payments phase of that tournament's console is displayed

#### Scenario: Query string survives login
- **WHEN** a logged-out visitor follows `/?tab=mine`
- **THEN** Login is shown, and after they authenticate the tournament list opens on the Mine tab

#### Scenario: Public deep link is not gated
- **WHEN** a logged-out visitor follows `/?tab=past`
- **THEN** the Past list is shown and Login is not

#### Scenario: Back after login does not return to Login
- **WHEN** a visitor authenticates from a deep link and presses Back
- **THEN** the Login screen is not shown again

#### Scenario: Logout returns home
- **WHEN** an authenticated user logs out from any screen
- **THEN** the tournament list is shown at `/`, in its anonymous form

#### Scenario: Expired credential on returning to the app
- **WHEN** a fencer reopens a tab on `/profile` holding a credential the server no longer accepts, and the session request is answered with 401
- **THEN** the credential is discarded and Login is shown, rather than a signed-in shell with an empty identity

#### Scenario: Expired credential keeps the destination
- **WHEN** that fencer was on `/t/spring-open-2026` when the credential was rejected
- **THEN** the tournament's detail is shown in its anonymous form at the same URL, offering sign-in, rather than a signed-in shell with a blank identity

#### Scenario: Offline visitor is not signed out
- **WHEN** the session request fails because the device has no network
- **THEN** the stored credential is kept and the visitor is not returned to Login
