## MODIFIED Requirements

### Requirement: In-app registration
An authenticated fencer SHALL register for a tournament by selecting disciplines and any of the tournament's configured extra services, each with a quantity up to the item's per-registration limit and an option value where the item declares an option label, plus one non-billable field: a free-text note to the organizer. For legacy tournaments without configured extra services, the fixed weapon-rental and afterparty options SHALL remain accepted as before and SHALL be presented as rows in the same checklist. The system SHALL record the registration time, compute the total from the tournament's itemized pricing and discounts, and create a reservation with a unique VS. The confirmation email and exports SHALL list the selected items with their quantities and option values. Registration is exposed through the API and through the fencer-facing tournament detail page (fencer-home capability).

The registration API SHALL continue to accept and store the after-sparring flag and the accommodation note, because the table-import path still parses both from legacy sources; a registration created in-app SHALL simply carry neither, and their absence SHALL NOT change any total, export, or email.

#### Scenario: Successful registration
- **WHEN** a fencer submits a registration with two disciplines, weapon rental quantity 1, and "afterparty saturday"
- **THEN** a reservation is created with a unique VS and a total computed from the tournament's items and discounts
- **AND** a confirmation email itemizing the selection with payment instructions is sent

#### Scenario: Quantity above the item limit
- **WHEN** a fencer submits an extra-service quantity above the item's per-registration limit
- **THEN** the registration is rejected with a validation error

#### Scenario: Note retained
- **WHEN** a fencer writes a note to the organizer and registers
- **THEN** it is stored on the registration, appears wherever the registration is presented to the organizer, and does not change the computed total

#### Scenario: In-app registration carries no after-sparring or accommodation
- **WHEN** a fencer completes the in-app form
- **THEN** the created registration has no after-sparring flag set and no accommodation note, and every total, export and email is exactly what it would have been with those fields empty

#### Scenario: Imported registration keeps both
- **WHEN** a registration is created through the table-import path from a source row declaring after-sparring and an accommodation note
- **THEN** both are stored on the registration as before

### Requirement: Registration form as a priced checklist
The registration form SHALL present everything a tournament offers as a single ordered checklist of sections. Each row SHALL carry a selection control, the item's name, and its price aligned in a shared column, with the item's optional `when`, `where`, and `remark` text as indented lines beneath it. A row whose per-registration limit is 1 SHALL be a checkbox alone; a row allowing more SHALL offer a quantity, defaulting to 1 when selected.

Sections SHALL be derived from item categories, not from a separate list: the tournament's disciplines; the optional programme (`seminar`, `afterparty`, `other_action`); and optional items (`rental`, `merch`, `other_item`). A section with no rows SHALL be omitted entirely. The form SHALL show the tournament's display name, its subtitle when set, and its registration instructions when set, above the first section, and the running total below the last.

The form SHALL set the registration instructions and the total apart from the checklist by a vertical space visibly larger than the space between sections, so neither reads as a continuation of the block above it. The total SHALL be aligned to the trailing edge of the price column it sums, so it reads as that column's sum rather than as a line of prose.

Below the total the form SHALL offer exactly one non-billable field: a free-text note to the organizer, under its own section heading. It SHALL NOT offer an after-sparring checkbox or an accommodation field.

#### Scenario: Sections rendered from categories
- **WHEN** a tournament offers two disciplines, one seminar, one afterparty, and one merch item and a fencer opens the registration form
- **THEN** the disciplines appear in the tournament section, the seminar and afterparty in the optional programme, the merch item in optional items, and each row shows its price

#### Scenario: Empty section omitted
- **WHEN** a tournament offers disciplines and no extra services of any programme category
- **THEN** the optional programme section is not rendered

#### Scenario: Descriptive lines shown per row
- **WHEN** an extra service carries when, where, and remark text
- **THEN** those lines appear indented under that item's row and nowhere else

#### Scenario: Quantity offered only above limit one
- **WHEN** one item has a per-registration limit of 1 and another a limit of 5
- **THEN** the first renders as a checkbox alone and the second offers a quantity that defaults to 1 on selection

#### Scenario: Instructions and subtitle carried
- **WHEN** the tournament has a subtitle and registration instructions
- **THEN** both appear above the first section, and a tournament with neither renders the form correctly without them

#### Scenario: Instructions and total set apart
- **WHEN** a fencer opens a form with registration instructions and at least one section
- **THEN** the gap above the instructions and the gap above the total are each visibly larger than the gap between two consecutive sections

#### Scenario: Total aligned over the price column
- **WHEN** a fencer reads the total on a form whose rows show prices in a shared right-hand column
- **THEN** the total's amount is aligned to that column's trailing edge

#### Scenario: Only the note remains below the total
- **WHEN** a fencer reaches the bottom of the form
- **THEN** they find one free-text note field under its own heading, and no after-sparring checkbox and no accommodation field anywhere on the form
