## ADDED Requirements

### Requirement: An extra item may carry a capacity
Any extra item, in any category, SHALL carry an optional capacity, a whole number of at least one, edited in Setup with the item. An empty capacity SHALL mean unlimited. Pieces SHALL be counted: a selection's whole quantity is taken. Capacity SHALL be consumed by every live registration holding the item, as `registration` defines live for disciplines, including a registration waiting in a discipline queue and one with no payment yet. A cancelled or expired registration SHALL give its pieces back at once.

Setup SHALL show an item's taken count against its capacity. Lowering a capacity below the taken count SHALL be accepted and SHALL take nothing from any registration.

#### Scenario: Every category
- **WHEN** the organizer sets a capacity on a seminar, an `other_action` item and a merch item
- **THEN** each is limited on the same terms

#### Scenario: Empty means unlimited
- **WHEN** an item has no capacity
- **THEN** its selection is never refused for capacity

#### Scenario: Pieces are counted
- **WHEN** a fencer selects two of an item with capacity 5 that has 1 taken
- **THEN** 3 are taken and 2 stay free

#### Scenario: A queued fencer holds their item
- **WHEN** a fencer waiting wholly in a discipline queue holds the last seminar place and owes nothing yet
- **THEN** the seminar is full for everybody else, and admission leaves the seminar held

#### Scenario: Expiry frees a place
- **WHEN** a reservation holding a place on a full item expires
- **THEN** the item has a free place for the next submission

#### Scenario: Capacity lowered below taken
- **WHEN** the organizer lowers a capacity from 20 to 10 with 15 taken
- **THEN** all 15 registrations keep the item, and it reads full

### Requirement: A full item is sold out
A full item SHALL NOT be selectable and SHALL have no queue. The form SHALL state the free places of every capped item and SHALL present a full one as sold out. A submission wanting more pieces than are free SHALL be refused whole, naming the items, and nothing SHALL be written. The last piece SHALL be taken under a lock, so concurrent submissions cannot together exceed the capacity. A freed place SHALL go to whoever submits next, and nobody SHALL be notified of it.

The `Register` tab of an event whose every item is full SHALL NOT be offered. A full item SHALL NOT affect the offer of a tournament that has open disciplines.

#### Scenario: Free places stated
- **WHEN** a fencer opens the form with a seminar holding 3 of 20 free
- **THEN** the row states 3 of 20 free

#### Scenario: Sold out on the form
- **WHEN** a seminar has no free place
- **THEN** its row is marked sold out and cannot be selected

#### Scenario: Two fencers want the last place
- **WHEN** two submissions for the last place arrive together
- **THEN** one succeeds and the other is refused naming the item, with no registration created

#### Scenario: Quantity above what is left
- **WHEN** a fencer asks for 3 of an item with 2 free
- **THEN** the submission is refused

#### Scenario: A sold-out event
- **WHEN** every item of an event is full
- **THEN** no `Register` tab is offered

### Requirement: What a fencer holds survives a full item
An amendment SHALL need free places only for an increase over the quantity already held. Keeping a held item SHALL always be accepted, also where the item is full or its capacity was lowered below the taken count. Removing an item SHALL free its pieces at once. A late payment SHALL reinstate an expired registration only if each of its capped items has room for it, as well as each of its seats; otherwise it SHALL be handled as a reinstatement blocked by a taken seat is. Substituting a registration's fencer SHALL leave the taken count unchanged.

#### Scenario: Amending beside a held item
- **WHEN** a fencer holding the last place on a full seminar amends another part of the registration
- **THEN** the amendment is accepted and the place is kept

#### Scenario: Raising a held quantity
- **WHEN** a fencer holding one of a full item asks for two
- **THEN** the amendment is refused and they keep one

#### Scenario: Reinstatement into a full item
- **WHEN** a late payment arrives for an expired registration whose seminar has filled since
- **THEN** it is not reinstated and is routed to the organizer as a taken seat would be

### Requirement: The organizer's own entry is not refused
Hand entry and issuing of imported rows SHALL NOT be refused by a full item, since they record what the organizer already agreed. They SHALL count against the capacity and MAY exceed it.

#### Scenario: Hand entry past the limit
- **WHEN** the organizer hand-enters a fencer with a rental that is full
- **THEN** the registration is created and the taken count exceeds the capacity

### Requirement: Capacity round-trips through the export
The JSON export SHALL carry an item's capacity, and the document version SHALL be raised. A document from before it SHALL load with every item unlimited.

#### Scenario: Round trip
- **WHEN** a tournament with a capped item is exported and restored
- **THEN** the item has the same capacity

#### Scenario: Older document
- **WHEN** a document of the previous version is restored
- **THEN** its items are unlimited
