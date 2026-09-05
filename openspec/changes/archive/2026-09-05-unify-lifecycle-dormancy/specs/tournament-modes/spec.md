## MODIFIED Requirements

### Requirement: The payments feature suspends the payment machinery
The payments feature governs whether Squire handles payment processing for a tournament, not merely whether its settings are shown. WHEN it is off, the tournament SHALL:

- require no bank account to be published, whatever it charges, as fixed by `tournament-admin`;
- offer none of the payment and reservation parameters in Setup — the payment mode, the deposit, the payment window, the reminder day, the seating deadline, the bank account, the unpaid-list treatment and the variable-symbol statement;
- request no money at registration: no payment window opens, no due date is set, and no variable symbol is put to work;
- send no payment instructions, QR code, reminder, expiry notice or surcharge mail;
- expire no reservation for non-payment;
- **demote no registration to the substitute queue when the seating deadline passes**, because nothing was owed and a seat given without a price SHALL NOT be lost for want of payment;
- offer no Payments phase in the console, and reconcile no bank transactions.

Seating SHALL nevertheless still close on the deadline, placing later registrations in the queue rather than in seats: capacity is a property of the room and not of the payment feature. What the feature suspends is the demotion, not the closing.

Prices SHALL be unaffected. Disciplines and extra items SHALL keep their prices in the tournament's currency, discounts SHALL still apply, and the total SHALL still be computed and presented to the fencer — as a statement of what the tournament costs, settled outside Squire, rather than as a demand with a deadline.

Turning payments off SHALL retain every stored payment value: the bank account, the payment mode, the deposit, the window, credited payments, ingested transactions, payment events and issued variable symbols. Turning payments back on SHALL resume with all of them present. Registrations taken while payments were off carry no due date, so SHALL NOT expire retroactively when payments are turned on; they SHALL remain reserved until the organizer acts on them.

#### Scenario: Priced tournament publishes without an account
- **WHEN** an organizer publishes a tournament with priced disciplines, payments off and no bank account recorded
- **THEN** publication succeeds and no missing bank account is reported

#### Scenario: Registration takes no money
- **WHEN** a fencer registers for a payments-off tournament with a total of 1200 Kč
- **THEN** the registration is seated, no payment window opens, no due date is set, and the confirmation email states the total with no account block and no QR code

#### Scenario: Nothing expires
- **WHEN** the scheduler runs against a payments-off tournament holding registrations older than any payment window
- **THEN** no reservation expires, no reminder is sent, and no expiry notice is sent

#### Scenario: Nothing is demoted at the seating deadline
- **WHEN** the seating deadline passes on a payments-off tournament holding seated registrations
- **THEN** every registration keeps its seat, no capacity is freed, and no demotion is recorded

#### Scenario: Seating still closes
- **WHEN** a fencer registers for a payments-off tournament after its seating deadline has passed
- **THEN** the registration is placed in the substitute queue rather than seated

#### Scenario: No payments phase
- **WHEN** the organizer opens the console for a payments-off tournament
- **THEN** no Payments phase is offered and no transaction can be reconciled against the tournament

#### Scenario: Prices survive
- **WHEN** an organizer turns payments off on a tournament pricing in CZK with two discounts
- **THEN** the discipline and extra-item prices, the currency and both discounts are unchanged, and the registration form still shows the computed total

#### Scenario: Payments turned back on
- **WHEN** an organizer turns payments back on
- **THEN** the bank account, payment mode, deposit and payment window hold the values they held before, and the Payments phase is offered again

#### Scenario: Registrations taken while payments were off do not expire
- **WHEN** a tournament that took registrations with payments off turns payments on
- **THEN** those registrations remain reserved, none expires on account of a window that never opened, and the organizer decides what to do with them
