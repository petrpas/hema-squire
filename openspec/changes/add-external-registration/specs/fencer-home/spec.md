## MODIFIED Requirements

### Requirement: Fencer Home landing
Every logged-in account SHALL land on the Fencer Home page after login. The page SHALL be a full-screen console-style view with a top bar and a tournament list, filtered by four tabs: Vyhlášené turnaje (Announced — published, non-cancelled, upcoming tournaments whose registration is not open: not yet opened or already closed), Otevřené turnaje (Open — published, non-cancelled, upcoming tournaments whose registration is open right now), Proběhlé turnaje (Past — every published, non-cancelled tournament dated before today, whoever was involved), and Moje turnaje (Mine — the account's own, per its own requirement). The first three SHALL be disjoint and SHALL together hold every published, non-cancelled tournament; Mine overlaps them by design. "Published" means the tournament carries a publication record, not that its setup happens to be complete. The Open tab SHALL be selected after login. Upcoming tournaments SHALL be ordered by date ascending, tournaments already held by date descending.

Each card SHALL present, in this order: the tournament logo at the left when one is set, then the tournament name, the subtitle beneath it when one is set, then the date and the location together on their own line in bold, then the organizer names, then the offered disciplines with registered numbers as taken/capacity, and the registration status — open, opens on a date, or closed. The date and place line SHALL separate its parts with the spaced middle dot and SHALL wrap rather than overflow on a narrow screen. The logo SHALL be drawn at twice the size a card gave it before this change. Card content SHALL have 1 em of left and right padding inside the card. The card layout SHALL render correctly whether or not a logo, subtitle, location, or organizer is present. Each upcoming tournament SHALL offer a Register action when the account has no active registration for it, or a Manage registration action when it does; both open the tournament detail page. **A tournament whose registrations the organizer keeps SHALL offer in that place a way out to where its registration is held** (`registration-ownership`, `external-registration`), instead of a Register action and not beside one. The action SHALL state that registration is kept elsewhere; it SHALL NOT state that registration is closed, which would be untrue of a window that never existed here. Where such a tournament records no address, the card SHALL state that registration is held elsewhere without offering an action, rather than offering one that leads nowhere. Each tab SHALL show its own empty-state message when it lists nothing.

A discipline on a card SHALL be labelled by its name, never by its slug (`discipline-identity`). Names are longer than the codes they replace and a tournament MAY offer several disciplines whose names differ only in a trailing qualifier, so the discipline row on a card SHALL wrap across lines rather than truncate, overflow, or force the card wider, and SHALL remain legible on the narrowest supported screen.

#### Scenario: Open tournament listed with counts
- **WHEN** a fencer opens Fencer Home while a published upcoming tournament with two disciplines (18 of 25 taken, and 25 of 16 seats incl. queue) is open for registration
- **THEN** the tournament appears in the Open tab with its name, date and place in bold on their own line, organizers on the line below, each discipline named with its numbers, an "open" status, and a Register button

#### Scenario: Card lines in order
- **WHEN** a card renders a tournament with a subtitle, a location and two organizers
- **THEN** the name, the subtitle, the bold date and place line, and the organizers line appear in that order, with the logo at the left

#### Scenario: Disciplines named, not coded
- **WHEN** a card lists a tournament's disciplines
- **THEN** each is labelled by its name, and no slug appears on the card

#### Scenario: Many long discipline names wrap
- **WHEN** a card lists six disciplines whose names include trailing qualifiers, on a narrow screen
- **THEN** the discipline row wraps across lines, every name stays legible and untruncated, and the card does not widen or overflow

#### Scenario: Card shows logo and subtitle when set
- **WHEN** a listed tournament has a logo and a subtitle
- **THEN** its card shows the logo at the left at the enlarged size and the subtitle beneath the name

#### Scenario: Card degrades without logo, subtitle, or location
- **WHEN** a listed tournament has no logo, no subtitle, and no location
- **THEN** its card renders correctly without empty gaps for the missing logo, subtitle, or location line

#### Scenario: Tabs are disjoint
- **WHEN** a published upcoming tournament's registration has not yet opened or has already closed
- **THEN** it appears in the Announced tab with its status badge and not in the Open tab

#### Scenario: Held tournament leaves the upcoming tabs
- **WHEN** a published tournament's date passes
- **THEN** it appears in the Past tab and in neither Announced nor Open

#### Scenario: Login lands on the Open tab
- **WHEN** any account logs in
- **THEN** Fencer Home opens with the Open tab selected

#### Scenario: Draft hidden from fencers
- **WHEN** a tournament has not been published
- **THEN** it does not appear in any Fencer Home tab, even when its mandatory setup is complete

#### Scenario: An organizer-kept tournament points outward
- **WHEN** a fencer opens Fencer Home while a published upcoming tournament whose registrations the organizer keeps is listed
- **THEN** its card offers a way out to where registration is held, offers no Register action, and does not describe registration as closed

#### Scenario: An organizer-kept tournament with no address recorded
- **WHEN** such a tournament records no external registration address
- **THEN** the card states that registration is held elsewhere and offers no action

#### Scenario: Existing registration changes the action
- **WHEN** the fencer already has an active (reserved or paid) registration for a listed upcoming tournament
- **THEN** that tournament shows Manage registration instead of Register
