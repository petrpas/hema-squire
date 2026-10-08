## MODIFIED Requirements

### Requirement: Setup settings are navigated by tabs
The Setup phase's settings pane SHALL present its tabs in the fixed order `TOURNAMENT`,
`DISCIPLINES`, `EXTRA`, `TIMELINE`, `PAYMENTS`, `OTHER`, `PUBLISH`, and SHALL show the
sections of exactly one tab at a time. `TOURNAMENT` SHALL be selected when the Setup
phase is opened. The tab bar SHALL use the same control treatment as the preview pane's
tabs, and its labels SHALL be localized like all other user-facing text.

`TIMELINE` SHALL stand between `EXTRA` and `PAYMENTS`, so the bar reads in the order the
organizer works: what the tournament is, what it offers, what those cost, when it all
happens, and how it is paid for.

**Which of those tabs are offered SHALL follow the tournament's features**, as fixed by
`tournament-features`. `EXTRA` SHALL be offered only while the extra services feature is on.
`OTHER` SHALL keep its owner-only restriction. The remaining five SHALL always be
offered, so that a tournament with no feature enabled is navigated by `TOURNAMENT`, `DISCIPLINES`,
`TIMELINE`, `PAYMENTS`, `OTHER` and `PUBLISH`. Whichever tabs are offered SHALL keep the
fixed order above; the mode removes tabs, it never reorders them.

**Below the width at which the preview fits beside the settings, the bar SHALL end with
one further tab, `PREVIEW`**, after `PUBLISH`, as fixed by `setup-preview`. It follows
the viewport, not the tournament: it SHALL be offered in every mode and to every account
with console access, and SHALL NOT be offered on a viewport wide enough to show the
preview beside the settings. It is a tab to look at, not a settings tab, and the
requirement "The preview tab holds no settings" governs it.

**The payments tab SHALL be titled `PRICING` while the payments feature is off**, because
what it then holds is the currency the tournament prices in and the discounts it gives,
and a tab titled for payments on a tournament that takes none states something untrue.
The tab's identifier SHALL NOT change with its title: it remains the `payments` tab for
the URL it produces, for the incompleteness marker attributed to it, and for the panel it
controls.

#### Scenario: Seven tabs offered
- **WHEN** the organizer opens the Setup phase of a tournament with every feature enabled, on a wide viewport
- **THEN** the settings pane offers the seven tabs in that order, with `TOURNAMENT` selected and only its sections shown

#### Scenario: Preview tab added on a narrow viewport
- **WHEN** the organizer opens the Setup phase of a tournament with every feature enabled, on a viewport too narrow for the preview beside the settings
- **THEN** the settings pane offers the seven tabs in that order followed by `PREVIEW`, with `TOURNAMENT` selected

#### Scenario: Switching tabs
- **WHEN** the organizer selects `DISCIPLINES`
- **THEN** the discipline table is shown and no other tab's sections are shown

#### Scenario: Selection survives a save
- **WHEN** the organizer has `EXTRA` selected and saves an extra item
- **THEN** `EXTRA` is still the selected tab, with its sections refreshed from the saved state

#### Scenario: Timeline reachable like any other tab
- **WHEN** the organizer selects `TIMELINE`
- **THEN** the tournament's dates are shown and no other tab's sections are shown

#### Scenario: Easy mode offers six tabs
- **WHEN** the tournament owner opens the Setup phase of a tournament with no feature enabled, on a wide viewport
- **THEN** the tab bar offers `TOURNAMENT`, `DISCIPLINES`, `TIMELINE`, `PRICING`, `OTHER` and `PUBLISH`, in that order, and no `EXTRA` tab

#### Scenario: Payments tab titled for what it holds
- **WHEN** the organizer turns the payments feature off
- **THEN** the tab is titled `PRICING`, its URL and its incompleteness marker are unchanged, and turning payments back on titles it `PAYMENTS` again

#### Scenario: EXTRA appears with its feature
- **WHEN** the organizer turns the extra services feature on from `OTHER`
- **THEN** `EXTRA` appears in its fixed place between `DISCIPLINES` and `TIMELINE`, without leaving Setup

### Requirement: Tabs do not change what a section stores
Placing a section under a tab SHALL NOT change its fields, its validation rules,
its owner-only restriction, or the state it persists. What changes is when the write
happens, which is governed by the one-save-per-tab requirement. On a viewport wide
enough for both panes, the preview pane SHALL remain beside the settings pane on every
tab; on a narrower one it SHALL be reached through `PREVIEW`. In both layouts it SHALL
keep refreshing after a save regardless of which tab is selected, so that `PREVIEW`
opened after a save shows the newly saved state.

#### Scenario: Fields and validation unchanged
- **WHEN** the organizer edits any settings section from within its tab
- **THEN** it offers the same fields and rejects the same invalid input as before the tabs existed, and a saved section stores exactly what it stored before

#### Scenario: Preview present on every tab
- **WHEN** the organizer moves through every tab its mode offers, on a wide viewport
- **THEN** the preview pane is beside the settings on each of them, showing the tournament's saved state

#### Scenario: Save on one tab reflected in the preview
- **WHEN** the organizer changes the currency on `PAYMENTS` and saves the tab, with the preview showing the registration form
- **THEN** the preview refreshes to the newly saved state without leaving `PAYMENTS`

#### Scenario: Save reflected in the preview tab
- **WHEN** on a narrow viewport the organizer changes a discipline price on `DISCIPLINES`, saves the tab, and selects `PREVIEW`
- **THEN** the preview shows the new price

## ADDED Requirements

### Requirement: The preview tab holds no settings
`PREVIEW` SHALL hold the preview and nothing else. It SHALL carry no save control, so
the save bar of the tab selected before it SHALL NOT be shown on it; no settings
section SHALL be shown on it; and it SHALL NOT be counted among the tabs that can carry
unsaved changes.

It SHALL carry neither an incompleteness marker nor an unsaved marker: no item the
publication check reports is attributed to it, and it holds nothing to save. The
markers of the other tabs SHALL be shown as usual while `PREVIEW` is selected, since
the organizer still needs to see where unsaved changes and missing items are.

Selecting `PREVIEW` SHALL NOT save, discard or confirm anything, like any other tab
switch, and leaving Setup from it SHALL be confirmed exactly as leaving from any other
tab is when another tab holds unsaved changes.

**When the viewport widens past the threshold while `PREVIEW` is selected**, the
settings pane SHALL return to the settings tab that was selected before `PREVIEW`, and
the preview SHALL be shown beside it. Narrowing the viewport SHALL NOT select `PREVIEW`
on its own: the selected settings tab stays selected.

#### Scenario: No save bar on the preview tab
- **WHEN** on a narrow viewport the organizer edits a discipline price on `DISCIPLINES` without saving and selects `PREVIEW`
- **THEN** no save control is shown, `DISCIPLINES` still carries its unsaved marker, and the preview shows the previously saved price

#### Scenario: No marker on the preview tab
- **WHEN** an incomplete draft is opened on a narrow viewport
- **THEN** `PUBLISH` and the tabs that resolve the missing items carry their markers, and `PREVIEW` carries none

#### Scenario: Widening returns to the settings tab
- **WHEN** the organizer selects `TIMELINE`, then `PREVIEW`, and widens the window past the threshold
- **THEN** `TIMELINE` is selected, its sections are shown, the preview is beside them, and the tab bar no longer offers `PREVIEW`

#### Scenario: Narrowing keeps the selected tab
- **WHEN** the organizer has `PAYMENTS` selected on a wide viewport and narrows the window below the threshold
- **THEN** `PAYMENTS` stays selected with its sections shown, and `PREVIEW` is offered at the end of the bar
