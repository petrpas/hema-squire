## ADDED Requirements

### Requirement: The document carries the tournament's settings
The canonical document SHALL carry every setting that decides what Squire does
with the tournament or how it presents it, so that a restore reconstructs the
same tournament and not one that behaves differently: its mode (who keeps its
registrations), its payment mode and deposit in each currency, its seating
deadline and the moment seating settled, its amendments deadline, its expiry
grace, its external registration address, each of its features, its subtitle,
short code and cover and logo tints, and its HEMA Ratings category map.

Each registration SHALL carry whether its lifecycle clocks are dormant, the
fencer-list row it was issued from, and its own contact address. A source row
naming a manual row SHALL be rewritten to the restored manual row, as a rule
target is; one naming an imported row SHALL carry over as it stands.

The document SHALL NOT carry the logo or the cover photo; a restored tournament
has neither until the organizer uploads them. Nor SHALL it carry what belongs to
the deployment rather than the tournament: the owner, the publication moment and
author, the cancellation moment, the bank feed token, the export destination,
the retention stamp, and the generation of guest links. A guest's link from the
original therefore does not open the restored registration, and the organizer
sends it again.

The document version SHALL be raised for this addition. A document produced
before it states no mode, and SHALL restore as a tournament whose registrations
the organizer keeps: Squire then runs no lifecycle against it and sends no
lifecycle mail, and it cannot be published until it is given an external
registration address, so nobody publishes it without deciding its mode. Every
other setting such a document lacks SHALL take the value a new tournament takes.

#### Scenario: A manual tournament round-trips as manual
- **WHEN** a published manual tournament holding registrations issued from an imported fencer list is exported and restored
- **THEN** the restored draft is manual, carries the same external registration address, and every issued registration is dormant and stands in for its row under that row's id

#### Scenario: Payment settings round-trip
- **WHEN** a tournament in deposit mode, with a deposit in both currencies, a seating deadline, an amendments deadline, payments and teams on, is exported and restored
- **THEN** the restored tournament has the same payment mode, deposits, deadlines and features

#### Scenario: A settled seating stays settled
- **WHEN** a tournament whose seating already settled is exported and restored
- **THEN** the restored tournament records the same settlement moment, and no later pass settles it again

#### Scenario: Images stay behind
- **WHEN** a tournament with a logo and a cover photo is exported and restored
- **THEN** the restored tournament has the same tints, subtitle and short code and has no logo and no cover photo

#### Scenario: A guest's address comes back
- **WHEN** a registration entered as a guest, with a contact address of its own, is exported and restored
- **THEN** the restored registration carries that contact address, and its old management link does not open it

#### Scenario: An older document restores as manual
- **WHEN** a document of version 23 or earlier is restored
- **THEN** the restored tournament is manual, no reminder, expiry or demotion is ever run against its registrations, and publishing it is refused until an external registration address is set

#### Scenario: A copy restores beside its original
- **WHEN** a tournament with registrations issued from an imported fencer list is exported and restored on the same deployment under another slug
- **THEN** the restore succeeds and each tournament keeps its own registrations standing in for its own rows
