## MODIFIED Requirements

### Requirement: Form (tiskopis) conventions
Forms SHALL number their sections with Roman numerals ("I.", "II.", …). Every labeled field, in panels and in modal dialogs alike, SHALL place its label above the control, styled per the typography conventions (10.5–11px uppercase, `letter-spacing: 0.12em`, weight 500, `--ink-faded`), with the control occupying the full width of its container. Inputs SHALL have a transparent background with a bottom rule only (`1px solid var(--ink)`), switching to a 2px `--stamp` bottom rule on focus, and no full-perimeter frame. Multiline text areas SHALL follow the same treatment and SHALL resize vertically only. Select and checkbox inputs SHALL use a full `1px solid var(--hairline)` frame on `--paper-raised` with 2px radius. Field error messages SHALL be `--stamp`-colored, 12px, placed below the field, stating what happened and what to do, with no exclamation marks.

A field carrying an error SHALL mark itself with a `1px solid var(--stamp)` bottom rule, thickening to 2px on focus exactly as a valid field does, and SHALL carry `aria-invalid` with its message associated by `aria-describedby`. No other visual treatment SHALL signal invalidity: no browser default outline, no glow, no background fill, no icon, no animation. Numeric fields SHALL be rendered as text controls with a numeric input mode rather than native number inputs, so no separator a user types is discarded by the browser and no spinner appears.

When a save is blocked because fields need attention, the save control SHALL state so plainly — what is wrong and how many fields — in the same 12px `--stamp` text as a field error, with no exclamation mark, and the statement SHALL move focus to the first invalid field when activated.

#### Scenario: Focusing a text input
- **WHEN** a user focuses a form text input
- **THEN** its bottom rule becomes `2px solid var(--stamp)` and no other frame or outline appears around it

#### Scenario: Validation failure
- **WHEN** a field fails validation (e.g. an invalid variable symbol)
- **THEN** an error message appears below the field in `--stamp`, 12px, describing the problem and the fix, without an exclamation mark

#### Scenario: Marking the invalid field itself
- **WHEN** a field is showing an error message
- **THEN** its bottom rule is `--stamp`-colored, it reports `aria-invalid`, its message is reachable through `aria-describedby`, and no outline, glow, fill or icon is added

#### Scenario: A numeric field
- **WHEN** a form presents a field that accepts only numbers
- **THEN** it is a text control with a numeric input mode, showing no spinner and accepting a typed decimal comma or point without discarding it

#### Scenario: A blocked save
- **WHEN** a save is attempted while fields in that section are invalid
- **THEN** the save control states how many fields need attention in 12px `--stamp` text without an exclamation mark, and activating that statement focuses the first invalid field

#### Scenario: Field inside a modal dialog
- **WHEN** a form field is rendered inside a modal dialog
- **THEN** its label sits above the control in the uppercase label style and the control spans the dialog's content width, identical to the same field rendered in a panel

#### Scenario: Multiline field
- **WHEN** a form presents a multiline text area
- **THEN** it carries the same label-above, transparent, bottom-ruled treatment as single-line inputs and can be resized vertically but not horizontally
