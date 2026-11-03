## ADDED Requirements

### Requirement: An event's card meters its program
A card for an event (`discipline-less-events`) SHALL show, where a tournament's card shows its discipline rows, one row per meter the entry's `program_meters` carries (`public-browsing`): the item's name at the left and its figure at the right over a capacity meter, drawn and stated exactly as a discipline's (`design-system`, A capacity meter is a static figure), with `plno` / `full` in place of the fraction once the figure reaches the capacity. An item keeps no queue, so no waiting count SHALL be stated. An item's name SHALL wrap as a discipline's does.

An event with no program meter SHALL show no meter rows. Its foot SHALL state the fencer and club counts its entry carries, as a tournament's foot does. A tournament's card SHALL show its discipline meters only, and no meter for any of its items.

#### Scenario: A seminar filling up
- **WHEN** the list shows an event whose seminar of capacity 20 holds 12
- **THEN** its card has one meter row reading the seminar's name and `12/20`

#### Scenario: A full seminar
- **WHEN** the event's seminar of capacity 20 holds 20
- **THEN** its meter is filled in `--stamp` and reads `plno`, with no waiting count

#### Scenario: Uncapped program and the afterparty
- **WHEN** an event offers an uncapped workshop and an afterparty of capacity 50, and 14 fencers hold a place at the workshop
- **THEN** its card shows no meter row and its foot states 14 fencers

#### Scenario: A tournament's seminar has no meter
- **WHEN** a tournament with one discipline also offers a seminar of capacity 20
- **THEN** its card shows the discipline's meter alone
