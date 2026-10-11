## ADDED Requirements

### Requirement: The public detail carries the caller's manage bond
The public tournament detail answered for a signed-in caller SHALL carry `organized`: whether the caller may manage the tournament, as its owner or a console team member. It SHALL be absent from a detail answered without a credential, as the list's bond fields are (`An anonymous payload carries no bond`).

#### Scenario: Owner reads the detail
- **WHEN** the owner requests their published tournament's public detail
- **THEN** it carries `organized: true`

#### Scenario: Anonymous reads the detail
- **WHEN** the same detail is requested without a credential
- **THEN** it carries no `organized` field
