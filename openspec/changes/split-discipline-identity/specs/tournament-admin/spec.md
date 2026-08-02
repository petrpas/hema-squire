## MODIFIED Requirements

### Requirement: Tournament definition
A tournament SHALL be defined by internal name, display name, an optional subtitle, an optional logo, date, communication language, location (free text), an optional description, a qualification statement, a list of titular organizers, and a set of disciplines. The subtitle is free text that MAY be longer than the display name and is frequently empty; every presentation of the tournament SHALL render correctly whether or not the subtitle is set. The logo is an optional image supplied by the organizer, stored with the tournament and served for display; the system SHALL bound its size on upload (reject oversized uploads and re-encode to a bounded image) so it stays small. The description is optional free-form text of arbitrary length, authored in markdown and stored verbatim as its markdown source; it SHALL be presented as formatted content according to `organizer-prose`, which fixes the honored subset, the sanitizer allowlist, and the presentation rules. Titular organizers are free-text names of clubs or other entities shown publicly as the tournament's organizers, each with an optional link; they are independent of account-based console access.

Each discipline SHALL have a slug identifying it within the tournament, a human-readable name, a classification of weapon × gender × material, a **kind** (individual or team), a capacity limit, a unit price, optional schedule fields (`when`, `where`) mainly for multi-day events, and an optional ruleset consisting of a short style name and an optional external link. Slug, classification, and the derived taxonomy code are fixed by `discipline-identity`, which also fixes that a tournament MAY offer several disciplines classified alike and that a weapon outside the HEMA taxonomy is accepted. A **team** discipline SHALL additionally have a minimum and a maximum roster size; for it, the capacity limit counts teams rather than fencers and the unit price is the price of entering one team, as fixed by `team-disciplines`. An **individual** discipline is the default and behaves exactly as disciplines behaved before team disciplines existed. In the console, a discipline SHALL be identified by its name in emphasized text with its slug alongside it in faded ink, and each of its optional fields (`when`, `where`, ruleset name, ruleset link) SHALL carry a help hint stating what belongs in it; the capacity and price columns SHALL be labelled according to the row's kind, so that a team row states that its capacity counts teams and its price is charged per team.

A discipline row SHALL offer its weapon as a choice among the taxonomy weapons that also accepts a weapon they do not name, and SHALL offer its slug as a prefilled, editable field carrying a help hint stating that the slug names the discipline in exports and spreadsheets and is not shown to fencers. A row whose slug is frozen (`discipline-identity`) SHALL present it as read-only rather than offering an edit that would be refused.

Subtitle, logo, description, qualification, disciplines (including their slug, classification, kind, roster bounds, schedule and ruleset fields) and titular organizers SHALL be editable in the console Setup phase, disciplines and organizers as row tables with add and remove. The communication language SHALL NOT be editable in Setup: it is assigned when the tournament is created and thereafter governs fencer emails without being offered as a settings field. The Setup section carrying the tournament's own identity fields SHALL NOT be given a section heading of its own, and SHALL present those fields in this order: display name, subtitle, logo, date, location, description, qualification statement, registration opens, registration closes, registration instructions.

#### Scenario: Organizer configures disciplines
- **WHEN** the organizer adds an open longsword and a women's sabre in the Setup table, each with a capacity and a unit price
- **THEN** registration offers exactly those disciplines under those capacity constraints at those prices, each with a generated slug

#### Scenario: Organizer configures two tiers of one weapon
- **WHEN** the organizer adds two longsword disciplines, names them for the top and open brackets, and gives each its own capacity and price
- **THEN** both rows are accepted with distinct slugs, and registration offers them as two separate entries

#### Scenario: Organizer configures a team discipline alongside its individual counterpart
- **WHEN** the organizer adds an individual longsword discipline and a team longsword discipline with roster bounds 3 and 4
- **THEN** both are accepted, the team row's capacity is labelled as counting teams and its price as charged per team, and neither is rejected as a duplicate

#### Scenario: Organizer enters a weapon the taxonomy does not name
- **WHEN** the organizer adds a discipline whose weapon is Messer and gives it a name
- **THEN** the row is accepted and the discipline is offered like any other

#### Scenario: Slug editable then frozen
- **WHEN** the organizer edits a discipline's slug before anyone has registered, and attempts the same edit after a fencer has entered it
- **THEN** the first edit is accepted and the second is refused, the row presenting the slug as read-only thereafter

#### Scenario: Slug explains itself
- **WHEN** the organizer reaches the help marker next to a discipline's slug field
- **THEN** a hint appears stating that the slug names the discipline in exports and spreadsheets and is not shown to fencers

#### Scenario: Roster bounds offered only for team rows
- **WHEN** the organizer sets a discipline row's kind to individual
- **THEN** the row offers no roster bounds, and any previously entered bounds are not required

#### Scenario: Discipline schedule and ruleset captured
- **WHEN** the organizer sets a discipline's when to "Saturday", where to "Main Hall — Kurtzstrasse 21", and ruleset to "Right of Way" with an external link
- **THEN** the tournament information presents that discipline with its schedule and a ruleset link, and omits those lines for disciplines that leave them empty

#### Scenario: Optional discipline fields explain themselves
- **WHEN** the organizer reaches the help marker next to a discipline's `when`, `where`, ruleset name, or ruleset link field
- **THEN** a hint appears describing what belongs in that field (for example, for `when`: that it takes a rough time such as "Saturday morning")
