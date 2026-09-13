## ADDED Requirements

### Requirement: A registration's fencer is not fixed for its lifetime
A registration SHALL be capable of being moved from one fencer to another by a substitution (`fencer-substitution`), and SHALL be the same registration afterwards: the same id, the same variable symbol, the same registration moment, the same total, the same entries, the same journal and the same derived state.

Everything the lifecycle reads SHALL be unaffected. The reservation's expiry, its payment window, its reminders, its dormancy and its place in the seating settlement SHALL stand exactly as they stood, because none of them is a property of the person.

The uniqueness of one registration per fencer per tournament SHALL continue to hold. A substitution that would breach it SHALL be refused rather than accepted and repaired.

#### Scenario: The same registration, a different fencer
- **WHEN** a registration is moved to a substitute
- **THEN** its id, variable symbol, registration moment, total, entries and journal are unchanged, and it belongs to the substitute

#### Scenario: The lifecycle does not notice
- **WHEN** a reservation with a payment window still open is moved to a substitute and the lifecycle then runs
- **THEN** it is reminded and expires on exactly the schedule it had before

#### Scenario: One registration per fencer still holds
- **WHEN** a substitution would give a fencer a second registration on one tournament
- **THEN** it is refused

### Requirement: A registration may carry a contact address of its own
A registration SHALL be able to carry a **contact address** distinct from its fencer's account address. Where one is present, every message Squire sends about that registration SHALL go to it; where none is present, messages SHALL go to the fencer's own address as they do today.

It exists because a seat's address and a person's login are not the same thing: a club that entered three people under one address keeps that address when one of the three is replaced, and the address cannot be written onto the substitute's fencer record, which is a different person's and may have an address already.

A contact address SHALL NOT be credentials. It SHALL grant no access, and no account SHALL be created for it.

#### Scenario: Messages follow the contact address
- **WHEN** a registration carrying a contact address is reminded, receives a payment, or is amended
- **THEN** the message goes to the contact address and not to the fencer record's own

#### Scenario: Without one, nothing changes
- **WHEN** a registration carries no contact address
- **THEN** its messages go to its fencer's address exactly as before

#### Scenario: A contact address is not a login
- **WHEN** a registration carries a contact address belonging to no account
- **THEN** nobody can sign in with it and no account exists for it
