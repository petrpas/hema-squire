## MODIFIED Requirements

### Requirement: A count states who is shown above the line
Wherever a public screen states a discipline's count beside its capacity — the
information screen, the list card, the registration form — the count SHALL be the
entrants its roster lists above the line: live seated placements, or teams in a team
discipline, less the registrations whose row the organizer has taken out of the table by
deleting it or merging it into another. 28/32 then means twenty-eight entrants listed and
places still to be had, and a reader counting the roster arrives at the same number.

This governs what the count states and nothing else. A live registration's row can no
longer be deleted (`etl-console`, Reversible row deletion); a person is cancelled instead,
which frees the seat. A row deleted while holding a live registration before that rule
stood SHALL keep its seat until the organizer restores it and cancels the registration:
placement, the free places that decide whether a new entry is seated or queued, and the
queue SHALL count it as before. For such a row the count MAY show a place free while a new
entry is queued.

#### Scenario: A removed row is not counted
- **WHEN** a discipline of capacity 32 holds 30 live seated registrations and the organizer has deleted the rows of two of them
- **THEN** the information screen and the list card state 28/32, and the roster lists 28

#### Scenario: Restoring counts it again
- **WHEN** the organizer restores one of those rows
- **THEN** the count reads 29/32

#### Scenario: The seat is not released
- **WHEN** the same discipline is asked how many places are free
- **THEN** the two removed registrations still hold their seats
