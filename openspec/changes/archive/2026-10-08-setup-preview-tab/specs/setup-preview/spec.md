## REMOVED Requirements

### Requirement: Setup phase shows settings and preview side by side
**Reason**: Its "Narrow viewport stacks the panes" scenario is withdrawn: below the threshold the preview no longer falls below the settings but becomes the settings pane's last tab. It is replaced by "Setup shows the preview beside the settings, or as their last tab", which carries the rest of it unchanged.
**Migration**: None; the narrow layout is a presentation change with no stored state.

## ADDED Requirements

### Requirement: Setup shows the preview beside the settings, or as their last tab
The console Setup phase SHALL present two panes: the tournament's settings sections
on the left and a preview of the tournament's fencer-facing faces on the right. The
settings pane SHALL keep its existing editing behavior unchanged; how its sections are
navigated is governed by `setup-navigation`, and the preview pane SHALL be present
beside the settings pane whichever settings tab is selected. The preview pane SHALL be
present for every tournament in Setup, including one whose setup is incomplete.

**When the viewport is too narrow to carry both panes legibly, the preview SHALL NOT
fall below the settings.** It SHALL instead be offered as the settings pane's last tab,
`PREVIEW`, as fixed by `setup-navigation`, and its content SHALL be shown in that tab's
panel, at the settings pane's full width and beneath the same fixed tab bar. No preview
SHALL then be shown beside or below the settings on any other tab. The threshold SHALL
be the one at which the two panes stop fitting side by side; it is a content threshold,
not a device breakpoint.

The preview SHALL be one preview whichever place shows it: its selected face, its
registration-form selections and its scroll position SHALL survive switching to
`PREVIEW` and away from it. Its selected face and its registration-form selections
SHALL also survive the viewport crossing the threshold in either direction; its scroll
position need not, since the column it scrolls in changes width.

#### Scenario: Both panes present in Setup
- **WHEN** an organizer opens the Setup phase of a tournament on a wide viewport
- **THEN** the settings sections appear on the left and a preview of the tournament appears on the right

#### Scenario: Preview present on every settings tab
- **WHEN** the organizer switches between the settings tabs on a wide viewport
- **THEN** the preview pane stays beside the settings pane, keeping its own selected tab and its scroll position

#### Scenario: Incomplete setup still previewed
- **WHEN** an organizer opens Setup on a tournament that has no disciplines and no extra items yet
- **THEN** the preview renders the tournament as a fencer would currently see it, empty sections omitted, without error

#### Scenario: Narrow viewport moves the preview into its own tab
- **WHEN** the console is viewed at a width too narrow for two panes
- **THEN** no preview is shown below or beside the settings, the settings tab bar ends with `PREVIEW`, and selecting it shows the preview in place of the settings sections, at full width, with the tab bar still in place above it

#### Scenario: Preview state survives the tab switch
- **WHEN** on a narrow viewport the organizer selects `PREVIEW`, switches it to the registration form, ticks a discipline, opens `DISCIPLINES` and then `PREVIEW` again
- **THEN** the preview still shows the registration form with that discipline ticked, at the scroll position it was left at

#### Scenario: Preview state survives crossing the threshold
- **WHEN** the organizer has the registration form selected in the side pane and narrows the window below the threshold, then selects `PREVIEW`
- **THEN** the preview shows the registration form, not the tournament face

#### Scenario: Other phases unaffected
- **WHEN** the organizer switches from Setup to any other console phase
- **THEN** that phase renders as before, with no preview pane and no `PREVIEW` tab
