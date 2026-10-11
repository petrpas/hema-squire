## ADDED Requirements

### Requirement: A card names familiar faces to a signed-in visitor
Where a list entry carries `familiar`, the card's footer SHALL show at its left up to three round 28px faces bearing the people's initials, overlapping by 8px, each on a pastel tint chosen by its position and separated from its neighbour by a 2px `--paper-raised` ring, followed by a 13px `--ink-soft` note: `{total} z tvého klubu` / `{total} from your club` for basis club, for basis country `nejvýš hodnocení z {country}` / `top-rated from {country}` where the people are ordered by rating, and `{total} z {country}` / `{total} from {country}` where they are ordered by name — the note never claims a ranking the order does not follow. Each face SHALL carry its label as its accessible name and title. Where `familiar` is absent the footer's left side SHALL be empty and the counts at its right unchanged.

#### Scenario: Three clubmates
- **WHEN** a signed-in fencer's list entry carries three people from their club with a total of five
- **THEN** the footer shows three faces and reads `5 z tvého klubu`

#### Scenario: Compatriots without a rating snapshot
- **WHEN** the entry's familiar people are from the visitor's country and the tournament has no rating snapshot
- **THEN** the note reads `4 z CZ`, not a top-rated claim

#### Scenario: Anonymous visitor
- **WHEN** a visitor with no account reads the same card
- **THEN** the footer shows only the fencer and club counts

#### Scenario: A face names its person
- **WHEN** a screen reader reaches a face
- **THEN** it announces the person's label, such as `Kateřina V.`
