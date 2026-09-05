## ADDED Requirements

### Requirement: The payments setting suspends the payment machinery
Whether Squire handles payment processing for a tournament SHALL be a stored setting of that tournament, standing beside its mode (`tournament-mode`) as the second thing about a tournament that changes what Squire does rather than what it shows. It SHALL NOT be counted among the features fixed by `tournament-features`, every one of which governs Setup's controls alone; this one suspends machinery.

WHEN it is off, the tournament SHALL:

- require no bank account to be published, whatever it charges, as fixed by `tournament-admin`;
- offer none of the payment and reservation parameters in Setup — the payment mode, the deposit, the payment window, the reminder day, the seating deadline, the bank account, the unpaid-list treatment and the variable-symbol statement;
- request no money at registration: no payment window opens, no due date is set, and no variable symbol is put to work;
- send no payment instructions, QR code, reminder, expiry notice or surcharge mail;
- expire no reservation for non-payment;
- offer no Payments phase in the console, and reconcile no bank transactions.

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
