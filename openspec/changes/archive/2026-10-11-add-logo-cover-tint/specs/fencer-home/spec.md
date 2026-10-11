## ADDED Requirements

### Requirement: A card's cover tint follows its logo
Where a listed tournament's logo has a hue band, its card's cover SHALL wear the pastel tint of that band: `blue` the file-blue tint, `green` the seal-green tint, `warm` the form-yellow tint. Where the tournament has no logo, or its logo has no band, the cover SHALL wear the tint chosen from the slug, as before. No color taken from the logo itself SHALL be rendered: the band only chooses among the three tint tokens.

#### Scenario: Green logo, green cover
- **WHEN** a tournament whose logo band is `green` is listed
- **THEN** its cover wears the seal-green tint, whatever its slug would choose

#### Scenario: Achromatic logo
- **WHEN** a tournament's logo has no band
- **THEN** its cover wears the tint its slug chooses, the same on every render

#### Scenario: Logo replaced
- **WHEN** the organizer replaces a blue logo with a red one
- **THEN** the card's cover changes from the file-blue tint to the form-yellow tint
