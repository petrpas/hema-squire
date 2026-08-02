## MODIFIED Requirements

### Requirement: Fencer Home landing
Every logged-in account SHALL land on the Fencer Home page after login. The page SHALL be a full-screen console-style view with a top bar and a tournament list, filtered by three disjoint tabs: Otevřené turnaje (Open — published, non-cancelled, upcoming tournaments whose registration is open right now), Vyhlášené turnaje (Announced — published, non-cancelled, upcoming tournaments whose registration is not open: not yet opened or already closed), and Proběhlé turnaje (Past — the fencer's own history). "Published" means the tournament carries a publication record, not that its setup happens to be complete. The Open tab SHALL be selected after login. Upcoming tournaments SHALL be ordered by date ascending and each card SHALL show: the tournament logo on the left when one is set, the tournament name, the subtitle beneath the name when one is set, organizer names, date, location, the offered disciplines with registered numbers as taken/capacity (e.g. LS 18/25), and the registration status — open, opens on a date, or closed. Card content SHALL have 1 em of left and right padding inside the card. Date and place SHALL be presented as a responsive multi-column layout rather than one long line, collapsing to fewer columns on narrow screens. The card layout SHALL render correctly whether or not a logo, subtitle, or location is present. Each upcoming tournament SHALL offer a Register action when the account has no active registration for it, or a Manage registration action when it does; both open the tournament detail page. Each tab SHALL show its own empty-state message when it lists nothing.

#### Scenario: Open tournament listed with counts
- **WHEN** a fencer opens Fencer Home while a published upcoming tournament with disciplines LS (18 of 25 taken) and SA (25 of 16 seats incl. queue) is open for registration
- **THEN** the tournament appears in the Open tab with its name, organizers, date, location, per-discipline numbers, an "open" status, and a Register button

#### Scenario: Card shows logo and subtitle when set
- **WHEN** a listed tournament has a logo and a subtitle
- **THEN** its card shows the logo on the left and the subtitle beneath the name, with date and place in the responsive column layout

#### Scenario: Card degrades without logo, subtitle, or location
- **WHEN** a listed tournament has no logo, no subtitle, and no location
- **THEN** its card renders correctly without empty gaps for the missing logo, subtitle, or location line

#### Scenario: Tabs are disjoint
- **WHEN** a published upcoming tournament's registration has not yet opened or has already closed
- **THEN** it appears in the Announced tab with its status badge and not in the Open tab

#### Scenario: Login lands on the Open tab
- **WHEN** any account logs in
- **THEN** Fencer Home opens with the Open tab selected

#### Scenario: Draft hidden from fencers
- **WHEN** a tournament has not been published
- **THEN** it does not appear in any Fencer Home tab, even when its mandatory setup is complete

#### Scenario: Existing registration changes the action
- **WHEN** the fencer already has an active (reserved or paid) registration for a listed upcoming tournament
- **THEN** that tournament shows Manage registration instead of Register

### Requirement: Past tournaments tab
The Proběhlé turnaje tab SHALL list only published, non-cancelled tournaments dated before today in which the account participated — held a non-cancelled registration (paid, reserved, or substitute) — or which the account organized, ordered by date descending. Other past tournaments SHALL NOT be listed. Cards SHALL show the tournament name, organizer names, date, location, and per-discipline counts; a tournament where the account only organized SHALL be marked as organized instead of showing a registration state. Selecting a past tournament SHALL open its detail in read-only mode.

#### Scenario: Participated tournament listed
- **WHEN** a fencer opens the Past tab having had a paid registration for a tournament held last month
- **THEN** that tournament is listed with its data and opens in read-only detail when selected

#### Scenario: Unrelated and cancelled-registration tournaments hidden
- **WHEN** a past tournament exists where the fencer had no registration or only a cancelled one, and the fencer is not its organizer
- **THEN** it does not appear in the Past tab

#### Scenario: Organized tournament marked
- **WHEN** an organizer opens the Past tab for a tournament they organized but did not fence in
- **THEN** the tournament is listed with an organizer mark and no registration state

#### Scenario: Never-published past tournament hidden
- **WHEN** a past tournament was never published
- **THEN** it does not appear in the Past tab for anyone, including its organizer
