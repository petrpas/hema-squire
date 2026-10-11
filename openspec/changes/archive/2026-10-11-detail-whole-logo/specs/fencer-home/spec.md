## MODIFIED Requirements

### Requirement: Tournament detail opens on its cover
The detail's information block SHALL open with the same cover its card wears: a band in the tint the card would choose (`A card's cover tint follows its logo`), the plate at its centre — the whole logo on `--plate`, the plate taking the logo's own proportions at a fixed height so nothing of it is cut away, or the short code or monogram on a square plate — ringed in `--stamp` while registration is open and in `--hairline-strong` otherwise, and at its top left the status block stating registration's state as the card states it — none where the organizer keeps the registrations, as on the card. The status is the one the page itself computes against the server's clock, so the block changes in place when registration opens. The title, subtitle and facts follow beneath the cover. On a phone, where the plate and the status block do not fit side by side, the status block stands beneath the plate within the cover. The card on the list keeps its square plate, the logo cropped to fill it.

#### Scenario: An open tournament with a logo
- **WHEN** the detail of a tournament whose registration is open and whose logo is green is opened
- **THEN** it opens on a seal-green band with the logo filling a plate ringed in `--stamp`, and the status block reads `registrace` / `otevřena` / `do {date}`

#### Scenario: Registration opens while the page is open
- **WHEN** the opening moment passes with the detail open
- **THEN** the status block reads open and the plate's ring turns `--stamp`, without a reload

#### Scenario: An organizer-kept tournament's detail
- **WHEN** the detail of a tournament whose registrations its organizer keeps is opened
- **THEN** its cover carries no status block, and the way out to the organizer's registration stands where the form would be

#### Scenario: A wide logo on the detail
- **WHEN** the detail of a tournament whose logo is three times as wide as it is tall is opened
- **THEN** the whole logo is shown on a plate of the same proportions, and its card on the list shows it cropped to a square
