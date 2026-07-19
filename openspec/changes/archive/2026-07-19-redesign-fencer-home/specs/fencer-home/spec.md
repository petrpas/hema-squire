## MODIFIED Requirements

### Requirement: Fencer Home landing
Every logged-in account SHALL land on the Fencer Home page after login. The page SHALL be a full-screen console-style view with a top bar and a tournament list, filtered by three disjoint tabs: Otevřené turnaje (Open — published, non-cancelled, upcoming tournaments whose registration is open right now), Vyhlášené turnaje (Announced — published, non-cancelled, upcoming tournaments whose registration is not open: not yet opened or already closed), and Proběhlé turnaje (Past — the fencer's own history). The Open tab SHALL be selected after login. Upcoming tournaments SHALL be ordered by date ascending and each card SHALL show: tournament name, organizer names, date, location, the offered disciplines with registered numbers as taken/capacity (e.g. LS 18/25), and the registration status — open, opens on a date, or closed. Each upcoming tournament SHALL offer a Register action when the account has no active registration for it, or a Manage registration action when it does; both open the tournament detail page. Each tab SHALL show its own empty-state message when it lists nothing.

#### Scenario: Open tournament listed with counts
- **WHEN** a fencer opens Fencer Home while a published upcoming tournament with disciplines LS (18 of 25 taken) and SA (25 of 16 seats incl. queue) is open for registration
- **THEN** the tournament appears in the Open tab with its name, organizers, date, location, per-discipline numbers, an "open" status, and a Register button

#### Scenario: Tabs are disjoint
- **WHEN** a published upcoming tournament's registration has not yet opened or has already closed
- **THEN** it appears in the Announced tab with its status badge and not in the Open tab

#### Scenario: Login lands on the Open tab
- **WHEN** any account logs in
- **THEN** Fencer Home opens with the Open tab selected

#### Scenario: Draft hidden from fencers
- **WHEN** a tournament's mandatory setup is incomplete
- **THEN** it does not appear in any Fencer Home tab

#### Scenario: Existing registration changes the action
- **WHEN** the fencer already has an active (reserved or paid) registration for a listed upcoming tournament
- **THEN** that tournament shows Manage registration instead of Register

## ADDED Requirements

### Requirement: Fencer identity header
The Fencer Home top bar SHALL show, left to right: the Hema Squire logo, the three tournament filter tabs, the fencer's display name with their hemaratings identity, and the account menu (⋯). WHEN the account has a bound hemaratings profile, the identity SHALL read "HRID: <id>" and link to the fighter's hemaratings.com profile page in a new browser tab. WHEN no hemaratings profile is bound, the identity SHALL read "no hemaratings" and navigate to the Profile page, where binding is offered.

#### Scenario: Bound fencer sees HRID link
- **WHEN** a fencer whose account is bound to hemaratings fighter 1234 opens Fencer Home
- **THEN** the header shows their name and "HRID: 1234" linking to the hemaratings fighter page

#### Scenario: Unbound fencer is pointed to binding
- **WHEN** a fencer without a bound hemaratings profile clicks "no hemaratings" in the header
- **THEN** the Profile page opens

### Requirement: Past tournaments tab
The Proběhlé turnaje tab SHALL list only non-cancelled tournaments dated before today in which the account participated — held a non-cancelled registration (paid, reserved, or substitute) — or which the account organized, ordered by date descending. Other past tournaments SHALL NOT be listed. Cards SHALL show the tournament name, organizer names, date, location, and per-discipline counts; a tournament where the account only organized SHALL be marked as organized instead of showing a registration state. Selecting a past tournament SHALL open its detail in read-only mode.

#### Scenario: Participated tournament listed
- **WHEN** a fencer opens the Past tab having had a paid registration for a tournament held last month
- **THEN** that tournament is listed with its data and opens in read-only detail when selected

#### Scenario: Unrelated and cancelled-registration tournaments hidden
- **WHEN** a past tournament exists where the fencer had no registration or only a cancelled one, and the fencer is not its organizer
- **THEN** it does not appear in the Past tab

#### Scenario: Organized tournament marked
- **WHEN** an organizer opens the Past tab for a tournament they organized but did not fence in
- **THEN** the tournament is listed with an organizer mark and no registration state

### Requirement: Read-only past tournament detail
WHEN a tournament detail is opened from the Past tab, the page SHALL present the tournament information (name, date, location, organizers, disciplines with fees, extra services with prices) and, when the account had a registration, its summary — state, selected disciplines and extra services, and the computed total. The page SHALL NOT offer registration, payment instructions, or cancellation.

#### Scenario: Past detail shows history without actions
- **WHEN** a fencer opens a past tournament where they had a paid registration
- **THEN** the detail shows the tournament information and their paid registration summary, with no Register button, payment panel, or cancel action
