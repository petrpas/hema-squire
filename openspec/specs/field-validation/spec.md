# field-validation Specification

## Purpose
Ensure every editable field in Squire has a declared, enforced constraint — shared between backend and frontend, tested against drift — covering string, numeric, money, and URL fields; a machine-readable error envelope; full locale coverage for validation messages; and a consistent blur/save validation timing, so a mistyped value is caught before it can be stored or quoted to a fencer.

## Requirements

### Requirement: Every edit field has a declared constraint
Every field a user can type into SHALL have a declared data type and accepted value set: strings a maximum length (and a minimum where an empty value is meaningless), integers a minimum and a maximum, decimals a minimum, a maximum and a fixed number of decimal places, enumerations their permitted values, and patterned fields their pattern. No editable field SHALL remain unbounded.

The declarations SHALL live in one authoritative backend module. Every pydantic `Field(...)` bound SHALL be read from that module rather than written inline, and the frontend SHALL read the same bounds from a checked-in TypeScript mirror. The mirror SHALL NOT be trusted to stay correct by discipline: a test SHALL compare it against the constraints the backend actually publishes in its OpenAPI schema and SHALL fail when any bound differs or is missing on either side.

#### Scenario: A bound is changed on one side only
- **WHEN** a maximum length is changed in the backend constraint module and the TypeScript mirror is not updated
- **THEN** the mirror test fails, naming the field and both values

#### Scenario: A new editable field is added without a bound
- **WHEN** a new editable string, integer or decimal field is added to a request schema with no declared constraint
- **THEN** the mirror test fails, naming the field as unconstrained

#### Scenario: The frontend limits input to the declared length
- **WHEN** a user types into a field whose declared maximum length is 200
- **THEN** the control refuses characters past 200 and the value that reaches the backend can never exceed the declared maximum

### Requirement: Global string rules
All string fields SHALL be trimmed of leading and trailing whitespace before validation and before storage. Single-line string fields SHALL additionally collapse internal runs of whitespace to a single space. All string fields SHALL reject C0 and C1 control characters and zero-width joiner characters, whether typed, pasted or posted directly to the API.

Every string field SHALL carry an explicit ceiling drawn from three tiers: single-line fields at most 200 characters, longer single-line and short descriptive fields 300–500, and markdown body fields 5000.

#### Scenario: Padded input
- **WHEN** a value is submitted as `"  Prague  "`
- **THEN** it is validated and stored as `"Prague"`

#### Scenario: Pasted invisible characters
- **WHEN** a value containing a zero-width joiner or a control character is pasted into a field and submitted
- **THEN** the request is rejected with a validation error naming that field, and nothing is stored

#### Scenario: Markdown body at the ceiling
- **WHEN** a description longer than 5000 characters is submitted
- **THEN** the request is rejected with a too-long error carrying the limit, and the organizer sees how far over the limit they are

### Requirement: Numeric fields accept both decimal separators
A numeric field SHALL accept a decimal comma and a decimal point as equivalent, and SHALL tolerate spaces and non-breaking spaces used as thousands grouping. A value carrying more than one decimal separator, a separator in an impossible position, or any other non-numeric character SHALL be rejected as malformed rather than silently truncated.

This rule SHALL hold on both layers: the browser control SHALL NOT discard a typed separator before the application sees it, and the API SHALL apply the same parsing to a value posted directly. A field declared as an integer SHALL reject a value carrying a fractional part rather than rounding it.

#### Scenario: Decimal comma in the exchange rate
- **WHEN** an organizer types `25,5` into the exchange rate field and saves
- **THEN** the stored rate is 25.5, and the field reads back `25,5` in a Czech UI

#### Scenario: Separator is never silently dropped
- **WHEN** an organizer types a decimal separator into any numeric field
- **THEN** the character stays visible in the control and the digits after it are part of the submitted value

#### Scenario: Thousands grouping
- **WHEN** a price is typed as `1 250` or `1 250` with a non-breaking space
- **THEN** it validates as 1250

#### Scenario: Malformed number
- **WHEN** a value such as `2,5,5` or `12a` is submitted for a numeric field
- **THEN** it is rejected with a not-a-number error and nothing is stored

#### Scenario: Fraction in an integer field
- **WHEN** `3,5` is submitted for a capacity field
- **THEN** it is rejected with a must-be-a-whole-number error rather than stored as 3 or 4

#### Scenario: Direct API caller uses a comma
- **WHEN** a client posts `"25,5"` for a decimal field
- **THEN** the API accepts it exactly as it accepts `"25.5"`

### Requirement: Money fields are bounded whole units
Every fee, price, discount amount and other money field SHALL be a non-negative whole unit of its currency, with an upper bound declared **per currency** — 10 000 CZK and 1 000 EUR. A value above the bound for the currency that field is denominated in SHALL be rejected with a message stating that maximum, so that a mistyped extra digit is caught before it can be quoted to a fencer or written into a payment instruction. A percentage field SHALL be bounded to 0–100.

The bound SHALL be resolved from the currency the field actually carries, not from the field's name: a local-currency field on a EUR-priced tournament SHALL be held to the EUR ceiling. Adding a currency SHALL mean adding a row to the ceiling table and nothing else.

#### Scenario: An extra zero
- **WHEN** an organizer types a discipline fee of 95000 Kč where 950 was meant
- **THEN** the field is rejected with a message stating 10 000 Kč as the maximum, and the section does not save

#### Scenario: The same figure in each currency
- **WHEN** 5000 is entered as a local-currency fee on a CZK tournament and as a EUR fee
- **THEN** the CZK value is accepted and the EUR value is rejected against the 1 000 EUR ceiling

#### Scenario: A EUR-priced tournament
- **WHEN** a fee above 1 000 is entered in the local-currency field of a tournament whose local currency is EUR
- **THEN** it is rejected against the EUR ceiling, not the CZK one

#### Scenario: Negative price
- **WHEN** a negative value is submitted for any money field
- **THEN** it is rejected with a must-not-be-negative error

#### Scenario: Percentage above 100
- **WHEN** a percentage discount or tolerance above 100 is submitted
- **THEN** it is rejected with a range error naming 0 and 100

### Requirement: URL fields are parsed and scheme-restricted
Every field holding a link SHALL be parsed as a URL and SHALL be accepted only with an `http` or `https` scheme. `javascript:`, `data:` and other schemes SHALL be rejected at validation, not filtered at render time. A value that does not parse as a URL SHALL be rejected with a malformed-link error.

#### Scenario: A script URL in a ruleset link
- **WHEN** a `javascript:` URL is submitted as a discipline's ruleset link
- **THEN** the request is rejected with a link-scheme error and the value is never stored

#### Scenario: A link without a scheme
- **WHEN** `example.com/rules` is submitted as a link
- **THEN** the organizer is told the link must begin with `http://` or `https://`

### Requirement: Validation errors carry machine codes
A rejected request SHALL answer with the field path, a stable `snake_case` code, and the parameters the message needs (such as the limit that was exceeded). The response SHALL carry every failing field, not only the first. Codes SHALL be shared with the client-side checks, so one code has exactly one message wherever the failure was caught.

Existing single-code rejections already returned as `detail` SHALL be expressible in the same shape, so a client has one error format to read.

#### Scenario: Two fields fail at once
- **WHEN** a save is submitted with an over-long name and a negative fee
- **THEN** the response lists both fields, each with its own code and parameters

#### Scenario: A limit is in the response
- **WHEN** a value exceeds a declared maximum
- **THEN** the response carries that maximum as a parameter, so the message can state it without the client hardcoding it

#### Scenario: Same failure, same message
- **WHEN** an over-long value is caught by the client and the identical value is posted directly to the API
- **THEN** both paths produce the same code, and therefore the same message text

### Requirement: Validation messages exist in every bundled locale
Every validation code SHALL have a message in every bundled locale, written as plain matter-of-fact text stating what is wrong and what is accepted, without exclamation marks. A code without a message in any bundled locale SHALL fail a catalog-parity test rather than falling back silently to another language.

Messages SHALL interpolate their parameters rather than embedding limits in the text, so a bound changes in one place.

#### Scenario: A code with no Czech message
- **WHEN** a validation code is added with an English message only
- **THEN** the locale parity test fails, naming the missing key

#### Scenario: Reading an error in Czech
- **WHEN** a Czech-language user exceeds a 200-character limit
- **THEN** the message under the field is Czech and states the 200-character limit

#### Scenario: Limit changed
- **WHEN** a declared maximum is changed in the constraint module
- **THEN** the displayed message states the new limit with no locale file edited

### Requirement: Validation timing and save blocking
A field SHALL be validated when it loses focus and again when a save is attempted. A field SHALL NOT be validated on every keystroke. A field showing an error SHALL clear that error as soon as its value becomes valid.

A save SHALL NOT be sent while any field in the saved section is invalid. The save control SHALL state that fields need attention and how many, and the first invalid field SHALL be reachable from that statement.

#### Scenario: Leaving a field with a bad value
- **WHEN** a user types an invalid value and moves focus away
- **THEN** the message appears under that field immediately, with no request sent

#### Scenario: Typing a value that is not finished yet
- **WHEN** a user has typed the first two characters of a value that is not yet valid
- **THEN** no error is shown while focus remains in the field

#### Scenario: Saving a section holding an invalid field
- **WHEN** a save is attempted while a field in that section is invalid
- **THEN** no request is sent, the save control states how many fields need attention, and every invalid field shows its message

#### Scenario: Correcting an error
- **WHEN** a user edits an invalid field until its value is acceptable
- **THEN** the message disappears without waiting for a save

#### Scenario: A rejection the client could not predict
- **WHEN** the backend rejects a value the client considered valid, such as an already-taken slug
- **THEN** the message is placed under the field the response names, in the same form as a client-caught error
