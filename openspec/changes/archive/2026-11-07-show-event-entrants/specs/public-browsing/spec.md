## MODIFIED Requirements

### Requirement: A list entry states its public aggregates
Each entry of the tournament list SHALL carry three facts that do not depend on the caller, present alike for an anonymous and an authenticated request:

- `registration_closes_on`: the last day registration is open, resolved as the detail page resolves it (the set closing date, else the tournament's date), and absent where the tournament keeps no window here.
- `entrant_count`: the number of distinct seated fencers across the tournament's disciplines. A fencer seated in two disciplines SHALL count once; a fencer only queued, a cancelled registration, and an entry the organizer took off the public table SHALL NOT count.
- `club_count`: the number of distinct clubs among those fencers, clubs compared after normalization (case and diacritics folded, whitespace collapsed and trimmed), an empty club counting as none.

On an event (`discipline-less-events`), which has no discipline to be seated in, the fencers counted SHALL instead be those listed on its side-event rosters (`public-entrants`, Side events have rosters, the afterparty does not): live registrations holding a place at a seminar or other program item, whose row the organizer has not taken off the public table. A fencer holding places at two such items SHALL count once. Registrations holding only an afterparty or goods SHALL NOT count. A tournament's figures SHALL NOT include side-event attendees.

An event's entry SHALL also carry `program_meters`: one meter for each seminar or other program item the event offers that has a capacity, in the order the items were offered, each stating the item's name, the number of fencers its roster lists, and its capacity. An uncapped item SHALL have no meter. A tournament's entry SHALL carry `program_meters` empty.

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

#### Scenario: An event counts its program
- **WHEN** an event holds three live registrations, two for its seminar and one for the afterparty alone
- **THEN** its entry states two fencers

#### Scenario: A fencer at two program items
- **WHEN** one fencer holds a place at both an event's seminar and its castle tour
- **THEN** they count once

#### Scenario: A tournament ignores its seminar
- **WHEN** a tournament has two fencers seated in its discipline and a third registered for its seminar alone
- **THEN** its entry states two fencers and carries no program meter

#### Scenario: Event meters
- **WHEN** an event offers a seminar of capacity 20 holding 12, an uncapped workshop, and an afterparty of capacity 50
- **THEN** its entry carries one program meter, the seminar's, stating 12 of 20

#### Scenario: Aggregates are not personal
- **WHEN** an anonymous visitor and a registered fencer read the same tournament's entry
- **THEN** the closing date, the fencer count, the club count and the program meters are identical

#### Scenario: Closing date matches the detail
- **WHEN** a tournament with no explicit closing date is listed
- **THEN** its entry's closing date is the tournament's date, the same day its detail states

### Requirement: A signed-in caller is shown familiar entrants
A list entry answered for a signed-in caller SHALL carry `familiar` when the selection below finds anyone, and SHALL omit it otherwise. It SHALL be absent from every entry of a payload answered without a credential, for the same reason the other bond fields are (`An anonymous payload carries no bond`).

The selection is made per tournament, among its seated entrants — not queued, not cancelled, not taken off the public table — excluding the caller. On an event, the entrants selected among SHALL be the same fencers its `entrant_count` counts (`A list entry states its public aggregates`):

1. **Club.** The caller's club is the club of the hemaratings profile bound to the account, falling back to the account's own club where no profile is bound or the profile names none. Entrants whose club equals it after normalization (case and diacritics folded, whitespace collapsed and trimmed) match. `basis` is `club`.
2. **Country**, only when step 1 matched nobody: entrants whose nationality names the same country as the caller's, both read as ISO 3166 alpha-2 codes whatever vocabulary they were written in, the caller's taken from the bound profile and falling back to the account's own. `country` carries that code. `basis` is `country`. A caller with no nationality stops here.
3. Nobody matched: `familiar` is absent.

Matches SHALL be ordered by their hemaratings rating in the tournament's disciplines, highest first, where the tournament's latest rating snapshot holds one, then by name. At most three are returned as `people`, each with `initials` (first letter of the first name and of the surname) and `label` (first name and surname initial, `Kateřina V.`); `total` states how many matched in all, and `ranked` whether the order is by rating — true only where the tournament has a rating snapshot and at least one individual discipline. An event has no discipline to be rated in, so its matches SHALL be ordered by name and `ranked` SHALL be false, whatever snapshot it kept from a time it had one.

The selection SHALL be computed for all entries of a response together, not with queries per entry. It exposes nothing the public rosters do not already state.

#### Scenario: Club beats country
- **WHEN** a signed-in fencer from `Šermířský klub Brno` reads a tournament where two clubmates and five compatriots are seated
- **THEN** the entry's `familiar` has basis `club`, total 2 and two people

#### Scenario: Country fallback
- **WHEN** no clubmate is seated but four fencers of the caller's nationality are
- **THEN** `familiar` has basis `country`, total 4 and the three highest-rated of them

#### Scenario: The caller is not their own acquaintance
- **WHEN** the caller is seated in the tournament themselves
- **THEN** they are not among the people and not in the total

#### Scenario: Queued entrants excluded
- **WHEN** a clubmate is only in the queue
- **THEN** they are not among the people

#### Scenario: No nationality, no country step
- **WHEN** no clubmate is seated and the caller has no nationality
- **THEN** `familiar` is absent

#### Scenario: Anonymous caller
- **WHEN** the list is answered without a credential
- **THEN** no entry carries `familiar`

#### Scenario: Clubs written differently
- **WHEN** the caller's club is `Šermířský klub Brno` and an entrant wrote `sermirsky  KLUB brno`
- **THEN** the entrant matches

#### Scenario: Clubmates at an event's seminar
- **WHEN** a signed-in fencer reads an event whose seminar lists two of their clubmates and whose afterparty alone is taken by a third
- **THEN** the entry's `familiar` has basis `club`, total 2, and `ranked` false
