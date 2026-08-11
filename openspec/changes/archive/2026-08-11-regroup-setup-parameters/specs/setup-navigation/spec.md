## MODIFIED Requirements

### Requirement: Setup settings are navigated by seven tabs
The Setup phase's settings pane SHALL present exactly seven tabs — `TOURNAMENT`,
`DISCIPLINES`, `EXTRA`, `TIMELINE`, `PAYMENTS`, `OTHER`, `PUBLISH` — and SHALL show the
sections of exactly one tab at a time. `TOURNAMENT` SHALL be selected when the Setup
phase is opened. The tab bar SHALL use the same control treatment as the preview pane's
tabs, and its labels SHALL be localized like all other user-facing text.

`TIMELINE` SHALL stand between `EXTRA` and `PAYMENTS`, so the bar reads in the order the
organizer works: what the tournament is, what it offers, what those cost, when it all
happens, and how it is paid for.

#### Scenario: Seven tabs offered
- **WHEN** the organizer opens the Setup phase
- **THEN** the settings pane offers the seven tabs in that order, with `TOURNAMENT` selected and only its sections shown

#### Scenario: Switching tabs
- **WHEN** the organizer selects `DISCIPLINES`
- **THEN** the discipline table is shown and no other tab's sections are shown

#### Scenario: Selection survives a save
- **WHEN** the organizer has `EXTRA` selected and saves an extra item
- **THEN** `EXTRA` is still the selected tab, with its sections refreshed from the saved state

#### Scenario: Timeline reachable like any other tab
- **WHEN** the organizer selects `TIMELINE`
- **THEN** the tournament's dates are shown and no other tab's sections are shown

### Requirement: Section allocation to tabs
Every Setup settings section SHALL belong to exactly one tab, and no section SHALL be
dropped, duplicated, or split by this navigation:

- `TOURNAMENT` — the tournament's identity fields (display name, subtitle, logo, date,
  location, description, qualification statement, registration instructions) and the
  titular organizers.
- `DISCIPLINES` — the disciplines table.
- `EXTRA` — the extra-items table.
- `TIMELINE` — every date that governs the tournament as a whole: when registration
  opens, the seating deadline, when registration closes, and the team composition
  deadline.
- `PAYMENTS` — how fencers pay (the payment mode, the deposit, the payment window and
  the reminder day), the bank account payments are collected into, the currency and
  exchange-rate section, the VS series statement, the discount list, and — only while
  the tournament still carries them — the legacy fixed fees.
- `OTHER` — console team access, the export sheet address, and the danger zone.
- `PUBLISH` — the publication state, the items blocking publication, and the publish
  action, as fixed by `tournament-publication`.

The payment-mode section SHALL stand first on `PAYMENTS`, before the bank account the
money arrives in; the bank account SHALL keep its place ahead of the currency it is
denominated in.

**One field, one editor.** A field that governs whether a tournament may be published
SHALL be offered in exactly one place, so that an organizer reading it in Setup is
reading the value the publication check reads. This SHALL hold for the bank account, the
deposit amount, and the legacy fixed fees alike. No tournament parameter SHALL be offered
in the console's phase panels.

The team composition deadline SHALL sit on `TIMELINE` in its chronological place, and
SHALL be offered only while at least one discipline row is of the team kind, including a
row added in the current unsaved draft on `DISCIPLINES`. A deadline already stored on a
tournament whose team disciplines have all been removed SHALL be retained rather than
cleared.

The registration window — when registration opens and closes — SHALL move from
`TOURNAMENT` to `TIMELINE`. The tournament's own date SHALL remain editable on
`TOURNAMENT` and SHALL appear on `TIMELINE` read-only, as the anchor the other dates run
towards.

Within a tab, sections SHALL keep their existing relative order, except on
`TOURNAMENT`, where the identity fields follow the order fixed by `tournament-admin`.
Sections that are shown only to the tournament owner SHALL keep that restriction; when
a non-owner opens `OTHER` and it would therefore be empty, the tab SHALL NOT be
offered at all rather than opening onto nothing. `PUBLISH` SHALL be offered to every
account with console access.

#### Scenario: Every section reachable
- **WHEN** the organizer visits all seven tabs
- **THEN** every settings section that existed before this change is present on exactly one of them, and every tournament parameter formerly offered in a console phase panel is present on one of them

#### Scenario: Deadline appears with the first team row
- **WHEN** the organizer sets a discipline row's kind to team in an unsaved draft on `DISCIPLINES`
- **THEN** the composition deadline field appears in its place on `TIMELINE`

#### Scenario: Deadline hidden without team disciplines
- **WHEN** the tournament offers only individual disciplines
- **THEN** no composition deadline field is shown on `TIMELINE`

#### Scenario: Stored deadline survives removing the team discipline
- **WHEN** the organizer removes the last team discipline from a tournament that had a composition deadline set
- **THEN** the field stops being shown and the stored deadline is not cleared

#### Scenario: Money settings together
- **WHEN** the organizer opens `PAYMENTS`
- **THEN** how fencers pay, the bank account, the currency and exchange rate, the VS series statement, and the discount list are shown together, with the payment mode first and the bank account ahead of the currency

#### Scenario: Bank account has one editor
- **WHEN** the organizer looks for the bank account in the console's payments-phase panels
- **THEN** it is not offered there, and `PAYMENTS` in Setup is the only place it can be edited

#### Scenario: Deposit has one editor
- **WHEN** the organizer looks for the deposit amount in the console's payments-phase panels
- **THEN** it is not offered there, and `PAYMENTS` in Setup is the only place it can be edited

#### Scenario: Tournament date is shown but not edited on the timeline
- **WHEN** the organizer opens `TIMELINE`
- **THEN** the tournament date is shown as the timeline's anchor with no field to change it, and `TOURNAMENT` remains the only place it can be edited

#### Scenario: Non-owner sees no empty tab
- **WHEN** a console team member who is not the tournament owner opens Setup
- **THEN** the `OTHER` tab is not offered, and the remaining six tabs — including `PUBLISH` — behave as usual

### Requirement: Per-tab incompleteness markers
Each tab that contains at least one unconfigured mandatory item SHALL carry a marker in
the tab bar, drawn in `--stamp` with a localized accessible label, so that an item read
on `PUBLISH` can be traced to the tab that resolves it.

**Every item the publication check can report SHALL be attributed to a tab, and that tab
SHALL hold a section that resolves it.** Location and organizers attribute to
`TOURNAMENT`; missing disciplines, missing discipline prices and missing team bounds to
`DISCIPLINES`; missing extra-item prices to `EXTRA`; and the missing bank account, missing
discount amounts, the missing deposit amount, and the currency-mode conflicts — including
legacy fixed fees that cannot be priced in EUR — to `PAYMENTS`.

An item the client does not recognize SHALL mark no tab and SHALL NOT break the tab bar.
That fallback exists for a backend reporting something a deployed client has never heard
of; it SHALL NOT be the resting state of an item this client is expected to resolve.
`PUBLISH` SHALL carry a marker whenever any other tab does, since that is where the items
are listed.

The settings pane header SHALL consist of the tab bar alone. No list of unconfigured
items SHALL appear outside the `PUBLISH` tab. The header SHALL stay in place while the
selected tab's sections scroll beneath it, and no part of a scrolling section SHALL
ever be visible above it or through its background, at any scroll position and on any
tab.

#### Scenario: Marker points at the responsible tab
- **WHEN** the tournament has a discipline with no price and no other missing item
- **THEN** the `DISCIPLINES` tab carries the marker, `PUBLISH` carries one, and no other tab does

#### Scenario: Missing deposit marks the payments tab
- **WHEN** a deposit-mode tournament has no deposit amount
- **THEN** `PAYMENTS` carries the marker, `PUBLISH` carries one, and the deposit field is on `PAYMENTS`

#### Scenario: Legacy fees blocking EUR mark the tab that clears them
- **WHEN** a EUR-priced tournament still carries legacy fixed fees
- **THEN** `PAYMENTS` carries the marker and holds the section that clears them

#### Scenario: Every reported item marks a tab
- **WHEN** the publication check reports any item this client knows
- **THEN** some tab carries a marker, and `PUBLISH` carries one — no reported item leaves the tab bar unmarked
