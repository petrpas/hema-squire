## ADDED Requirements

### Requirement: The plate prefers the organizer's short code
Where a tournament has no logo and its organizer has set a short code, the card's plate SHALL show that short code instead of the monogram derived from the name. A tournament with a logo SHALL show its logo whether or not a short code is set.

#### Scenario: Short code set, no logo
- **WHEN** a tournament named `Pražský dlouhý meč 2027` with short code `PDM` and no logo is listed
- **THEN** its plate reads `PDM`

#### Scenario: Short code set, logo set
- **WHEN** the same tournament gains a logo
- **THEN** its plate shows the logo
