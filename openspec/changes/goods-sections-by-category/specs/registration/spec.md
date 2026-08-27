## MODIFIED Requirements

### Requirement: Registration form as a priced checklist
The registration form SHALL present everything a tournament offers as a single ordered checklist of sections. Each row SHALL carry a selection control, the item's name, and its price aligned in a shared column, with the item's optional `when`, `where`, and `remark` text as indented lines beneath it. A row whose per-registration limit is 1 SHALL be a checkbox alone; a row allowing more SHALL offer a quantity, defaulting to 1 when selected.

A discipline row SHALL be labelled by the discipline's name alone. A discipline's slug SHALL NOT appear on the registration form or anywhere else a fencer reads, as fixed by `discipline-identity`; it is the identifier the form submits, never text the form shows. Where a tournament offers several disciplines classified alike, their names are what distinguish them, and the form SHALL present those names as the organizer wrote them without prefixing, suffixing, or otherwise decorating them to mark the distinction.

Sections SHALL be derived from item categories, not from a separate list: the tournament's individual disciplines; the tournament's team disciplines; the optional programme, one section covering `seminar`, `afterparty`, and `other_action` together; and the goods, one section per item category — `rental`, then `merch`, then `other_item`, in that order. Each goods section SHALL be headed by the name of the category it holds, so the heading states what the rows are rather than that they are optional; no section SHALL pool the three item categories under one shared heading. A section with no rows SHALL be omitted entirely, so a tournament that only lends gear shows exactly one goods section. Within a section, rows SHALL keep the order the tournament states them in. The form SHALL show the tournament's display name, its subtitle when set, and its registration instructions when set, above the first section, and the running total below the last.

A team-discipline row SHALL NOT be a checkbox. It SHALL state the discipline, its roster bounds, and its per-team price, and SHALL offer an action that adds a team, which requires a team name. Each team the fencer has added SHALL appear as its own line beneath the discipline, showing the team name and the per-team price, and SHALL be removable. Adding a second team to the same discipline SHALL be offered, and each added team SHALL be priced separately rather than as a quantity. The composition deadline, when the tournament sets one, SHALL be stated in the team section together with the statement that rosters may be filled in later.

The form SHALL set the registration instructions and the total apart from the checklist by a vertical space visibly larger than the space between sections, so neither reads as a continuation of the block above it. The total SHALL be aligned to the trailing edge of the price column it sums, so it reads as that column's sum rather than as a line of prose.

Below the total the form SHALL offer exactly one non-billable field: a free-text note to the organizer, under its own section heading. It SHALL NOT offer an after-sparring checkbox or an accommodation field.

#### Scenario: Sections rendered from categories
- **WHEN** a tournament offers two disciplines, one seminar, one afterparty, and one merch item and a fencer opens the registration form
- **THEN** the disciplines appear in the tournament section, the seminar and afterparty together in the optional programme, the merch item under a section headed for merch, and each row shows its price

#### Scenario: Goods headed by their own category
- **WHEN** a tournament lends three weapons as rentals and sells one shirt as merch
- **THEN** the form shows two goods sections, the rental one first holding the three weapons and the merch one after it holding the shirt, each under its own category's heading

#### Scenario: Lending only, one section
- **WHEN** a tournament's only goods are three weapons offered as rentals
- **THEN** the form shows exactly one goods section, headed as equipment rental, and no heading naming the rows merely as optional appears anywhere on the form

#### Scenario: Discipline rows carry names, not slugs
- **WHEN** a fencer opens the registration form of a tournament whose disciplines have slugs
- **THEN** every discipline row reads as its name alone, and no slug appears anywhere on the form

#### Scenario: Two tiers distinguished by name
- **WHEN** a tournament offers two longsword disciplines named for its top and open brackets and a fencer opens the registration form
- **THEN** two rows appear, each labelled by its own name, each separately selectable and separately priced

#### Scenario: Team section rendered
- **WHEN** a tournament offers one individual and one team discipline
- **THEN** the form shows a team section stating the team discipline's roster bounds and per-team price, with an action to add a named team, and the composition deadline when one is set

#### Scenario: Individual and team in one weapon both offered
- **WHEN** a tournament offers both an individual and a team longsword discipline
- **THEN** the individual one appears in the disciplines section and the team one in the team section, each under its own name

#### Scenario: Two teams added to one discipline
- **WHEN** a fencer adds two named teams to the same team discipline
- **THEN** both appear as separate lines with the per-team price each, and the running total counts the fee twice

#### Scenario: Team requires a name
- **WHEN** a fencer adds a team without giving it a name
- **THEN** the form refuses the addition and asks for a name

#### Scenario: No team section without team disciplines
- **WHEN** a tournament offers only individual disciplines
- **THEN** no team section is rendered

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
