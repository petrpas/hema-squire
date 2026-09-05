## MODIFIED Requirements

### Requirement: The payments setting suspends the payment machinery
Whether Squire handles payment processing for a tournament SHALL be a stored setting of that tournament, standing beside its mode (`tournament-mode`) as the second thing about a tournament that changes what Squire does rather than what it shows. It SHALL NOT be counted among the features fixed by `tournament-features`, every one of which governs Setup's controls alone; this one suspends machinery.

WHEN it is off, the tournament SHALL:

- require no bank account to be published, whatever it charges, as fixed by `tournament-admin`;
- offer none of the payment and reservation parameters in Setup — the payment mode, the deposit, the payment window, the reminder day, the seating deadline, the bank account, the unpaid-list treatment and the variable-symbol statement;
- request no money at registration: no payment window opens, no due date is set, and no variable symbol is put to work;
- send no payment instructions, QR code, reminder, expiry notice or surcharge mail;
- expire no reservation for non-payment;
- reconcile no bank transactions, poll no bank feed and accept no statement.

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
- **WHEN** the organizer opens the console for a tournament whose payments Squire does not handle
- **THEN** the Payments phase is offered holding whether each registration is settled and nothing else, and no transaction can be reconciled against the tournament

#### Scenario: Prices survive
- **WHEN** an organizer turns payments off on a tournament pricing in CZK with two discounts
- **THEN** the discipline and extra-item prices, the currency and both discounts are unchanged, and the registration form still shows the computed total

#### Scenario: Payments turned back on
- **WHEN** an organizer turns payments back on
- **THEN** the bank account, payment mode, deposit and payment window hold the values they held before, and the Payments phase is offered again

#### Scenario: Registrations taken while payments were off do not expire
- **WHEN** a tournament that took registrations with payments off turns payments on
- **THEN** those registrations remain reserved, none expires on account of a window that never opened, and the organizer decides what to do with them

## ADDED Requirements

### Requirement: An organizer may mark a registration settled by hand
WHERE Squire does not handle a tournament's payments, an organizer with console access SHALL be able to mark a registration paid, and to unmark it. This SHALL be the only way a registration reaches the paid state on such a tournament, and the organizer's own knowledge SHALL be its whole basis: they collected the money, and nothing else in the system saw it.

The mark SHALL record the verdict and **SHALL NOT record an amount**. The registration's state becomes paid; the counters holding what Squire has received SHALL be left exactly as they were. Those counters mean money that passed through Squire and were filled by reconciliation reading a bank statement; a figure written into them from a mark would be indistinguishable afterwards from one Squire observed.

A hand-settled registration SHALL therefore read as paid while what it is owed remains what it always was. Every surface presenting both SHALL be able to explain the difference, because a reader who takes the outstanding figure for an error would be misreading the one thing that is true: the fencer owes the organizer nothing, and Squire received nothing.

Marking SHALL be refused on a tournament whose payments Squire handles, with a stated reason. There the paid state follows from credited transactions alone, and a second writer would mean a statement imported later could contradict a person with neither knowing.

Both marking and unmarking SHALL be recorded as payment events naming the organizer who acted, so that a roster stating that someone has paid can always state who said so and when.

The mark SHALL answer a yes-or-no question and SHALL NOT express partial settlement. A tournament that needs amounts tracked wants Squire handling its payments.

#### Scenario: The organizer marks a fencer settled
- **WHEN** the organizer of a tournament that handles its own payments marks a registration paid
- **THEN** the registration's state becomes paid, what Squire has received stays at nothing, and the action is recorded against the organizer

#### Scenario: Unmarking returns it
- **WHEN** the organizer unmarks a registration they had marked
- **THEN** it is no longer paid, and both the marking and the unmarking stand in the record

#### Scenario: Refused where Squire collects
- **WHEN** an organizer attempts to mark a registration paid on a tournament whose payments Squire handles
- **THEN** the attempt is refused with a stated reason and the registration is unchanged

#### Scenario: What Squire received is not invented
- **WHEN** a hand-settled registration is read
- **THEN** the amount Squire has received against it is nothing, and what the registration is owed is unchanged

#### Scenario: Switching afterwards is not specially handled
- **WHEN** a tournament holding hand-settled registrations is switched to having Squire handle the payments
- **THEN** the switch applies as any other does, the marks are neither cleared nor counted, and the registrations keep the state a person gave them
