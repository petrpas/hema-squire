## MODIFIED Requirements

### Requirement: Setup fields that recall prior values
The Setup screen SHALL offer previously used values on the titular organizer entry
(ORGANIZERS), the tournament city and the tournament address (IDENTITY), the
tournament bank account and the account holder. Choosing a recalled bank account SHALL
also fill the account holder recorded with it on the tournament it came from, when the
holder field is empty; it SHALL NOT overwrite a holder already typed. The city and the address SHALL recall independently of
each other: an organizer who holds the same event in a different town is offered
each town on one field and each venue on the other, neither dragging the other
along. No other Setup field carries the affordance. A field with nothing to recall SHALL
behave exactly as a plain field: no empty list, no placeholder entry, and no
indication that the feature exists.

#### Scenario: Organizer's second tournament
- **WHEN** an organizer who has already run one tournament begins typing in the city field of a new one
- **THEN** the city they held that earlier tournament in is offered

#### Scenario: The venue is recalled on its own field
- **WHEN** that organizer begins typing in the address field
- **THEN** the address of the earlier tournament is offered there, and the city field offers only cities

#### Scenario: A field outside the five
- **WHEN** the organizer types in the tournament's subtitle, description or any other Setup field
- **THEN** nothing is offered, and the field behaves as it did before this capability existed

#### Scenario: The very first tournament
- **WHEN** an organizer with no earlier tournaments opens Setup and types in any of the five fields
- **THEN** no list appears and the field shows no sign that suggestions exist

#### Scenario: A recalled account brings its holder
- **WHEN** an organizer picks a bank account recalled from an earlier tournament and the holder field is empty
- **THEN** the holder recorded on that tournament is filled in, and it is offered on the holder field as well
