## MODIFIED Requirements

### Requirement: Form (tiskopis) conventions
Forms SHALL number their sections with Roman numerals ("I.", "II.", …). Every labeled field, **in panels and in modal dialogs alike**, SHALL place its label above the control, styled per the typography conventions (10.5–11px uppercase, `letter-spacing: 0.12em`, weight 500, `--ink-faded`), with the control occupying the full width of its container. Inputs SHALL have a transparent background with a bottom rule only (`1px solid var(--ink)`), switching to a 2px `--stamp` bottom rule on focus, and no full-perimeter frame. Multiline text areas SHALL follow the same treatment and SHALL resize vertically only. Select and checkbox inputs SHALL use a full `1px solid var(--hairline)` frame on `--paper-raised` with 2px radius. Field error messages SHALL be `--stamp`-colored, 12px, placed below the field, stating what happened and what to do, with no exclamation marks.

#### Scenario: Focusing a text input
- **WHEN** a user focuses a form text input
- **THEN** its bottom rule becomes `2px solid var(--stamp)` and no other frame or outline appears around it

#### Scenario: Validation failure
- **WHEN** a field fails validation (e.g. an invalid variable symbol)
- **THEN** an error message appears below the field in `--stamp`, 12px, describing the problem and the fix, without an exclamation mark

#### Scenario: Field inside a modal dialog
- **WHEN** a form field is rendered inside a modal dialog
- **THEN** its label sits above the control in the uppercase label style and the control spans the dialog's content width, identical to the same field rendered in a panel

#### Scenario: Multiline field
- **WHEN** a form presents a multiline text area
- **THEN** it carries the same label-above, transparent, bottom-ruled treatment as single-line inputs and can be resized vertically but not horizontally

## ADDED Requirements

### Requirement: Field help hints
A form field MAY carry a help hint explaining what belongs in it. The hint SHALL be reached through a marker placed after the field's label, drawn from the outline icon set or as a bordered glyph in `--ink-faded`, never an emoji and never filled. The hint SHALL be revealed on pointer hover **and** on keyboard focus of the marker, and SHALL be rendered as a static box on `--paper-raised` with a `1px solid var(--ink)` border and 2px radius — with no shadow, no blur, no transition, and no entrance animation. The marker SHALL be a focusable control associated with the hint text via `aria-describedby`. Help hints SHALL be reserved for fields whose expected content is not evident from the label; they SHALL NOT replace field labels or error messages.

#### Scenario: Revealing a hint by pointer
- **WHEN** a user hovers the help marker next to a field label
- **THEN** the hint text appears in a static bordered box with no shadow and no animation, and disappears when the pointer leaves

#### Scenario: Revealing a hint by keyboard
- **WHEN** a user tabs to the help marker
- **THEN** the same hint box appears and the marker's `aria-describedby` resolves to the hint text

#### Scenario: A self-evident field
- **WHEN** a field's label already states what belongs in it
- **THEN** no help marker is rendered
