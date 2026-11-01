## MODIFIED Requirements

### Requirement: Confirmation email with QR payment
On registration for a tournament whose payments feature is on, the system SHALL send a localized confirmation email containing the registration summary — items with quantities and option values — the total amount with its currency, the bank account, the VS, and a QR code encoding amount, currency, account, VS, and message in the format its currency takes, as fixed by `payments` (**A payment code's format follows its currency**). When the tournament prices in EUR as a second currency, the email SHALL additionally carry the EUR total and a second QR code denominated in EUR against the same account.

**What the confirmation states about when money is due follows the tournament's payment mode**, and it SHALL NOT state a consequence the mode does not have:

- In `immediate` mode it SHALL state the date the payment window closes and that an unpaid reservation is released then.
- In `deposit` mode it SHALL state the deposit amount and the date the payment window closes, that the deposit holds the seat, and that the balance is due by the seating deadline, naming that date. It SHALL carry two QR codes per currency the tournament takes: one encoding the deposit and one encoding the full total. Each SHALL be labelled — in the body and in its attachment name — with what it pays and in which currency, so that a CZK + EUR tournament's four codes cannot be confused.
- In `reservation` mode it SHALL state that the full amount is due by the seating deadline, naming that date, and that a seat still unpaid on that day is moved to the substitute queue. It SHALL NOT state an expiry date and SHALL NOT state that the place is released.

**On a tournament whose payments feature is off, the confirmation email SHALL carry the summary and the total and nothing about paying it**: no bank account, no variable symbol, no QR code, no expiry date and no payment instruction. It SHALL confirm the registration rather than request money, and where the organizer has written registration instructions those SHALL be the tournament's own statement of how it is settled. No reminder, expiry notice, surcharge or payment-received mail SHALL be sent for such a tournament, because nothing generates one.

A registration placed wholly in the queue at submission SHALL, where the tournament lets paying substitutes take free places, carry instructions and a QR code for its claim instead of a total owed, with the statement of when the payment takes a place.

Each discipline entered SHALL be summarized by its name alone. The email SHALL NOT carry discipline slugs, which are not fencer-facing text (`discipline-identity`); where a tournament offers several disciplines classified alike, the name is what tells the fencer which one they entered.

Each total QR code SHALL encode the stored total of its own currency, and each deposit QR code the tournament's stored deposit amount of its own currency, with its currency taken from that currency. No amount in any QR code SHALL be produced by conversion.

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
- **THEN** the email carries a CZK QR for 1500 and a EUR QR for 60, the CZK one a SPAYD string with `CC:CZK` and the EUR one an EPC code for `EUR60`

#### Scenario: No EUR block in single-currency mode
- **WHEN** a tournament prices in one currency and its payment mode is not `deposit`
- **THEN** the email carries exactly one amount and one QR code

#### Scenario: Deposit-mode confirmation carries the deposit and the total
- **WHEN** a fencer registers on a CZK-only deposit-mode tournament with a 500 Kč deposit, a total of 1800 Kč and a seating deadline of 1 March
- **THEN** the email states the 500 Kč deposit and the date the window closes, the 1800 Kč total and that the balance is due by 1 March, and carries a QR code for 500 and one for 1800, each labelled

#### Scenario: Deposit-mode confirmation with EUR carries four labelled codes
- **WHEN** a fencer registers on a CZK + EUR deposit-mode tournament whose deposit is 500 Kč and 20 € and whose total is 1800 Kč and 72 €
- **THEN** the email carries four QR codes — deposit CZK, deposit EUR, total CZK, total EUR — each labelled with what it pays and its currency

#### Scenario: Reservation-mode confirmation states the seating deadline
- **WHEN** a fencer registers on a reservation-mode tournament whose seating deadline is 1 March
- **THEN** the email states that the total is due by 1 March and that an unpaid seat is moved to the substitute queue that day, and states no expiry date and no release of the place

#### Scenario: Payments-off confirmation carries no payment block
- **WHEN** a fencer registers for a payments-off tournament totalling 1200 Kč
- **THEN** the email states the summary and the total, and carries no account, no VS, no QR code and no expiry date

#### Scenario: No payment mail for a payments-off tournament
- **WHEN** the scheduler runs against a payments-off tournament holding registrations of every age
- **THEN** no reminder, expiry notice, surcharge or payment-received mail is sent

#### Scenario: Emailed amounts stable against configuration changes
- **WHEN** the organizer changes prices or the recorded ratio after a confirmation email was sent
- **THEN** the reminder and the in-app instructions for that reservation state the same amounts and carry the same QR codes as the original confirmation

#### Scenario: Queued at submission, told what to pay
- **WHEN** a fencer registers into a full discipline on a tournament that lets paying substitutes take places
- **THEN** the confirmation states they are queued and carries instructions and a QR code for their claim, with its condition

### Requirement: In-app payment instructions retrieval
The system SHALL provide, to the owning account only, the payment data for its unpaid reservation: total amount with its currency, the bank account, variable symbol, payment message, reservation expiry, and the QR code in the format its currency takes (`payments`) — plus the EUR total and a EUR-denominated QR code when the tournament prices in EUR as a second currency. Every amount SHALL be a stored total and every QR code SHALL encode the stored total of its own currency. The content SHALL be identical to the confirmation email's. The EUR fields SHALL be absent, not empty, when they do not apply.

The account SHALL be presented in the form the payer can use. Where the tournament's account is Czech, both its domestic form and its IBAN SHALL be presented, because a Czech payer enters the domestic form in their banking application and a foreign payer needs the IBAN. Where it is not Czech, the IBAN alone SHALL be presented and no domestic form SHALL be invented. The domestic form SHALL be derived from the stored account rather than stored a second time, and SHALL be carried as its own field rather than requiring the presenting surface to take an IBAN apart. No label SHALL name the account as an IBAN where a domestic form may be shown beside it.

Whether anything is owed SHALL be decided in one place, by the system that holds the registration, and SHALL NOT be decided a second time by the surface that displays the answer. A registration owes nothing exactly when every individual entry it carries is queued as a substitute **and** every team it carries is waitlisted; a registration carrying nothing on one of those axes SHALL be judged on the other alone, so that a team-only registration is judged on its teams. No presentation SHALL predict this answer before requesting the instructions.

A fencer holding a reservation SHALL be told either how to pay or why they cannot yet. Where instructions cannot be produced, the reason SHALL be shown in terms the fencer can act on, and the absence of instructions SHALL NOT be presented as an empty space. Where the tournament lets paying substitutes take free places, a registration wholly in the queue whose clocks run SHALL instead be given instructions for its **claim** (`seating-queue`, **A paying substitute takes free places**), in the same form as any instructions, stating that the payment takes the places waited for only if all of them are free when it is credited, and otherwise waits until they free or the organizer decides. Three reasons SHALL be distinguished: that nothing is owed because every place requested is queued, where the tournament does not let paying substitutes take places; that the tournament has recorded no bank account to pay into; and that the reservation is no longer awaiting payment. A reason the fencer cannot resolve SHALL say who will resolve it rather than instructing the fencer to act.

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

#### Scenario: Claim instructions for a waiting fencer
- **WHEN** a fencer wholly in the queue opens their registration on a tournament that lets paying substitutes take places
- **THEN** they are shown instructions for their claim with its condition, not told that nothing is owed
