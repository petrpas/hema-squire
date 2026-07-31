## ADDED Requirements

### Requirement: Tournament currency
A tournament SHALL have a primary currency drawn from a closed enumeration, initially `CZK` and `EUR`, defaulting to `CZK`. Every price the organizer configures — discipline unit prices, extra-service prices, fixed discount amounts, legacy fee parameters — and every computed total SHALL be expressed in whole units of that primary currency.

When the primary currency is not `EUR`, the organizer MAY enable EUR payments. Enabling them SHALL require an exchange rate expressed as primary-currency units per 1 EUR, which MUST be greater than zero. Disabling EUR payments SHALL clear the stored rate. When the primary currency is `EUR`, EUR payments SHALL be treated as enabled and no exchange rate SHALL be stored.

The Setup UI SHALL state the rate's direction explicitly and SHALL warn — without blocking the save — when the entered rate falls outside a plausible range.

#### Scenario: Czech tournament enables EUR payments
- **WHEN** the organizer sets the primary currency to CZK, enables EUR payments, and enters 25.5
- **THEN** the tournament stores CZK as its primary currency with EUR payments enabled at 25.5 CZK per EUR

#### Scenario: EUR payments without a rate rejected
- **WHEN** the organizer enables EUR payments on a CZK tournament and leaves the exchange rate empty
- **THEN** the save is rejected with a field-level validation error and no change is stored

#### Scenario: Non-positive rate rejected
- **WHEN** the organizer submits an exchange rate of 0 or a negative number
- **THEN** the save is rejected with a field-level validation error

#### Scenario: EUR-priced tournament stores no rate
- **WHEN** the organizer sets the primary currency to EUR
- **THEN** EUR payments are enabled, no exchange rate is stored, and no second currency figure is presented anywhere

#### Scenario: Disabling EUR payments clears the rate
- **WHEN** the organizer turns EUR payments off on a tournament that had a rate
- **THEN** the rate is cleared and EUR figures stop being presented

#### Scenario: Implausible rate warns but saves
- **WHEN** the organizer enters an exchange rate far outside the plausible range
- **THEN** Setup shows a warning naming the expected direction and the save still succeeds

#### Scenario: Existing tournaments unchanged
- **WHEN** a tournament created before this change is loaded
- **THEN** its primary currency is CZK with EUR payments disabled, and its prices and totals are identical to before

### Requirement: Registration instructions
A tournament SHALL have an optional multiline free-text `registration instructions` field, editable in the Setup phase and distinct from the public description. It SHALL be presented only on the registration form, with line breaks preserved and no markup interpretation. It SHALL NOT be part of mandatory setup, and its absence SHALL NOT change any other presentation.

#### Scenario: Instructions shown on the form only
- **WHEN** the organizer fills registration instructions and a fencer opens the tournament
- **THEN** the instructions appear on the registration form and do not appear on the information screen

#### Scenario: Instructions absent
- **WHEN** a tournament has no registration instructions
- **THEN** the registration form renders correctly with no instructions block

#### Scenario: Line breaks preserved
- **WHEN** the instructions contain several paragraphs
- **THEN** they render with their line breaks and no markup is interpreted

### Requirement: Extra-service option field
An extra service MAY declare a single option: an option label (for example "size") and an optional list of preset choices. A label with choices SHALL be answered by picking one of the choices; a label without choices SHALL be answered with free text. An extra service with no option label SHALL take no option. Options SHALL be purely descriptive and SHALL NOT affect price computation.

#### Scenario: Option with preset choices configured
- **WHEN** the organizer defines "t-shirt" (category `merch`, 300, limit 5) with option label "size" and choices S, M, L, XL
- **THEN** registration offers that item with a choice of those four sizes

#### Scenario: Free-text option configured
- **WHEN** the organizer defines an option label with no choices
- **THEN** registration offers that item with a free-text field for the option

#### Scenario: Option does not change the total
- **WHEN** totals are computed for a selection with an option answered and for the same selection without the option
- **THEN** both totals are identical

## MODIFIED Requirements

### Requirement: Setup completeness
Mandatory setup SHALL comprise: display name, date, location, at least one titular organizer, at least one discipline with a unit price, and — whenever EUR payments are enabled on a tournament whose primary currency is not EUR — a positive exchange rate. The Setup phase SHALL show a completeness checklist naming each missing item. A tournament with incomplete mandatory setup SHALL NOT accept registrations.

#### Scenario: Checklist shows gaps
- **WHEN** the organizer opens Setup for a tournament without location and without discipline prices
- **THEN** the checklist lists location and the missing unit prices as blocking registration

#### Scenario: Missing exchange rate blocks registration
- **WHEN** a CZK tournament has EUR payments enabled with no exchange rate
- **THEN** the checklist lists the missing exchange rate and registration is unavailable

#### Scenario: Setup completed
- **WHEN** the last mandatory item is filled
- **THEN** the checklist reports the tournament ready and registration becomes available (subject to the registration window)
