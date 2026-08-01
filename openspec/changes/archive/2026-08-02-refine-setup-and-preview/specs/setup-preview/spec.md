## MODIFIED Requirements

### Requirement: Preview carries the tournament's two faces as tabs
The preview pane SHALL offer exactly two tabs, corresponding to the two faces a
fencer sees: the tournament face (its information page) and the fencer registration
form. Exactly one tab SHALL be selected at a time, the tournament face on entry. The
selected tab SHALL survive a save of any settings section, so an organizer editing
prices while watching the registration form is not returned to the other tab.

The tab bar SHALL be sized to its labels and aligned to the leading edge of the pane,
never stretched to the pane's full width. It SHALL match the settings pane's tab bar
in this as in its control treatment, so the two bars read as the same control at
different sizes.

#### Scenario: Two tabs offered
- **WHEN** the organizer looks at the preview pane
- **THEN** it offers a tournament-face tab and a registration-form tab, with the tournament face selected

#### Scenario: Tab bar sized to its labels
- **WHEN** the organizer widens the console so the preview pane is far wider than the two tab labels
- **THEN** the tab bar stays as wide as its labels, aligned to the pane's leading edge, with empty pane to its trailing side

#### Scenario: Tab switching
- **WHEN** the organizer selects the registration-form tab
- **THEN** the preview shows the registration form and the tournament face is no longer shown

#### Scenario: Tab selection survives a save
- **WHEN** the organizer has the registration-form tab selected and saves a settings section
- **THEN** the preview still shows the registration form, refreshed
