## MODIFIED Requirements

### Requirement: Every edit field has a declared constraint
Every field a user can type into SHALL have a declared data type and accepted value set: strings a maximum length (and a minimum where an empty value is meaningless), integers a minimum and a maximum, decimals a minimum, a maximum and a fixed number of decimal places, enumerations their permitted values, and patterned fields their pattern. No editable field SHALL remain unbounded.

The declarations SHALL live in one authoritative backend module. Every pydantic `Field(...)` bound SHALL be read from that module rather than written inline, and the frontend SHALL read the same bounds from a checked-in TypeScript mirror. The mirror SHALL NOT be trusted to stay correct by discipline: a test SHALL compare it against the constraints the backend actually publishes in its OpenAPI schema and SHALL fail when any bound differs or is missing on either side.

A field MAY additionally be subject to a check that no declaration can express — a checksum, a uniqueness rule, a relationship to another field's value. Such a check SHALL live in the backend alone and SHALL NOT be mirrored, because the mirror compares declared literals and can prove nothing about two implementations of an algorithm. The declared constraint SHALL still cover the field's shape, so that a value which is not plausibly of the right kind is caught as the user types; the backend check SHALL then decide validity on save, and its rejection SHALL reach the field it concerns like any other backend rejection. A field whose only meaningful validation is such a check SHALL NOT be left with no declared constraint on that account.

#### Scenario: A bound is changed on one side only
- **WHEN** a maximum length is changed in the backend constraint module and the TypeScript mirror is not updated
- **THEN** the mirror test fails, naming the field and both values

#### Scenario: A new editable field is added without a bound
- **WHEN** a new editable string, integer or decimal field is added to a request schema with no declared constraint
- **THEN** the mirror test fails, naming the field as unconstrained

#### Scenario: The frontend limits input to the declared length
- **WHEN** a user types into a field whose declared maximum length is 200
- **THEN** the control refuses characters past 200 and the value that reaches the backend can never exceed the declared maximum

#### Scenario: Shape is declared where validity is a checksum
- **WHEN** a field's validity depends on a checksum the declaration cannot express
- **THEN** the declared pattern still describes its shape, a value of the wrong shape is caught as the user types, and the checksum decides the value on save

#### Scenario: A checksum is not mirrored
- **WHEN** a backend checksum check is added for a field
- **THEN** no equivalent is written into the TypeScript mirror, and the mirror test neither requires nor compares one
