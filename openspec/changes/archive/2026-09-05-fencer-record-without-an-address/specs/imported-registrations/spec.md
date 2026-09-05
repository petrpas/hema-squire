## ADDED Requirements

### Requirement: What a row must have to be issued
A fencer-list row SHALL be issued a registration where it states a name and at
least one discipline. It SHALL NOT be refused for anything else about its
contents.

A row SHALL NOT be required to carry an e-mail address, and SHALL NOT be refused
because another row carries the same one. Neither is a defect in the row: a
roster is routinely entered by one person for several — a parent, a club
representative — and the address is that person's. The fencer record such a row
needs is created on the tournament's behalf, holds no credentials and is never
written to (`fencer-accounts`), so it needs no address of its own.

The reasons a row can be skipped SHALL therefore describe the row rather than
the system's bookkeeping: no name, because there is no fencer to make; and no
discipline, because the registration would total zero, read as settled, and
quietly absorb a payment.

Every reason a row was skipped SHALL be reported, named, wherever the skipped
rows are stated — the enrolment's own report and the surfaces that ask what the
next enrolment would leave alone.

#### Scenario: Two rows on one address are both issued
- **WHEN** registrations are issued for a list in which a parent's address appears on two fencers' rows
- **THEN** both rows are issued registrations, and neither is reported as skipped

#### Scenario: A row carrying no address is issued
- **WHEN** a row states a name and a discipline but no e-mail address
- **THEN** it is issued a registration

#### Scenario: A row with no discipline is still refused
- **WHEN** the list holds a row that entered no discipline
- **THEN** no registration is issued for it, and it is reported as skipped with that reason

#### Scenario: A row with no name is still refused
- **WHEN** the list holds a row that states no name
- **THEN** no registration is issued for it, and it is reported as skipped with that reason
