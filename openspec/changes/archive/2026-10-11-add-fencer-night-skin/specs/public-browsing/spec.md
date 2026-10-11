## ADDED Requirements

### Requirement: A list entry states its public aggregates
Each entry of the tournament list SHALL carry three facts that do not depend on the caller, present alike for an anonymous and an authenticated request:

- `registration_closes_on`: the last day registration is open, resolved as the detail page resolves it (the set closing date, else the tournament's date), and absent where the tournament keeps no window here.
- `entrant_count`: the number of distinct seated fencers across the tournament's disciplines. A fencer seated in two disciplines SHALL count once; a fencer only queued, a cancelled registration, and an entry the organizer took off the public table SHALL NOT count.
- `club_count`: the number of distinct clubs among those fencers, clubs compared after normalization (case and diacritics folded, whitespace collapsed and trimmed), an empty club counting as none.

These are aggregates of what the public rosters already state, and disclose nothing they do not. The list SHALL compute them for all its entries together, not with a query per entry.

#### Scenario: A fencer in two disciplines
- **WHEN** a tournament has one fencer seated in both its longsword and its sabre discipline, and two others seated in one each
- **THEN** its entry states three fencers

#### Scenario: Clubs compared loosely
- **WHEN** the three fencers name their clubs `Šermířský klub Brno`, `sermirsky klub brno ` and an empty club
- **THEN** the entry states one club

#### Scenario: The queue does not count
- **WHEN** a discipline is full with two fencers waiting
- **THEN** the waiting fencers are not in the entry's fencer count

#### Scenario: Aggregates are not personal
- **WHEN** an anonymous visitor and a registered fencer read the same tournament's entry
- **THEN** the closing date, the fencer count and the club count are identical

#### Scenario: Closing date matches the detail
- **WHEN** a tournament with no explicit closing date is listed
- **THEN** its entry's closing date is the tournament's date, the same day its detail states
