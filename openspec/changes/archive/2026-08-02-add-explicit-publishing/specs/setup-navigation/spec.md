## MODIFIED Requirements

### Requirement: Setup settings are navigated by five tabs
The Setup phase's settings pane SHALL present exactly six tabs — `TOURNAMENT`,
`DISCIPLINES`, `EXTRA`, `PAYMENTS`, `OTHER`, `PUBLISH` — and SHALL show the sections of
exactly one tab at a time. `TOURNAMENT` SHALL be selected when the Setup phase is
opened. The tab bar SHALL use the same control treatment as the preview pane's tabs,
and its labels SHALL be localized like all other user-facing text.

#### Scenario: Six tabs offered
- **WHEN** the organizer opens the Setup phase
- **THEN** the settings pane offers the six tabs in that order, with `TOURNAMENT` selected and only its sections shown

#### Scenario: Switching tabs
- **WHEN** the organizer selects `DISCIPLINES`
- **THEN** the discipline table is shown and no other tab's sections are shown

#### Scenario: Selection survives a save
- **WHEN** the organizer has `EXTRA` selected and saves an extra item
- **THEN** `EXTRA` is still the selected tab, with its sections refreshed from the saved state

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
- `PUBLISH` — the publication state, the items blocking publication, and the publish
  action, as fixed by `tournament-publication`.

Within a tab, sections SHALL keep their existing relative order, except on
`TOURNAMENT`, where the identity fields follow the order fixed by `tournament-admin`.
Sections that are shown only to the tournament owner SHALL keep that restriction; when
a non-owner opens `OTHER` and it would therefore be empty, the tab SHALL NOT be
offered at all rather than opening onto nothing. `PUBLISH` SHALL be offered to every
account with console access.

#### Scenario: Every section reachable
- **WHEN** the organizer visits all six tabs
- **THEN** every settings section that existed before this change is present on exactly one of them

#### Scenario: Money settings together
- **WHEN** the organizer opens `PAYMENTS`
- **THEN** the currency and exchange rate, the VS series statement, and the discount list are shown together

#### Scenario: Non-owner sees no empty tab
- **WHEN** a console team member who is not the tournament owner opens Setup
- **THEN** the `OTHER` tab is not offered, and the remaining five tabs — including `PUBLISH` — behave as usual

### Requirement: One save control per tab
Each editing tab SHALL carry exactly one save control, at the bottom of the tab, and
that control SHALL be the only element in the tab that writes to the server. It SHALL
state how many unsaved changes it will write, and SHALL be inert when the tab has
none. No section within a tab SHALL carry a save control of its own, and no row within
a table SHALL carry one.

Two categories of control are exempt, and SHALL be visibly distinguishable from the
save control so the exemption is legible rather than surprising: the logo upload and
removal on `TOURNAMENT`, which act on file choice, and every action on `OTHER` and
`PUBLISH` — team invitation and removal, tournament cancellation and deletion,
publication — which are actions rather than settings and keep their own controls and
confirmations. `OTHER` and `PUBLISH` SHALL therefore carry no save control. The logo
controls SHALL take the tertiary text-action treatment fixed by `tournament-admin`,
which is how their exemption is made legible.

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

#### Scenario: PUBLISH has no save control
- **WHEN** the organizer opens `PUBLISH`
- **THEN** there is no save control, and publication acts through its own control with its own confirmation

## ADDED Requirements

### Requirement: Per-tab incompleteness markers
Each tab that contains at least one unconfigured mandatory item SHALL carry a marker in
the tab bar, drawn in `--stamp` with a localized accessible label, so that an item read
on `PUBLISH` can be traced to the tab that resolves it. An item SHALL be attributed to
the tab holding the section that resolves it: location and organizers to `TOURNAMENT`,
missing disciplines and missing discipline prices to `DISCIPLINES`, missing extra-item
prices to `EXTRA`, and missing discount amounts and the currency-mode conflicts to
`PAYMENTS`. An item the client does not recognize SHALL mark no tab and SHALL NOT break
the tab bar. `PUBLISH` SHALL carry a marker whenever any other tab does, since that is
where the items are listed.

The settings pane header SHALL consist of the tab bar alone. No list of unconfigured
items SHALL appear outside the `PUBLISH` tab. The header SHALL stay in place while the
selected tab's sections scroll beneath it, and no part of a scrolling section SHALL
ever be visible above it or through its background, at any scroll position and on any
tab.

#### Scenario: Marker points at the responsible tab
- **WHEN** the tournament has a discipline with no price and no other missing item
- **THEN** the `DISCIPLINES` tab carries the marker, `PUBLISH` carries one, and no other tab does

#### Scenario: Markers clear on publication
- **WHEN** the tournament is published
- **THEN** no tab carries a marker, and none can appear again

#### Scenario: Nothing listed outside PUBLISH
- **WHEN** the organizer moves through the tabs of an incomplete draft
- **THEN** no tab except `PUBLISH` lists the missing items, and the header above the sections is the tab bar alone

#### Scenario: Nothing shows above the tab bar
- **WHEN** the organizer scrolls a long tab such as `TOURNAMENT` to its bottom
- **THEN** the band above the tab bar stays empty and opaque, with no field, table row or table header visible in it

#### Scenario: Sticky table header stays below the pane header
- **WHEN** the organizer scrolls the `DISCIPLINES` table far enough for its column headers to stick
- **THEN** those headers stick below the tab bar, and never over it

#### Scenario: Unrecognized item key
- **WHEN** the setup state reports an item the client has no tab mapping for
- **THEN** no tab is marked because of it and the tab bar renders normally

## REMOVED Requirements

### Requirement: Checklist above the tabs with per-tab markers
**Reason**: The checklist no longer lives in the settings pane header. The items
blocking publication are listed on the `PUBLISH` tab, which is the only place that
answers "why can't fencers see this yet?"; the per-tab markers survive under the new
`Per-tab incompleteness markers` requirement, together with the header's
non-overlappability.

**Migration**: The chip rendering moves verbatim into the `PUBLISH` tab. No item key,
no tab attribution and no marker treatment changes; only the checklist's placement and
its per-tab visibility do.
