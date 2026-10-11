## ADDED Requirements

### Requirement: A cancelled issued registration keeps its row out
WHERE a registration issued for a fencer-list row is cancelled, by the organizer or by the
fencer, the row it was issued for SHALL NOT return to the fencer list as a row of its own,
and SHALL NOT be offered to issuing again. The registration stood in the row's place under
the row's own id; cancelling it is a decision about that person, and a row reappearing as
unissued would let the next intake pass recreate the person just cancelled. That is likely
for a fencer with no address, who is given a new record every time.

The row's number SHALL stay with it and SHALL NOT be reused.

#### Scenario: Cancelled on a manual tournament
- **WHEN** the organizer cancels a registration issued for imported row 17 and then runs intake again
- **THEN** row 17 is not listed as unissued and no registration is issued for it

#### Scenario: Re-imported later
- **WHEN** the organizer imports a new roster that names the same person again
- **THEN** the new row is a row of its own and travels through intake as any other row does
