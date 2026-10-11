## ADDED Requirements

### Requirement: A signed-in caller is shown familiar entrants
A list entry answered for a signed-in caller SHALL carry `familiar` when the selection below finds anyone, and SHALL omit it otherwise. It SHALL be absent from every entry of a payload answered without a credential, for the same reason the other bond fields are (`An anonymous payload carries no bond`).

The selection is made per tournament, among its seated entrants — not queued, not cancelled, not taken off the public table — excluding the caller:

1. **Club.** The caller's club is the club of the hemaratings profile bound to the account, falling back to the account's own club where no profile is bound or the profile names none. Entrants whose club equals it after normalization (case and diacritics folded, whitespace collapsed and trimmed) match. `basis` is `club`.
2. **Country**, only when step 1 matched nobody: entrants whose nationality names the same country as the caller's, both read as ISO 3166 alpha-2 codes whatever vocabulary they were written in, the caller's taken from the bound profile and falling back to the account's own. `country` carries that code. `basis` is `country`. A caller with no nationality stops here.
3. Nobody matched: `familiar` is absent.

Matches SHALL be ordered by their hemaratings rating in the tournament's disciplines, highest first, where the tournament's latest rating snapshot holds one, then by name. At most three are returned as `people`, each with `initials` (first letter of the first name and of the surname) and `label` (first name and surname initial, `Kateřina V.`); `total` states how many matched in all, and `ranked` whether the order is by rating — true only where the tournament has a rating snapshot.

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
