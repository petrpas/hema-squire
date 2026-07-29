## MODIFIED Requirements

### Requirement: Tournament definition
A tournament SHALL be defined by internal name, display name, an optional subtitle, an optional logo, date, communication language, location (free text), an optional description, a qualification statement, a list of titular organizers, and a set of disciplines. The subtitle is free text that MAY be longer than the display name and is frequently empty; every presentation of the tournament SHALL render correctly whether or not the subtitle is set. The logo is an optional image supplied by the organizer, stored with the tournament and served for display; the system SHALL bound its size on upload (reject oversized uploads and re-encode to a bounded image) so it stays small. The description is optional free-form plain text of arbitrary length, stored and presented verbatim with its line breaks preserved; it SHALL NOT be interpreted as markup of any kind. Titular organizers are free-text names of clubs or other entities shown publicly as the tournament's organizers, each with an optional link; they are independent of account-based console access. Each discipline SHALL have a code and human-readable name drawn from the HEMA taxonomy (weapon LS/SA/RA/RD/SB × gender Open/Women/Men × material Steel/Plastic), a capacity limit, a unit price, optional schedule fields (`when`, `where`) mainly for multi-day events, and an optional ruleset consisting of a short style name and an optional external link. In the console, a discipline SHALL be identified by its name in emphasized text, and each of its optional fields (`when`, `where`, ruleset name, ruleset link) SHALL carry a help hint stating what belongs in it. Subtitle, logo, description, qualification, disciplines (including their schedule and ruleset fields) and titular organizers SHALL be editable in the console Setup phase, disciplines and organizers as row tables with add and remove. The Setup section carrying the tournament's own identity fields SHALL NOT be given a section heading of its own.

#### Scenario: Organizer configures disciplines
- **WHEN** the organizer adds disciplines LS and SAW in the Setup table, each with a capacity and a unit price
- **THEN** registration offers exactly those disciplines under those capacity constraints at those prices

#### Scenario: Discipline schedule and ruleset captured
- **WHEN** the organizer sets a discipline's when to "Saturday", where to "Main Hall — Kurtzstrasse 21", and ruleset to "Right of Way" with an external link
- **THEN** the tournament information presents that discipline with its schedule and a ruleset link, and omits those lines for disciplines that leave them empty

#### Scenario: Optional discipline fields explain themselves
- **WHEN** the organizer reaches the help marker next to a discipline's `when`, `where`, ruleset name, or ruleset link field
- **THEN** a hint appears describing what belongs in that field (for example, for `when`: that it takes a rough time such as "Saturday morning")

#### Scenario: Subtitle and logo optional
- **WHEN** a tournament is saved with a subtitle and a logo, and another is saved with neither
- **THEN** both render correctly wherever the tournament is presented, the first showing its subtitle and logo and the second showing neither

#### Scenario: Oversized logo rejected
- **WHEN** the organizer uploads a logo larger than the configured cap
- **THEN** the upload is rejected with a clear message and no logo is stored

#### Scenario: Titular organizers edited
- **WHEN** the organizer adds "Duelanti od sv. Rocha" as a titular organizer row
- **THEN** the name appears wherever the tournament presents its organizers, without granting any console access

#### Scenario: Organizer with a link
- **WHEN** a titular organizer row carries a link and another leaves it empty
- **THEN** the first is presented as a link on the organizer's name and the second as plain text, and both are stored with the tournament

#### Scenario: Description written and presented
- **WHEN** the organizer writes a multi-paragraph description in Setup and saves
- **THEN** the description is stored as plain text and presented with its paragraph breaks intact, with no markup interpreted and no HTML rendered from its content

### Requirement: Pricing configuration
The system SHALL compute registration totals from categorized billable items and an ordered discount list.

Items: every billable item SHALL have a name, a price, and a category. Disciplines are items of category `discipline`, priced on their Setup rows. Extra services SHALL be organizer-defined rows with a free-text name (for example "afterparty saturday", "castle visit sunday", "t-shirt"), a category from a fixed enum, a price, an optional per-registration quantity limit (limit 1 renders as a checkbox, higher limits as a quantity selector), and optional descriptive fields `when`, `where`, and `remark` used when the item is presented informationally. These descriptive fields SHALL NOT affect pricing.

The extra-service category enum SHALL be `seminar`, `rental`, `afterparty`, `merch`, `other_action`, and `other_item`, and SHALL divide into two kinds: **action** categories (`seminar`, `afterparty`, `other_action`), which happen at a time and place, and **item** categories (`rental`, `merch`, `other_item`), which are goods. For action categories the console SHALL offer `when` and `where` and SHALL NOT offer a quantity limit; their quantity limit SHALL be stored as 1. For item categories the console SHALL offer the quantity limit and SHALL NOT offer `when` or `where`. `remark` SHALL be available for both kinds. `other_action` SHALL behave in every respect as `afterparty` and `seminar` do, and `other_item` as `merch` does. Existing rows in an action category whose stored quantity limit is greater than 1 SHALL retain that value until the row is next saved, so previously computed totals remain reproducible.

Discounts: an ordered list of rows, each with a name, a condition, an effect, and a category scope. Conditions SHALL be drawn from an extensible enumeration, initially: registered discipline count equals N, and registration date on or before a configured date (early bird). Effects SHALL be a fixed amount or a percentage. The total SHALL be computed by summing selected item prices, subtracting applicable fixed discounts from their scoped category subtotals (floored at zero), then applying applicable percentage discounts sequentially to their scoped subtotals, and finally rounding half-up to a whole currency unit exactly once. The category scope SHALL be stored per discount from the start (defaulting to `discipline`), even while the Setup UI does not yet expose a scope picker, and SHALL accept every category in the enum.

Tournaments with no extra-service items and no discounts SHALL keep the legacy computation (per-discipline fees, `fee_early`, and the fixed weapon-rental/afterparty parameters) so that historical totals remain reproducible.

#### Scenario: Count discount applied
- **WHEN** disciplines are priced 30 € each and a discount row "−10 € when 2 disciplines" exists, and a fencer registers for two disciplines
- **THEN** the discipline part of the total is 50 €, not 60 €

#### Scenario: Early bird as percentage discount
- **WHEN** a discount row "−15 % when registered before the early-bird date" exists and a fencer registers in time for two disciplines priced 30 € each with the −10 € count discount
- **THEN** the total is (60 − 10) × 0.85 = 42.5, rounded half-up to 43, and remains reproducible for that reservation

#### Scenario: Extra service with quantity
- **WHEN** the organizer defines "weapon rental" (category `rental`, 2 €, limit 4) and a fencer selects quantity 2
- **THEN** 4 € is added to the total

#### Scenario: Descriptive fields do not change totals
- **WHEN** an extra service carries when/where/remark text
- **THEN** the computed total is identical to the same item without those fields

#### Scenario: Action category offers place and time, not quantity
- **WHEN** the organizer sets an extra service's category to `afterparty`, `seminar`, or `other_action`
- **THEN** the row offers `when` and `where`, offers no quantity limit, and is stored with a quantity limit of 1

#### Scenario: Item category offers quantity, not place and time
- **WHEN** the organizer sets an extra service's category to `merch`, `rental`, or `other_item`
- **THEN** the row offers a quantity limit and offers neither `when` nor `where`

#### Scenario: Generic categories behave like their models
- **WHEN** a tournament defines an `other_action` row priced 15 € and an `other_item` row priced 15 €, and a fencer selects both
- **THEN** 30 € is added to the total, and discounts scoped to those categories apply exactly as they would to `afterparty` and `merch`

#### Scenario: Legacy tournament unaffected
- **WHEN** totals are recomputed for a tournament that has no extra-service items and no discounts
- **THEN** the legacy per-discipline fees and fixed extras produce the same totals as before this change

## ADDED Requirements

### Requirement: Tournament qualification statement
Each tournament SHALL carry a qualification statement consisting of an openness flag and optional criteria text. The flag SHALL default to open, so a tournament that never sets it presents as open to everyone. When the organizer marks the tournament as requiring qualification, criteria text SHALL be required and SHALL be free text (for example "national championship placement, HR top 500"); the field SHALL carry a help hint offering such examples. Marking the tournament open again SHALL clear the criteria text. The statement SHALL be editable in the Setup phase between the registration dates and the logo, and SHALL be presented wherever the tournament is described. The statement is informational: it SHALL NOT restrict, block, or flag any registration.

#### Scenario: Default is open
- **WHEN** a tournament is created and its qualification is never touched
- **THEN** it is stored as open to everyone and presented as such

#### Scenario: Qualification criteria recorded
- **WHEN** the organizer marks the tournament as requiring qualification and enters "mistrovství ČR, HR top 500"
- **THEN** that text is stored and presented as the tournament's qualification criteria

#### Scenario: Criteria required when qualification is required
- **WHEN** the organizer marks the tournament as requiring qualification and saves with empty criteria
- **THEN** the save is rejected with a field-level message and the tournament's stored qualification is unchanged

#### Scenario: Reopening clears criteria
- **WHEN** a tournament with qualification criteria is switched back to open to everyone and saved
- **THEN** the criteria text is cleared and the tournament presents as open to everyone

#### Scenario: Qualification does not gate registration
- **WHEN** a fencer registers for a tournament that requires qualification
- **THEN** the registration proceeds exactly as it would for an open tournament

### Requirement: Logo upload failure reporting
A failed logo upload SHALL tell the organizer which of the distinguishable causes occurred: the file exceeded the size cap, the file could not be decoded as an image, the account is not authorized, or the upload failed for another reason. A message SHALL NOT attribute a failure to the file's format unless the server actually rejected it as undecodable. The size cap SHALL be generous enough to accept an ordinary photograph produced by a phone or camera, since the server re-encodes every accepted image down to the stored bound regardless of input size, and the server SHALL record the underlying decode failure for diagnosis.

#### Scenario: Ordinary JPEG accepted
- **WHEN** the organizer uploads a multi-megapixel JPEG photograph of a few megabytes
- **THEN** the upload succeeds, the tournament reports having a logo, and the stored image is the re-encoded bounded version

#### Scenario: Oversized file named as oversized
- **WHEN** the uploaded file exceeds the size cap
- **THEN** the message states that the file is too large, and does not claim it is not an image

#### Scenario: Undecodable file named as such
- **WHEN** the uploaded file cannot be decoded as an image
- **THEN** the message states that the file is not a supported image, and the server records the decode failure

#### Scenario: Other failure not blamed on the file
- **WHEN** the upload fails for any other reason, such as an authorization or server error
- **THEN** the message reflects that cause and does not claim the file is not an image
