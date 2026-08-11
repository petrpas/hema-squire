## MODIFIED Requirements

### Requirement: Section allocation to tabs
Every Setup settings section SHALL belong to exactly one tab, and no section SHALL be
dropped, duplicated, or split by this navigation:

- `TOURNAMENT` — the tournament's identity fields (display name, subtitle, logo, date,
  location, description, qualification statement, registration window, registration
  instructions) and the titular organizers.
- `DISCIPLINES` — the disciplines table and the team composition deadline.
- `EXTRA` — the extra-items table.
- `PAYMENTS` — the bank account payments are collected into, the currency and
  exchange-rate section, the VS series statement, and the discount list.
- `OTHER` — console team access and the danger zone.
- `PUBLISH` — the publication state, the items blocking publication, and the publish
  action, as fixed by `tournament-publication`.

The bank account SHALL stand first on `PAYMENTS`, before the currency it is denominated
in. It SHALL be offered nowhere else: a field that governs whether a tournament may be
published SHALL have one editor, so that an organizer reading it in Setup is reading the
value the publication check reads.

The team composition deadline SHALL sit below the disciplines table and SHALL be offered
only while at least one discipline row is of the team kind, including a row added in the
current unsaved draft. It SHALL be written by the `DISCIPLINES` tab's single save control
along with the table, and a deadline already stored on a tournament whose team
disciplines have all been removed SHALL be retained rather than cleared.

Within a tab, sections SHALL keep their existing relative order, except on
`TOURNAMENT`, where the identity fields follow the order fixed by `tournament-admin`.
Sections that are shown only to the tournament owner SHALL keep that restriction; when
a non-owner opens `OTHER` and it would therefore be empty, the tab SHALL NOT be
offered at all rather than opening onto nothing. `PUBLISH` SHALL be offered to every
account with console access.

#### Scenario: Every section reachable
- **WHEN** the organizer visits all six tabs
- **THEN** every settings section that existed before this change is present on exactly one of them

#### Scenario: Deadline appears with the first team row
- **WHEN** the organizer sets a discipline row's kind to team in an unsaved draft
- **THEN** the composition deadline field appears below the table, and saving the tab writes both the row and the deadline

#### Scenario: Deadline hidden without team disciplines
- **WHEN** the tournament offers only individual disciplines
- **THEN** no composition deadline field is shown on `DISCIPLINES`

#### Scenario: Stored deadline survives removing the team discipline
- **WHEN** the organizer removes the last team discipline from a tournament that had a composition deadline set
- **THEN** the field stops being shown and the stored deadline is not cleared

#### Scenario: Money settings together
- **WHEN** the organizer opens `PAYMENTS`
- **THEN** the bank account, the currency and exchange rate, the VS series statement, and the discount list are shown together, with the bank account first

#### Scenario: Bank account has one editor
- **WHEN** the organizer looks for the bank account in the console's payments-phase parameters
- **THEN** it is not offered there, and `PAYMENTS` in Setup is the only place it can be edited

#### Scenario: Non-owner sees no empty tab
- **WHEN** a console team member who is not the tournament owner opens Setup
- **THEN** the `OTHER` tab is not offered, and the remaining five tabs — including `PUBLISH` — behave as usual

### Requirement: Per-tab incompleteness markers
Each tab that contains at least one unconfigured mandatory item SHALL carry a marker in
the tab bar, drawn in `--stamp` with a localized accessible label, so that an item read
on `PUBLISH` can be traced to the tab that resolves it. An item SHALL be attributed to
the tab holding the section that resolves it: location and organizers to `TOURNAMENT`,
missing disciplines and missing discipline prices to `DISCIPLINES`, missing extra-item
prices to `EXTRA`, and the missing bank account, missing discount amounts and the
currency-mode conflicts to `PAYMENTS`. An item the client does not recognize SHALL mark
no tab and SHALL NOT break the tab bar. `PUBLISH` SHALL carry a marker whenever any
other tab does, since that is where the items are listed.

The settings pane header SHALL consist of the tab bar alone. No list of unconfigured
items SHALL appear outside the `PUBLISH` tab. The header SHALL stay in place while the
selected tab's sections scroll beneath it, and no part of a scrolling section SHALL
ever be visible above it or through its background, at any scroll position and on any
tab.

#### Scenario: Marker points at the responsible tab
- **WHEN** the tournament has a discipline with no price and no other missing item
- **THEN** the `DISCIPLINES` tab carries the marker, `PUBLISH` carries one, and no other tab does

#### Scenario: Missing bank account marks PAYMENTS
- **WHEN** a tournament that charges has no bank account recorded and no other missing item
- **THEN** the `PAYMENTS` tab carries the marker, `PUBLISH` carries one, and no other tab does

#### Scenario: Marker appears when a price is set on another tab
- **WHEN** the organizer sets the first nonzero discipline price on `DISCIPLINES` for a tournament with no bank account
- **THEN** the `PAYMENTS` tab gains the marker, without the organizer having visited it

#### Scenario: Markers clear on publication
- **WHEN** the tournament is published
- **THEN** no tab carries a marker, and none can appear again
