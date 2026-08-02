## MODIFIED Requirements

### Requirement: Registration form as a priced checklist
The registration form SHALL present everything a tournament offers as a single ordered checklist of sections. Each row SHALL carry a selection control, the item's name, and its price aligned in a shared column, with the item's optional `when`, `where`, and `remark` text as indented lines beneath it. A row whose per-registration limit is 1 SHALL be a checkbox alone; a row allowing more SHALL offer a quantity, defaulting to 1 when selected.

A discipline row SHALL be labelled by the discipline's name alone. A discipline's slug SHALL NOT appear on the registration form or anywhere else a fencer reads, as fixed by `discipline-identity`; it is the identifier the form submits, never text the form shows. Where a tournament offers several disciplines classified alike, their names are what distinguish them, and the form SHALL present those names as the organizer wrote them without prefixing, suffixing, or otherwise decorating them to mark the distinction.

Sections SHALL be derived from item categories, not from a separate list: the tournament's individual disciplines; the tournament's team disciplines; the optional programme (`seminar`, `afterparty`, `other_action`); and optional items (`rental`, `merch`, `other_item`). A section with no rows SHALL be omitted entirely. The form SHALL show the tournament's display name, its subtitle when set, and its registration instructions when set, above the first section, and the running total below the last.

A team-discipline row SHALL NOT be a checkbox. It SHALL state the discipline, its roster bounds, and its per-team price, and SHALL offer an action that adds a team, which requires a team name. Each team the fencer has added SHALL appear as its own line beneath the discipline, showing the team name and the per-team price, and SHALL be removable. Adding a second team to the same discipline SHALL be offered, and each added team SHALL be priced separately rather than as a quantity. The composition deadline, when the tournament sets one, SHALL be stated in the team section together with the statement that rosters may be filled in later.

#### Scenario: Sections rendered from categories
- **WHEN** a tournament offers two disciplines, one seminar, one afterparty, and one merch item and a fencer opens the registration form
- **THEN** the disciplines appear in the tournament section, the seminar and afterparty in the optional programme, the merch item in optional items, and each row shows its price

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

#### Scenario: Empty section omitted
- **WHEN** a tournament offers disciplines and no extra services of any programme category
- **THEN** the optional programme section is not rendered

#### Scenario: No team section without team disciplines
- **WHEN** a tournament offers only individual disciplines
- **THEN** no team section is rendered

#### Scenario: Descriptive lines shown per row
- **WHEN** an extra service carries when, where, and remark text
- **THEN** those lines appear indented under that item's row and nowhere else

#### Scenario: Quantity offered only above limit one
- **WHEN** one item has a per-registration limit of 1 and another a limit of 5
- **THEN** the first renders as a checkbox alone and the second offers a quantity that defaults to 1 on selection

#### Scenario: Instructions and subtitle carried
- **WHEN** the tournament has a subtitle and registration instructions
- **THEN** both appear above the first section, and a tournament with neither renders the form correctly without them

### Requirement: Confirmation email with QR payment
On registration the system SHALL send a localized confirmation email containing the registration summary — items with quantities and option values — the total amount with its currency, the bank account, the VS, and an SPAYD-format QR code encoding amount, currency, account, VS, and message. When the tournament prices in EUR as a second currency, the email SHALL additionally carry the EUR total and a second QR code denominated in EUR against the same account.

Each discipline entered SHALL be summarized by its name alone. The email SHALL NOT carry discipline slugs, which are not fencer-facing text (`discipline-identity`); where a tournament offers several disciplines classified alike, the name is what tells the fencer which one they entered.

Each QR code SHALL encode the stored total of its own currency, with the SPAYD currency field taken from that currency. No amount in either QR code SHALL be produced by conversion.

#### Scenario: QR payment
- **WHEN** the fencer scans the QR code from the confirmation email in a banking app
- **THEN** the prefilled payment carries the exact amount, currency, account, and VS needed for automatic matching

#### Scenario: Disciplines summarized by name
- **WHEN** a fencer registers for two disciplines
- **THEN** the email lists each by its name alone, with no slug alongside it

#### Scenario: Tiers legible in the summary
- **WHEN** a fencer registers for one of two longsword disciplines that differ only by name
- **THEN** the email names the one they entered, and it is distinguishable from the one they did not

#### Scenario: EUR QR carries the stored EUR total
- **WHEN** a CZK + EUR tournament confirms a reservation totalling 1500 Kč and 60 €
- **THEN** the email carries a CZK QR for 1500 and a EUR QR for 60, each with its own currency in the SPAYD currency field

#### Scenario: No EUR block in single-currency mode
- **WHEN** a tournament prices in one currency
- **THEN** the email carries exactly one amount and one QR code

#### Scenario: Emailed amounts stable against configuration changes
- **WHEN** the organizer changes prices or the recorded ratio after a confirmation email was sent
- **THEN** the reminder and the in-app instructions for that reservation state the same amounts and carry the same QR codes as the original confirmation
