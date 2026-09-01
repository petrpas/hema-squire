## MODIFIED Requirements

### Requirement: Unauthenticated visits keep their destination
An unauthenticated visit to any route SHALL present the Login screen while leaving the
requested URL in the address bar, and on successful authentication SHALL show the originally
requested screen — path, tournament slug, console phase, and query string alike. Logging in
SHALL NOT leave a history entry that Back would return to afterwards. Logging out SHALL
return to `/`.

A stored credential that the server rejects SHALL be treated as an unauthenticated visit
rather than as an authenticated one. WHEN the request that establishes the session is
answered with 401, the stored credential SHALL be discarded and the Login screen SHALL be
presented — at the URL the visitor is on, so an expired session costs them the session and
not their destination as well.

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
- **THEN** Login is shown, and after they authenticate Fencer Home opens on the Mine tab

#### Scenario: Back after login does not return to Login
- **WHEN** a visitor authenticates from a deep link and presses Back
- **THEN** the Login screen is not shown again

#### Scenario: Logout returns home
- **WHEN** an authenticated user logs out from any screen
- **THEN** the Login screen is shown at `/`

#### Scenario: Expired credential on returning to the app
- **WHEN** a fencer reopens a tab holding a credential the server no longer accepts, and the session request is answered with 401
- **THEN** the credential is discarded and Login is shown, rather than a signed-in shell with an empty identity and an empty list

#### Scenario: Expired credential keeps the destination
- **WHEN** that fencer was on `/t/spring-open-2026` when the credential was rejected
- **THEN** Login is shown at `/t/spring-open-2026`, and after they authenticate that tournament's detail is displayed

#### Scenario: Offline visitor is not signed out
- **WHEN** the session request fails because the device has no network
- **THEN** the stored credential is kept and the visitor is not returned to Login
