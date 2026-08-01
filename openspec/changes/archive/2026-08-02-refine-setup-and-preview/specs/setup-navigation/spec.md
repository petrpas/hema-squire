## MODIFIED Requirements

### Requirement: Section allocation to tabs
Every Setup settings section SHALL belong to exactly one tab, and no section SHALL be
dropped, duplicated, or split by this navigation:

- `TOURNAMENT` — the tournament's identity fields (display name, subtitle, logo, date,
  location, description, qualification statement, registration window, registration
  instructions) and the titular organizers.
- `DISCIPLINES` — the disciplines table.
- `EXTRA` — the extra-items table.
- `PAYMENTS` — the currency and exchange-rate section, the VS series statement, and the
  discount list.
- `OTHER` — console team access and the danger zone.

Within a tab, sections SHALL keep their existing relative order, except on
`TOURNAMENT`, where the identity fields follow the order fixed by `tournament-admin`.
Sections that are shown only to the tournament owner SHALL keep that restriction; when
a non-owner opens `OTHER` and it would therefore be empty, the tab SHALL NOT be
offered at all rather than opening onto nothing.

#### Scenario: Every section reachable
- **WHEN** the organizer visits all five tabs
- **THEN** every settings section that existed before this change is present on exactly one of them

#### Scenario: Money settings together
- **WHEN** the organizer opens `PAYMENTS`
- **THEN** the currency and exchange rate, the VS series statement, and the discount list are shown together

#### Scenario: Non-owner sees no empty tab
- **WHEN** a console team member who is not the tournament owner opens Setup
- **THEN** the `OTHER` tab is not offered, and the remaining four tabs behave as usual

### Requirement: Checklist above the tabs with per-tab markers
The setup completeness checklist SHALL be presented above the tab bar and SHALL be
visible on every tab. The checklist and the tab bar together form the settings pane's
header, which SHALL stay in place while the selected tab's sections scroll beneath it.
No part of a scrolling section SHALL ever be visible above the checklist or through
the header's background, at any scroll position and on any tab.

In addition, each tab that contains at least one unconfigured item SHALL carry a
marker in the tab bar, drawn in `--stamp` with a localized accessible label, so the
organizer sees which tabs still need attention without reading the chips. A checklist
item SHALL be attributed to the tab holding the section that resolves it: location and
organizers to `TOURNAMENT`, missing disciplines and missing discipline prices to
`DISCIPLINES`, missing extra-item prices to `EXTRA`, and missing discount amounts and
the currency-mode conflicts to `PAYMENTS`. A checklist item the client does not
recognize SHALL still be shown as a chip and SHALL mark no tab, never suppressing the
checklist or breaking the tab bar.

#### Scenario: Checklist visible from every tab
- **WHEN** the organizer switches between tabs with the setup incomplete
- **THEN** the checklist chips remain visible above the tab bar on each of them

#### Scenario: Nothing shows above the checklist
- **WHEN** the organizer scrolls a long tab such as `TOURNAMENT` to its bottom
- **THEN** the band above the checklist stays empty and opaque, with no field, table row or table header visible in it

#### Scenario: Sticky table header stays below the pane header
- **WHEN** the organizer scrolls the `DISCIPLINES` table far enough for its column headers to stick
- **THEN** those headers stick below the checklist and tab bar, and never over them

#### Scenario: Marker points at the responsible tab
- **WHEN** the tournament has a discipline with no price and no other missing item
- **THEN** the `DISCIPLINES` tab carries the marker and no other tab does

#### Scenario: Marker clears on completion
- **WHEN** the organizer fills the last missing discipline price and saves
- **THEN** the checklist reports the setup complete and no tab carries a marker

#### Scenario: Unrecognized checklist key
- **WHEN** the setup checklist reports an item the client has no tab mapping for
- **THEN** it appears among the chips, no tab is marked because of it, and the tab bar renders normally

### Requirement: One save control per tab
Each editing tab SHALL carry exactly one save control, at the bottom of the tab, and
that control SHALL be the only element in the tab that writes to the server. It SHALL
state how many unsaved changes it will write, and SHALL be inert when the tab has
none. No section within a tab SHALL carry a save control of its own, and no row within
a table SHALL carry one.

Two categories of control are exempt, and SHALL be visibly distinguishable from the
save control so the exemption is legible rather than surprising: the logo upload and
removal on `TOURNAMENT`, which act on file choice, and every action on `OTHER` — team
invitation and removal, tournament cancellation and deletion — which are actions
rather than settings and keep their own controls and confirmations. `OTHER` SHALL
therefore carry no save control. The logo controls SHALL take the tertiary text-action
treatment fixed by `tournament-admin`, which is how their exemption is made legible.

Controls that compute or restructure without persisting — "recalculate missing", "add
discount", "add row" — SHALL be presented as tertiary text actions, never in the save
control's treatment.

#### Scenario: One writer per tab
- **WHEN** the organizer inspects any editing tab
- **THEN** it carries exactly one save control, at the bottom, and no section or row within it carries a save control

#### Scenario: Save control reports its scope
- **WHEN** the organizer has edited two discipline rows and added a third on `DISCIPLINES`
- **THEN** the save control states that three changes are unsaved, and it is the only control on the tab that will write them

#### Scenario: Nothing to save
- **WHEN** a tab has no unsaved changes
- **THEN** its save control is inert and states that there is nothing to save

#### Scenario: Non-saving controls are not saves
- **WHEN** the organizer looks at "recalculate missing" or "add discount"
- **THEN** they are presented as tertiary text actions, distinct from the tab's save control, and clicking them writes nothing to the server

#### Scenario: Logo controls read as exempt
- **WHEN** the organizer looks at the logo upload and removal on `TOURNAMENT`
- **THEN** they are tertiary text actions, plainly distinct from the tab's save control, and they act immediately on file choice rather than waiting for a save

#### Scenario: OTHER has no save control
- **WHEN** the tournament owner opens `OTHER`
- **THEN** there is no save control, and inviting a member, cancelling the tournament and deleting it each act through their own control with their own confirmation
