## ADDED Requirements

### Requirement: The not-found screen wears the night skin
The not-found screen SHALL render in the night skin (`design-system`, Skins), whichever URL led to it — a public one, an unknown slug, or a console URL the account may not open — so that it reads the same in every case and discloses nothing by its appearance about which kind of address it was.

#### Scenario: Unknown public address
- **WHEN** a visitor opens `/nonsense`
- **THEN** the not-found screen renders night

#### Scenario: Refused console address
- **WHEN** an organizer opens a console URL for a tournament they have no access to
- **THEN** the not-found screen renders night, identical in appearance to the unknown-slug case
