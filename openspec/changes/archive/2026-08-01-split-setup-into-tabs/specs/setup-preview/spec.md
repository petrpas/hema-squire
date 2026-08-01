## MODIFIED Requirements

### Requirement: Setup phase shows settings and preview side by side
The console Setup phase SHALL present two panes: the tournament's settings sections
on the left and a preview of the tournament's fencer-facing faces on the right. The
settings pane SHALL keep its existing editing behavior unchanged; how its sections are
navigated is governed by `setup-navigation`, and the preview pane SHALL be present
beside the settings pane whichever settings tab is selected. The preview pane SHALL be
present for every tournament in Setup, including one whose setup is incomplete. When
the viewport is too narrow to carry both panes legibly, the preview SHALL fall below
the settings rather than compress either pane.

#### Scenario: Both panes present in Setup
- **WHEN** an organizer opens the Setup phase of a tournament
- **THEN** the settings sections appear on the left and a preview of the tournament appears on the right

#### Scenario: Preview present on every settings tab
- **WHEN** the organizer switches between the settings tabs
- **THEN** the preview pane stays beside the settings pane, keeping its own selected tab and its scroll position

#### Scenario: Incomplete setup still previewed
- **WHEN** an organizer opens Setup on a tournament that has no disciplines and no extra items yet
- **THEN** the preview renders the tournament as a fencer would currently see it, empty sections omitted, without error

#### Scenario: Narrow viewport stacks the panes
- **WHEN** the console is viewed at a width too narrow for two panes
- **THEN** the preview appears below the settings, both at full width

#### Scenario: Other phases unaffected
- **WHEN** the organizer switches from Setup to any other console phase
- **THEN** that phase renders as before, with no preview pane

### Requirement: Preview reflects saved settings and refreshes on save
The preview SHALL render the tournament's saved state, so that what the organizer
sees is what fencers can see at that moment. It SHALL NOT render unsaved edits,
including rows drafted, edited or deleted in a settings tab but not yet written. When
a settings tab is saved, the preview SHALL refresh from the newly saved state without
the organizer reloading the console.

#### Scenario: Saved change appears
- **WHEN** the organizer changes a discipline's price and saves the tab
- **THEN** the preview shows the new price on the registration form and on the tournament face

#### Scenario: Unsaved edit not shown
- **WHEN** the organizer has typed a new price but has not saved the tab
- **THEN** the preview still shows the previously saved price

#### Scenario: Drafted row not shown
- **WHEN** the organizer has added an extra-item row and deleted another, and has not saved the tab
- **THEN** the preview still shows the deleted item and does not show the added one

#### Scenario: Newly added item appears after save
- **WHEN** the organizer adds an extra item in a category whose section was previously empty and saves the tab
- **THEN** the preview's registration form now renders that section with the new item's row and price

#### Scenario: Partially written save reflected as written
- **WHEN** a tab save writes two changes and the server rejects a third
- **THEN** the preview shows the two written changes and does not show the rejected one
