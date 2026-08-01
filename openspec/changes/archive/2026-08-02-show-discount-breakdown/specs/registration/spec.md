## MODIFIED Requirements

### Requirement: Price preview
The system SHALL compute the total price for a hypothetical selection (disciplines and extra services with quantities and option values) for a tournament without creating a registration, using the same pricing engine — itemized pricing with discounts, or the legacy fee fields for legacy tournaments — that applies at registration time, evaluated as of the current date. The preview SHALL return a total per configured currency, each summed from that currency's prices by the same computation the registration will use.

The preview SHALL additionally return a discount breakdown: one entry for every discount the tournament configures, in configured order, each carrying the discount's name, its effect, and whether that discount applied to the previewed selection. An entry that applied SHALL also carry the amount the discount deducted, per configured currency for a fixed effect and as a single figure for a currency-neutral percentage effect. Applicability SHALL be reported once for the whole entry, since a discount's condition is evaluated from discipline counts and dates and never from money, and therefore cannot differ between currencies. The breakdown SHALL report the discounts the priced computation actually applied and SHALL NOT be evaluated separately from it. A tournament with no configured discounts SHALL return an empty breakdown.

#### Scenario: Preview matches registration
- **WHEN** a price preview is requested for a selection and the same selection is then submitted as a registration at the same date
- **THEN** the previewed totals equal the registration's computed totals in every configured currency

#### Scenario: Preview carries both totals
- **WHEN** a price preview is requested on a CZK + EUR tournament
- **THEN** the response carries the CZK total and the EUR total, each summed from its own prices

#### Scenario: Preview in single-currency mode
- **WHEN** a price preview is requested on a tournament pricing in one currency
- **THEN** the response carries exactly one total

#### Scenario: Breakdown reports applied and unapplied discounts
- **WHEN** a tournament configures a discount for exactly 2 disciplines and one for exactly 3, and a preview is requested for a 2-discipline selection
- **THEN** the breakdown carries both discounts, the 2-discipline one marked as applied and the 3-discipline one marked as not applied

#### Scenario: Applied fixed discount reports its deduction per currency
- **WHEN** a preview on a CZK + EUR tournament activates a fixed discount of 500 Kč / 20 € that is fully absorbed by its scoped subtotal
- **THEN** its breakdown entry reports 500 deducted in CZK and 20 deducted in EUR, each read from that currency's own computation

#### Scenario: Applied percentage discount reports one figure
- **WHEN** a preview activates a −10 % discount
- **THEN** its breakdown entry reports the percentage effect without a second, EUR-denominated value

#### Scenario: Deduction floored at the scoped subtotal is reported as taken
- **WHEN** a fixed discount of 500 activates against a scoped subtotal of 300
- **THEN** the entry is marked as applied and reports 300 deducted, matching what the total reflects

#### Scenario: Early-bird applicability judged by the server date
- **WHEN** a preview is requested on a tournament whose early-bird date has passed
- **THEN** the early-bird entry is marked as not applied, and the total carries no early-bird reduction

#### Scenario: Tournament without discounts
- **WHEN** a price preview is requested on a legacy tournament, or on any tournament with no configured discounts
- **THEN** the response carries its totals and an empty discount breakdown
