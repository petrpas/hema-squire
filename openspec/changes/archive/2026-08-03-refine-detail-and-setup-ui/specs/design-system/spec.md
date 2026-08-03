## MODIFIED Requirements

### Requirement: Field help hints
A form field MAY carry a help hint explaining what belongs in it. The hint SHALL be reached through a marker placed after the field's label, drawn from the outline icon set or as a bordered glyph in `--ink-faded`, never an emoji and never filled. The hint SHALL be revealed on pointer hover **and** on keyboard focus of the marker, and SHALL be rendered as a static box on `--paper-raised` with a `1px solid var(--ink)` border and 2px radius — with no shadow, no blur, no transition, and no entrance animation. The marker SHALL be a focusable control associated with the hint text via `aria-describedby`. Help hints SHALL be reserved for fields whose expected content is not evident from the label; they SHALL NOT replace field labels or error messages.

A revealed hint SHALL be legible in full, above every element it overlaps — including the neighbouring cells of a sticky table header it is opened from, and the rows beneath it. Nothing on the page SHALL paint over an open hint box.

#### Scenario: Revealing a hint by pointer
- **WHEN** a user hovers the help marker next to a field label
- **THEN** the hint text appears in a static bordered box with no shadow and no animation, and disappears when the pointer leaves

#### Scenario: Revealing a hint by keyboard
- **WHEN** a user tabs to the help marker
- **THEN** the same hint box appears and the marker's `aria-describedby` resolves to the hint text

#### Scenario: A self-evident field
- **WHEN** a field's label already states what belongs in it
- **THEN** no help marker is rendered

#### Scenario: Hint opened from a table header
- **WHEN** a user reveals the hint on a column header that has other column headers to its right in the same sticky header row
- **THEN** the whole hint box is readable above those headers, with no part of it hidden behind them
