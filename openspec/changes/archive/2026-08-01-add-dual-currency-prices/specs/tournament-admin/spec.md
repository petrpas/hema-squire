## MODIFIED Requirements

### Requirement: Tournament currency
A tournament SHALL be priced in one of three currency modes, chosen in Setup above the price tables:

- **local only** — a single local currency drawn from a closed enumeration, initially `CZK` and `EUR`.
- **local + EUR** — a local currency that is not EUR, plus EUR as an accepted second currency.
- **EUR only** — the local currency is EUR and there is no second currency.

The mode SHALL decide how the price tables render: one price column in the single-currency modes, and two in local + EUR. Every configured price SHALL be a whole unit of the currency of its column, and completeness SHALL follow from the form — a rendered price field left empty is an incomplete price, checked by the same rule that already governs single-currency tournaments, with no separate EUR-completeness rule.

In local + EUR mode the local price and the EUR price of any item SHALL both be organizer decisions and SHALL both be stored as entered. Neither SHALL be computed from the other at any point after entry. The two prices of an item, and therefore the two totals of a registration, are NOT required to correspond at any exchange rate, and the system SHALL NOT check, warn about, or reconcile the ratio between them.

The organizer MAY record an exchange ratio, expressed as local-currency units per 1 EUR. It SHALL be used for exactly one purpose: a **recalculate missing** action that fills empty price fields from filled ones, rounding half-up to whole units, in either direction. The action SHALL fill only empty fields and SHALL NOT overwrite any price the organizer has entered. It SHALL run only when explicitly invoked, never on save, on rate change, or automatically. The recorded ratio SHALL NOT be read by price computation, registration totals, payment instructions, QR generation, or payment matching.

Changing the currency mode SHALL retain stored prices rather than clearing them, so that a mode switched away from and back again reveals the same prices unchanged.

The Setup UI SHALL state the ratio's direction explicitly and SHALL warn — without blocking the save — when the entered ratio falls outside a plausible range.

#### Scenario: Czech tournament prices in both currencies
- **WHEN** the organizer selects CZK + EUR and enters 800 Kč and 32 € for a discipline
- **THEN** both prices are stored as entered and neither is recomputed from the other

#### Scenario: Prices need not correspond at the ratio
- **WHEN** the organizer prices one discipline 800 Kč / 32 € and another 700 Kč / 30 € while the recorded ratio is 25
- **THEN** both rows are accepted, no warning is raised about the differing implied ratios, and both totals compute from their own column

#### Scenario: Single-currency mode renders one column
- **WHEN** the organizer selects CZK only, or EUR only
- **THEN** the price tables render a single price column and no EUR figure is presented anywhere

#### Scenario: Recalculate fills only what is empty
- **WHEN** the organizer fills every CZK price, fills the EUR price of one discipline by hand, and invokes recalculate missing at a ratio of 25
- **THEN** the empty EUR prices are filled with the CZK prices divided by 25 rounded to whole units, and the hand-entered EUR price is left exactly as typed

#### Scenario: Recalculate works in either direction
- **WHEN** the organizer fills only EUR prices and invokes recalculate missing
- **THEN** the empty local prices are filled from the EUR prices at the recorded ratio, rounded to whole units

#### Scenario: Ratio never reaches a computed amount
- **WHEN** the organizer changes the recorded ratio after prices are entered
- **THEN** no stored price, no registration total, no payment instruction, and no QR code changes

#### Scenario: Mode switch retains prices
- **WHEN** the organizer switches a fully priced CZK + EUR tournament to CZK only and later switches back
- **THEN** the EUR prices are hidden while in single-currency mode and are present and unchanged on switching back

#### Scenario: Incomplete EUR prices block registration
- **WHEN** a tournament is in CZK + EUR mode with one discipline's EUR price left empty
- **THEN** the completeness checklist reports that price as missing and registration is unavailable

#### Scenario: Implausible ratio warns but saves
- **WHEN** the organizer enters an exchange ratio far outside the plausible range
- **THEN** Setup shows a warning naming the expected direction and the save still succeeds

#### Scenario: Existing tournaments unchanged
- **WHEN** a tournament created before this change is loaded
- **THEN** its local currency and prices are those it already had, and its totals are identical to before

### Requirement: Pricing configuration
The system SHALL compute registration totals from categorized billable items and an ordered discount list.

Items: every billable item SHALL have a name, a price, and a category. In local + EUR mode every billable item SHALL additionally have a EUR price, stored independently of its local price. Disciplines are items of category `discipline`, priced on their Setup rows, with standard and early-bird prices in each configured currency. Extra services SHALL be organizer-defined rows with a free-text name (for example "afterparty saturday", "castle visit sunday", "t-shirt"), a category from a fixed enum, a price per configured currency, an optional per-registration quantity limit (limit 1 renders as a checkbox, higher limits as a quantity selector), and optional descriptive fields `when`, `where`, and `remark` used when the item is presented informationally. These descriptive fields SHALL NOT affect pricing.

The extra-service category enum SHALL be `seminar`, `rental`, `afterparty`, `merch`, `other_action`, and `other_item`, and SHALL divide into two kinds: **action** categories (`seminar`, `afterparty`, `other_action`), which happen at a time and place, and **item** categories (`rental`, `merch`, `other_item`), which are goods. For action categories the console SHALL offer `when` and `where` and SHALL NOT offer a quantity limit; their quantity limit SHALL be stored as 1. For item categories the console SHALL offer the quantity limit and SHALL NOT offer `when` or `where`. `remark` SHALL be available for both kinds. `other_action` SHALL behave in every respect as `afterparty` and `seminar` do, and `other_item` as `merch` does. Existing rows in an action category whose stored quantity limit is greater than 1 SHALL retain that value until the row is next saved, so previously computed totals remain reproducible.

Discounts: an ordered list of rows, each with a name, a condition, an effect, and a category scope. Conditions SHALL be drawn from an extensible enumeration, initially: registered discipline count equals N, and registration date on or before a configured date (early bird). Effects SHALL be a fixed amount or a percentage. A fixed-amount effect SHALL carry an amount per configured currency, since a fixed discount is a price decision like any other; a percentage effect is currency-neutral and SHALL carry a single value. The total SHALL be computed **independently for each configured currency**, in each case by summing that currency's selected item prices, subtracting that currency's applicable fixed discounts from their scoped category subtotals (floored at zero), then applying applicable percentage discounts sequentially to their scoped subtotals, and finally rounding half-up to a whole currency unit exactly once. The category scope SHALL be stored per discount from the start (defaulting to `discipline`), even while the Setup UI does not yet expose a scope picker, and SHALL accept every category in the enum.

The totals produced for the two currencies are independent results of the same computation over different inputs, and SHALL NOT be expected or required to correspond at any exchange ratio.

Tournaments with no extra-service items and no discounts SHALL keep the legacy computation (per-discipline fees, `fee_early`, and the fixed weapon-rental/afterparty parameters) so that historical totals remain reproducible. The fixed weapon-rental and afterparty parameters SHALL remain single-currency; a tournament whose pricing still uses them SHALL NOT be able to enable EUR, and the completeness checklist SHALL name them and direct the organizer to itemized extra services.

#### Scenario: Count discount applied
- **WHEN** disciplines are priced 30 € each and a discount row "−10 € when 2 disciplines" exists, and a fencer registers for two disciplines
- **THEN** the discipline part of the total is 50 €, not 60 €

#### Scenario: Early bird as percentage discount
- **WHEN** a discount row "−15 % when registered before the early-bird date" exists and a fencer registers in time for two disciplines priced 30 € each with the −10 € count discount
- **THEN** the total is (60 − 10) × 0.85 = 42.5, rounded half-up to 43, and remains reproducible for that reservation

#### Scenario: Extra service with quantity
- **WHEN** the organizer defines "weapon rental" (category `rental`, 2 €, limit 4) and a fencer selects quantity 2
- **THEN** 4 € is added to the total

#### Scenario: Each currency totalled independently
- **WHEN** a fencer registers for two disciplines priced 800 Kč / 32 € and 700 Kč / 28 € on a CZK + EUR tournament
- **THEN** the local total is 1500 Kč and the EUR total is 60 €, each summed from its own column

#### Scenario: Fixed discount applied per currency
- **WHEN** a fixed discount of 200 Kč / 8 € applies to a registration
- **THEN** 200 is subtracted from the local total and 8 from the EUR total, each floored at zero within its own computation

#### Scenario: Percentage discount applied to both
- **WHEN** a −15 % discount applies on a CZK + EUR tournament
- **THEN** it is applied to each currency's scoped subtotals, each rounded half-up to a whole unit exactly once

#### Scenario: Totals need not correspond
- **WHEN** a registration's two totals are computed and their implied ratio differs from the recorded exchange ratio
- **THEN** both totals stand as computed and no reconciliation, warning, or adjustment occurs

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

#### Scenario: Legacy fixed parameters block EUR
- **WHEN** the organizer attempts to enable EUR on a tournament still pricing through the fixed weapon-rental and afterparty parameters
- **THEN** the completeness checklist names those parameters as blocking EUR and directs the organizer to itemized extra services

## ADDED Requirements

### Requirement: Price changes during open registration
The organizer SHALL be able to change prices at any time, including while registration is open. The system SHALL NOT prevent it.

When a price is changed on a tournament whose registration is open, the organizer SHALL be warned before the change is saved, and the warning SHALL state what actually happens: that fencers already registered keep the amount they were quoted, that a fencer who subsequently amends their registration is repriced at the new prices, and that new registrations use the new prices. The warning SHALL state that changing prices mid-registration is bad practice, and SHALL allow the organizer to proceed.

Registrations already created SHALL retain the total computed when they were created, so a price change SHALL NOT alter what any existing registration owes and SHALL NOT affect the reconciliation of any payment.

#### Scenario: Warning shown on a price change with registration open
- **WHEN** the organizer changes a discipline price on a tournament whose registration is open
- **THEN** a warning states that existing registrations keep their quoted amount, that amending fencers are repriced, and that new registrations use the new price, and the organizer can proceed

#### Scenario: No warning before registration opens
- **WHEN** the organizer changes a price on a tournament whose registration has not opened
- **THEN** the price is saved without the warning

#### Scenario: Existing registrations keep their total
- **WHEN** a discipline's price is raised after fencers have registered for it
- **THEN** every existing registration's total is unchanged and every pending payment reconciles against the amount originally quoted

#### Scenario: New registrations take the new price
- **WHEN** a fencer registers after a price change
- **THEN** their total is computed from the new prices
