## MODIFIED Requirements

### Requirement: Tournament definition
A tournament SHALL be defined by internal name, display name, an optional subtitle, an optional logo, date, communication language, location (free text), a list of titular organizers, and a set of disciplines. The subtitle is free text that MAY be longer than the display name and is frequently empty; every presentation of the tournament SHALL render correctly whether or not the subtitle is set. The logo is an optional image supplied by the organizer, stored with the tournament and served for display; the system SHALL bound its size on upload (reject oversized uploads and re-encode to a bounded image) so it stays small. Titular organizers are free-text names of clubs or other entities shown publicly as the tournament's organizers; they are independent of account-based console access. Each discipline SHALL have a code and human-readable name drawn from the HEMA taxonomy (weapon LS/SA/RA/RD/SB × gender Open/Women/Men × material Steel/Plastic), a capacity limit, a unit price, optional schedule fields (`when`, `where`) mainly for multi-day events, and an optional ruleset consisting of a short style name and an optional external link. Subtitle, logo, disciplines (including their schedule and ruleset fields) and titular organizers SHALL be editable in the console Setup phase, disciplines and organizers as row tables with add and remove.

#### Scenario: Organizer configures disciplines
- **WHEN** the organizer adds disciplines LS and SAW in the Setup table, each with a capacity and a unit price
- **THEN** registration offers exactly those disciplines under those capacity constraints at those prices

#### Scenario: Discipline schedule and ruleset captured
- **WHEN** the organizer sets a discipline's when to "Saturday", where to "Main Hall — Kurtzstrasse 21", and ruleset to "Right of Way" with an external link
- **THEN** the tournament information presents that discipline with its schedule and a ruleset link, and omits those lines for disciplines that leave them empty

#### Scenario: Subtitle and logo optional
- **WHEN** a tournament is saved with a subtitle and a logo, and another is saved with neither
- **THEN** both render correctly wherever the tournament is presented, the first showing its subtitle and logo and the second showing neither

#### Scenario: Oversized logo rejected
- **WHEN** the organizer uploads a logo larger than the configured cap
- **THEN** the upload is rejected with a clear message and no logo is stored

#### Scenario: Titular organizers edited
- **WHEN** the organizer adds "Duelanti od sv. Rocha" as a titular organizer row
- **THEN** the name appears wherever the tournament presents its organizers, without granting any console access

### Requirement: Pricing configuration
The system SHALL compute registration totals from categorized billable items and an ordered discount list.

Items: every billable item SHALL have a name, a price, and a category. Disciplines are items of category `discipline`, priced on their Setup rows. Extra services SHALL be organizer-defined rows with a free-text name (for example "afterparty saturday", "castle visit sunday", "t-shirt"), a category from a fixed enum (`seminar`, `rental`, `afterparty`, `merch`), a price, an optional per-registration quantity limit (limit 1 renders as a checkbox, higher limits as a quantity selector), and optional descriptive fields `when`, `where`, and `remark` used when the item is presented informationally. These descriptive fields SHALL NOT affect pricing.

Discounts: an ordered list of rows, each with a name, a condition, an effect, and a category scope. Conditions SHALL be drawn from an extensible enumeration, initially: registered discipline count equals N, and registration date on or before a configured date (early bird). Effects SHALL be a fixed amount or a percentage. The total SHALL be computed by summing selected item prices, subtracting applicable fixed discounts from their scoped category subtotals (floored at zero), then applying applicable percentage discounts sequentially to their scoped subtotals, and finally rounding half-up to a whole currency unit exactly once. The category scope SHALL be stored per discount from the start (defaulting to `discipline`), even while the Setup UI does not yet expose a scope picker.

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

#### Scenario: Legacy tournament unaffected
- **WHEN** totals are recomputed for a tournament that has no extra-service items and no discounts
- **THEN** the legacy per-discipline fees and fixed extras produce the same totals as before this change
