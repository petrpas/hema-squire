## ADDED Requirements

### Requirement: Exporting waits for publication
Every export SHALL be refused on an unpublished tournament, with a stated reason naming
publication. This covers the worksheet export and the canonical JSON document alike.

The export reads and writes nothing, so the rule that gates the console's data work
does not reach it on its own terms. It is gated because it is the one read whose
product leaves the console: a worksheet goes to the check-in desk, the referees and the
scorekeepers, and a canonical document is a tournament's whole state handed to
somebody. From a tournament nobody can enter, holding nobody, such a document states a
roster of nobody to a reader with no way to know that.

A draft has nothing to export in any case — it can hold no participant
(`tournament-publication`) — so what the refusal prevents is not a wrong answer but a
confident empty one.

#### Scenario: A draft is not exported to a worksheet
- **WHEN** an organizer exports a draft to Sheets
- **THEN** the export is refused with a reason naming publication, and no worksheet is created

#### Scenario: A draft produces no canonical document
- **WHEN** an organizer asks a draft for its canonical JSON document
- **THEN** it is refused with a reason naming publication

#### Scenario: Publication opens the export
- **WHEN** the tournament is published and the export asked for again
- **THEN** it runs as it does for any published tournament
