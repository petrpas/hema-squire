## MODIFIED Requirements

### Requirement: In-app payment instructions retrieval
The system SHALL provide, to the owning account only, the payment data for its unpaid reservation: total amount with its currency, the bank account, variable symbol, payment message, reservation expiry, and the SPAYD QR code — plus the EUR total and a EUR-denominated QR code when the tournament prices in EUR as a second currency. Every amount SHALL be a stored total and every QR code SHALL encode the stored total of its own currency. The content SHALL be identical to the confirmation email's. The EUR fields SHALL be absent, not empty, when they do not apply.

The account SHALL be presented in the form the payer can use. Where the tournament's account is Czech, both its domestic form and its IBAN SHALL be presented, because a Czech payer enters the domestic form in their banking application and a foreign payer needs the IBAN. Where it is not Czech, the IBAN alone SHALL be presented and no domestic form SHALL be invented. The domestic form SHALL be derived from the stored account rather than stored a second time, and SHALL be carried as its own field rather than requiring the presenting surface to take an IBAN apart. No label SHALL name the account as an IBAN where a domestic form may be shown beside it.

Whether anything is owed SHALL be decided in one place, by the system that holds the registration, and SHALL NOT be decided a second time by the surface that displays the answer. A registration owes nothing exactly when every individual entry it carries is queued as a substitute **and** every team it carries is waitlisted; a registration carrying nothing on one of those axes SHALL be judged on the other alone, so that a team-only registration is judged on its teams. No presentation SHALL predict this answer before requesting the instructions.

A fencer holding a reservation SHALL be told either how to pay or why they cannot yet. Where instructions cannot be produced, the reason SHALL be shown in terms the fencer can act on, and the absence of instructions SHALL NOT be presented as an empty space. Three reasons SHALL be distinguished: that nothing is owed because every place requested is queued; that the tournament has recorded no bank account to pay into; and that the reservation is no longer awaiting payment. A reason the fencer cannot resolve SHALL say who will resolve it rather than instructing the fencer to act.

#### Scenario: Owner retrieves payment data
- **WHEN** the fencer who holds an unpaid reservation requests its payment instructions
- **THEN** the amount with its currency, the account, VS, message, expiry, and QR code are returned

#### Scenario: Czech account presented in both forms
- **WHEN** payment instructions are retrieved for a tournament whose account is Czech
- **THEN** both the domestic form and the IBAN are returned, each as its own field

#### Scenario: Foreign account presented as IBAN alone
- **WHEN** payment instructions are retrieved for a tournament banking outside Czechia
- **THEN** the IBAN is returned and no domestic form is

#### Scenario: Domestic form is derived, not stored
- **WHEN** the organizer saves the account as an IBAN and a fencer then retrieves payment instructions
- **THEN** the domestic form is present just as it would be had the organizer typed it, without having been stored

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

### Requirement: Confirmation email with QR payment
On registration the system SHALL send a localized confirmation email containing the registration summary — items with quantities and option values — the total amount with its currency, the bank account, the VS, and an SPAYD-format QR code encoding amount, currency, account, VS, and message. When the tournament prices in EUR as a second currency, the email SHALL additionally carry the EUR total and a second QR code denominated in EUR against the same account.

Each discipline entered SHALL be summarized by its name alone. The email SHALL NOT carry discipline slugs, which are not fencer-facing text (`discipline-identity`); where a tournament offers several disciplines classified alike, the name is what tells the fencer which one they entered.

Each QR code SHALL encode the stored total of its own currency, with the SPAYD currency field taken from that currency. No amount in either QR code SHALL be produced by conversion.

The account SHALL be stated in the same form as the in-app instructions: a Czech account as its domestic form together with its IBAN, any other account as its IBAN alone. The two surfaces SHALL NOT differ in how they present one account, because a fencer comparing the email against the page must not have to work out whether they are looking at the same thing. The QR code SHALL continue to encode the IBAN whatever form the email states, since the payment descriptor admits no other.

#### Scenario: QR payment
- **WHEN** the fencer scans the QR code from the confirmation email in a banking app
- **THEN** the prefilled payment carries the exact amount, currency, account, and VS needed for automatic matching

#### Scenario: Czech account stated in both forms
- **WHEN** a confirmation email goes out for a tournament whose account is Czech
- **THEN** it states the domestic form and the IBAN, while the QR code encodes the IBAN

#### Scenario: Email and page agree
- **WHEN** a fencer compares their confirmation email against the in-app payment instructions
- **THEN** the account is presented identically in both

#### Scenario: Disciplines summarized by name
- **WHEN** a fencer registers for two disciplines
- **THEN** the email lists each by its name alone, with no slug alongside it

#### Scenario: Tiers legible in the summary
- **WHEN** a fencer registers for one of two longsword disciplines that differ only by name
- **THEN** the email names the one they entered, and it is distinguishable from the one they did not

#### Scenario: EUR QR carries the stored EUR total
- **WHEN** a CZK + EUR tournament confirms a reservation totalling 1500 Kč and 60 €
- **THEN** the email carries a CZK QR for 1500 and a EUR QR for 60, each with its own currency in the SPAYD currency field

#### Scenario: No EUR block in single-currency mode
- **WHEN** a tournament prices in one currency
- **THEN** the email carries exactly one amount and one QR code

#### Scenario: Emailed amounts stable against configuration changes
- **WHEN** the organizer changes prices or the recorded ratio after a confirmation email was sent
- **THEN** the reminder and the in-app instructions for that reservation state the same amounts and carry the same QR codes as the original confirmation
