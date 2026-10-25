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
| `/t/:slug/entrants` | that page on its Entrants tab, at the first discipline | public |
| `/t/:slug/entrants/:discipline` | that page on its Entrants tab, at that discipline's roster | public |
| `/t/:slug/entrants/events/:item` | that page on its Entrants tab, at that side event's roster | public |
| `/t/:slug/manage#<key>` | that page on its registration tab, managing the guest registration the key names | the key |
| `/verify#<key>` | finishing a signup: the account is created and the fencer signed in | the key |
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
A row marked with the key SHALL render for a visitor holding no credential. Its key SHALL be
carried in the fragment, which the browser does not send to the server and does not pass on
in a referrer, and SHALL be presented to the API by the page. A key that is not accepted
SHALL produce the row's own statement that the link is no longer valid, never the sign-in
screen and never the not-found screen.

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

#### Scenario: A roster's address
- **WHEN** a visitor holding no credential types `/t/spring-open-2026/entrants/sabre-open` into a fresh tab
- **THEN** that tournament's detail page opens on its Entrants tab at the Sabre Open roster, and the sign-in screen is not shown

#### Scenario: An unknown discipline
- **WHEN** a visitor opens `/t/spring-open-2026/entrants/no-such-discipline`
- **THEN** the not-found screen is shown

#### Scenario: A manage link survives a refresh
- **WHEN** a guest on `/t/spring-open-2026/manage#<key>` refreshes the page
- **THEN** the same registration is shown again, and the key never appeared in a request line the server received

#### Scenario: A verification link opened on another device
- **WHEN** a fencer who signed up on a laptop opens the verification link on a phone
- **THEN** the account is created and the phone is signed in, landing where the signup was started from
