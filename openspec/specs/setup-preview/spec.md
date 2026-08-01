# setup-preview

## Purpose

Give organizers a live preview, inside the Setup phase of the tournament console, of
what fencers see: the tournament's public information page and its registration form.
The preview renders through the same fencer-facing components used on the public
site, stays read-only against the real registration data, and refreshes whenever the
organizer saves a settings change.

## Requirements

### Requirement: Setup phase shows settings and preview side by side
The console Setup phase SHALL present two panes: the tournament's settings sections
on the left and a preview of the tournament's fencer-facing faces on the right. The
settings pane SHALL keep its existing content, order, and editing behavior unchanged.
The preview pane SHALL be present for every tournament in Setup, including one whose
setup is incomplete. When the viewport is too narrow to carry both panes legibly, the
preview SHALL fall below the settings rather than compress either pane.

#### Scenario: Both panes present in Setup
- **WHEN** an organizer opens the Setup phase of a tournament
- **THEN** the settings sections appear on the left and a preview of the tournament appears on the right

#### Scenario: Incomplete setup still previewed
- **WHEN** an organizer opens Setup on a tournament that has no disciplines and no extra items yet
- **THEN** the preview renders the tournament as a fencer would currently see it, empty sections omitted, without error

#### Scenario: Narrow viewport stacks the panes
- **WHEN** the console is viewed at a width too narrow for two panes
- **THEN** the preview appears below the settings, both at full width

#### Scenario: Other phases unaffected
- **WHEN** the organizer switches from Setup to any other console phase
- **THEN** that phase renders as before, with no preview pane

### Requirement: Preview carries the tournament's two faces as tabs
The preview pane SHALL offer exactly two tabs, corresponding to the two faces a
fencer sees: the tournament face (its information page) and the fencer registration
form. Exactly one tab SHALL be selected at a time, the tournament face on entry. The
selected tab SHALL survive a save of any settings section, so an organizer editing
prices while watching the registration form is not returned to the other tab.

#### Scenario: Two tabs offered
- **WHEN** the organizer looks at the preview pane
- **THEN** it offers a tournament-face tab and a registration-form tab, with the tournament face selected

#### Scenario: Tab switching
- **WHEN** the organizer selects the registration-form tab
- **THEN** the preview shows the registration form and the tournament face is no longer shown

#### Scenario: Tab selection survives a save
- **WHEN** the organizer has the registration-form tab selected and saves a settings section
- **THEN** the preview still shows the registration form, refreshed

### Requirement: Preview renders through the fencer-facing components
The preview SHALL be rendered by the same components that render the fencer-facing
tournament page and registration form. No separate preview-only rendering of a
tournament's information or of the registration checklist SHALL exist. Consequently a
change to a fencer-facing component SHALL appear in the preview without any
corresponding preview-side change.

#### Scenario: One implementation serves both call sites
- **WHEN** the fencer-facing tournament page and the Setup preview both render the registration form
- **THEN** both render it through the same component, and neither carries its own copy of that markup

#### Scenario: Change to the fencer view propagates
- **WHEN** a row, label, or section is changed in the fencer-facing registration form
- **THEN** the Setup preview shows that change with no further edit to the preview

#### Scenario: Fencer-facing page keeps its own flow
- **WHEN** a fencer opens a tournament
- **THEN** they see the information page and reach the registration form through the register or amend action, exactly as before this change — the tabs exist only in the console preview

### Requirement: Previewed registration form is interactive but cannot be submitted
The previewed registration form SHALL accept the same interactions a fencer has —
selecting disciplines and items, setting quantities, answering option fields and
free-text fields — and SHALL recompute and display the running total through the same
read-only price preview a fencer's form uses. The form's submit control SHALL be
absent from the preview, replaced by a static marker stating that this is a preview
and cannot be submitted. No interaction within the preview SHALL create, amend, or
cancel any registration, or alter the tournament in any way.

#### Scenario: Selection recomputes the total
- **WHEN** the organizer ticks two disciplines and a dinner item at quantity 2 in the preview
- **THEN** the preview's running total reflects those selections at the tournament's configured prices, in the tournament's currency

#### Scenario: Submit not offered
- **WHEN** the organizer reaches the bottom of the previewed registration form
- **THEN** there is no submit control, and a static marker states the form is a preview that cannot be submitted

#### Scenario: Preview creates no registration
- **WHEN** the organizer has made selections in the preview and leaves the Setup phase
- **THEN** no registration exists for the organizer on that tournament and the tournament's registration count is unchanged

#### Scenario: Discounts and capacity visible in preview
- **WHEN** the tournament has a discount that applies to a combination of disciplines, or a discipline that is full
- **THEN** selecting that combination shows the discounted total, and the full discipline states its full status exactly as a fencer's form would

### Requirement: Preview reflects saved settings and refreshes on save
The preview SHALL render the tournament's saved state, so that what the organizer
sees is what fencers can see at that moment. It SHALL NOT render unsaved edits. When
any settings section is saved, the preview SHALL refresh from the newly saved state
without the organizer reloading the console.

#### Scenario: Saved change appears
- **WHEN** the organizer changes a discipline's price and saves that section
- **THEN** the preview shows the new price on the registration form and on the tournament face

#### Scenario: Unsaved edit not shown
- **WHEN** the organizer has typed a new price but has not saved
- **THEN** the preview still shows the previously saved price

#### Scenario: Newly added item appears after save
- **WHEN** the organizer adds an extra item in a category whose section was previously empty and saves
- **THEN** the preview's registration form now renders that section with the new item's row and price
