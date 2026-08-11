## MODIFIED Requirements

### Requirement: In-app payment instructions retrieval
The system SHALL provide, to the owning account only, the payment data for its unpaid reservation: total amount with its currency, bank account (IBAN), variable symbol, payment message, reservation expiry, and the SPAYD QR code — plus the EUR total and a EUR-denominated QR code when the tournament prices in EUR as a second currency. Every amount SHALL be a stored total and every QR code SHALL encode the stored total of its own currency. The content SHALL be identical to the confirmation email's. The EUR fields SHALL be absent, not empty, when they do not apply.

Whether anything is owed SHALL be decided in one place, by the system that holds the registration, and SHALL NOT be decided a second time by the surface that displays the answer. A registration owes nothing exactly when every individual entry it carries is queued as a substitute **and** every team it carries is waitlisted; a registration carrying nothing on one of those axes SHALL be judged on the other alone, so that a team-only registration is judged on its teams. No presentation SHALL predict this answer before requesting the instructions.

A fencer holding a reservation SHALL be told either how to pay or why they cannot yet. Where instructions cannot be produced, the reason SHALL be shown in terms the fencer can act on, and the absence of instructions SHALL NOT be presented as an empty space. Three reasons SHALL be distinguished: that nothing is owed because every place requested is queued; that the tournament has recorded no bank account to pay into; and that the reservation is no longer awaiting payment. A reason the fencer cannot resolve SHALL say who will resolve it rather than instructing the fencer to act.

#### Scenario: Owner retrieves payment data
- **WHEN** the fencer who holds an unpaid reservation requests its payment instructions
- **THEN** the amount with its currency, IBAN, VS, message, expiry, and QR code are returned

#### Scenario: EUR pair present only when applicable
- **WHEN** payment instructions are requested on a CZK + EUR tournament and again on a CZK-only one
- **THEN** the first response carries the EUR total and EUR QR and the second omits both fields entirely

#### Scenario: Instructions match the original email after a configuration change
- **WHEN** prices or the recorded ratio change and the fencer then retrieves their payment instructions
- **THEN** the amounts and QR codes returned are the ones from their confirmation email

#### Scenario: Other accounts denied
- **WHEN** a different account requests those payment instructions
- **THEN** the request is rejected

#### Scenario: Team-only registration is judged on its teams
- **WHEN** a fencer holds a reservation carrying one team and no individual entries, and that team is not waitlisted
- **THEN** payment instructions are produced for it, and it is not treated as owing nothing

#### Scenario: Team-only waitlisted registration owes nothing
- **WHEN** a fencer holds a reservation carrying only teams and every one of them is waitlisted
- **THEN** the fencer is told nothing is owed yet, and no payment instructions and no empty space are shown

#### Scenario: Queued entries do not hide an owed team
- **WHEN** a reservation's individual entries are all queued as substitutes while one of its teams is not waitlisted
- **THEN** payment instructions are shown for the amount owed, and the fencer is not told that everything is queued

#### Scenario: Missing bank account explained, not blank
- **WHEN** a fencer holds a reservation on a tournament that has recorded no bank account
- **THEN** the fencer is told that payment details are not available and that the organizer will supply them, rather than being shown nothing

#### Scenario: Reservation settled while its instructions were open
- **WHEN** the fencer's reservation is matched to a payment between the page being opened and the instructions being requested
- **THEN** the fencer is told the reservation is no longer awaiting payment rather than being shown an empty panel
