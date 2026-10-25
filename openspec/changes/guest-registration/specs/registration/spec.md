## MODIFIED Requirements

### Requirement: In-app registration
An authenticated fencer, or a visitor registering without an account as `guest-registration` fixes, SHALL register for a tournament by selecting disciplines and any of the tournament's configured extra services, each with a quantity up to the item's per-registration limit and an option value where the item declares an option label, plus one non-billable field: a free-text note to the organizer. For legacy tournaments without configured extra services, the fixed weapon-rental and afterparty options SHALL remain accepted as before and SHALL be presented as rows in the same checklist. The system SHALL record the registration time, compute the total from the tournament's itemized pricing and discounts, and create a reservation with a unique VS. The confirmation email and exports SHALL list the selected items with their quantities and option values. Registration is exposed through the API and through the fencer-facing tournament detail page (fencer-home capability).

A guest registration and an account holder's registration of the same selection at the same moment SHALL be placed, priced, numbered and timed identically. They SHALL differ only in how the fencer behind them is identified and in the manage link that `guest-registration` adds to a guest's messages.

The registration API SHALL continue to accept and store the after-sparring flag and the accommodation note, because the table-import path still parses both from legacy sources; a registration created in-app SHALL simply carry neither, and their absence SHALL NOT change any total, export, or email.

#### Scenario: Successful registration
- **WHEN** a fencer submits a registration with two disciplines, weapon rental quantity 1, and "afterparty saturday"
- **THEN** a reservation is created with a unique VS and a total computed from the tournament's items and discounts
- **AND** a confirmation email itemizing the selection with payment instructions is sent

#### Scenario: A guest registers on the same terms
- **WHEN** a guest submits the same selection on the same tournament
- **THEN** a reservation is created with a unique VS, the same total and the same payment window, and the confirmation email itemizes the selection with payment instructions and carries the registration's manage link

#### Scenario: Quantity above the item limit
- **WHEN** a fencer submits an extra-service quantity above the item's per-registration limit
- **THEN** the registration is rejected with a validation error

#### Scenario: Note retained
- **WHEN** a fencer writes a note to the organizer and registers
- **THEN** it is stored on the registration, appears wherever the registration is presented to the organizer, and does not change the computed total

#### Scenario: In-app registration carries no after-sparring or accommodation
- **WHEN** a fencer completes the in-app form
- **THEN** the created registration has no after-sparring flag set and no accommodation note, and every total, export and email is exactly what it would have been with those fields empty

#### Scenario: Imported registration keeps both
- **WHEN** a registration is created through the table-import path from a source row declaring after-sparring and an accommodation note
- **THEN** both are stored on the registration as before

### Requirement: A registration may carry a contact address of its own
A registration SHALL be able to carry a **contact address** distinct from its fencer's account address. Where one is present, every message Squire sends about that registration SHALL go to it; where none is present, messages SHALL go to the fencer's own address as they do today.

It exists because a seat's address and a person's login are not the same thing: a club that entered three people under one address keeps that address when one of the three is replaced, and the address cannot be written onto the substitute's fencer record, which is a different person's and may have an address already. For the same reason, a guest entering several people from one address (`guest-registration`) writes it as the contact address of every registration after the first.

A contact address SHALL NOT be credentials. It SHALL grant no access of its own, and no account SHALL be created for it. A guest registration's manage link is sent to it like every other message about the registration. What that link grants is fixed by `guest-registration` and belongs to the link, not to the address.

#### Scenario: Messages follow the contact address
- **WHEN** a registration carrying a contact address is reminded, receives a payment, or is amended
- **THEN** the message goes to the contact address and not to the fencer record's own

#### Scenario: Without one, nothing changes
- **WHEN** a registration carries no contact address
- **THEN** its messages go to its fencer's address exactly as before

#### Scenario: A contact address is not a login
- **WHEN** a registration carries a contact address belonging to no account
- **THEN** nobody can sign in with it and no account exists for it

#### Scenario: A signup on a contact address takes nothing over
- **WHEN** somebody verifies a signup on an address that a guest registration carries only as its contact address
- **THEN** the registration stays with its own fencer record and remains managed through its link
