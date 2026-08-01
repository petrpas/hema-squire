# setup-navigation

## Purpose

Govern how the Setup phase's settings pane is navigated and committed: the five
tabs and which sections belong to each, the default and persistence of the
selection, the checklist's placement and per-tab incompleteness marker, the
preservation of unsaved edits across tab switches, the one-save-per-tab rule
with its drafted row tables, the non-atomic flush and its error reporting, the
stated immediate-action exceptions, and the confirmation on leaving Setup
dirty.

## Requirements

### Requirement: Setup settings are navigated by five tabs
The Setup phase's settings pane SHALL present exactly five tabs — `TOURNAMENT`,
`DISCIPLINES`, `EXTRA`, `PAYMENTS`, `OTHER` — and SHALL show the sections of exactly
one tab at a time. `TOURNAMENT` SHALL be selected when the Setup phase is opened. The
tab bar SHALL use the same control treatment as the preview pane's tabs, and its
labels SHALL be localized like all other user-facing text.

#### Scenario: Five tabs offered
- **WHEN** the organizer opens the Setup phase
- **THEN** the settings pane offers the five tabs in that order, with `TOURNAMENT` selected and only its sections shown

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

### Requirement: Unsaved edits survive tab switching
Switching tabs SHALL NOT discard edits typed into a section and not yet saved.
Returning to a tab SHALL show the section exactly as the organizer left it, including
half-filled rows and rows added but not yet saved. No confirmation prompt SHALL be
required on tab switch. Tab switching SHALL NOT save anything: a tab's changes SHALL
be written only by its own save control.

#### Scenario: Typed edit preserved
- **WHEN** the organizer types a price into a discipline row, switches to `PAYMENTS`, then switches back to `DISCIPLINES`
- **THEN** the typed price is still in the field, still unsaved

#### Scenario: Tab switch saves nothing
- **WHEN** the organizer edits a field and switches tabs without saving
- **THEN** the tournament is unchanged and the preview still shows the previously saved state

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

### Requirement: Tabs do not change what a section stores
Placing a section under a tab SHALL NOT change its fields, its validation rules,
its owner-only restriction, or the state it persists. What changes is when the write
happens, which is governed by the one-save-per-tab requirement. The preview pane SHALL
remain beside the settings pane on every tab and SHALL keep refreshing after a save
regardless of which tab is selected.

#### Scenario: Fields and validation unchanged
- **WHEN** the organizer edits any settings section from within its tab
- **THEN** it offers the same fields and rejects the same invalid input as before the tabs existed, and a saved section stores exactly what it stored before

#### Scenario: Preview present on every tab
- **WHEN** the organizer moves through all five tabs
- **THEN** the preview pane is beside the settings on each of them, showing the tournament's saved state

#### Scenario: Save on one tab reflected in the preview
- **WHEN** the organizer changes the currency on `PAYMENTS` and saves the tab, with the preview showing the registration form
- **THEN** the preview refreshes to the newly saved state without leaving `PAYMENTS`

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

#### Scenario: OTHER has no save control
- **WHEN** the tournament owner opens `OTHER`
- **THEN** there is no save control, and inviting a member, cancelling the tournament and deleting it each act through their own control with their own confirmation

#### Scenario: Logo controls read as exempt
- **WHEN** the organizer looks at the logo upload and removal on `TOURNAMENT`
- **THEN** they are tertiary text actions, plainly distinct from the tab's save control, and they act immediately on file choice rather than waiting for a save

### Requirement: Row tables are drafts until the tab is saved
In the discipline and extra-item tables, adding a row, editing a row, and deleting a
row SHALL change only the local draft. No create, update, or delete SHALL reach the
server until the tab's save control is used. A deleted row SHALL leave the list
immediately; it SHALL be recoverable only by leaving the tab without saving, which
discards that tab's other pending changes with it. A drafted row that is invalid SHALL
be marked, and SHALL block the save until corrected rather than being written or
silently dropped.

#### Scenario: Added row is not written until save
- **WHEN** the organizer adds a discipline row, fills it, and leaves the Setup phase without saving
- **THEN** the tournament has no such discipline, and the preview never showed one

#### Scenario: Deleted row leaves the list at once
- **WHEN** the organizer deletes an extra-item row
- **THEN** the row disappears from the table, the save control counts the removal among the unsaved changes, and the item still exists on the server until the tab is saved

#### Scenario: Save flushes the whole tab
- **WHEN** the organizer has one edited row, one added row and one deleted row, and saves the tab
- **THEN** all three are written, the tournament detail is refetched once, and the tab reports no unsaved changes

#### Scenario: Invalid drafted row blocks the save
- **WHEN** a drafted discipline row is missing a value its own validation requires
- **THEN** that row is marked, the save does not proceed, and no other pending change is written by that attempt

### Requirement: A tab save is not atomic and reports what it failed to write
Saving a tab SHALL flush its pending changes in a defined order. If the server rejects
one of them, the changes already written SHALL remain written, the flush SHALL report
which change failed and why against the row or section that caused it, and that change
SHALL remain pending so it can be corrected and saved again. The save SHALL NOT claim
success while anything remains unwritten, and the tab's unsaved count SHALL continue
to reflect what is still pending.

#### Scenario: One rejected row among several changes
- **WHEN** the organizer saves a tab with three pending row changes and the server rejects the second
- **THEN** the first is written and stays written, the second is marked with the reason it was rejected and stays pending, and the tab reports that changes remain unsaved

#### Scenario: Corrected change saves on the next attempt
- **WHEN** the organizer corrects the rejected row and saves again
- **THEN** only what is still pending is written, nothing already written is written twice, and the tab reports no unsaved changes

#### Scenario: Price change warned once per save
- **WHEN** the organizer saves a tab whose pending changes alter a price, on a tournament that already has registrations
- **THEN** the existing price-change warning is raised once before anything is written, and cancelling it writes nothing

### Requirement: Leaving Setup with unsaved changes is confirmed
When the organizer moves from the Setup phase to another console phase while any tab
holds unsaved changes, the console SHALL ask for confirmation and SHALL state that the
changes will be discarded. Confirming SHALL leave without writing them; declining SHALL
stay in Setup with every pending change intact. Moving between Setup's own tabs SHALL
NOT be confirmed, because nothing is discarded by it.

#### Scenario: Confirmation on leaving Setup dirty
- **WHEN** the organizer has unsaved changes on `EXTRA` and clicks the Payments phase
- **THEN** a confirmation states the changes will be discarded, and declining returns to Setup with the changes intact

#### Scenario: Clean Setup leaves without asking
- **WHEN** the organizer has saved everything and switches to another phase
- **THEN** no confirmation appears

#### Scenario: Tab switching is never confirmed
- **WHEN** the organizer switches between Setup tabs with unsaved changes in both
- **THEN** no confirmation appears and no change is discarded
