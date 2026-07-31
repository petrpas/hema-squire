## ADDED Requirements

### Requirement: Money rendered from amount and currency
Monetary values SHALL be rendered by a single formatting function per surface — one in the frontend, one for emails and generated documents — taking the amount and a currency code and returning the localized string, with the unit drawn from a currency-symbol table. Locale resources SHALL NOT contain a currency unit baked into message text or field labels; labels that need to name a currency SHALL take it as an interpolated parameter. Adding a currency SHALL require extending the symbol table only, with no change to locale resources.

#### Scenario: Total rendered in the tournament's currency
- **WHEN** a total of 1750 is rendered for a CZK tournament and the same amount for a EUR tournament
- **THEN** each renders with its own unit from the symbol table using one shared message key

#### Scenario: Field labels take the currency as a parameter
- **WHEN** a price field label is rendered for a tournament
- **THEN** the label names that tournament's currency through interpolation rather than through a currency-specific message key

#### Scenario: No currency literals in locale resources
- **WHEN** the locale resources and email templates are inspected
- **THEN** no currency unit or code appears as literal text in any message value

#### Scenario: Email amounts follow the communication language
- **WHEN** a confirmation email is generated for a tournament whose communication language is Czech
- **THEN** the amount is formatted for Czech with the tournament's currency unit, from the shared email formatter
