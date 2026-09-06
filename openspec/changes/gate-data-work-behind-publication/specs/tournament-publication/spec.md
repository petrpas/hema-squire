## MODIFIED Requirements

### Requirement: A tournament is a draft until it is published
Every tournament SHALL carry a publication record: the moment it was published and the
account that published it, both empty until publication. A tournament with an empty
publication record is a draft. Completing mandatory setup SHALL NOT publish a
tournament, and no tournament SHALL become published by any means other than the
publish action.

A draft SHALL be invisible to fencers — absent from every fencer-facing list — and
SHALL reject new registrations with the not-yet-published reason, regardless of how
complete its setup is or where the current date falls in its registration window. Its
console and its detail record SHALL remain reachable to its organizers.

**Reachable means readable, not operable.** A draft SHALL hold no participants and no
money. Every operation that writes the tournament's data SHALL be refused while it is
unpublished, with a stated reason naming publication: importing a roster and
interpreting it, matching against HEMA Ratings, deduplication and its verdicts,
issuing registrations, entering a fencer by hand, the manual edits kept as rules, every
part of the payments surface — statement import, the bank poll, matching, links,
recorded payments, the settled mark — and settling seating. Exporting SHALL be refused
with them, alone among the reads, because its product leaves the console.

A draft's clocks SHALL NOT run. No lifecycle pass SHALL select an unpublished
tournament (`registration`).

Reading SHALL be untouched: the console's tables, the tournament's detail record, the
manual-edits log and the records of past operations stay available to its organizers.
They will hold nothing, which is the consequence of the rule rather than a gap in it.

Configuration SHALL be untouched. A draft is a tournament being written, and its
place, disciplines, prices, mode, payments setting, features and organizers stay
freely editable, including into incompleteness, as fixed below.

#### Scenario: Newly created tournament is a draft
- **WHEN** an organizer creates a tournament
- **THEN** its publication record is empty, it appears in no fencer-facing list, and a registration attempt is rejected with the not-yet-published reason

#### Scenario: Completing setup does not publish
- **WHEN** the organizer fills the last mandatory setup item of a draft and saves it
- **THEN** the tournament is still a draft, still absent from the fencer-facing lists, and still rejects registration with the not-yet-published reason

#### Scenario: Draft console stays reachable
- **WHEN** an organizer opens the console of a draft tournament
- **THEN** the console and the tournament's detail record are served as for any other tournament

#### Scenario: A draft refuses an import
- **WHEN** an organizer uploads a roster to a draft
- **THEN** it is refused with a reason naming publication, and the tournament holds no imported row

#### Scenario: A draft refuses money
- **WHEN** an organizer uploads a bank statement to a draft, or records a payment by hand against it
- **THEN** each is refused with a reason naming publication, and the tournament holds no transaction and no recorded payment

#### Scenario: A draft refuses an export
- **WHEN** an organizer exports a draft to a worksheet
- **THEN** it is refused with a reason naming publication, and no worksheet is produced

#### Scenario: Setup still saves on a draft
- **WHEN** the organizer of a draft changes its prices, adds a discipline and turns a feature on
- **THEN** every one of those is saved, as on any draft today

#### Scenario: Publication opens the data work
- **WHEN** a draft that refused an import is published and the roster uploaded again
- **THEN** the import runs
