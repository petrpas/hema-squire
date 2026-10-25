## MODIFIED Requirements

### Requirement: Confirmation email with QR payment
On registration for a tournament whose payments feature is on, the system SHALL send a localized confirmation email containing the registration summary — items with quantities and option values — the total amount with its currency, the bank account, the VS, and an SPAYD-format QR code encoding amount, currency, account, VS, and message. When the tournament prices in EUR as a second currency, the email SHALL additionally carry the EUR total and a second QR code denominated in EUR against the same account.

**What the confirmation states about when money is due follows the tournament's payment mode**, and it SHALL NOT state a consequence the mode does not have:

- In `immediate` mode it SHALL state the date the payment window closes and that an unpaid reservation is released then.
- In `deposit` mode it SHALL state the deposit amount and the date the payment window closes, that the deposit holds the seat, and that the balance is due by the seating deadline, naming that date. It SHALL carry two QR codes per currency the tournament takes: one encoding the deposit and one encoding the full total. Each SHALL be labelled — in the body and in its attachment name — with what it pays and in which currency, so that a CZK + EUR tournament's four codes cannot be confused.
- In `reservation` mode it SHALL state that the full amount is due by the seating deadline, naming that date, and that a seat still unpaid on that day is moved to the substitute queue. It SHALL NOT state an expiry date and SHALL NOT state that the place is released.

**On a tournament whose payments feature is off, the confirmation email SHALL carry the summary and the total and nothing about paying it**: no bank account, no variable symbol, no QR code, no expiry date and no payment instruction. It SHALL confirm the registration rather than request money, and where the organizer has written registration instructions those SHALL be the tournament's own statement of how it is settled. No reminder, expiry notice, surcharge or payment-received mail SHALL be sent for such a tournament, because nothing generates one.

A registration placed wholly in the queue at submission SHALL, where the tournament lets paying substitutes take free places, carry instructions and a QR code for its claim instead of a total owed, with the statement of when the payment takes a place.

Each discipline entered SHALL be summarized by its name alone. The email SHALL NOT carry discipline slugs, which are not fencer-facing text (`discipline-identity`); where a tournament offers several disciplines classified alike, the name is what tells the fencer which one they entered.

Each total QR code SHALL encode the stored total of its own currency, and each deposit QR code the tournament's stored deposit amount of its own currency, with the SPAYD currency field taken from that currency. No amount in any QR code SHALL be produced by conversion.

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
